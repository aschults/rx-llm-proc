"""Functionality to load addititional code as plugins.

Default location for plugins: rxllmproc.plugins.
"""

from typing import List, Any, Dict
import pkgutil
import types
import argparse

from rxllmproc.llm import commons as llm_commons

# Load Gemini wrapper so the registry has the models.
import rxllmproc.llm.api as _  # noqa: F401

from rxllmproc.core import auth


class _AlternateStorageAction(argparse.Action):
    """Argparse Action to store options outside of the passed namespace.

    As the implementation of argparse actions is passed by type, this class
    needs to be subclassed for specific attributes.

    To avoid the option being set in the namespace returned by parse_args(),
    use `dest=argparse.SUPPRESS`.
    """

    # Class variable to store the dict or object to be updated.
    target: Dict[str, Any] | argparse.Namespace | None = None

    # Name of the attribute, or dict key to set.
    target_name: str | None = None

    def __init__(self, **kwargs: Any):
        """Create an instance, preventing the use of `nargs`."""
        if kwargs.get('nargs') is not None:
            raise ValueError("nargs not allowed")

        super().__init__(**kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ):
        """Store the option into `target`.

        Uses class variables `target` and `target_name`.
        """
        if self.target is None:
            raise ValueError('Need to have target set')
        if self.target_name is None:
            raise ValueError('Need to have target_name set')

        if isinstance(self.target, dict):
            self.target[self.target_name] = values
        else:
            setattr(self.target, self.target_name, values)

    @classmethod
    def create_subclass(
        cls, target: Dict[str, Any] | Any, target_name: str
    ) -> type[argparse.Action]:
        """Create a subclass to store in a particular target."""
        return type(
            "Anonymous",
            (_AlternateStorageAction,),
            {'target': target, 'target_name': target_name},
        )


# List of namespaces to search plugins from.
PLUGIN_NAMESPACES_LIST: List[Any] = []

try:
    import rxllmproc.plugins  # type: ignore

    PLUGIN_NAMESPACES_LIST.append(rxllmproc.plugins)
except ImportError:
    pass


class PluginRegistry:
    """Store plugin-related details.

    Contains the list of plugin modules found, as well as context to be used
    during plugin loading.
    """

    def __init__(
        self,
        llm_registry: llm_commons.LlmModelFactory | None = None,
        cred_store: auth.CredentialsFactory | None = None,
        argparse_instance: argparse.ArgumentParser | None = None,
    ) -> None:
        """Create an instance.

        Args:
            llm_registry: Registry to load additional LLM factory functions.
            cred_store: Credentials store, to add additional credentials.
            argparse_instance: If set, allows plugins to add their own options.
        """
        self.plugins: List[Any] = []
        self._load_plugin_modules()

        self.context: Dict[str, Any] = dict()
        self.llm_registry = (
            llm_registry or llm_commons.LlmModelFactory.shared_instance()
        )
        self.cred_store = (
            cred_store or auth.CredentialsFactory.shared_instance()
        )
        self.argparse_instance = argparse_instance

    def _load_plugin_modules(self, *additional_bases: Any):
        """Find and load all plugin modules."""
        self.plugins = []
        for base in PLUGIN_NAMESPACES_LIST:
            for module_info in pkgutil.walk_packages(base.__path__):
                if module_info.name == 'loader':
                    continue
                module_spec = module_info.module_finder.find_spec(
                    module_info.name, None
                )
                if not module_spec:
                    raise ModuleNotFoundError(
                        f'Plugin module not found {repr(module_info.name)}'
                    )
                if not module_spec.loader:
                    raise ModuleNotFoundError(
                        'Plugin module loader not available'
                        f' {repr(module_info.name)}'
                    )
                module = types.ModuleType(module_spec.name)
                module_spec.loader.exec_module(module)
                self.plugins.append(module)

    def load_plugins(self):
        """Load the plugin content.

        Allows plugin modules to initialize. Tries to find a function named
        `load_plugin` in each plugin and calls it, passing this instance as
        argument.
        """
        for module in self.plugins:
            if hasattr(module, 'load_plugin'):
                getattr(module, 'load_plugin')(self)

    def make_action_to_store(
        self, target: Dict[str, Any] | Any, target_name: str
    ) -> type[argparse.Action]:
        """Create an ArgParse Action that allows storing to dict/object."""
        return _AlternateStorageAction.create_subclass(target, target_name)
