"""Test Plugin loader."""

import unittest
import argparse
import importlib
from typing import Any, Dict

from rxllmproc.plugins import loader


class SampleOptionsReceiver:
    """Sample object container to receive options."""

    def __init__(self) -> None:
        """Create an instance, initializing option to be set."""
        self.y = ''


class TestPluginLoader(unittest.TestCase):
    """Test the plugin registry."""

    def setUp(self):
        """Set up the test."""
        super().setUp()
        additional_modules: list[Any] = []
        if __package__:
            plugins = importlib.import_module(__package__)
            additional_modules.append(plugins)
        self.parser = argparse.ArgumentParser()
        self.registry = loader.PluginRegistry(
            argparse_instance=self.parser, additional_modules=additional_modules
        )

    def test_simple_load(self):
        """Test a simple load from two plugin modules."""
        self.registry.load_plugins()
        self.assertEqual('here', self.registry.context.get('test_attr'))
        self.assertEqual('here2', self.registry.context.get('test_attr2'))

    def test_arg_action(self):
        """Test the argparse Action class to store plugin options."""
        dict_target: Dict[str, Any] = {}
        self.registry.context['dict_target'] = dict_target
        obj_target = SampleOptionsReceiver()
        self.registry.context['obj_target'] = obj_target

        self.registry.load_plugins()
        self.parser.parse_args(['-x', 'abc', '-y', 'def'])

        self.assertEqual('abc', dict_target['x'])
        self.assertEqual('def', obj_target.y)
