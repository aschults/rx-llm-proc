"""Test Plugin loader."""

import unittest
import argparse
from typing import Any, Dict

from rxllmproc.plugins import loader


class SampleOptionsReceiver:
    """Sample object container to receive options."""

    def __init__(self) -> None:
        """Create an instance, initializing option to be set."""
        self.y = ''


class TestPluginLoader(unittest.TestCase):
    """Test the plugin registry."""

    def test_simple_load(self):
        """Test a simple load from two plugin modules."""
        registry = loader.PluginRegistry()
        registry.load_plugins()
        self.assertEqual('here', registry.context.get('test_attr'))
        self.assertEqual('here2', registry.context.get('test_attr2'))

    def test_arg_action(self):
        """Test the argparse Action class to store plugin options."""
        parser = argparse.ArgumentParser()
        registry = loader.PluginRegistry(argparse_instance=parser)

        dict_target: Dict[str, Any] = {}
        registry.context['dict_target'] = dict_target
        obj_target = SampleOptionsReceiver()
        registry.context['obj_target'] = obj_target

        registry.load_plugins()
        parser.parse_args(['-x', 'abc', '-y', 'def'])

        self.assertEqual('abc', dict_target['x'])
        self.assertEqual('def', obj_target.y)
