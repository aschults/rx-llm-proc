# pyright: basic
"""Test Google Drive CLI class `get_all` subcommand."""

from unittest import mock
from pyfakefs import fake_filesystem_unittest

from rxllmproc.drive import api
from rxllmproc.cli import gdrive_cli


class TestDriveCliGetAll(fake_filesystem_unittest.TestCase):
    """Test the Drive CLI class `get_all` subcommand."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

        self.creds = mock.Mock()
        self.wrap = mock.Mock(api.DriveWrap)
        self.instance = gdrive_cli.DriveCli(self.creds, self.wrap)

        self.file_list = [
            {'id': 'id1', 'name': 'file1.txt'},
            {'id': 'id2', 'name': 'file2.gdoc'},
        ]
        self.wrap.list.return_value = self.file_list

        def get_doc_side_effect(doc_id, mime_type=None):
            if doc_id == 'id1':
                return 'content1'
            if doc_id == 'id2':
                if mime_type == 'text/html' or not mime_type:
                    return '<h2>content2</h2>'
            return ''

        self.wrap.get_doc.side_effect = get_doc_side_effect

    def test_get_all_basic(self):
        """Test basic get_all functionality."""
        self.fs.create_dir('/output')
        self.instance.main(['get_all', 'some_query', '--output_dir=/output'])

        self.wrap.list.assert_called_once_with('some_query')
        self.assertEqual(self.wrap.get_doc.call_count, 2)
        self.wrap.get_doc.assert_any_call('id1')
        self.wrap.get_doc.assert_any_call('id2')

        self.assertTrue(self.fs.exists('/output/file1.txt'))
        self.assertTrue(self.fs.exists('/output/file2.gdoc'))
        self.assertEqual(
            self.fs.get_object('/output/file1.txt').contents, 'content1'
        )
        self.assertEqual(
            self.fs.get_object('/output/file2.gdoc').contents,
            '<h2>content2</h2>',
        )

    def test_get_all_dry_run(self):
        """Test get_all with --dry_run."""
        self.fs.create_dir('/output')
        self.instance.main(
            ['get_all', '--dry_run', 'some_query', '--output_dir=/output']
        )

        self.wrap.list.assert_called_once_with('some_query')
        self.wrap.get_doc.assert_not_called()
        self.assertFalse(self.fs.exists('/output/file1.txt'))
        self.assertFalse(self.fs.exists('/output/file2.gdoc'))

    def test_get_all_force(self):
        """Test get_all with --force to overwrite existing files."""
        self.fs.create_dir('/output')
        self.fs.create_file('/output/file1.txt', contents='old content')

        self.instance.main(
            ['get_all', '--force', 'some_query', '--output_dir=/output']
        )

        self.assertEqual(self.wrap.get_doc.call_count, 2)
        self.assertEqual(
            self.fs.get_object('/output/file1.txt').contents, 'content1'
        )

    def test_get_all_skip_existing(self):
        """Test that get_all skips existing files without --force."""
        self.fs.create_dir('/output')
        self.fs.create_file('/output/file1.txt', contents='old content')

        self.instance.main(['get_all', 'some_query', '--output_dir=/output'])

        # Only called for the non-existing file
        self.wrap.get_doc.assert_called_once_with('id2')
        self.assertEqual(
            self.fs.get_object('/output/file1.txt').contents, 'old content'
        )

    @mock.patch('rxllmproc.text_processing.converters.convert_html_to_markdown')
    def test_get_all_as_markdown(self, mock_convert):
        """Test get_all with --as_markdown conversion."""
        mock_convert.return_value = '## content2'
        self.fs.create_dir('/output')

        self.instance.main(
            ['get_all', '--as_markdown', 'some_query', '--output_dir=/output']
        )

        self.assertTrue(self.fs.exists('/output/file1.md'))
        self.assertTrue(self.fs.exists('/output/file2.md'))

        mock_convert.assert_any_call('<h2>content2</h2>')
        self.assertEqual(
            self.fs.get_object('/output/file2.md').contents, '## content2'
        )
