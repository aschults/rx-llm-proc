"""Types used with the Drive REST interface."""

from typing import Any, Protocol, Literal, TypedDict

from rxllmproc.drive.types import File


class FileList(TypedDict, total=False):
    """File List returned by Drive API."""

    files: list[File]
    incompleteSearch: bool
    kind: str
    nextPageToken: str


class Request(Protocol):
    """Partial and type anostic request interface."""

    def execute(self) -> Any:
        """Execute the formed request."""


class FilesInterface(Protocol):
    """files() API interface."""

    def get(
        self,
        *,
        fileId: str,
        acknowledgeAbuse: bool = ...,
        includeLabels: str = ...,
        includePermissionsForView: str = ...,
        supportsAllDrives: bool = ...,
        supportsTeamDrives: bool = ...,
        **kwargs: Any,
    ) -> Request:
        """Get a file."""
        ...

    def create(
        self,
        *,
        body: File = ...,
        enforceSingleParent: bool = ...,
        ignoreDefaultVisibility: bool = ...,
        includeLabels: str = ...,
        includePermissionsForView: str = ...,
        keepRevisionForever: bool = ...,
        ocrLanguage: str = ...,
        supportsAllDrives: bool = ...,
        supportsTeamDrives: bool = ...,
        useContentAsIndexableText: bool = ...,
        **kwargs: Any,
    ) -> Request:
        """Create a new file."""
        ...

    def export_media(
        self, *, fileId: str, mimeType: str, **kwargs: Any
    ) -> Request:
        """Export with different mime type."""
        ...

    def get_media(
        self,
        *,
        fileId: str,
        acknowledgeAbuse: bool = ...,
        includeLabels: str = ...,
        includePermissionsForView: str = ...,
        supportsAllDrives: bool = ...,
        supportsTeamDrives: bool = ...,
        **kwargs: Any,
    ) -> Request:
        """Download the file content."""
        ...

    def list(
        self,
        *,
        corpora: str = ...,
        corpus: Literal["domain", "user"] = ...,
        driveId: str = ...,
        includeItemsFromAllDrives: bool = ...,
        includeLabels: str = ...,
        includePermissionsForView: str = ...,
        includeTeamDriveItems: bool = ...,
        orderBy: str = ...,
        pageSize: int = ...,
        pageToken: str = ...,
        q: str = ...,
        spaces: str = ...,
        supportsAllDrives: bool = ...,
        supportsTeamDrives: bool = ...,
        teamDriveId: str = ...,
        **kwargs: Any,
    ) -> Request:
        """List all matching files."""
        ...

    def update(
        self,
        *,
        fileId: str,
        body: File = ...,
        addParents: str = ...,
        enforceSingleParent: bool = ...,
        includeLabels: str = ...,
        includePermissionsForView: str = ...,
        keepRevisionForever: bool = ...,
        ocrLanguage: str = ...,
        removeParents: str = ...,
        supportsAllDrives: bool = ...,
        supportsTeamDrives: bool = ...,
        useContentAsIndexableText: bool = ...,
        **kwargs: Any,
    ) -> Request:
        """Update file metadata and file."""
        ...


class DriveInterface(Protocol):
    """Top level Drive API."""

    def files(self) -> FilesInterface:
        """Return the files API part."""
        ...
