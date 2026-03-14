"""Google Calendar REST interface wrapper."""

import dataclasses
import logging
import threading
from typing import Any

from googleapiclient import discovery
import dacite

from rxllmproc.calendar import types
from rxllmproc.calendar import _interface
from rxllmproc.core import auth
from rxllmproc.core import api_base


class CalendarWrap(api_base.ApiBase):
    """Wrapper around Google Calendar API."""

    def __init__(
        self,
        creds: auth.Credentials | None = None,
        service: _interface.CalendarInterface | None = None,
    ):
        """Create an instance.

        Args:
            creds: Credentials to be used for the requests.
            service: Optionally provide service instance (mainly for testing.)
        """
        super().__init__(creds)
        self._service_arg = service
        self._local = threading.local()

    @property
    def _service(self) -> _interface.CalendarInterface:
        """Lazily build the service."""
        if self._service_arg:
            return self._service_arg
        if not hasattr(self._local, "service"):
            self._local.service = discovery.build(
                "calendar",
                "v3",
                credentials=self._creds,
                requestBuilder=self.build_request,
            )
        return self._local.service

    def search(
        self,
        q: str | None = None,
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int | None = None,
        single_events: bool | None = None,
        i_cal_uid: str | None = None,
        max_attendees: int | None = None,
        **kwargs: Any,
    ) -> list[types.Event]:
        """Search for events in a calendar.

        Args:
            q: Free text search terms to find events.
            calendar_id: Calendar identifier. Defaults to 'primary'.
            time_min: Lower bound (exclusive) for an event's end time to filter by.
            time_max: Upper bound (exclusive) for an event's start time to filter by.
            max_results: Maximum number of events returned on one result page.
            single_events: Whether to expand recurrent events into instances.
            i_cal_uid: Specifies an event's iCalendar UID to filter by.
            max_attendees: The maximum number of attendees to include in the response.
            **kwargs: Additional arguments for the API list call.

        Returns:
            A list of events.
        """
        logging.info("Searching calendar %s for %r", calendar_id, q)
        api_kwargs: dict[str, Any] = {"calendarId": calendar_id}
        if q:
            api_kwargs["q"] = q
        if time_min:
            api_kwargs["timeMin"] = time_min
        if time_max:
            api_kwargs["timeMax"] = time_max
        if max_results:
            api_kwargs["maxResults"] = max_results
        if single_events is not None:
            api_kwargs["singleEvents"] = single_events
        if i_cal_uid:
            api_kwargs["iCalUID"] = i_cal_uid
        if max_attendees:
            api_kwargs["maxAttendees"] = max_attendees
        api_kwargs.update(kwargs)

        result_dict = self._service.events().list(**api_kwargs).execute()
        result = dacite.from_dict(_interface.EventsList, result_dict)
        return result.items

    def create(
        self,
        event: types.Event,
        calendar_id: str = "primary",
        **kwargs: Any,
    ) -> types.Event:
        """Create a new event.

        Args:
            event: The event to create.
            calendar_id: Calendar identifier. Defaults to 'primary'.
            **kwargs: Additional arguments for the API insert call.

        Returns:
            The created event.
        """
        logging.info(
            "Creating event in calendar %s: %s", calendar_id, event.summary
        )
        body = dataclasses.asdict(event)
        # Remove None values to avoid sending them to the API
        body = {k: v for k, v in body.items() if v is not None}

        result_dict = (
            self._service.events()
            .insert(calendarId=calendar_id, body=body, **kwargs)
            .execute()
        )
        return dacite.from_dict(types.Event, result_dict)

    def update(
        self,
        event: types.Event,
        calendar_id: str = "primary",
        **kwargs: Any,
    ) -> types.Event:
        """Update an existing event.

        Args:
            event: The event to update (must have an ID).
            calendar_id: Calendar identifier. Defaults to 'primary'.
            **kwargs: Additional arguments for the API update call.

        Returns:
            The updated event.

        Raises:
            ValueError: If event.id is not set.
        """
        if not event.id:
            raise ValueError("Event must have an ID to be updated.")

        logging.info("Updating event %s in calendar %s", event.id, calendar_id)
        body = dataclasses.asdict(event)
        body = {k: v for k, v in body.items() if v is not None}

        result_dict = (
            self._service.events()
            .update(
                calendarId=calendar_id, eventId=event.id, body=body, **kwargs
            )
            .execute()
        )
        return dacite.from_dict(types.Event, result_dict)
