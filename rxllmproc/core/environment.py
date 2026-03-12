"""Shared environment for reactive operators."""

import logging
from typing import Optional, List, Any, Callable, TypedDict, TypeVar
from typing_extensions import Unpack

import reactivex as rx
from reactivex import operators as ops

from rxllmproc.core import auth
from rxllmproc.gmail import api as gmail_api
from rxllmproc.calendar import api as calendar_api
from rxllmproc.llm import commons as llm_commons
from rxllmproc.tasks import api as tasks_wrapper
from rxllmproc.tasks.api import ManagedTasks
from rxllmproc.docs import (
    docs_model,
    api as docs_wrapper,
)
from rxllmproc.core.infra import cache, collector

_T = TypeVar("_T")


def shared() -> 'Environment':
    """Get the shared instance."""
    return Environment.shared()


class EnvArgs(TypedDict, total=False):
    """Arguments for the Environment."""

    creds_factory: auth.CredentialsFactory | None
    creds: auth.Credentials | None
    cache_instance: cache.CacheInterface | None
    llm_factory: llm_commons.LlmModelFactory
    llm_factory_args: dict[str, Any]
    model_name: str
    functions: List[llm_commons.LlmFunction]
    template_globals: dict[str, Any]
    template_filters: dict[str, Callable[..., Any]]
    collector: collector.Collector
    sample_interleave: int
    error_handler: Callable[[Exception], None]


def log_only_error_handler(e: Exception):
    """Log only error handler."""
    logging.error("Environment error", exc_info=e)


