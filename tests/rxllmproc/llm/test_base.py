"""Test the base LLM functionality."""

import unittest
from unittest import mock
from typing import Any
import dataclasses
import json
import pydantic_ai

from rxllmproc.llm import api as llm_api


@dataclasses.dataclass
class SampleClass:
    """Sample class for object generation."""

    x: int
    y: list[str]


class DummyLlmWrapper(llm_api.LlmBase):
    """Dummy class to inherit from the Mixin."""

    def __init__(self, response: str) -> None:
        """Create an instance passing a fixed response."""
        super().__init__()
        self.response = response
        self.request: Any = None

    def query(
        self,
        *prompt_parts: Any,
        output_format: str | None = None,
        schema: Any = None,
    ) -> str:
        """Capture args and returns fixed response."""
        self.request = '::'.join(str(p) for p in prompt_parts)
        return self.response


class TestStructuredLlmMixin(unittest.TestCase):
    """Test the mixin."""

    def test_json_query(self):
        """Test a JSON response."""
        data = {'x': 123, 'y': ['a', 'b']}
        data_as_str = json.dumps(data)
        instance = DummyLlmWrapper(f'``` json\n{data_as_str}\n```')

        result = instance.query_json('test prompt')

        self.assertEqual(data, result)
        self.assertRegex(instance.request, '(?s).*test prompt.*')

    def test_json_query_bad_json(self):
        """Test a JSON response."""
        instance = DummyLlmWrapper('')

        with mock.patch.object(instance, 'query') as query_mock:
            query_mock.side_effect = [
                '``` json\nNOT JSON\n```',
                '``` json\n[1, 2, 3]\n```',
            ]
            result = instance.query_json('test prompt')

        self.assertEqual([1, 2, 3], result)
        call_args = [call.args[0] for call in query_mock.mock_calls]
        self.assertEqual(2, len(call_args))
        self.assertRegex(call_args[0], 'test prompt')
        self.assertRegex(call_args[1], 'Fix the following')

    def test_json_query_bad_output(self):
        """Test a JSON response."""
        instance = DummyLlmWrapper('')

        with mock.patch.object(instance, 'query') as query_mock:
            query_mock.side_effect = [
                'NOT JSON',
                '``` json\n[1, 2, 3]\n```',
            ]
            result = instance.query_json('test prompt')

        self.assertEqual([1, 2, 3], result)
        call_args = [call.args[0] for call in query_mock.mock_calls]
        self.assertEqual(2, len(call_args))
        self.assertRegex(call_args[0], 'test prompt')
        self.assertRegex(call_args[1], 'Fix the following')

    def test_json_object_query(self):
        """Test an object response."""
        data = {'x': 123, 'y': ['a', 'b']}
        data_as_str = json.dumps(data)
        instance = DummyLlmWrapper(f'``` json\n{data_as_str}\n```')

        result = instance.query_json_object(SampleClass, 'test prompt')

        self.assertEqual(SampleClass(123, ['a', 'b']), result)
        self.assertRegex(
            instance.request, '(?s).*test prompt.*.*JSON.*```.*some string.*'
        )

    def test_json_object_query_alternative_output(self):
        """Test object response with other response text formats."""
        data = {'x': 123, 'y': ['a', 'b']}
        data_as_str = json.dumps(data)
        instance = DummyLlmWrapper(f'```\n{data_as_str}  \n```  ')

        result = instance.query_json_object(SampleClass, 'test prompt')

        self.assertEqual(SampleClass(123, ['a', 'b']), result)
        self.assertRegex(
            instance.request, '(?s).*test prompt.*.*JSON.*```.*some string.*'
        )

    def test_add_function(self):
        """Test adding a function."""
        instance = DummyLlmWrapper('response')
        func = mock.Mock(spec=pydantic_ai.Tool)
        func.name = 'test_func'

        instance.add_function(func)

        self.assertIn('test_func', instance.functions)
        self.assertIs(instance.functions['test_func'], func)

        # Test overwrite
        func2 = mock.Mock(spec=pydantic_ai.Tool)
        func2.name = 'test_func'
        instance.add_function(func2)
        self.assertIs(instance.functions['test_func'], func2)
