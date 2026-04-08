"""Types used with the GMail REST interface."""

from typing import Any, Protocol, Literal
import pydantic

from rxllmproc.gmail import types


class GmailHttpRequestInterface(Protocol):
    """Partial and type anostic request interface."""

    def execute(self) -> Any:
        """Execute the formed request."""


class GmailMessagesInterface(Protocol):
    """message() API part."""

    def get(
        self,
        *,
        userId: str,
        id: str,
        format: Literal['minimal', 'full', 'raw', 'metadata'] = ...,
        metadataHeaders: Any = ...,
        **kwargs: Any,
    ) -> GmailHttpRequestInterface:
        """Get a message."""
        ...

    def list(
        self,
        *,
        userId: str,
        includeSpamTrash: bool = ...,
        labelIds: str | list[str] = ...,
        maxResults: int = ...,
        pageToken: str = ...,
        q: str = ...,
        **kwargs: Any,
    ) -> GmailHttpRequestInterface:
        """Return matching message IDs."""
        ...

    def send(
        self, *, userId: str, body: Any = ..., **kwargs: Any
    ) -> GmailHttpRequestInterface:
        """Sedn an email."""
        ...


class GmailUsersInterface(Protocol):
    """users() API part."""

    def messages(self) -> GmailMessagesInterface:
        """Get the messages API."""
        ...

    def getProfile(
        self, *, userId: str, **kwargs: Any
    ) -> GmailHttpRequestInterface:
        """Get the profile of a user."""
        ...


class GmailInterface(Protocol):
    """Top level GMail API interface."""

    def users(self) -> GmailUsersInterface:
        """Get the users API part."""
        ...


class ListMessageResponse(pydantic.BaseModel):
    """Response for messages().list()."""

    model_config = pydantic.ConfigDict(extra='ignore')

    messages: list[types.MessageId] = pydantic.Field(default_factory=lambda: [])
    nextPageToken: str = ''


class Profile(pydantic.BaseModel):
    """User profile returned in users API part."""

    model_config = pydantic.ConfigDict(extra='ignore')

    emailAddress: str
