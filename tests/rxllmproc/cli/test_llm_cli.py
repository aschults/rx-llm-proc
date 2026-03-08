# pyright: basic
"""Test Cemini CLI class."""

from typing import Any
import contextlib
import io

from unittest import mock
from pyfakefs import fake_filesystem_unittest

from rxllmproc.llm import commons as llm_commons
from rxllmproc.cli import llm_cli
import requests_mock


class DummyLlm(llm_commons.LlmBase):
    """Dummy LLM implementation to test the CLI."""

    def query(
        self, functions: Any = None, *prompt_parts: Any, **other: Any
    ) -> str:
        """Return a fixed value for testing."""
        return "something"


class TestLlmCli(fake_filesystem_unittest.TestCase):
    """Test the Gmail CLI class."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

        self.creds = mock.Mock()
        self.wrap = mock.Mock(spec=DummyLlm)
        self.instance = llm_cli.LlmCli(self.wrap)

        def factory_func(**kwargs: Any) -> DummyLlm:
            return self.wrap

        self.instance.llm_registry.set('gemini', factory_func)

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_write_stdout(self, stdout_mock: mock.Mock):
        """Test a simple prompt and write to stdout."""
        self.wrap.query.return_value = 'the_result'

        self.instance.main(['the_query'])

        self.wrap.query.assert_called_once_with('the_query')
        stdout_mock.write.assert_called_with('the_result\n')

    @mock.patch('rxllmproc.cli.cli_base.sys.stdin')
    def test_read_stdin(self, stdin_mock: mock.Mock):
        """Test a simple prompt and read from STDIN."""
        self.wrap.query.return_value = 'the_result'
        stdin_mock.read.return_value = 'the_query'

        self.instance.main(['--output', 'file.txt'])

        self.wrap.query.assert_called_once_with('the_query')
        msg_file = self.fs.get_object('/file.txt')
        self.assertIsNotNone(msg_file)
        self.assertEqual('the_result\n', msg_file.contents)

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_json_output(self, stdout_mock: mock.Mock):
        """Test a simple prompt and write to stdout."""
        self.wrap.query_json.return_value = [1, 2, 3]

        self.instance.main(['--as_json', 'the_query'])

        self.wrap.query_json.assert_called_once_with('the_query')
        stdout_mock.write.assert_called_with('[\n 1,\n 2,\n 3\n]\n')

    def test_write_file(self):
        """Test a simple prompt and write to file."""
        self.wrap.query.return_value = 'the_result\n'

        self.instance.main(['the_query', '--output=file.txt'])

        self.wrap.query.assert_called_once_with('the_query')
        msg_file = self.fs.get_object('/file.txt')
        self.assertIsNotNone(msg_file)
        self.assertEqual('the_result\n', msg_file.contents)

    def test_dry_run(self):
        """Ensure that existing files are not overwritten."""
        self.wrap.query.return_value = 'the_result'

        self.instance.main(['the_query', '--output=file.txt', '--dry_run'])

        self.wrap.query.assert_called_once_with('the_query')
        self.assertFalse(self.fs.exists('/file.txt'))  # type: ignore

    def test_read_file_args(self):
        """Test that positional args like `@<<file>>` are expanded."""
        self.wrap.query.return_value = 'the_result'
        self.fs.create_file(  # type: ignore
            'some_file.txt',
            contents='query_part2',
        )

        self.instance.main(['the_query', '@some_file.txt'])

        self.wrap.query.assert_called_once_with('the_query', 'query_part2')

    def test_upload_local_file(self):
        """Test uploading a local file via container spec."""
        self.wrap.query.return_value = 'the_result'
        self.fs.create_file('upload_me.txt', contents='upload content')

        self.instance.main(['the_prompt', '--upload', 'upload_me.txt'])

        # The query should be called with the prompt and a LocalFileContainer
        self.wrap.query.assert_called_once()
        call_args = self.wrap.query.call_args.args
        self.assertEqual(len(call_args), 2)
        self.assertEqual(call_args[0], 'the_prompt')
        container = call_args[1]
        self.assertIsInstance(container, llm_cli.containers.LocalFileContainer)
        self.assertEqual(container.filename, 'upload_me.txt')

    def test_template_expansion(self):
        """Test that prompts are expanded using Jinja2 templates."""
        self.wrap.query.return_value = 'the_result'
        self.fs.create_file('vars.json', contents='{"name": "file"}')

        self.instance.main(
            [
                'Hello {{name}} and {{v.name}}!',
                '-D',
                'name=world',
                '-D',
                'v=(json)@vars.json',
            ]
        )

        self.wrap.query.assert_called_once_with('Hello world and file!')

    def test_include_file_in_template(self):
        """Test that include_file function in Jinja2 templates works."""
        self.wrap.query.return_value = 'the_result'
        self.fs.create_file('included_file.txt', contents='file content')

        self.instance.main(
            ["Prompt with {{ include_file('included_file.txt') }}"]
        )

        self.wrap.query.assert_called_once_with('Prompt with file content')

    def test_retreive_file_function(self):
        """Test the get file function that is handed to Gemini."""

        def _handle_query(*args: str) -> str:
            self.assertEqual(
                {
                    'contents': 'some_contents',
                    'filename': 'some_file.txt',
                    'success': 'The file was read completely',
                },
                self.instance.retreive_file('some_file.txt'),
            )
            self.assertEqual(
                {
                    'contents': 'some_contents2',
                    'filename': 'some_file2.txt',
                    'success': 'The file was read completely',
                },
                self.instance.retreive_file('some_file2.txt'),
            )
            return 'the_result'

        self.wrap.query.side_effect = _handle_query
        self.fs.create_file(  # type: ignore
            'some_file.txt',
            contents='some_contents',
        )
        self.fs.create_file(  # type: ignore
            'some_file2.txt',
            contents='some_contents2',
        )

        self.instance.main(
            [
                'the_query',
                '--context_file=some_file.txt',
                '--context_file=some_file2.txt',
            ]
        )

        self.assertIn(
            'read_file', [func.name for func in self.instance.functions]
        )

    def test_retreive_file_function_not_existing(self):
        """Test the get file function when the file doesn't exist."""

        def _handle_query(*args: str) -> str:
            self.assertEqual(
                {
                    'file_not_found': 'The requested file does not exist.',
                    'filename': 'some_file.txt',
                },
                self.instance.retreive_file('some_file.txt'),
            )
            return 'the_result'

        self.wrap.query.side_effect = _handle_query
        self.instance.main(['the_query', '--context_file=some_file.txt'])

    def test_retreive_file_function_not_permitted(self):
        """Test the get file function, when access is not OK."""

        def _handle_query(*args: str) -> str:
            self.assertEqual(
                {
                    'file_not_found': 'The requested file does not exist.',
                    'filename': 'some_file.txt',
                },
                self.instance.retreive_file('some_file.txt'),
            )
            return 'the_result'

        self.wrap.query.side_effect = _handle_query
        self.instance.main(['the_query', '--context_file=some_file.txt'])

    def test_write_file_function(self):
        """Test the write_file function that is handed to Gemini."""

        def _handle_query(*args: str) -> str:
            self.assertEqual(
                {
                    'content': 'test123',
                    'filename': 'outfile.txt',
                    'success': 'File completely written.',
                },
                self.instance.write_file('outfile.txt', 'test123'),
            )
            return 'the_result'

        self.wrap.query.side_effect = _handle_query

        self.instance.main(
            [
                'the_query',
                '--writeable_files=outfile.txt',
            ]
        )

        self.assertEqual(
            'test123',
            self.fs.get_object('outfile.txt').contents,
        )
        self.assertIn(
            'write_file', [func.name for func in self.instance.functions]
        )

    def test_write_file_function_no_permission(self):
        """Test the write_file function fails when no write option."""

        def _handle_query(*args: str) -> str:
            self.assertEqual(
                {
                    'content': None,
                    'filename': '/outfile.txt',
                    'no_permissions': 'Not permitted to write file',
                },
                self.instance.write_file('/outfile.txt', 'test123'),
            )
            return 'the_result'

        self.wrap.query.side_effect = _handle_query

        self.instance.main(['the_query'])

        self.assertFalse(self.fs.exists('/outfile.txt'))

    def test_list_files_function(self):
        """Test the get file function that is handed to Gemini."""

        def _handle_query(*args: str) -> str:
            self.assertEqual(
                {
                    'files': ['some_file.txt'],
                    'pattern': '*.txt',
                    'success': 'All files listed',
                },
                self.instance.list_files('*.txt'),
            )
            return 'the_result'

        self.wrap.query.side_effect = _handle_query
        self.fs.create_file(  # type: ignore
            'some_file.txt',
            contents='some_contents',
        )
        self.fs.create_file(  # type: ignore
            'some_file2.txt',
            contents='some_contents2',
        )

        self.instance.main(
            ['the_query', '--context_file=some_file.txt', '--enable_list_files']
        )

        self.assertIn(
            'list_files', [func.name for func in self.instance.functions]
        )

    def test_retreive_url(self):
        """Test the get file function, when access is not OK."""

        def _handle_query(*args: str) -> str:
            with requests_mock.Mocker() as req_mock:
                req_mock.get(
                    'http://test.com',
                    text='the_content',
                    headers={'content-type': 'text/plain'},
                )
                self.assertEqual(
                    {
                        'contents': 'the_content',
                        'mime-type': 'text/plain',
                        'status': 'OK',
                        'url': 'http://test.com',
                    },
                    self.instance.retreive_url('http://test.com'),
                )
            return 'the_result'

        self.wrap.query.side_effect = _handle_query
        self.instance.main(['the_query', '--enable_fetch_url'])

        self.assertIn(
            'get_url', [func.name for func in self.instance.functions]
        )

    def test_retreive_url_fail(self):
        """Test the get file function, when access is not OK."""

        def _handle_query(*args: str) -> str:
            with requests_mock.Mocker() as req_mock:
                req_mock.get(
                    'http://test.com', text='the_content', status_code=404
                )
                self.assertEqual(
                    {'status': 'failed', 'url': 'http://test.com'},
                    self.instance.retreive_url('http://test.com'),
                )
            return 'the_result'

        self.wrap.query.side_effect = _handle_query
        self.instance.main(['the_query'])

    @mock.patch('rxllmproc.cli.cli_base.sys.exit')
    def test_fail_generator(self, exit_mock: mock.Mock):
        """Test failing with GeneratorError."""
        self.wrap.query.side_effect = llm_commons.GeneratorError(
            'test_exc_value', mock.Mock()
        )

        stderr_output = io.StringIO()
        with contextlib.redirect_stderr(stderr_output):
            self.instance.main(['the_query'])

        exit_mock.assert_called_with(30)
        self.wrap.query.assert_called_with('the_query')
        self.assertIn('test_exc_value', stderr_output.getvalue())
