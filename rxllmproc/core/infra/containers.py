"""Representation of a containers to read/write data from/to."""

from typing import Protocol, runtime_checkable, Any
import os.path
import os
import mimetypes

from rxllmproc.drive.api import DriveWrap

import dateutil.parser


@runtime_checkable
class Container(Protocol):
    """Interface, allowing to get and put data."""

    def get(self) -> str:
        """Get the content stored in the container."""
        ...

    def put(self, content: str):
        """Replace the content in the container."""
        ...

    def exists(self) -> bool:
        """Check if the container exists."""
        ...

    def modified_time_us(self) -> int:
        """Find out when the container was last modified."""
        ...

    def mime_type(self) -> str:
        """Get the MIME type of the container."""
        ...


class DriveFileContainer(Container):
    """Represent a GDrive file."""

    def __init__(
        self,
        service: DriveWrap,
        mime_type: str,
        filename: str | None = None,
        file_id: str | None = None,
    ) -> None:
        """Create an instance.

        Args:
            service: Drive wrapper instance.
            mime_type: Mime type of the container's content.
            filename: Human readable name of the file, not unique.
            file_id: Unique file id of the file.
                Note: Exactly one filename or file_id can be provided.
        """
        super().__init__()
        self.service = service
        self._mime_type = mime_type
        self.filename = filename
        self.file_id = file_id

    def exists(self) -> bool:
        """Check if the container exists."""
        file_obj = self.service.get_file(
            filename=self.filename,
            file_id=self.file_id,
            mime_type=self._mime_type,
        )
        return file_obj is not None

    def get(self) -> str:
        """Download the GDrive file."""
        file_obj = self.service.get_file(
            filename=self.filename,
            file_id=self.file_id,
            mime_type=self._mime_type,
        )
        if not file_obj:
            raise Exception()

        return self.service.get_doc(
            file_id=file_obj.get('id', '---none--'),
            mime_type=self._mime_type,
        )

    def put(self, content: str):
        """Upload the GDrive file."""
        self.service.update_or_create(
            content,
            self._mime_type,
            self.filename,
            file_id=self.file_id,
        )

    def modified_time_us(self) -> int:
        """Fetch the last modified date."""
        file_obj = self.service.get_file(
            filename=self.filename,
            file_id=self.file_id,
            mime_type=self._mime_type,
        )
        if not file_obj:
            raise Exception()

        date_str = file_obj.get('modifiedTime')
        if not date_str:
            raise Exception()
        date_obj = dateutil.parser.isoparse(date_str)
        return int(date_obj.timestamp() * 1000 * 1000)

    def url(self) -> str:
        """Return the URL to the file."""
        if not self.file_id:
            raise Exception('no file set')
        return f'https://docs.google.com/document/d/{self.file_id}/edit'

    def asdict(self) -> dict[str, Any]:
        """Return dict representation."""
        return {
            'mime_type': self._mime_type,
            'filename': self.filename,
            'file_id': self.file_id,
        }

    def mime_type(self) -> str:
        """Get the MIME type of the container."""
        return self._mime_type


class LocalFileContainer(Container):
    """Represent a local file."""

    def __init__(self, filename: str) -> None:
        """Create an instance."""
        self.filename = filename

    def get(self) -> str:
        """Read the file content."""
        with open(self.filename, 'r') as handle:
            return handle.read()

    def put(self, content: str):
        """Write the file content."""
        with open(self.filename, 'w') as handle:
            handle.write(content)

    def exists(self) -> bool:
        """Check if file exists."""
        return os.path.isfile(self.filename)

    def modified_time_us(self) -> int:
        """Fetch mtime from stats."""
        return os.stat(self.filename).st_mtime_ns // 1000

    def mime_type(self) -> str:
        """Get the MIME type of the container."""
        mime_type, _ = mimetypes.guess_type(self.filename)
        return mime_type or 'application/octet-stream'

    def asdict(self) -> dict[str, Any]:
        """Return dict representation."""
        return {'filename': self.filename}
