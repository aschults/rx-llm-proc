"""Another sample plugin for unit tests."""

from rxllmproc.plugins import loader


def load_plugin(registry: loader.PluginRegistry):
    """Load the plugin and set some context to prove."""
    registry.context['test_attr2'] = 'here2'
