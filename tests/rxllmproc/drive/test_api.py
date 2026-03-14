"""Test the API wrapper for GDrive."""

from typing import Any
import unittest
from unittest import mock
import io

from google.oauth2 import credentials  # type: ignore
from googleapiclient import http

from rxllmproc.drive import api, _interface


class TestWrapper(unittest.TestCase):
    """Test the wrapper class."""

    def setUp(self) -> None:
        """Providde credentials, a mocked API interface and a wrapper."""
        self.creds = mock.Mock(spec=credentials.Credentials)
        self.service = mock.Mock(spec=_interface.DriveInterface)

        self.wrap = api.DriveWrap(self.creds, self.service)
        return super().setUp()

    def test_list(self):
        """Test the list function."""
        self.service.files().list().execute.return_value = {'files': ['1']}
        self.assertEqual(['1'], self.wrap.list('theq'))
        self.service.files().list.assert_called_with(q='theq', fields=mock.ANY)

    def test_get_file(self):
        """Test the get file function (by ID)."""
        self.service.files().get().execute.return_value = {'id': '1111'}
        self.assertEqual({'id': '1111'}, self.wrap.get_file(file_id='1234'))
        self.service.files().get.assert_called_with(
            fileId='1234', fields=mock.ANY
        )

    def test_get_file_by_name(self):
        """Test the get file function (by name)."""
        self.service.files().list().execute.return_value = {
            'files': [{'id': '1234'}]
        }
        self.assertEqual({'id': '1234'}, self.wrap.get_file(filename='abc'))
        self.service.files().list.assert_called_with(
            q='name = \'abc\'', fields=mock.ANY
        )
        self.service.files().get.assert_not_called()

    def test_get_file_by_name_with_mimetype(self):
        """Test get file function (name and mime type)."""
        self.service.files().list().execute.return_value = {
            'files': [{'id': '1234'}]
        }
        self.assertEqual(
            {'id': '1234'}, self.wrap.get_file(filename='abc', mime_type='xxx')
        )
        self.service.files().list.assert_called_with(
            q='name = \'abc\' and mimeType = \'xxx\'', fields=mock.ANY
        )
        self.service.files().get.assert_not_called()

    def test_get_doc(self):
        """Test getting a Google Doc."""
        self.service.files().export_media().execute.return_value = b'123'
        self.assertEqual('123', self.wrap.get_doc('111'))
        self.service.files().export_media.assert_called_with(
            fileId='111', mimeType='text/html'
        )

    def test_create_file(self):
        """Test crreating a file on Drive."""
        self.service.files().create().execute.return_value = '123'

        instr = io.BytesIO(b'abcde')
        self.assertEqual('123', self.wrap.create_file(instr, 'thefn', 'x/y'))
        self.assertEqual(
            {'name': 'thefn', 'mimeType': 'x/y'},
            self.service.files().create.call_args[1]['body'],
        )
        uploader: http.MediaIoBaseUpload = (
            self.service.files().create.call_args[1]['media_body']
        )
        uploader_content: Any = uploader.getbytes(0, 5)  # type: ignore
        self.assertEqual(b'abcde', uploader_content)

    def test_update_file(self):
        """Test the update file function."""
        self.service.files().update().execute.return_value = '123'

        instr = io.BytesIO(b'abcde')
        self.wrap.update_file(instr, 'theid', 'x/y')
        self.assertEqual(
            'theid', self.service.files().update.call_args[1]['fileId']
        )
        uploader: http.MediaIoBaseUpload = (
            self.service.files().update.call_args[1]['media_body']
        )
        uploader_content: Any = uploader.getbytes(0, 5)  # type: ignore
        self.assertEqual(b'abcde', uploader_content)

    def test_update_or_create_existing(self):
        """Test updating or creating a file on existing file."""
        with mock.patch.object(api.DriveWrap, 'get_file') as get_file_mock:
            with mock.patch.object(
                api.DriveWrap, 'create_file'
            ) as create_file_mock:
                with mock.patch.object(
                    api.DriveWrap, 'update_file'
                ) as update_file_mock:
                    get_file_mock.return_value = {'id': '123'}
                    self.wrap = api.DriveWrap(self.creds, self.service)
                    instr = io.BytesIO(b'abcde')

                    self.wrap.update_or_create(instr, 'x/y', 'thefn')
                    create_file_mock.assert_not_called()
                    update_file_mock.assert_called_with(instr, '123', 'x/y')

    def test_update_or_create_new(self):
        """Test updating or creating a file for new file."""
        with mock.patch.object(api.DriveWrap, 'get_file') as get_file_mock:
            with mock.patch.object(
                api.DriveWrap, 'create_file'
            ) as create_file_mock:
                with mock.patch.object(
                    api.DriveWrap, 'update_file'
                ) as update_file_mock:
                    get_file_mock.return_value = None
                    self.wrap = api.DriveWrap(self.creds, self.service)
                    instr = io.BytesIO(b'abcde')

                    self.wrap.update_or_create(instr, 'x/y', 'thefn')
                    update_file_mock.assert_not_called()
                    create_file_mock.assert_called_with(instr, 'thefn', 'x/y')
