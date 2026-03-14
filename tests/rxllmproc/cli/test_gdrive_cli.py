# pyright: basic
"""Test Google Drive CLI class."""

import contextlib
import io

from unittest import mock
from pyfakefs import fake_filesystem_unittest

from googleapiclient import errors
from rxllmproc.drive import types
from rxllmproc.drive import api
from rxllmproc.cli import gdrive_cli


class TestDriveCli(fake_filesystem_unittest.TestCase):
    """Test the Drive CLI class."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

        self.creds = mock.Mock()
        self.wrap = mock.Mock(api.DriveWrap)
        self.instance = gdrive_cli.DriveCli(self.creds, self.wrap)

    def test_get_file_stdout(self):
        self.wrap.get_doc.return_value = 'the_content'
        with mock.patch('sys.stdout') as buf_mock:
            self.instance.main(['get', '--id=12345'])

            buf_mock.write.assert_called_once_with('the_content')
            self.wrap.get_doc.assert_called_once_with('12345')

    def test_get_file_to_file(self):
        """Test saving a file to local FS."""
        self.wrap.get_doc.return_value = 'the_content'
        self.instance.main(['get', '--id=12345', '--output=tst.txt'])

        self.wrap.get_doc.assert_called_once_with('12345')
        actual_content = self.fs.get_object('tst.txt').contents
        self.assertEqual('the_content', actual_content)

    def test_get_file_to_file_dry_run(self):
        """Test saving locally in dry run."""
        self.wrap.get_doc.return_value = 'the_content'
        self.instance.main(
            ['get', '--dry_run', '--id=12345', '--output=tst.txt']
        )

        self.wrap.get_doc.assert_called_once_with('12345')
        self.assertFalse(self.fs.exists('tst.txt'))

    @mock.patch('rxllmproc.cli.cli_base.sys.exit')
    def test_get_no_id(self, exit_mock: mock.Mock):
        """Test passing no ID option."""
        self.wrap.get_doc.return_value = b'the_content'
        self.instance.main(['get', '--output=tst.txt'])

        self.wrap.get_doc.assert_not_called()
        exit_mock.assert_called_once_with(2)

    @mock.patch('rxllmproc.cli.cli_base.sys.exit')
    def test_get_no_drive_file(self, exit_mock: mock.Mock):
        """Test with missing doc on Drive."""
        exception = mock.Mock(errors.HttpError)
        exception.reason = 'some reason'
        exception.status = 404
        self.wrap.get_doc.side_effect = errors.HttpError(exception, b'{}')
        stderr_capture = io.StringIO()

        with contextlib.redirect_stderr(stderr_capture):
            self.instance.main(['get', '--id=12345'])

        self.wrap.get_doc.assert_called_once_with('12345')
        exit_mock.assert_called_once_with(30)
        self.assertIn('some reason', stderr_capture.getvalue())

    def test_list_stdout(self):
        """Test listing to stdout."""
        list_items = [
            {
                'id': 'the_id1',
                'name': 'the_name1',
                'mimeType': 'text/html',
                'description': 'blah',
                'md5Checksum': '12345',
                'modifiedTime': 'some_time',
            },
            {
                'id': 'the_id2',
                'name': 'the_name2.pdf',
                'fileExtension': '.pdfblah',
                'mimeType': 'application/pdf',
                'md5Checksum': '67890',
                'modifiedTime': 'some_time2',
            },
        ]
        self.wrap.list.return_value = list_items

        expected = (
            'id\tname\tfileExtension\tmimeType\t'
            'description\tmd5Checksum\tmodifiedTime\n'
            'the_id1\tthe_name1\t.html\ttext/html\t'
            'blah\t12345\tsome_time\n'
            'the_id2\tthe_name2.pdf\t.pdfblah\tapplication/pdf\t'
            '\t67890\tsome_time2\n'
        )
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.instance.main(['list', 'the_query'])

        self.assertEqual(expected, stdout_capture.getvalue())
        self.wrap.list.assert_called_once_with('the_query')

    @mock.patch('rxllmproc.cli.cli_base.sys.exit')
    def test_list_stdout_bad_api(self, exit_mock: mock.Mock):
        """Test listing to stdout when API fails."""
        exception = mock.Mock(errors.HttpError)
        exception.reason = 'some reason'
        exception.status = 404
        self.wrap.list.side_effect = errors.HttpError(exception, b'{}')

        self.instance.main(['list', 'the_query'])

        self.wrap.list.assert_called_once_with('the_query')
        exit_mock.assert_called_once_with(30)

    @mock.patch('rxllmproc.cli.cli_base.sys.stdin')
    def test_put_file_from_stdin(self, stdin_mock: mock.Mock):
        """Test putting a file from stdin."""
        input_io = io.BytesIO(b'the_content')
        stdin_mock.buffer = input_io

        self.wrap.get_file.return_value = types.File(id='12345')
        self.instance.main(
            ['put', '--update_id=12345', '--mime_type=text/plain']
        )

        self.wrap.update_file.assert_called_once_with(
            mock.ANY, '12345', 'text/plain'
        )

        self.wrap.create_file.assert_not_called()

        self.assertEqual(
            b'the_content', self.wrap.update_file.call_args[0][0].getvalue()
        )

    def test_put_file_from_file(self):
        """Test putting a file from local file."""
        self.fs.create_file('in.txt', contents='the_content')

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.wrap.get_file.return_value = types.File(id='123456')
            self.instance.main(['put', '--update_id=12345', 'in.txt'])

        self.assertEqual('123456\n', stdout_capture.getvalue())

        self.wrap.get_file.assert_called_once_with('12345', None)
        self.wrap.update_file.assert_called_once_with(
            mock.ANY, '123456', 'text/plain'
        )

        self.wrap.create_file.assert_not_called()

        self.assertEqual(
            b'the_content', self.wrap.update_file.call_args[0][0].getvalue()
        )

    def test_put_file_from_file_dry_run(self):
        """Test updating a file in dry_run."""
        self.fs.create_file('in.txt', contents='the_content')

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.wrap.get_file.return_value = types.File(id='123456')
            self.instance.main(
                ['put', '--dry_run', '--update_id=12345', 'in.txt']
            )

        self.assertEqual('123456\n', stdout_capture.getvalue())

        self.wrap.get_file.assert_called_once_with('12345', None)
        self.wrap.update_file.assert_not_called()
        self.wrap.create_file.assert_not_called()

    def test_put_file_from_file_by_name(self):
        """Test updating a file by name."""
        self.fs.create_file('in.txt', contents='the_content')

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.wrap.get_file.return_value = types.File(id='123456')
            self.instance.main(['put', '--update_name=the_name', 'in.txt'])

        self.assertEqual('123456\n', stdout_capture.getvalue())

        self.wrap.get_file.assert_called_once_with(None, 'the_name')
        self.wrap.update_file.assert_called_once_with(
            mock.ANY, '123456', 'text/plain'
        )

        self.wrap.create_file.assert_not_called()

        self.assertEqual(
            b'the_content', self.wrap.update_file.call_args[0][0].getvalue()
        )

    def test_put_file_from_file_create(self):
        """Test creating a file, all derived from local filename."""
        self.fs.create_file('in.txt', contents='the_content')

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.wrap.create_file.return_value = types.File(id='123456')
            self.instance.main(['put', 'in.txt'])

        self.assertEqual('123456\n', stdout_capture.getvalue())

        self.wrap.create_file.assert_called_with(
            mock.ANY, 'in.txt', 'text/plain'
        )
        self.wrap.get_file.assert_not_called()

        self.assertEqual(
            b'the_content', self.wrap.create_file.call_args[0][0].getvalue()
        )

    def test_put_file_from_file_create_with_flags(self):
        """Test creating a file, supplying details through flags."""
        self.fs.create_file('in.txt', contents='the_content')

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.wrap.create_file.return_value = types.File(id='123456')
            self.instance.main(
                [
                    'put',
                    '--create_name=file_name',
                    '--mime_type=application/pdf',
                    'in.txt',
                ]
            )

        self.assertEqual('123456\n', stdout_capture.getvalue())

        self.wrap.create_file.assert_called_with(
            mock.ANY, 'file_name', 'application/pdf'
        )
        self.wrap.get_file.assert_not_called()

        self.assertEqual(
            b'the_content', self.wrap.create_file.call_args[0][0].getvalue()
        )

    def test_put_file_from_file_create_dry_run(self):
        """Test creating a file in dry_run."""
        self.fs.create_file('in.txt', contents='the_content')

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.wrap.create_file.return_value = types.File(id='123456')
            self.instance.main(['put', '--dry_run', 'in.txt'])

        self.assertEqual('--new-file--\n', stdout_capture.getvalue())

        self.wrap.create_file.assert_not_called()
        self.wrap.get_file.assert_not_called()

    @mock.patch('rxllmproc.cli.cli_base.sys.exit')
    def test_put_file_from_file_by_name_not_existing(
        self, exit_mock: mock.Mock
    ):
        """Test updating by name with name not existing."""
        self.fs.create_file('in.txt', contents='the_content')

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.wrap.get_file.return_value = None
            self.instance.main(['put', '--update_name=the_name', 'in.txt'])

        self.wrap.get_file.assert_called_once_with(None, 'the_name')
        self.wrap.update_file.assert_not_called()
        self.wrap.create_file.assert_not_called()
        exit_mock.assert_called_once_with(30)

    @mock.patch('rxllmproc.cli.cli_base.sys.exit')
    def test_put_file_from_file_fail_api(self, exit_mock: mock.Mock):
        """Test updating with API failure."""
        self.fs.create_file('in.txt', contents='the_content')

        exception = mock.Mock(errors.HttpError)
        exception.reason = 'some reason'
        exception.status = 404
        self.wrap.get_file.side_effect = errors.HttpError(exception, b'{}')

        self.instance.main(['put', '--update_id=12345', 'in.txt'])

        exit_mock.assert_called_once_with(30)
