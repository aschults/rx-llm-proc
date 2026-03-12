"""Test the Google Calendar reactive operators."""

import unittest
from unittest import mock
import reactivex as rx

from rxllmproc.calendar import operators as calendar_operators
from rxllmproc.core import environment
from rxllmproc.calendar import api as calendar_wrapper
from rxllmproc.calendar import types as calendar_types


class TestCalendarOperators(unittest.TestCase):
    """Test the Google Calendar reactive operators."""

    def setUp(self):
        self.creds_patcher = mock.patch(
            "rxllmproc.core.auth.CredentialsFactory.shared_instance"
        )
        self.creds_patcher.start()
        # Initialize the environment correctly
        self.env = environment.Environment()
        self.env.__enter__()

    def tearDown(self):
        self.env.__exit__(None, None, None)
        self.creds_patcher.stop()

    def test_fetch_events(self):
        """Test fetching events triggered by an observable."""
        wrapper = mock.Mock(spec=calendar_wrapper.CalendarWrap)
        event1 = calendar_types.Event(id="1", summary="e1")
        event2 = calendar_types.Event(id="2", summary="e2")

        wrapper.search.return_value = [event1, event2]

        results: list[calendar_types.Event] = []
        source = rx.of("trigger")

        source.pipe(
            calendar_operators.fetch_events(query="meeting", wrapper=wrapper)
        ).subscribe(results.append)

        self.assertEqual(results, [event1, event2])
        wrapper.search.assert_called_once_with(
            q="meeting",
            calendar_id="primary",
            time_min=None,
            time_max=None,
            max_results=None,
            single_events=None,
            i_cal_uid=None,
            max_attendees=None,
        )

    def test_create_event(self):
        """Test creating an event."""
        wrapper = mock.Mock(spec=calendar_wrapper.CalendarWrap)
        event_to_create = calendar_types.Event(summary="New Event")
        created_event = calendar_types.Event(id="new_id", summary="New Event")

        wrapper.create.return_value = created_event

        results: list[calendar_types.Event] = []
        source = rx.of(event_to_create)

        source.pipe(calendar_operators.create_event(wrapper=wrapper)).subscribe(
            results.append
        )

        self.assertEqual(results, [created_event])
        wrapper.create.assert_called_once_with(
            event_to_create, calendar_id="primary"
        )

    def test_update_event(self):
        """Test updating an event."""
        wrapper = mock.Mock(spec=calendar_wrapper.CalendarWrap)
        event_to_update = calendar_types.Event(
            id="existing_id", summary="Updated Event"
        )
        updated_event = calendar_types.Event(
            id="existing_id", summary="Updated Event"
        )

        wrapper.update.return_value = updated_event

        results: list[calendar_types.Event] = []
        source = rx.of(event_to_update)

        source.pipe(calendar_operators.update_event(wrapper=wrapper)).subscribe(
            results.append
        )

        self.assertEqual(results, [updated_event])
        wrapper.update.assert_called_once_with(
            event_to_update, calendar_id="primary"
        )

    @mock.patch("rxllmproc.calendar.api.CalendarWrap")
    def test_default_wrapper(self, mock_wrapper_cls: mock.Mock):
        """Test that operators use the default wrapper from environment."""
        wrapper_instance = mock_wrapper_cls.return_value
        wrapper_instance.search.return_value = []

        source = rx.of("trigger")
        # This will trigger environment.shared().calendar_wrapper which we need to mock or ensure it's set
        with mock.patch.object(
            environment.Environment,
            "calendar_wrapper",
            new_callable=mock.PropertyMock,
        ) as mock_cal_prop:
            mock_cal_prop.return_value = wrapper_instance
            source.pipe(calendar_operators.fetch_events()).subscribe()

        wrapper_instance.search.assert_called()
