# pyright: basic
"""Test base CLI class."""

from typing import Tuple, List
from unittest import mock
import contextlib
import io
import dataclasses

from pyfakefs import fake_filesystem_unittest

from rxllmproc.core import auth
from rxllmproc.cli import cli_base


class DummyCli(cli_base.CommonDirOutputCli):
    """Dummy class to test the CLI base with."""

    def _add_args(self):
        self.arg_parser.add_argument('--test_opt')
        return super()._add_args()

    def __init__(self) -> None:
        """Creeate an instance, mocking credentials."""
        super().__init__(mock.Mock(spec=auth.CredentialsFactory))
        self.test_opt = None

    def run(self) -> None:
        """Fake exection."""


class DummyCliMinimal(cli_base.CliBase):
    """Dummy class to test the CLI base with."""

    def _add_args(self):
        self.arg_parser.add_argument('--test_opt')
        return super()._add_args()

    def __init__(self) -> None:
        """Creeate an instance, mocking credentials."""
        super().__init__(mock.Mock(spec=auth.CredentialsFactory))
        self.test_opt = None

    def run(self) -> None:
        """Fake exection."""


class DummyCliWithCheck(cli_base.CliBase):
    """Dummy cli to test check_args function."""

    def _add_args(self):
        self.arg_parser.add_argument('--test_opt')
        return super()._add_args()

    def __init__(self) -> None:
        """Creeate an instance, mocking credentials."""
        super().__init__(mock.Mock(spec=auth.CredentialsFactory))
        self.test_opt = None

    def check_args(self) -> List[str]:
        """Check args, returning some error strings to match."""
        return ['the_issue', 'second_issue']


class DummyCliWithException(cli_base.CliBase):
    """Dummy class to test Exception hanlding."""

    def __init__(self, e: Exception) -> None:
        """Creeate an instance."""
        super().__init__(mock.Mock(spec=auth.CredentialsFactory))
        self.throw_exception = e

    def run(self) -> None:
        """Fake execution, throwing exception."""
        raise self.throw_exception

    def _exception_to_status(self, e: Exception) -> Tuple[int, str] | None:
        """Map ValueError to exit value 33 for testing."""
        if isinstance(e, ValueError):
            return 33, "the_message_value"
        return super()._exception_to_status(e)


class TestFileOutputOptions(fake_filesystem_unittest.TestCase):
    """Test single file output options."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_write_stdout(self, stdout_mock: mock.Mock):
        """Test writing to stdout."""
        cli_base.CommonFileOutputCli().write_output('the_result')
        stdout_mock.write.assert_called_with('the_result')

    def test_write_file(self):
        """Test writing to file."""
        instance = cli_base.CommonFileOutputCli()
        instance.output = '/file.txt'
        instance.write_output('the_result')

        msg_file = self.fs.get_object('/file.txt')
        self.assertIsNotNone(msg_file)
        self.assertEqual('the_result', msg_file.contents)

    def test_dry_run(self):
        """Ensure that files are not written in dry_run."""
        instance = cli_base.CommonFileOutputCli()
        instance.output = '/file.txt'
        instance.dry_run = True
        instance.write_output('the_result')

        self.assertFalse(self.fs.exists('/file.txt'))  # type: ignore


class TestCliBase(fake_filesystem_unittest.TestCase):
    """Test the CLI base class."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

    def test_no_args(self):
        """Test the CLI with no args passed."""
        instance = DummyCliMinimal()
        instance.main([])

        self.assertIsNone(instance.test_opt)

    def test_common_flags(self):
        """Test common flags."""
        instance = DummyCliMinimal()
        instance.main(['--verbose'])
        self.assertTrue(instance.verbose)

    @mock.patch('rxllmproc.cli.cli_base.sys.exit')
    def test_check_option_fail(self, exit_mock: mock.MagicMock):
        """Test that usage triggers exit and stderr message."""
        stderr_output = io.StringIO()
        with contextlib.redirect_stderr(stderr_output):
            instance = DummyCliWithCheck()
            instance.main([])

        stderr_msg = stderr_output.getvalue()
        exit_mock.assert_called()
        self.assertIn('the_issue', stderr_msg)
        self.assertIn('second_issue', stderr_msg)

    @mock.patch('rxllmproc.cli.cli_base.sys.exit')
    def test_check_raises(self, exit_mock: mock.MagicMock):
        """Test that exception cause specific exit value and message."""
        stderr_output = io.StringIO()
        with contextlib.redirect_stderr(stderr_output):
            instance = DummyCliWithException(ValueError('the_exception_msg'))
            instance.main([])

        stderr_msg = stderr_output.getvalue()
        exit_mock.assert_called_with(33)
        self.assertIn('the_message_value', stderr_msg)
        self.assertIn('the_exception_msg', stderr_msg)

    @mock.patch('rxllmproc.cli.cli_base.sys.exit')
    def test_check_raises_unknown(self, exit_mock: mock.MagicMock):
        """Test exception exit with unexpected exception."""
        stderr_output = io.StringIO()
        with contextlib.redirect_stderr(stderr_output):
            instance = DummyCliWithException(KeyError('the_exception_msg'))
            instance.main([])

        stderr_msg = stderr_output.getvalue()
        exit_mock.assert_called_with(100)
        self.assertIn('Unexpected', stderr_msg)
        self.assertIn('the_exception_msg', stderr_msg)

    def test_flag_name_mapping(self):
        """Test mapping CLI flags to different field names via metadata."""

        @dataclasses.dataclass
        class ConfigWithFlag:
            real_name: str | None = dataclasses.field(
                default=None, metadata={'flag_name': 'cli_flag'}
            )

        config = ConfigWithFlag()

        class FlagCli(cli_base.CliBase):
            def _add_args(self):
                self.arg_parser.add_argument('--cli_flag')
                super()._add_args()

            def run(self):
                pass

        instance = FlagCli(creds=mock.Mock(), config_objects=[config])
        instance.main(['--cli_flag', 'value'])

        self.assertEqual(config.real_name, 'value')
