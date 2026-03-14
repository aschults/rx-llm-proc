"""Google Drive REST interface wrapper."""

import io
import logging
from typing import IO, cast

from googleapiclient import discovery, http

from rxllmproc.drive import types
from rxllmproc.core import auth, api_base
from rxllmproc.drive import _interface


class FileNotFoundInDriveError(IOError):
    """Raised when a file is not found in Google Drive."""


class DriveWrap(api_base.ApiBase):
    """Wrapper around Drive API."""

    def __init__(
        self,
        creds: auth.Credentials | None = None,
        service: _interface.DriveInterface | None = None,
    ):
        """Create an instance.

        Args:
            creds: Credentials to be used for the requests.
            service: Optionally provide service instance (mainly for testing.)
                Note: If provided, this instance is shared across threads and
                is not thread-safe.
        """
        super().__init__(creds)
        self._service: _interface.DriveInterface = service or discovery.build(
            'drive',
            'v3',
            credentials=self._creds,
            requestBuilder=self.build_request,
        )

    _FILE_FIELDS = 'id,name,modifiedTime,mimeType,md5Checksum,fileExtension'

    def get_file(
        self,
        file_id: str | None = None,
        filename: str | None = None,
        mime_type: str | None = None,
    ) -> types.File | None:
        """Get File metadata by file ID or filename.

        Args:
            file_id: The ID of the file.
            filename: The name of the file.
            mime_type: The MIME type to filter by when searching by filename.

        Returns:
            The file metadata dictionary or None if not found.

        Raises:
            ValueError: If neither file_id nor filename is provided.
        """
        if file_id:
            return (
                self._service.files()
                .get(fileId=file_id, fields=self._FILE_FIELDS)
                .execute()
            )
        elif filename:
            # Escape single quotes in filename
            safe_filename = filename.replace("'", "\\'")
            q = f"name = '{safe_filename}'"
            if mime_type:
                q += f' and mimeType = \'{mime_type}\''
            file_list = self.list(q)
            if len(file_list) == 1:
                return file_list[0]
            if len(file_list) > 1:
                logging.warning(
                    'Found multiple files named %s, returning None', filename
                )
            return None
        else:
            raise ValueError("Either file_id or filename must be provided.")

    def list(self, q: str) -> list[types.File]:
        """Find specific files and get their metadata."""
        resp: _interface.FileList = (
            self._service.files()
            .list(q=q, fields=f'files({self._FILE_FIELDS})')
            .execute()
        )
        return resp.get('files', [])

    def get_doc(self, file_id: str, mime_type: str | None = 'text/html') -> str:
        """Download the content of a Docs file as HTML."""
        kwargs = {'fileId': file_id}
        if mime_type:
            kwargs.update(mimeType=mime_type)
        result: bytes = self._service.files().export_media(**kwargs).execute()
        return result.decode('utf-8', 'ignore')

    def create_file(
        self,
        content: IO[bytes] | str,
        filename: str,
        mime_type: str,
    ) -> types.File:
        """Create a new file."""
        metadata: types.File = {
            'name': filename,
            'mimeType': mime_type,
        }
        if isinstance(content, str):
            content = io.BytesIO(content.encode())

        media_body = http.MediaIoBaseUpload(
            cast(io.IOBase, content), mime_type, resumable=True
        )
        return (
            self._service.files()
            .create(body=metadata, media_body=media_body)
            .execute()
        )

    def update_file(
        self,
        content: IO[bytes] | str,
        file_id: str,
        mime_type: str,
    ) -> None:
        """Update the content of a file."""
        if isinstance(content, str):
            content = io.BytesIO(content.encode())

        media_body = http.MediaIoBaseUpload(
            cast(io.IOBase, content), mimetype=mime_type, resumable=True
        )

        self._service.files().update(
            fileId=file_id, media_body=media_body
        ).execute()

    def update_or_create(
        self,
        content: IO[bytes] | str,
        mime_type: str,
        filename: str | None = None,
        file_id: str | None = None,
    ) -> types.File | None:
        """Update a file if exists, otherwise create a new one."""
        file_obj = self.get_file(
            filename=filename, file_id=file_id, mime_type=mime_type
        )
        if isinstance(content, str):
            content = io.BytesIO(content.encode())

        if file_obj is None:
            if not filename:
                raise ValueError("A filename is required to create a new file.")
            file_obj = self.create_file(
                content,
                filename,
                mime_type,
            )
        else:
            file_id = file_obj.get('id')
            if not file_id:
                raise ValueError("Existing file metadata is missing 'id'.")
            self.update_file(content, file_id, mime_type)

        return file_obj
