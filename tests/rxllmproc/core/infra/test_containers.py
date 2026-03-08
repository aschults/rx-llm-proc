"""Test the container classes."""

import unittest
from unittest import mock

from pyfakefs import fake_filesystem_unittest  # type: ignore
import rxllmproc.core.infra.containers
from rxllmproc.drive import types
from rxllmproc.drive import api


class TestDriveContainer(unittest.TestCase):
    """Test the GDrive container."""

    def setUp(self) -> None:
        """Provide mock service wrapper."""
        self.service = mock.Mock(spec=api.DriveWrap)
        return super().setUp()

    def test_get(self):
        """Test getting the content by name."""
        self.service.get_doc.return_value = b'abc'
        self.service.get_file.return_value = {'id': 'theid'}
        container = rxllmproc.core.infra.containers.DriveFileContainer(
            self.service, 'x/y', 'filenm'
        )
        self.assertEqual(b'abc', container.get())
        self.service.get_file.assert_called_with(
            filename='filenm', file_id=None, mime_type='x/y'
        )
        self.service.get_doc.assert_called_with(
            file_id='theid', mime_type='x/y'
        )

    def test_get_by_id(self):
        """Test getting the content by ID."""
        self.service.get_doc.return_value = b'abc'
        self.service.get_file.return_value = {'id': 'theid'}
        container = rxllmproc.core.infra.containers.DriveFileContainer(
            self.service, 'x/y', file_id='theid2'
        )
        self.assertEqual(b'abc', container.get())
        self.service.get_file.assert_called_with(
            filename=None, file_id='theid2', mime_type='x/y'
        )
        self.service.get_doc.assert_called_with(
            file_id='theid', mime_type='x/y'
        )

    def test_put(self):
        """Test writing the content by name."""
        container = rxllmproc.core.infra.containers.DriveFileContainer(
            self.service, 'x/y', 'filenm'
        )
        container.put('abc')
        self.service.update_or_create.assert_called_with(
            'abc',
            'x/y',
            'filenm',
            file_id=None,
        )

    def test_put_by_id(self):
        """Test writing the content by ID."""
        container = rxllmproc.core.infra.containers.DriveFileContainer(
            self.service, 'x/y', file_id='theid2'
        )
        container.put('abc')
        self.service.update_or_create.assert_called_with(
            'abc',
            'x/y',
            None,
            file_id='theid2',
        )

    def test_get_mtime(self):
        """Test getting the modification time."""
        self.service.get_file.return_value = types.File(
            id='theid', modifiedTime='2000-01-01T00:00:00.100Z'
        )
        container = rxllmproc.core.infra.containers.DriveFileContainer(
            self.service, 'x/y', 'filenm'
        )
        self.assertEqual(946684800100000, container.modified_time_us())

    def test_exists(self):
        """Test the exists function."""
        self.service.get_file.side_effect = [types.File(id='theid'), None]
        container = rxllmproc.core.infra.containers.DriveFileContainer(
            self.service, 'x/y', 'filenm'
        )
        self.assertTrue(container.exists())
        self.assertFalse(container.exists())


class TestLocalFileContainer(fake_filesystem_unittest.TestCase):
    """Test the local file container class."""

    def setUp(self) -> None:
        """Set up fake filesystem."""
        super().setUp()
        self.setUpPyfakefs()

    def test_get(self):
        """Test getting the file content."""
        self.fs.create_file(  # type: ignore
            file_path='/blah',
            contents='whatever',
        )
        container = rxllmproc.core.infra.containers.LocalFileContainer('/blah')

        self.assertEqual('whatever', container.get())

    def test_exists(self):
        """Test the exists function."""
        self.fs.create_file(  # type: ignore
            file_path='/blah',
            contents='whatever',
        )
        container = rxllmproc.core.infra.containers.LocalFileContainer('/blah')
        self.assertTrue(container.exists())

    def test_not_exists(self):
        """Test the exists function, file not existing."""
        container = rxllmproc.core.infra.containers.LocalFileContainer('/blah')
        self.assertFalse(container.exists())

    def test_modified(self):
        """Test getting the modification time."""
        self.fs.create_file(  # type: ignore
            file_path='/blah',
            contents='whatever',
        )
        self.fs.utime('/blah', times=(123, 111))
        container = rxllmproc.core.infra.containers.LocalFileContainer('/blah')

        self.assertEqual(111000000, container.modified_time_us())