class Environment:
    """Singleton environment to hold shared resources."""

    _instance: Optional['Environment'] = None

    @classmethod
    def shared(cls) -> 'Environment':
        """Get the shared instance."""
        if cls._instance is None:
            raise ValueError("Environment not initialized")
        return cls._instance

    def _clear_wrappers(self):
        """Clear all wrappers."""
        self._gmail_wrapper = None
        self._calendar_wrapper = None
        self._tasks_wrapper = None
        self._managed_tasks = None
        self._docs_wrapper = None

    def __init__(
        self,
        parent: 'Environment | None' = None,
        **kwargs: Unpack[EnvArgs],
    ):
        """Initialize the environment, using parent as default, if available."""
        # Initialize all members.
        self._outer_environment: Optional['Environment'] = None

        self._gmail_wrapper: Optional[gmail_api.GMailWrap] = None
        self._calendar_wrapper: Optional[calendar_api.CalendarWrap] = None
        self._tasks_wrapper: Optional[tasks_wrapper.TasksWrap] = None
        self._managed_tasks: Optional[ManagedTasks] = None
        self._docs_wrapper: Optional[docs_wrapper.DocsWrapper] = None

        # First, set hard coded defaults or shared factories.
        self._settings: EnvArgs = {
            'creds_factory': auth.CredentialsFactory.shared_instance(),
            'cache_instance': cache.NoCache(),
            'llm_factory': llm_commons.LlmModelFactory.shared_instance(),
            'model_name': 'gemini',
            'functions': [],
            'template_globals': {},
            'template_filters': {},
            'creds': None,
            'llm_factory_args': {},
            'collector': collector.NoCollector(),
            'sample_interleave': 0,
            'error_handler': log_only_error_handler,
        }

        # Second: If an env is set, transfer from there.
        if Environment._instance:
            self._settings.update(Environment._instance._settings)

        # Third: Apply parent settings.
        if parent and parent._settings:
            self._settings.update(parent._settings)

        # Last not least, apply passed args.
        if kwargs:
            self._settings.update(kwargs)

        # Handle creds separately... If not explicitly set then use default.
        if self._settings['creds'] is None and self._settings['creds_factory']:
            self._settings['creds'] = self._settings[
                'creds_factory'
            ].get_default()

        if 'collector' not in self._settings:
            self._settings['collector'] = collector.MemoryCollector()

    def update(self, **kwargs: Unpack[EnvArgs]) -> 'Environment':
        """Update the environment settings."""
        return Environment(parent=self, **kwargs)

    def add(
        self,
        llm_factory_args: Optional[dict[str, Any]] = None,
        functions: Optional[List[llm_commons.LlmFunction]] = None,
        template_globals: Optional[dict[str, Any]] = None,
        template_filters: Optional[dict[str, Callable[..., Any]]] = None,
    ) -> 'Environment':
        """Create a new environment with added settings."""
        new_llm_factory_args = (
            self._settings.get('llm_factory_args') or {}
        ).copy()
        new_llm_factory_args.update(llm_factory_args or {})

        new_functions = {func.name: func for func in self.functions or []}
        for func in functions or []:
            new_functions[func.name] = func

        new_template_globals = (
            self._settings.get('template_globals') or {}
        ).copy()
        new_template_globals.update(template_globals or {})

        new_template_filters = (
            self._settings.get('template_filters') or {}
        ).copy()
        new_template_filters.update(template_filters or {})

        return Environment(
            parent=self,
            llm_factory_args=new_llm_factory_args,
            functions=list(new_functions.values()),
            template_globals=new_template_globals,
            template_filters=new_template_filters,
        )

    @property
    def creds(self) -> Optional[auth.Credentials]:
        """Get the credentials."""
        return self._settings.get('creds') or self.creds_factory.get_default()

    @property
    def creds_factory(self) -> auth.CredentialsFactory:
        """Get the credentials factory."""
        factory = self._settings.get('creds_factory')
        if not factory:
            raise ValueError("No credentials factory set")
        return factory

    @property
    def llm_factory(self) -> llm_commons.LlmModelFactory:
        """Get the LLM model factory."""
        factory = self._settings.get('llm_factory')
        if not factory:
            raise ValueError("No LLM factory set")
        return factory

    @property
    def llm_factory_args(self) -> dict[str, Any]:
        """Get the LLM model factory arguments."""
        return self._settings.get('llm_factory_args') or {}

    @property
    def template_globals(self) -> dict[str, Any]:
        """Get the template globals."""
        return self._settings.get('template_globals') or {}

    @property
    def template_filters(self) -> dict[str, Callable[..., Any]]:
        """Get the template filters."""
        return self._settings.get('template_filters') or {}

    def create_model(
        self, model_name: str | None = None, **kwargs: Any
    ) -> llm_commons.LlmBase:
        """Create a new LLM model."""
        create_args = {
            'cache_instance': self.cache_instance,
            'functions': self.functions,
        }
        create_args.update(self.llm_factory_args)
        create_args.update(kwargs)

        llm_factory = self.llm_factory
        if not llm_factory:
            raise ValueError("No LLM factory set")
        return llm_factory.create(model_name or self.model_name, **create_args)

    @property
    def gmail_wrapper(self) -> gmail_api.GMailWrap:
        """Get or create the GMail wrapper."""
        if self._gmail_wrapper is None:
            self._gmail_wrapper = gmail_api.GMailWrap(
                creds=self.creds,
            )
        return self._gmail_wrapper

    @property
    def calendar_wrapper(self) -> calendar_api.CalendarWrap:
        """Get or create the Calendar wrapper."""
        if self._calendar_wrapper is None:
            self._calendar_wrapper = calendar_api.CalendarWrap(
                creds=self.creds,
            )
        return self._calendar_wrapper

    @property
    def tasks_wrapper(self) -> tasks_wrapper.TasksWrap:
        """Get or create the Tasks wrapper."""
        if self._tasks_wrapper is None:
            self._tasks_wrapper = tasks_wrapper.TasksWrap(
                creds=self.creds,
            )
        return self._tasks_wrapper

    @property
    def docs_wrapper(self) -> docs_wrapper.DocsWrapper:
        """Get or create the Docs wrapper."""
        if self._docs_wrapper is None:
            self._docs_wrapper = docs_wrapper.DocsWrapper(
                creds=self.creds,
            )
        return self._docs_wrapper

    @property
    def managed_tasks(self) -> ManagedTasks:
        """Get or create the ManagedTasks wrapper."""
        if self._managed_tasks is None:
            self._managed_tasks = tasks_wrapper.ManagedTasks(self.tasks_wrapper)
        return self._managed_tasks

    @property
    def model_name(self) -> Optional[str]:
        """Get the model name."""
        return self._settings.get('model_name')

    @property
    def cache_instance(self) -> cache.CacheInterface:
        """Get the cache instance."""
        return self._settings.get('cache_instance') or cache.NoCache()

    @property
    def functions(self) -> List[llm_commons.LlmFunction]:
        """Get the LLM functions."""
        return self._settings.get('functions') or []

    @functions.setter
    def functions(self, value: List[llm_commons.LlmFunction]):
        self._settings['functions'] = value

    @property
    def collector(self) -> collector.Collector:
        """Get the collector."""
        return self._settings.get('collector', collector.NoCollector())

    def collect(
        self,
        key: str | Callable[[], str],
    ) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
        """Rx operator to collect stats and samples.

        Args:
            key: The key to use for collection, or a function returning the key.
            collector: The collector instance to use (default: shared instance).
            sample_interleave: How many items to skip between samples (0 = no sampling).
        """
        _collector = self._settings.get('collector', collector.NoCollector())
        _sample_interleave = self._settings.get('sample_interleave', 0)
        return ops.do(
            collector.CollectingObserver(key, _collector, _sample_interleave)
        )

    def create_doc_model(self, document_id: str) -> docs_model.Document:
        """Create a Document model instance."""
        return docs_model.Document(self.docs_wrapper, document_id)

    @property
    def error_handler(self) -> Callable[[Exception], None]:
        """Get the error handler."""
        return self._settings.get('error_handler', log_only_error_handler)

    def __enter__(
        self,
    ) -> 'Environment':
        """Enter the environment."""
        logging.debug("Entering environment: %s", self)
        self._outer_environment = Environment._instance
        Environment._instance = self

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        """Exit the environment."""
        logging.debug(
            "Exiting environment: %s (%s, %s, %s)",
            self,
            exc_type,
            exc_val,
            exc_tb,
        )
        Environment._instance = self._outer_environment
