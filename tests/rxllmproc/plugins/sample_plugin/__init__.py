"""Sample plugin for unit tests."""

from rxllmproc.plugins import loader


def load_plugin(registry: loader.PluginRegistry):
    """Load the plugin, setting a context attribute and some options."""
    registry.context['test_attr'] = 'here'

    if 'dict_target' not in registry.context:
        return
    if 'obj_target' not in registry.context:
        return

    # Register some options that will end up in the registry context.
    if registry.argparse_instance:
        registry.argparse_instance.add_argument(
            '-x',
            action=registry.make_action_to_store(
                registry.context['dict_target'],
                'x',
            ),
        )
        registry.argparse_instance.add_argument(
            '-y',
            action=registry.make_action_to_store(
                registry.context['obj_target'],
                'y',
            ),
        )
