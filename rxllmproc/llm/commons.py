"""Common definitions and implementations for LLM handling."""

from typing import (
    TypeVar,
    Dict,
    Literal,
    Protocol,
    TypedDict,
    Any,
    List,
    Callable,
    Optional,
)
import re
import json
import logging
import dataclasses
import dacite
from rxllmproc.core.infra import utilities

_O = TypeVar('_O')


class GeneratorError(Exception):
    """Raised when the LLM generation fails."""

    def __init__(
        self,
        msg: str,
        source: 'LlmBase| None',
        prompt: Any = None,
        config: Any = None,
        result: Any = None,
    ) -> None:
        """Create an instance with context."""
        super().__init__(msg)

        self.source = source
        self.prompt = prompt
        self.result = result

    def __repr__(self) -> str:
        """Build representation string."""
        return (
            f'{self.__class__.__name__}({str(self)}, source={self.source!r}, '
            f'prompt={self.prompt!r}, result={self.result!r})'
        )


class GeneratorRetryError(GeneratorError):
    """Raised when retry is ok as the error may be transient."""


class GeneratorPromptError(GeneratorError):
    """Raised when there was an issue with the prompt."""


class GeneratorFormatError(GeneratorError):
    """Raised when the output format is unexcpected."""


class FunctionArgDeclaration(TypedDict):
    """Definition of a function arg."""

    type: Literal['string', 'number', 'boolean']
    description: str


class FunctionSignatureDeclaration(TypedDict):
    """Definition of the function, as used by an LLM."""

    type: Literal['object']
    properties: Dict[str, FunctionArgDeclaration]


class LlmFunction(Protocol):
    """Specification for a Function to be used for an LLM."""

    @property
    def name(self) -> str:
        """Get the name of the function."""
        ...

    @property
    def description(self) -> str:
        """Get the function description."""
        ...

    @property
    def parameters(self) -> Dict[str, FunctionArgDeclaration]:
        """Get the function parameters."""
        ...

    def __call__(self, **kwargs: Any) -> Dict[str, Any]:
        """Produce the result to feed back to an LLM."""
        ...


class BasicLlmFunction(LlmFunction):
    """Attribute-based function implementation."""

    def __init__(
        self,
        name: str,
        description: str,
        callback: Callable[..., Dict[str, Any]],
        **parameters: FunctionArgDeclaration,
    ) -> None:
        """Create an instance.

        Args:
            name: Function name.
            description: function description.
            callback: Callable to produce the function result.
            parameters: Definition of function arguments.
        """
        self._name = name
        self._description = description
        self.callback = callback
        self._parameters: Dict[str, FunctionArgDeclaration] = parameters

    @property
    def name(self) -> str:
        """Get the name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the description."""
        return self._description

    @property
    def parameters(self) -> Dict[str, FunctionArgDeclaration]:
        """Get the parameters."""
        return self._parameters

    def __call__(self, **kwargs: Any) -> Dict[str, Any]:
        """Produce the result."""
        return self.callback(**kwargs)


