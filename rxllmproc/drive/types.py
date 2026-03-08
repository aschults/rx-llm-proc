"""Google Drive classes used in steps."""

from typing import Any, TypedDict


class File(TypedDict, total=False):
    """GDrive file as defined by the REST interface."""

    appProperties: dict[str, Any]
    capabilities: dict[str, Any]
    contentHints: dict[str, Any]
    contentRestrictions: Any
    copyRequiresWriterPermission: bool
    createdTime: str
    description: str
    driveId: str
    explicitlyTrashed: bool
    exportLinks: dict[str, Any]
    fileExtension: str
    folderColorRgb: str
    fullFileExtension: str
    hasAugmentedPermissions: bool
    hasThumbnail: bool
    headRevisionId: str
    iconLink: str
    id: str
    imageMediaMetadata: dict[str, Any]
    isAppAuthorized: bool
    kind: str
    labelInfo: dict[str, Any]
    lastModifyingUser: Any
    linkShareMetadata: dict[str, Any]
    md5Checksum: str
    mimeType: str
    modifiedByMe: bool
    modifiedByMeTime: str
    modifiedTime: str
    name: str
    originalFilename: str
    ownedByMe: bool
    owners: Any
    parents: list[str]
    permissionIds: list[str]
    permissions: Any
    properties: dict[str, Any]
    quotaBytesUsed: str
    resourceKey: str
    sha1Checksum: str
    sha256Checksum: str
    shared: bool
    sharedWithMeTime: str
    sharingUser: Any
    shortcutDetails: dict[str, Any]
    size: str
    spaces: list[str]
    starred: bool
    teamDriveId: str
    thumbnailLink: str
    thumbnailVersion: str
    trashed: bool
    trashedTime: str
    trashingUser: Any
    version: str
    videoMediaMetadata: dict[str, Any]
    viewedByMe: bool
    viewedByMeTime: str
    viewersCanCopyContent: bool
    webContentLink: str
    webViewLink: str
    writersCanShare: bool
    downloadRestrictions: Any
    inheritedPermissionsDisabled: bool
