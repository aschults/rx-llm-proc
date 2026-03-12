# pyright: basic
"""Test the Calendar CLI class."""

import json
from unittest import mock
import io

from pyfakefs import fake_filesystem_unittest

from rxllmproc.calendar import api as calendar_wrapper
from rxllmproc.calendar import types as calendar_types
from rxllmproc.core import auth
from rxllmproc.cli import calendar_cli


class TestCalendarCli(fake_filesystem_unittest.TestCase):
    """Test the Calendar CLI class."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

        self.creds = mock.Mock(spec=auth.CredentialsFactory)
        self.wrap = mock.Mock(spec=calendar_wrapper.CalendarWrap)
        self.instance = calendar_cli.CalendarCli(
            creds=self.creds, calendar_wrap=self.wrap
        )

    def test_list_csv(self):
        """Test listing events in CSV format (default)."""
        events = [
            calendar_types.Event(
                id="event1",
                summary="Event 1",
                start=calendar_types.EventDateTime(
                    dateTime="2024-01-01T10:00:00Z"
                ),
                end=calendar_types.EventDateTime(
                    dateTime="2024-01-01T11:00:00Z"
                ),
                location="Room 1",
            )
        ]
        self.wrap.search.return_value = events

        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            self.instance.main(["list", "the_query"])
            output = fake_out.getvalue()

        # Check that search was called with some time_max (defaulting to 90d future)
        _, kwargs = self.wrap.search.call_args
        self.assertEqual(kwargs["q"], "the_query")
        self.assertEqual(kwargs["calendar_id"], "primary")
        self.assertIsNotNone(kwargs["time_max"])
        self.assertIn("Z", kwargs["time_max"])

        self.assertIn("id\tsummary\tstart\tend\tlocation", output)
        self.assertIn(
            "event1\tEvent 1\t2024-01-01T10:00:00Z\t2024-01-01T11:00:00Z\tRoom 1",
            output,
        )

    def test_list_max_results(self):
        """Test listing events with --max_results."""
        self.wrap.search.return_value = []

        self.instance.main(["list", "--max_results=10"])

        _, kwargs = self.wrap.search.call_args
        self.assertEqual(kwargs["max_results"], 10)

    def test_list_more_flags(self):
        """Test listing events with additional flags."""
        self.wrap.search.return_value = []

        self.instance.main(
            [
                "list",
                "--single_events",
                "--i_cal_uid=uid123",
                "--max_attendees=5",
            ]
        )

        _, kwargs = self.wrap.search.call_args
        self.assertTrue(kwargs["single_events"])
        self.assertEqual(kwargs["i_cal_uid"], "uid123")
        self.assertEqual(kwargs["max_attendees"], 5)

    def test_list_json(self):
        """Test listing events in JSON format."""
        events = [
            calendar_types.Event(
                id="event1",
                summary="Event 1",
            )
        ]
        self.wrap.search.return_value = events

        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            self.instance.main(["list", "--as_json"])
            output = fake_out.getvalue()

        data = json.loads(output)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "event1")
        self.assertEqual(data[0]["summary"], "Event 1")

    def test_create(self):
        """Test creating an event from a file."""
        event_dict = {
            "summary": "New Event",
            "start": {"dateTime": "2024-01-02T10:00:00Z"},
            "end": {"dateTime": "2024-01-02T11:00:00Z"},
        }
        self.fs.create_file("event.json", contents=json.dumps(event_dict))

        created_event = calendar_types.Event(id="new_id", summary="New Event")
        self.wrap.create.return_value = created_event

        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            self.instance.main(["create", "event.json"])
            output = fake_out.getvalue()

        self.assertEqual(output.strip(), "new_id")
        # Check that create was called with an Event object
        args, kwargs = self.wrap.create.call_args
        self.assertIsInstance(args[0], calendar_types.Event)
        self.assertEqual(args[0].summary, "New Event")
        self.assertEqual(kwargs["calendar_id"], "primary")

    def test_update(self):
        """Test updating an event from a file."""
        event_dict = {
            "id": "existing_id",
            "summary": "Updated Event",
        }
        self.fs.create_file("event.json", contents=json.dumps(event_dict))

        updated_event = calendar_types.Event(
            id="existing_id", summary="Updated Event"
        )
        self.wrap.update.return_value = updated_event

        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            self.instance.main(["update", "event.json"])
            output = fake_out.getvalue()

        self.assertEqual(output.strip(), "existing_id")
        args, kwargs = self.wrap.update.call_args
        self.assertIsInstance(args[0], calendar_types.Event)
        self.assertEqual(args[0].id, "existing_id")
        self.assertEqual(args[0].summary, "Updated Event")

    def test_update_missing_id(self):
        """Test that update fails if ID is missing in input."""
        event_dict = {
            "summary": "Updated Event",
        }
        self.fs.create_file("event.json", contents=json.dumps(event_dict))

        with mock.patch("rxllmproc.cli.cli_base.sys.exit") as exit_mock:
            self.instance.main(["update", "event.json"])
            exit_mock.assert_called()
