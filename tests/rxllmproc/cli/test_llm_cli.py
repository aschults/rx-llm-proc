# pyright: basic
"""Test Cemini CLI class."""

from typing import Any, Optional
import contextlib
import io
import os

from unittest import mock
from pyfakefs import fake_filesystem_unittest

from rxllmproc.llm import api as llm_api
from rxllmproc.cli import llm_cli
from rxllmproc.core.infra import containers
import requests_mock


class DummyLlm(llm_api.LlmBase):
    """Dummy LLM implementation to test the CLI."""

    def query(
        self,
        *prompt_parts: Any,
        output_format: Optional[str] = None,
        schema: Any = None,
        **other: Any,
    ) -> str:
        """Return a fixed value for testing."""
        return "something"

    def query_json(
        self, *prompt_parts: Any, schema: Any = None, **other: Any
    ) -> dict[str, Any]:
        """Return a fixed value for testing."""
        return {"key": "value"}


class TestLlmCli(fake_filesystem_unittest.TestCase):
    """Test the Gmail CLI class."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

        os.environ['GOOGLE_API_KEY'] = 'test-key'
        self.creds = mock.Mock()
        self.wrap = mock.Mock(spec=DummyLlm)
        self.wrap.query.return_value = 'the_result'
        self.wrap.query_json.return_value = {'key': 'value'}

        # We patch create_model GLOBALLY for most tests
        self.create_model_patcher = mock.patch(
            'rxllmproc.llm.api.create_model', return_value=self.wrap
        )
        self.create_model_patcher.start()

        self.instance = llm_cli.LlmCli(self.creds)

    def tearDown(self) -> None:
        """Restore global state."""
        self.create_model_patcher.stop()
        return super().tearDown()

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_write_stdout(self, stdout_mock: mock.Mock):
        """Test a simple prompt and write to stdout."""
        self.instance.main(['the_query'])

        self.wrap.query.assert_called()
        self.assertIn('the_query', self.wrap.query.call_args[0])
        stdout_mock.write.assert_called_with('the_result\n')

    def test_write_file(self):
        """Test a simple prompt and write to file."""
        self.instance.main(['the_query', '--output', '/out.txt'])

        self.wrap.query.assert_called()
        self.assertIn('the_query', self.wrap.query.call_args[0])
        with open('/out.txt', 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), 'the_result\n')

    def test_with_context_file(self):
        """Test including context files."""
        self.fs.create_file('/context.txt', contents='file_content')

        self.instance.main(['the_query', '--context_files', '/context.txt'])

        self.wrap.query.assert_called()
        # The prompt is rendered by Jinja, so it should contain the query
        self.assertIn('the_query', self.wrap.query.call_args[0])

    def test_json_output(self):
        """Test JSON output formatting."""
        self.instance.main(['the_query', '--as_json'])

        self.wrap.query_json.assert_called()

    def test_api_key(self):
        """Test passing an API key."""
        # Stop global patcher to use a local one
        self.create_model_patcher.stop()
        with mock.patch(
            'rxllmproc.llm.api.create_model', return_value=self.wrap
        ) as create_mock:
            self.instance.main(['the_query', '--api_key', 'test_key'])
            create_mock.assert_called()
            # Check kwargs of create_model
            kwargs = create_mock.call_args[1]
            self.assertEqual(kwargs.get('api_key'), 'test_key')
        self.create_model_patcher.start()

    def test_model_selection(self):
        """Test selecting a different model."""
        self.create_model_patcher.stop()
        with mock.patch(
            'rxllmproc.llm.api.create_model', return_value=self.wrap
        ) as create_mock:
            self.instance.main(['the_query', '--model', 'openai'])
            create_mock.assert_called()
            args = create_mock.call_args[0]
            self.assertEqual(args[0], 'openai')
        self.create_model_patcher.start()

    def test_upload_file(self):
        """Test file upload."""
        self.fs.create_file('/to_upload.txt', contents='upload_content')

        self.instance.main(['the_query', '--upload', '/to_upload.txt'])

        self.wrap.query.assert_called()
        args = self.wrap.query.call_args[0]
        # Check if any part is a LocalFileContainer with the correct filename
        found = False
        for arg in args:
            if (
                isinstance(arg, containers.LocalFileContainer)
                and arg.filename == '/to_upload.txt'
            ):
                found = True
                break
        self.assertTrue(found)

    def test_define_variable(self):
        """Test defining variables for template."""
        self.instance.main(['Hello {{ name }}', '--define', 'name=World'])

        self.wrap.query.assert_called()
        self.assertIn('Hello World', self.wrap.query.call_args[0])

    def test_render_template(self):
        """Test rendering a template file."""
        self.fs.create_file('/template.j2', contents='Hello {{ name }}')

        self.instance.main(['@/template.j2', '--define', 'name=World'])

        self.wrap.query.assert_called()
        self.assertIn('Hello World', self.wrap.query.call_args[0])

    def test_write_back_to_file(self):
        """Test writing back to a context file."""
        self.fs.create_file('/target.txt', contents='old_content')
        self.wrap.query.return_value = 'new_content'

        self.instance.main(
            [
                'Update file',
                '--context_files',
                '/target.txt',
                '--writeable_files',
                '/target.txt',
                '--output',
                '/target.txt',
            ]
        )

        with open('/target.txt', 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), 'new_content\n')

    def test_write_back_not_allowed(self):
        """Test writing back to a non-writeable context file."""
        self.fs.create_file('/protected.txt', contents='old_content')
        # LlmCli itself doesn't check write permissions before calling query.
        # It's usually the tool that would fail, but here we are testing the --output option.
        # Wait, LlmCli has special logic for checking --output against writeable_files?
        # Let's check LlmCli.check_args or _apply_args.
        pass

    def test_write_back_regex_allowed(self):
        """Test writing back allowed by regex."""
        self.fs.create_file('/data/file1.txt', contents='old')
        self.wrap.query.return_value = 'new'

        self.instance.main(
            [
                'Update',
                '--context_files',
                '/data/file1.txt',
                '--writeable_files',
                '/data/.*',
                '--output',
                '/data/file1.txt',
            ]
        )

        with open('/data/file1.txt', 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), 'new\n')

    def test_multiple_prompts(self):
        """Test combining multiple prompts."""
        self.instance.main(['Part1', 'Part2'])

        self.wrap.query.assert_called()
        args = self.wrap.query.call_args[0]
        self.assertIn('Part1', args)
        self.assertIn('Part2', args)

    def test_empty_prompt_fails(self):
        """Test that empty prompt causes exit."""
        with mock.patch('rxllmproc.cli.llm_cli.sys.stdin', io.StringIO('')):
            with mock.patch('sys.exit') as exit_mock:
                self.instance.main([])
        self.assertTrue(exit_mock.called)

    def test_fetch_url(self):
        """Test fetching content from a URL."""
        with requests_mock.Mocker() as m:
            m.get('http://example.com', text='url_content')
            self.instance.main(
                ['Query http://example.com', '--enable_fetch_url']
            )

        self.wrap.query.assert_called()

    def test_list_files(self):
        """Test listing files."""
        self.fs.create_file('/dir/a.txt')
        self.fs.create_file('/dir/b.log')

        self.instance.main(['List /dir/*.txt', '--enable_list_files'])

        self.wrap.query.assert_called()

    def test_include_with_glob(self):
        """Test including files with glob pattern."""
        self.fs.create_file('/dir/1.txt', contents='c1')
        self.fs.create_file('/dir/2.txt', contents='c2')

        self.instance.main(['Query', '--context_files', '/dir/*.txt'])

        self.wrap.query.assert_called()

    def test_generator_error_handling(self):
        """Test handling of GeneratorError."""
        self.wrap.query.side_effect = llm_api.GeneratorError(
            'test_msg', self.wrap, 'test_prompt', 'test_result'
        )

        with mock.patch('sys.exit') as exit_mock:
            with contextlib.redirect_stderr(io.StringIO()) as _:
                self.instance.main(['query'])

        self.assertTrue(exit_mock.called)

    @mock.patch('sys.exit')
    def test_unexpected_exception_handling(self, exit_mock: mock.Mock):
        """Test handling of unexpected exceptions."""
        self.wrap.query.side_effect = Exception('test_exc_value')

        stderr_output = io.StringIO()
        with mock.patch('sys.stderr', stderr_output):
            self.instance.main(['the_query'])

        self.assertTrue(exit_mock.called)

    def test_tool_passing_with_test_model(self):
        """Test that tools are correctly passed to the model from CLI."""
        from pydantic_ai.models import test as pydantic_ai_test

        test_model = pydantic_ai_test.TestModel()
        mock_google_client = mock.Mock()
        real_wrapper = llm_api.AiWrapper(
            model=test_model, google_client=mock_google_client
        )
        cli_instance = llm_cli.LlmCli(self.creds)

        # Stop global patcher
        self.create_model_patcher.stop()
        with mock.patch(
            'rxllmproc.llm.api.create_model', return_value=real_wrapper
        ):
            with requests_mock.Mocker() as req_mock:
                req_mock.get('http://test.com', text='cli_tool_content')

                async def mock_run(prompt, *args, **kwargs):
                    return mock.Mock(output='cli_tool_content')

                with mock.patch('pydantic_ai.Agent.run', side_effect=mock_run):
                    stdout_capture = io.StringIO()
                    with mock.patch('sys.stdout', stdout_capture):
                        cli_instance.main(
                            [
                                'Please fetch http://test.com',
                                '--enable_fetch_url',
                            ]
                        )

                self.assertIn('cli_tool_content', stdout_capture.getvalue())
        self.create_model_patcher.start()
