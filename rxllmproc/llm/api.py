"""Gemini/VertexAI interface wrapper."""

from typing import Callable, Any, Optional
import logging
import pathlib
import threading

from google.genai import client as genai_client
from google.genai import types as genai_types
from google.genai import errors as genai_errors
from google.api_core import exceptions as google_exceptions

from rxllmproc.core.infra import containers
from rxllmproc.core.infra import cache
from rxllmproc.llm import commons


def _convert_function_type(tp: str) -> genai_types.Type:
    if tp == 'string':
        return genai_types.Type.STRING
    if tp == 'integer':
        return genai_types.Type.INTEGER
    if tp == 'number':
        return genai_types.Type.NUMBER
    if tp == 'boolean':
        return genai_types.Type.BOOLEAN
    raise ValueError(f'Unknown function type: {tp}')


class Gemini(commons.LlmBase):
    """Wrapper around Gemini/VertexAI API."""

    def _convert_function(
        self, func: commons.LlmFunction
    ) -> genai_types.FunctionDeclaration:
        """Convert a `GeminiFunction` object to Gemini function declaration."""
        properties = {
            name: genai_types.Schema(
                type=_convert_function_type(param_def.get('type')),
                description=param_def.get('description'),
            )
            for name, param_def in func.parameters.items()
        }
        params = genai_types.Schema(
            type=genai_types.Type.OBJECT, properties=properties
        )
        return genai_types.FunctionDeclaration(
            name=func.name,
            description=func.description,
            parameters=params,
        )

    def __init__(
        self,
        api_key: str | None = None,
        client: genai_client.Client | None = None,
        preproc: Callable[[Any], Any] | None = None,
        functions: Optional[list[commons.LlmFunction]] = None,
        use_search: bool = False,
        model_name: str = 'gemini-1.5-flash',
        cache_instance: cache.CacheInterface | None = None,
    ) -> None:
        """Create an instance.

        Args:
            api_key: The API key for the Gemini API.
            client: Optionally provide service instance (mainly for testing.)
                Note: If provided, this instance is shared across threads and
                is not thread-safe.
            preproc: General preproc function, e.g. to trim long inputs.
            functions: Functions that Gemini will have access to.
            use_search: Enable Google Search as a tool.
            model_name: Gemini model name, see also
                https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models
            cache_instance: The cache instance to use.
        """
        super().__init__(preproc, functions)
        self.model_name = model_name
        self.cache_instance = cache_instance or cache.NoCache()

        safety_settings = [
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ]
        self._client_arg = client
        self._api_key = api_key
        self._local = threading.local()
        self._use_search = use_search
        self._safety_settings = safety_settings

        logging.debug('+- Gemini safety_settings: %s', repr(safety_settings))

    def _generate_function_responses(
        self, calls: list[genai_types.FunctionCall]
    ) -> list[genai_types.Content]:
        """Execute functions requested by Gemini and return the result."""
        result: list[genai_types.Content] = []
        for the_call in calls:
            logging.debug('About to execute function call: %s', repr(the_call))
            if the_call.name is None or the_call.name not in self.functions:
                raise ValueError(
                    f'Gemini requested call to unknown function {the_call.name}'
                )
            func_obj = self.functions[
                the_call.name
            ]  # pyright: ignore[reportGeneralTypeIssues]
            args = dict(
                the_call.args or {}
            )  # pyright: ignore[reportGeneralTypeIssues]
            logging.info(
                'Calling Gemini Function %s with args %s',
                the_call.name,
                repr(args),
            )
            response = func_obj(**args)
            result.append(
                genai_types.Content(
                    role='function',
                    parts=[
                        genai_types.Part(
                            function_response=genai_types.FunctionResponse(
                                name=the_call.name, response=response
                            )
                        )
                    ],
                )
            )
        return result

    def _upload_file_part(
        self, filename: str, mime_type: str | None = None
    ) -> genai_types.Part:
        uploaded_file = self.client.files.upload(file=filename)
        return genai_types.Part(
            file_data=genai_types.FileData(
                mime_type=mime_type or uploaded_file.mime_type,
                file_uri=uploaded_file.uri,
            )
        )

    def _convert_prompt_parts(
        self, *prompt_parts: Any
    ) -> list[genai_types.Part]:
        """Convert prompt parts to Gemini Parts."""
        parts: list[genai_types.Part] = []
        for part in prompt_parts:
            if isinstance(part, str):
                parts.append(genai_types.Part(text=self.preproc(part)))
            elif isinstance(part, containers.LocalFileContainer):
                parts.append(
                    self._upload_file_part(part.filename, part.mime_type())
                )
            elif isinstance(part, containers.DriveFileContainer):
                file_data = genai_types.FileData(
                    mime_type=part.mime_type(), file_uri=part.url()
                )
                parts.append(genai_types.Part(file_data=file_data))
            elif isinstance(part, pathlib.Path):
                parts.append(self._upload_file_part(str(part)))
            elif isinstance(part, genai_types.File):
                file_data = genai_types.FileData(
                    mime_type=part.mime_type, file_uri=part.uri
                )
                parts.append(genai_types.Part(file_data=file_data))
            else:
                raise TypeError(f'Unsupported prompt part type: {type(part)}')
        return parts

    def _handle_function_calls(
        self, resp_content: genai_types.Content
    ) -> list[genai_types.Content]:
        """Extract and execute function calls from response content."""
        pending_function_calls = [
            part.function_call
            for part in (resp_content.parts or [])
            if part.function_call
        ]
        return self._generate_function_responses(pending_function_calls)

    def _check_candidate(
        self,
        resp: genai_types.GenerateContentResponse,
        candidate: genai_types.Candidate,
        prompt_parts: tuple[Any, ...],
    ) -> None:
        """Check if the candidate is valid and finished successfully."""
        finish_reason = candidate.finish_reason
        if finish_reason is None:
            raise commons.GeneratorPromptError(
                f'No finish reason set by Gemini, {resp!r}',
                self,
                prompt_parts,
            )

        if finish_reason != genai_types.FinishReason.STOP:
            finish_message = candidate.finish_message
            logging.info(
                'Failed Gemini generation. Context: Response: %s',
                repr(resp),
            )
            raise commons.GeneratorPromptError(
                'Failed to generate response. Reason:'
                + f' {finish_reason.name}, {finish_message}',
                self,
                prompt_parts,
            )

    def _query(
        self,
        *prompt_parts: Any,
        output_format: str | None = None,
        schema: Any = None,
    ) -> str:
        return cache.cached_call(
            self.cache_instance,
            f'gemini_query({self.model_name})',
            self._execute_query,
            *prompt_parts,
            output_format=output_format,
            schema=schema,
        )

    def _execute_query(
        self,
        *prompt_parts: Any,
        output_format: str | None = None,
        schema: Any = None,
    ) -> str:
        """Generate a response from the supplied prompt."""
        logging.debug(
            'Gemini model %s, query input: %s',
            self.model_name,
            repr(prompt_parts),
        )

        tools: genai_types.ToolListUnion = []
        if self.functions:
            tools.append(
                genai_types.Tool(
                    function_declarations=[
                        self._convert_function(func)
                        for func in self.functions.values()
                    ],
                )
            )
        if self._use_search:
            tools.append(
                genai_types.Tool(google_search=genai_types.GoogleSearch())
            )

        # https://github.com/google-gemini/deprecated-generative-ai-python/issues/515
        response_mime_type = (
            'application/json' if output_format == 'json' else None
        )
        if tools and response_mime_type == 'application/json':
            logging.warning(
                'Disabling JSON response mode because tools are present.'
            )
            response_mime_type = None
            if schema:
                schema = None

        config = genai_types.GenerateContentConfig(
            tools=tools,
            safety_settings=self._safety_settings,
            response_mime_type=response_mime_type,
            response_schema=schema,
        )

        content_args: list[genai_types.Content] = [
            genai_types.Content(
                role='user', parts=self._convert_prompt_parts(*prompt_parts)
            )
        ]
        try:
            function_call_content: list[genai_types.Content] = []
            while True:
                contents = list(content_args)
                contents.extend(function_call_content)

                try:
                    logging.debug('Gemini LLM request: %s', repr(contents))
                    resp: genai_types.GenerateContentResponse = (
                        self.client.models.generate_content(  # type: ignore
                            model=self.model_name,
                            contents=contents,
                            config=config,
                        )
                    )
                except google_exceptions.TooManyRequests as exc:
                    raise commons.GeneratorRetryError(
                        'Too many requests', self
                    ) from exc
                except genai_errors.ClientError as exc:
                    raise commons.GeneratorPromptError(
                        'Client Error (e.g. Bad function)',
                        self,
                        prompt=prompt_parts,
                        config=config,
                    ) from exc
                except genai_errors.ServerError as exc:
                    raise commons.GeneratorRetryError(
                        'Server Error (e.g. Overloaded)', self
                    ) from exc

                if not resp.candidates:
                    raise commons.GeneratorPromptError(
                        f'No response generated from Gemini, {resp!r}',
                        self,
                        prompt_parts,
                    )
                resp_candidate = resp.candidates[0]
                self._check_candidate(resp, resp_candidate, prompt_parts)

                resp_content = resp_candidate.content
                if resp_content is None:
                    raise commons.GeneratorPromptError(
                        f'No content set by Gemini, {resp_content!r}',
                        self,
                        prompt_parts,
                    )

                new_function_responses = self._handle_function_calls(
                    resp_content
                )
                function_call_content.extend(new_function_responses)

                if new_function_responses:
                    continue

                resp_text = resp.text
                if resp_text is None:
                    raise commons.GeneratorPromptError(
                        f'No response text set by Gemini, {resp!r}',
                        self,
                        prompt_parts,
                    )

                logging.debug('Gemini query result: %s', resp_text)

                return resp_text
                # Load Gemini Pro Vision
                # gemini_pro_vision_model =
                #         GenerativeModel("gemini-pro-vision")
        except Exception:
            logging.exception(
                'Exception raised on config: %s',
                repr(config),
            )
            logging.exception(
                'Exception raised on message: %s',
                repr(prompt_parts),
            )
            raise

    @classmethod
    def register(cls, registry: commons.LlmModelFactory):
        """Register the class with the LLM registry."""

        def _create_model_maker(
            model_name: str, **kwargs: Any
        ) -> Callable[..., commons.LlmBase]:
            """Create a gemini model with a specific model name.

            Passed as factory function to the LLM registry.
            """

            def _func(**factory_kwargs: Any) -> commons.LlmBase:
                valid_params = {
                    'api_key',
                    'client',
                    'preproc',
                    'functions',
                    'use_search',
                    'cache_instance',
                }

                all_kwargs = kwargs.copy()
                all_kwargs.update(factory_kwargs)

                filtered_kwargs = {
                    k: v for k, v in all_kwargs.items() if k in valid_params
                }
                return cls(model_name=model_name, **filtered_kwargs)

            return _func

        if 'gemini' in registry.list():
            return
        registry.set(
            'gemini',
            _create_model_maker('gemini-2.5-flash'),
        )
        registry.set(
            'gemini-lite',
            _create_model_maker('gemini-2.5-flash-lite'),
        )
        registry.set(
            'gemini_pro',
            _create_model_maker('gemini-2.5-pro'),
        )
        if not registry.default_model:
            registry.default_model = 'gemini'

    @property
    def client(self) -> genai_client.Client:
        """Get the thread-local client instance."""
        if self._client_arg:
            return self._client_arg
        if not hasattr(self._local, 'client'):
            logging.debug('Creating Gemini client for thread')
            self._local.client = genai_client.Client(
                api_key=self._api_key,
            )
        return self._local.client


Gemini.register(commons.LlmModelFactory.shared_instance())
