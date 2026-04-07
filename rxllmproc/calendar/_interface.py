"""Types used with the Google Calendar REST interface."""

from typing import Any, Protocol, Literal
from pydantic import BaseModel, Field, ConfigDict
from rxllmproc.calendar import types


class EventsList(BaseModel):
    """Response for events().list()."""

    model_config = ConfigDict(extra='ignore')

    kind: str = "calendar#events"
    etag: str | None = None
    summary: str | None = None
    description: str | None = None
    updated: str | None = None
    timeZone: str | None = None
    accessRole: str | None = None
    defaultReminders: list[types.EventReminder] = Field(
        default_factory=lambda: []
    )
    nextPageToken: str | None = None
    nextSyncToken: str | None = None
    items: list[types.Event] = Field(default_factory=lambda: [])


class CalendarHttpRequestInterface(Protocol):
    """Partial and type agnostic request interface."""

    def execute(self) -> Any:
        """Execute the formed request."""


class EventsInterface(Protocol):
    """events() API part."""

    def get(
        self,
        *,
        calendarId: str,
        eventId: str,
        maxAttendees: int = ...,
        timeZone: str = ...,
        **kwargs: Any,
    ) -> CalendarHttpRequestInterface:
        """Get an event."""
        ...

    def list(
        self,
        *,
        calendarId: str,
        iCalUID: str = ...,
        maxAttendees: int = ...,
        maxResults: int = ...,
        orderBy: Literal["startTime", "updated"] = ...,
        pageToken: str = ...,
        privateExtendedProperty: str | list[str] = ...,
        q: str = ...,
        sharedExtendedProperty: str | list[str] = ...,
        showDeleted: bool = ...,
        showHiddenInvitations: bool = ...,
        singleEvents: bool = ...,
        timeMax: str = ...,
        timeMin: str = ...,
        timeZone: str = ...,
        updatedMin: str = ...,
        **kwargs: Any,
    ) -> CalendarHttpRequestInterface:
        """List events."""
        ...

    def insert(
        self,
        *,
        calendarId: str,
        body: Any,
        conferenceDataVersion: int = ...,
        maxAttendees: int = ...,
        sendUpdates: Literal["all", "externalOnly", "none"] = ...,
        supportsAttachments: bool = ...,
        **kwargs: Any,
    ) -> CalendarHttpRequestInterface:
        """Create a new event."""
        ...

    def update(
        self,
        *,
        calendarId: str,
        eventId: str,
        body: Any,
        conferenceDataVersion: int = ...,
        maxAttendees: int = ...,
        sendUpdates: Literal["all", "externalOnly", "none"] = ...,
        supportsAttachments: bool = ...,
        **kwargs: Any,
    ) -> CalendarHttpRequestInterface:
        """Update an event."""
        ...

    def patch(
        self,
        *,
        calendarId: str,
        eventId: str,
        body: Any,
        conferenceDataVersion: int = ...,
        maxAttendees: int = ...,
        sendUpdates: Literal["all", "externalOnly", "none"] = ...,
        supportsAttachments: bool = ...,
        **kwargs: Any,
    ) -> CalendarHttpRequestInterface:
        """Patch an event."""
        ...

    def delete(
        self,
        *,
        calendarId: str,
        eventId: str,
        sendUpdates: Literal["all", "externalOnly", "none"] = ...,
        **kwargs: Any,
    ) -> CalendarHttpRequestInterface:
        """Delete an event."""
        ...


class CalendarInterface(Protocol):
    """Top level Calendar API interface."""

    def events(self) -> EventsInterface:
        """Get the events API part."""
        ...
