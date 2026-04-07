"""Common definitions and implementations for LLM handling."""

import re
import json
import logging
import dataclasses
import dacite
import asyncio
import pathlib
from typing import (
    TypeVar,
    Dict,
    Any,
    Sequence,
    Callable,
    Type,
    Union,
    cast,
)
import google.genai as genai
from google.genai import types as genai_types
import pydantic_ai
import pydantic_ai.models
import pydantic_ai.models.google
import pydantic_ai.providers.google
import pydantic_ai.messages
import nest_asyncio

from rxllmproc.core.infra import utilities
from rxllmproc.core.infra import containers
from rxllmproc.core.infra import cache

_O = TypeVar('_O')

ToolList = Sequence[pydantic_ai.Tool | Callable[..., Any]]


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


class LlmBase:
    """Base class for all LLM models."""

    def __init__(
        self,
        preproc: Callable[[Any], Any] | None = None,
        functions: ToolList | None = None,
        cache_instance: cache.CacheInterface | None = None,
    ) -> None:
        """Create an instance.

        Args:
            preproc: General preproc function, e.g. to trim long inputs.
            functions: Functions that the LLM will have access to.
            cache_instance: Optional cache instance.
        """
        self.preproc: Callable[[Any], Any] = preproc or self._default_preproc
        self.functions: Dict[
            str, Union[pydantic_ai.Tool, Callable[..., Any]]
        ] = {}
        self.cache_instance = cache_instance or cache.NoCache()
        for func in functions or []:
            self.add_function(func)

    def add_function(
        self, func: Union[pydantic_ai.Tool, Callable[..., Any]]
    ) -> None:
        """Add a function to the LLM."""
        if isinstance(func, pydantic_ai.Tool):
            name = func.name
        else:
            name = getattr(func, '__name__', str(id(func)))

        self.functions[name] = func

    def _default_preproc(self, arg: Any) -> Any:
        """Preprocess arguments, default function.

        Limits number of text characters for strings.
        """
        if isinstance(arg, str):
            return arg[:20000]
        return arg

    def query(
        self,
        *prompt_parts: Any,
        output_format: str | None = None,
        schema: Any = None,
    ) -> str:
        """Run a text query."""
        # Use caching if enabled
        key = f'{self.__class__.__name__}_query({self.model_id})'

        def _run_query(*args: Any, **kwargs: Any):
            func = utilities.with_backoff_retry(
                self._query, GeneratorRetryError
            )
            return func(*args, **kwargs)

        return cache.cached_call(
            self.cache_instance,
            key,
            _run_query,
            *prompt_parts,
            output_format=output_format,
            schema=schema,
        )

    @property
    def model_id(self) -> str:
        """Get the model ID for caching."""
        return "unknown"

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


MODEL_ALIASES = {
    'gemini': 'google-gla:gemini-2.5-flash-lite',
    'openai': 'openai:gpt-4o',
}


