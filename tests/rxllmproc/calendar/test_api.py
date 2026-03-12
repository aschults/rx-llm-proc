"""Test the Google Calendar API wrapper."""

import unittest
from unittest import mock

from rxllmproc.calendar import api as calendar_wrapper
from rxllmproc.calendar import _interface as _calendar_interface
from rxllmproc.calendar import types as calendar_types


class TestCalendarWrapper(unittest.TestCase):
    """Test the CalendarWrap class."""

    def setUp(self) -> None:
        """Provide mock credentials and service."""
        self.creds = mock.Mock()
        self.service = mock.Mock(spec=_calendar_interface.CalendarInterface)
        return super().setUp()

    def test_search(self):
        """Test searching for events."""
        wrapper = calendar_wrapper.CalendarWrap(
            creds=self.creds, service=self.service
        )
        self.service.events().list().execute.return_value = {
            "items": [
                {"id": "event1", "summary": "Event 1"},
                {"id": "event2", "summary": "Event 2"},
            ]
        }

        result = wrapper.search(q="test query")

        self.assertEqual(2, len(result))
        self.assertEqual("event1", result[0].id)
        self.assertEqual("Event 1", result[0].summary)
        self.service.events().list.assert_called_with(
            calendarId="primary", q="test query"
        )

    def test_create(self):
        """Test creating an event."""
        wrapper = calendar_wrapper.CalendarWrap(
            creds=self.creds, service=self.service
        )
        event_to_create = calendar_types.Event(summary="New Event")
        self.service.events().insert().execute.return_value = {
            "id": "new_id",
            "summary": "New Event",
        }

        result = wrapper.create(event_to_create)

        self.assertEqual("new_id", result.id)
        self.assertEqual("New Event", result.summary)
        # Check that insert was called with the correct body (dict)
        self.service.events().insert.assert_called_with(
            calendarId="primary",
            body={
                "summary": "New Event",
                "kind": "calendar#event",
                "attendees": [],
                "attachments": [],
            },
        )

    def test_update(self):
        """Test updating an event."""
        wrapper = calendar_wrapper.CalendarWrap(
            creds=self.creds, service=self.service
        )
        event_to_update = calendar_types.Event(
            id="existing_id", summary="Updated Event"
        )
        self.service.events().update().execute.return_value = {
            "id": "existing_id",
            "summary": "Updated Event",
        }

        result = wrapper.update(event_to_update)

        self.assertEqual("existing_id", result.id)
        self.assertEqual("Updated Event", result.summary)
        self.service.events().update.assert_called_with(
            calendarId="primary",
            eventId="existing_id",
            body={
                "id": "existing_id",
                "summary": "Updated Event",
                "kind": "calendar#event",
                "attendees": [],
                "attachments": [],
            },
        )

    def test_update_missing_id(self):
        """Test updating an event without an ID raises ValueError."""
        wrapper = calendar_wrapper.CalendarWrap(
            creds=self.creds, service=self.service
        )
        event_to_update = calendar_types.Event(summary="No ID")

        with self.assertRaises(ValueError):
            wrapper.update(event_to_update)