class LlmBase:
    """Base class for all LLM models."""

    def __init__(
        self,
        preproc: Callable[[Any], Any] | None = None,
        functions: Optional[List[LlmFunction]] = None,
    ) -> None:
        """Create an instance.

        Args:
            preproc: General preproc function, e.g. to trim long inputs.
            functions: Functions that the LLM will have access to.
        """
        self.preproc: Callable[[Any], Any] = preproc or self._default_preproc
        self.functions = {func.name: func for func in functions or []}

    def add_function(self, func: LlmFunction) -> None:
        """Add a function to the LLM."""
        if func.name in self.functions:
            logging.debug('Function %s already exists. Overwriting.', func.name)
        self.functions[func.name] = func

    def _default_preproc(self, arg: Any) -> Any:
        """Preprocess arguments, default function.

        Limits number of text characters.
        """
        return arg[:20000]

    def query(
        self,
        *prompt_parts: Any,
        output_format: str | None = None,
        schema: Any = None,
    ) -> str:
        """Run a text query."""
        func = utilities.with_backoff_retry(self._query, GeneratorRetryError)
        return func(*prompt_parts, output_format=output_format, schema=schema)

    def _query(
        self,
        *prompt_parts: Any,
        output_format: str | None = None,
        schema: Any = None,
    ) -> str:
        """Internal function to generate a response.

        Abstract. To be overridden when inheriting.
        """
        raise NotImplementedError()

    _JSON_RESULT_REGEXES = [
        re.compile(r'^```(?:[ ]*json)?\s*\n(.*)\n```\s*$', re.S),
        re.compile(r'^\s*(["\{\[0-9].*["\}\]0-9])\s*$', re.S),
    ]

    def _decode_json(self, result: str) -> Any:
        # Handle tripple quotes
        try:
            for regex in self._JSON_RESULT_REGEXES:
                match = regex.fullmatch(result)
                if match is not None:
                    return json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise GeneratorFormatError(
                'Could not parse result.', self, result=result
            ) from exc

        raise GeneratorFormatError(
            'JSON is not in known format', self, result=result
        )

    _FIX_JSON_TEMPLATE = '''
    Fix the following JSON string while keeping structure and content.
    It is important that the result is a single, valid JSON string.
    Only reply with the fixed JSON, nothing else.

    The JSON string:
    ----------------------------
    {}
    ----------------------------
    '''

    def query_json(self, *args: str, schema: Any = None) -> Any:
        """Generate a JSON-like structure from the prompt."""
        result = self.query(*args, output_format='json', schema=schema)
        try:
            return self._decode_json(
                result
            )  # pyright: ignore[reportGeneralTypeIssues]
        except GeneratorError:
            logging.info(
                'Returned JSON not decodable. Trying to fix: %s', repr(result)
            )

        fixed_result = self.query(self._FIX_JSON_TEMPLATE.format(result))
        try:
            return self._decode_json(fixed_result)
        except GeneratorError as exc:
            logging.exception('Could not fix JSON: %s', repr(fixed_result))
            exc.prompt = args
            raise

    # Prompt fragment to instruct LLM to return JSON of specific format.
    _JSON_OBJECT_INSTRUCTIONS = '''
Always return only valid JSON using double quotes.
Make sure to structure the response as shown in this sample:
```
{sample_as_str}
```
'''

    def query_json_object(self, result_type: type[_O], *args: str) -> _O:
        """Generate a dataclass instance from a propmt.

        Args:
            result_type: Dataclass to deserialize into.
            args: Prompt fragments.
        """
        schema = None

        # Support for Pydantic V2
        if hasattr(result_type, 'model_json_schema'):
            schema = getattr(result_type, 'model_json_schema')(
                mode='serialization'
            )
        elif dataclasses.is_dataclass(result_type):
            schema = utilities.build_json_schema(result_type)

        sample_asdict = utilities.build_sample(result_type)
        sample_as_str = json.dumps(sample_asdict)

        json_instructions = self._JSON_OBJECT_INSTRUCTIONS.format(
            sample_as_str=sample_as_str
        )
        if schema is None:
            as_dict = self.query_json(*args, json_instructions)
        else:
            logging.debug('JSON schema: %s', json.dumps(schema, indent=2))
            as_dict = self.query_json(*args, json_instructions, schema=schema)
            if hasattr(result_type, 'model_validate'):
                return getattr(result_type, 'model_validate')(as_dict)

        try:
            return dacite.from_dict(result_type, as_dict)
        except (dacite.DaciteError, TypeError) as exc:
            logging.exception('Original data: %s', repr(as_dict))
            logging.exception('JSON instructions: %s', repr(json_instructions))
            logging.exception('LLM request: %s', repr(args))
            raise GeneratorError(
                'Failed to create object with Dacite',
                self,
                (args, json_instructions, result_type),
                as_dict,
            ) from exc


FactoryType = Callable[..., LlmBase]


class LlmModelFactory:
    """Factory for LLM models.

    Allows to create model instances using factory functions.
    """

    _shared_instance: 'LlmModelFactory| None' = None

    @classmethod
    def shared_instance(cls) -> 'LlmModelFactory':
        """Create a shared instance."""
        if not cls._shared_instance:
            cls._shared_instance = LlmModelFactory()
        return cls._shared_instance

    def __init__(self) -> None:
        """Create an instance."""
        self._registry: Dict[str, FactoryType] = {}
        self.default_model: str | None = None

    def list(self) -> List[str]:
        """List all registered."""
        return list(self._registry.keys())

    def set(self, name: str, factory: FactoryType):
        """Set the factory function for a model named `name`."""
        self._registry[name] = factory

    def create(self, name: str | None = None, **kwargs: Any) -> LlmBase:
        """Create a model instance."""
        if name is None:
            name = self.default_model
        if name not in self._registry:
            raise KeyError(f'No model wrapper named {name} can be created')

        return self._registry[name](**kwargs)
