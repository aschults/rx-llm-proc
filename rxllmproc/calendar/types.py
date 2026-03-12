"""Google Calendar classes used in steps."""

import dataclasses
from typing import Any


@dataclasses.dataclass
class EventDateTime:
    """Date and time of an event."""

    date: str | None = None
    dateTime: str | None = None
    timeZone: str | None = None


@dataclasses.dataclass
class EventAttendee:
    """Attendee of an event."""

    email: str | None = None
    displayName: str | None = None
    organizer: bool | None = None
    self: bool | None = None
    resource: bool | None = None
    optional: bool | None = None
    responseStatus: str | None = None
    comment: str | None = None
    additionalGuests: int | None = None


@dataclasses.dataclass
class EventReminder:
    """Reminder for an event."""

    method: str | None = None
    minutes: int | None = None


@dataclasses.dataclass
class EventReminders:
    """Reminders for an event."""

    useDefault: bool | None = None
    overrides: list[EventReminder] = dataclasses.field(
        default_factory=lambda: []
    )


@dataclasses.dataclass
class EventAttachment:
    """Attachment of an event."""

    fileUrl: str | None = None
    title: str | None = None
    mimeType: str | None = None
    iconLink: str | None = None
    fileId: str | None = None


@dataclasses.dataclass
class Event:
    """Represents one calendar event."""

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
    attendees: list[EventAttendee] = dataclasses.field(
        default_factory=lambda: []
    )
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
    attachments: list[EventAttachment] = dataclasses.field(
        default_factory=lambda: []
    )
    eventType: str | None = None
