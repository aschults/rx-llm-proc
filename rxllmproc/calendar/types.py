"""Google Calendar classes used in steps."""

from typing import Any
import pydantic


class EventDateTime(pydantic.BaseModel):
    """Date and time of an event."""

    model_config = pydantic.ConfigDict(extra='ignore')

    date: str | None = None
    dateTime: str | None = None
    timeZone: str | None = None


class EventAttendee(pydantic.BaseModel):
    """Attendee of an event."""

    model_config = pydantic.ConfigDict(populate_by_name=True, extra='ignore')

    email: str | None = None
    displayName: str | None = None
    organizer: bool | None = None
    # NOTE: Calendar API uses `self` as attribute.
    is_self: bool | None = pydantic.Field(None, alias="self")
    resource: bool | None = None
    optional: bool | None = None
    responseStatus: str | None = None
    comment: str | None = None
    additionalGuests: int | None = None


class EventReminder(pydantic.BaseModel):
    """Reminder for an event."""

    model_config = pydantic.ConfigDict(extra='ignore')

    method: str | None = None
    minutes: int | None = None


class EventReminders(pydantic.BaseModel):
    """Reminders for an event."""

    model_config = pydantic.ConfigDict(extra='ignore')

    useDefault: bool | None = None
    overrides: list[EventReminder] = pydantic.Field(default_factory=lambda: [])


class EventAttachment(pydantic.BaseModel):
    """Attachment of an event."""

    model_config = pydantic.ConfigDict(extra='ignore')

    fileUrl: str | None = None
    title: str | None = None
    mimeType: str | None = None
    iconLink: str | None = None
    fileId: str | None = None


class Event(pydantic.BaseModel):
    """Represents one calendar event."""

    model_config = pydantic.ConfigDict(populate_by_name=True, extra='ignore')

    kind: str = "calendar#event"
    etag: str | None = None
    id: str | None = None
    status: str | None = None
    htmlLink: str | None = None
    created: str | None = None
    updated: str | None = None
    summary: str | None = None
    description: str | None = None
    location: str | None = None
    colorId: str | None = None
    creator: dict[str, Any] | None = None
    organizer: dict[str, Any] | None = None
    start: EventDateTime | None = None
    end: EventDateTime | None = None
    endTimeUnspecified: bool | None = None
    recurrence: list[str] | None = None
    recurringEventId: str | None = None
    originalStartTime: EventDateTime | None = None
    transparency: str | None = None
    visibility: str | None = None
    iCalUID: str | None = None
    sequence: int | None = None
    attendees: list[EventAttendee] = pydantic.Field(default_factory=lambda: [])
    attendeesOmitted: bool | None = None
    extendedProperties: dict[str, Any] | None = None
    hangoutLink: str | None = None
    conferenceData: dict[str, Any] | None = None
    gadget: dict[str, Any] | None = None
    anyoneCanAddSelf: bool | None = None
    guestsCanInviteOthers: bool | None = None
    guestsCanModify: bool | None = None
    guestsCanSeeOtherGuests: bool | None = None
    privateCopy: bool | None = None
    locked: bool | None = None
    reminders: EventReminders | None = None
    source: dict[str, Any] | None = None
    attachments: list[EventAttachment] = pydantic.Field(
        default_factory=lambda: []
    )
    eventType: str | None = None