class AiWrapper(LlmBase):
    """Wrapper around Pydantic AI."""

    def __init__(
        self,
        model: str | pydantic_ai.models.Model = 'gemini',
        preproc: Callable[[Any], Any] | None = None,
        functions: ToolList | None = None,
        system_prompt: str | None = None,
        cache_instance: cache.CacheInterface | None = None,
        google_client: genai.Client | None = None,
        **kwargs: Any,
    ) -> None:
        """Create an instance.

        Args:
            model: The model to use (name string, alias or Model instance).
            preproc: General preproc function.
            functions: Functions that the LLM will have access to.
            system_prompt: Optional system prompt.
            cache_instance: Optional cache instance.
            google_client: Optional Gemini client.
            **kwargs: Extra arguments, currently ignored.
        """
        super().__init__(preproc, functions, cache_instance)

        # Resolve alias
        if isinstance(model, str):
            model = MODEL_ALIASES.get(model, model)
            self.model: pydantic_ai.models.Model = (
                pydantic_ai.models.infer_model(model)
            )
        else:
            self.model = model

        self.system_prompt = system_prompt
        self.google_client = google_client or genai.Client()

    @property
    def model_id(self) -> str:
        """Get the model ID for caching."""
        return self.model.model_id

    def _upload_file_part(
        self, filename: str, mime_type: str | None = None
    ) -> genai_types.Part:
        """Upload a file and return a Gemini Part.

        Args:
            filename: The path to the file to upload.
            mime_type: Optional MIME type.

        Returns:
            A Gemini Part object containing the file data.
        """
        if not self.google_client:
            raise GeneratorError("Google client not initialized", self)

        uploaded_file = self.google_client.files.upload(file=filename)
        return genai_types.Part(
            file_data=genai_types.FileData(
                mime_type=mime_type or uploaded_file.mime_type,
                file_uri=uploaded_file.uri,
            )
        )

    def _query(
        self,
        *prompt_parts: Any,
        output_format: str | None = None,
        schema: Any = None,
    ) -> str:
        """Generate a response from the supplied prompt."""
        # Handle complex parts (files etc)
        is_gemini = self.model_id.startswith('google-gla:')

        pydantic_parts: list[Union[str, pydantic_ai.messages.UploadedFile]] = []
        for p in prompt_parts:
            if isinstance(p, (str, int, float, bool)):
                pydantic_parts.append(str(self.preproc(p)))
            elif isinstance(p, (containers.LocalFileContainer, pathlib.Path)):
                file_path = (
                    str(p) if isinstance(p, pathlib.Path) else str(p.filename)
                )

                if self.google_client and is_gemini:
                    # Upload and use UploadedFile part
                    uploaded = self.google_client.files.upload(file=file_path)
                    pydantic_parts.append(
                        pydantic_ai.messages.UploadedFile(
                            file_id=uploaded.uri
                            or '',  # For Gemini, uri is the ID
                            provider_name='google-gla',
                            media_type=uploaded.mime_type,
                        )
                    )
                else:
                    pydantic_parts.append(f"[Local File: {file_path}]")
            elif isinstance(p, containers.DriveFileContainer):
                if is_gemini:
                    pydantic_parts.append(
                        pydantic_ai.messages.UploadedFile(
                            file_id=p.url() or '',
                            provider_name='google-gla',
                            media_type=p.mime_type(),
                        )
                    )
                else:
                    pydantic_parts.append(f"[GDrive File: {p.filename}]")
            elif isinstance(p, genai_types.File):
                if is_gemini:
                    pydantic_parts.append(
                        pydantic_ai.messages.UploadedFile(
                            file_id=p.uri or '',
                            provider_name='google-gla',
                            media_type=p.mime_type,
                        )
                    )
                else:
                    pydantic_parts.append(f"[Gemini File: {p.display_name}]")
            else:
                pydantic_parts.append(str(self.preproc(p)))

        # Join text parts if possible
        user_prompt: Union[str, list[Union[str, pydantic_ai.messages.UploadedFile]]]
        if all(isinstance(p, str) for p in pydantic_parts):
            user_prompt = " ".join(cast(list[str], pydantic_parts))
        else:
            user_prompt = pydantic_parts

        # result_type for pydantic-ai
        result_type: Type[Any] = str
        if self.functions:
            # If we have functions, we usually want to disable structured output
            # at the agent level to avoid conflicts with tool calling
            result_type = str
        elif schema:
            # If it's a dict (JSON schema), Pydantic AI might not directly support it as result_type
            # unless it's a Pydantic model.
            result_type = str
        elif output_format == 'json':
            result_type = Dict[str, Any]

        model = self.model
        if isinstance(model, str) and model.startswith('google-gla:'):
            model_name = model[len('google-gla:') :]
            provider = 'google-gla'
            if self.google_client:
                provider = pydantic_ai.providers.google.GoogleProvider(
                    client=self.google_client
                )
            model = pydantic_ai.models.google.GoogleModel(
                model_name, provider=provider
            )

        # Agent creation with tools from self.functions
        agent = pydantic_ai.Agent(
            model=model,
            output_type=result_type,
            system_prompt=self.system_prompt or (),
            tools=list(self.functions.values()),
        )

        # Handle async execution in a sync environment
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # If a loop is already running, apply nest_asyncio and use run_until_complete
        if loop.is_running():
            nest_asyncio.apply()
            result = loop.run_until_complete(agent.run(user_prompt))
        else:
            result = asyncio.run(agent.run(user_prompt))

        # Check for successful generation
        # Pydantic AI result doesn't directly expose finish reason in a generic way
        # across all models, but for Gemini it might be in provider_details or similar.
        # For now, let's just use the result and hope for the best, or check for specific
        # failure conditions if we can extract them.

        if output_format == 'json' and not isinstance(result.output, str):
            return json.dumps(result.output)

        return str(result.output)


def create_model(name: str | None = None, **kwargs: Any) -> LlmBase:
    """Create an LLM model instance.

    Args:
        name: The model name or alias.
        **kwargs: Arguments for AiWrapper.
    """
    return AiWrapper(model=name or 'gemini', **kwargs)
