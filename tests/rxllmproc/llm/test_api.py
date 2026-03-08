"""Test the Gemini / VertexAI API wrapper."""

import unittest
from unittest import mock
from typing import Any
import pathlib
import datetime

from google.genai import client as genai_client
from google.genai import types as genai_types  # type: ignore
from pyfakefs import fake_filesystem_unittest

from rxllmproc.llm import api as gemini_wrapper, commons as llm_commons
from rxllmproc.core.infra import containers
from rxllmproc.core.infra import cache


class TestGeminiWrapper(unittest.TestCase):
    """Test the wrapper."""

    @staticmethod
    def _response_to_obj(data: Any) -> genai_types.GenerateContentResponse:
        """Convert the response for the VertexAI mock from a dict."""
        candidates: list[genai_types.Candidate] = []
        for candidate_data in data['candidates']:
            content_data = candidate_data.get('content', {})
            parts_data = content_data.get('parts', [])
            parts = [genai_types.Part(p) for p in parts_data]
            content = genai_types.Content(parts=parts)
            candidate = genai_types.Candidate(
                content=content,
                finish_reason=candidate_data.get('finish_reason'),
                finish_message=candidate_data.get('finish_message'),
            )
            candidates.append(candidate)
        return genai_types.GenerateContentResponse(candidates=candidates)

    def setUp(self) -> None:
        """Provide mock credentials and service API."""
        self.client = mock.Mock(spec=genai_client.Client)
        self.models_mock = mock.Mock()
        self.files_mock = mock.Mock()
        self.client.files = self.files_mock
        self.default_result: Any = {
            'candidates': [
                {
                    'finish_reason': 'STOP',
                    'content': {'parts': [{'text': 'response text'}]},
                }
            ]
        }

        self.function_call_result: Any = {
            'candidates': [
                {
                    'finish_reason': 'STOP',
                    'content': {
                        'parts': [
                            {
                                'function_call': {
                                    'name': 'funcname',
                                    'args': {'par1': 'arg1', 'par2': 'arg2'},
                                }
                            }
                        ]
                    },
                }
            ]
        }

        def get_response(
            *args: Any, **kwargs: Any
        ) -> genai_types.GenerateContentResponse:
            """Build a response for the VertexAI mock."""
            return TestGeminiWrapper._response_to_obj(self.default_result)

        self.models_mock.generate_content.side_effect = get_response
        self.client.models = self.models_mock
        self.instance = gemini_wrapper.Gemini(client=self.client)
        return super().setUp()

    def test_query(self):
        """Test a text response."""
        result = self.instance.query('test prompt')

        self.assertEqual('response text', result)
        self.assertEqual(
            self.models_mock.generate_content.call_args.kwargs['contents'][0]
            .parts[0]
            .text,
            'test prompt',
        )

    def test_query_fail(self):
        """Test a text response failing."""
        self.default_result['candidates'][0]['finish_reason'] = 'OTHER'
        self.default_result['candidates'][0][
            'finish_message'
        ] = 'failure_reason'
        self.assertRaisesRegex(
            llm_commons.GeneratorError,
            'Failed to generate response. Reason: OTHER, failure_reason',
            lambda: self.instance.query('test prompt'),
        )

    def test_query_with_function(self):
        """Test text response with function call."""
        self.models_mock.generate_content.side_effect = [
            TestGeminiWrapper._response_to_obj(rv)
            for rv in (self.function_call_result, self.default_result)
        ]

        mock_callback = mock.Mock()
        mock_callback.return_value = {'rv': 'return_value'}
        functions: list[llm_commons.LlmFunction] = [
            llm_commons.BasicLlmFunction(
                'funcname', description='desc', callback=mock_callback
            )
        ]
        self.instance = gemini_wrapper.Gemini(
            client=self.client, functions=functions
        )

        result = self.instance.query('test prompt')

        self.assertEqual('response text', result)
        mock_callback.assert_called_once_with(par1='arg1', par2='arg2')
        self.assertEqual(
            self.models_mock.generate_content.call_args_list[0]
            .kwargs['contents'][0]
            .parts[0]
            .text,
            'test prompt',
        )
        self.assertEqual(
            self.models_mock.generate_content.call_args_list[1]
            .kwargs['contents'][1]
            .parts[0]
            .function_response.name,
            'funcname',
        )
        self.assertEqual(
            self.models_mock.generate_content.call_args_list[1]
            .kwargs['contents'][1]
            .parts[0]
            .function_response.response,
            {'rv': 'return_value'},
        )

    def test_query_with_file_upload_path(self):
        """Test a query with a file upload using pathlib.Path."""
        # Arrange
        mock_uploaded_file = mock.Mock()
        mock_uploaded_file.uri = 'file_uri_for_test'
        mock_uploaded_file.mime_type = 'text/plain'
        self.files_mock.upload.return_value = mock_uploaded_file

        # Act
        with fake_filesystem_unittest.Patcher():
            file_path = pathlib.Path('/test.txt')
            file_path.write_text('test content')
            result = self.instance.query('test prompt', file_path)

        # Assert
        self.assertEqual('response text', result)
        self.files_mock.upload.assert_called_once_with(file=str(file_path))

        # Check the contents passed to generate_content
        call_args = self.models_mock.generate_content.call_args
        contents = call_args.kwargs['contents']
        self.assertEqual(len(contents), 1)
        parts = contents[0].parts
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0].text, 'test prompt')
        self.assertEqual(parts[1].file_data.file_uri, 'file_uri_for_test')
        self.assertEqual(parts[1].file_data.mime_type, 'text/plain')

    def test_query_with_file_upload_container(self):
        """Test a query with a file upload using LocalFileContainer."""
        # Arrange
        mock_uploaded_file = mock.Mock()
        mock_uploaded_file.uri = 'file_uri_for_test'
        mock_uploaded_file.mime_type = 'text/plain'
        self.files_mock.upload.return_value = mock_uploaded_file

        # Act
        with fake_filesystem_unittest.Patcher() as patcher:
            patcher.fs.create_file('/test.txt', contents='test content')  # type: ignore
            container = containers.LocalFileContainer('/test.txt')
            result = self.instance.query('test prompt', container)

        # Assert
        self.assertEqual('response text', result)
        self.files_mock.upload.assert_called_once_with(file='/test.txt')

        # Check the contents passed to generate_content
        call_args = self.models_mock.generate_content.call_args
        parts = call_args.kwargs['contents'][0].parts
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[1].file_data.file_uri, 'file_uri_for_test')
        self.assertEqual(parts[1].file_data.mime_type, 'text/plain')

    @mock.patch(
        'rxllmproc.core.infra.cache.get_time_now',
        return_value=datetime.datetime(2024, 1, 1),
    )
    def test_query_cached(self, _: mock.MagicMock):
        """Test that query uses the cache."""

        mock_cache = mock.Mock()
        # Setup cache miss
        mock_cache.get.return_value = None

        self.instance = gemini_wrapper.Gemini(
            client=self.client, cache_instance=mock_cache
        )

        # Execute query (Cache Miss)
        result = self.instance.query('test prompt')

        self.assertEqual('response text', result)
        mock_cache.get.assert_called_once_with(
            'gemini_query(gemini-1.5-flash)',
            'test prompt',
            output_format=None,
            schema=None,
        )
        mock_cache.add_call.assert_called_once_with(
            'gemini_query(gemini-1.5-flash)',
            cache.CachedCall.create(
                'response text',
                'test prompt',
                output_format=None,
                schema=None,
            ),
        )

        # Test cache hit
        mock_cache.reset_mock()
        self.models_mock.generate_content.reset_mock()

        mock_cached_val = mock.Mock()
        mock_cached_val.value = 'cached response'
        mock_cache.get.return_value = mock_cached_val

        result = self.instance.query('test prompt')

        self.assertEqual('cached response', result)
        mock_cache.get.assert_called_once_with(
            'gemini_query(gemini-1.5-flash)',
            'test prompt',
            output_format=None,
            schema=None,
        )
        mock_cache.add.assert_not_called()
        self.models_mock.generate_content.assert_not_called()

    def test_query_json_with_functions_disables_json_mode(self):
        """Test that JSON mode is disabled when functions are present."""
        mock_callback = mock.Mock()
        mock_callback.return_value = {'rv': 'return_value'}
        functions: list[llm_commons.LlmFunction] = [
            llm_commons.BasicLlmFunction(
                'funcname', description='desc', callback=mock_callback
            )
        ]
        self.instance = gemini_wrapper.Gemini(
            client=self.client, functions=functions
        )

        self.instance.query('test prompt', output_format='json')

        call_args = self.models_mock.generate_content.call_args
        config = call_args.kwargs['config']
        self.assertIsNone(config.response_mime_type)
        self.assertTrue(config.tools)
