"""Reactive operators for Google Calendar."""

from typing import Any, Callable, Optional, TypeVar

import reactivex as rx
from reactivex import operators as ops

from rxllmproc.calendar import api as calendar_wrapper
from rxllmproc.calendar import types as calendar_types
from rxllmproc.core import auth, environment

_T = TypeVar("_T")


def fetch_events(
    query: Optional[str] = None,
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: Optional[int] = None,
    single_events: Optional[bool] = None,
    i_cal_uid: Optional[str] = None,
    max_attendees: Optional[int] = None,
    creds: Optional[auth.Credentials] = None,
    wrapper: Optional[calendar_wrapper.CalendarWrap] = None,
) -> Callable[[rx.Observable[Any]], rx.Observable[calendar_types.Event]]:
    """Fetch Calendar events based on a trigger from the source observable.

    Args:
        query: Free text search terms to find events.
        calendar_id: Calendar identifier. Defaults to 'primary'.
        time_min: Lower bound (exclusive) for an event's end time to filter by.
        time_max: Upper bound (exclusive) for an event's start time to filter by.
        max_results: Maximum number of events returned on one result page.
        single_events: Whether to expand recurrent events into instances.
        i_cal_uid: Specifies an event's iCalendar UID to filter by.
        max_attendees: The maximum number of attendees to include in the response.
        wrapper: The Calendar wrapper instance to use.
        creds: Credentials to use if wrapper is not provided.

    Returns:
        An operator function that transforms the source observable.
    """
    if wrapper is None:
        if creds:
            wrapper = calendar_wrapper.CalendarWrap(creds=creds)
        else:
            wrapper = environment.shared().calendar_wrapper

    def _fetch_events(
        source: rx.Observable[Any],
    ) -> rx.Observable[calendar_types.Event]:
        def _search(_: Any) -> rx.Observable[calendar_types.Event]:
            try:
                events = wrapper.search(
                    q=query,
                    calendar_id=calendar_id,
                    time_min=time_min,
                    time_max=time_max,
                    max_results=max_results,
                    single_events=single_events,
                    i_cal_uid=i_cal_uid,
                    max_attendees=max_attendees,
                )
                return rx.from_iterable(events)
            except Exception as e:
                return rx.throw(e)

        return source.pipe(ops.flat_map(_search))

    return _fetch_events


def create_event(
    calendar_id: str = "primary",
    creds: Optional[auth.Credentials] = None,
    wrapper: Optional[calendar_wrapper.CalendarWrap] = None,
) -> Callable[
    [rx.Observable[calendar_types.Event]], rx.Observable[calendar_types.Event]
]:
    """Create a Calendar event for each item in the source observable.

    Args:
        calendar_id: Calendar identifier. Defaults to 'primary'.
        wrapper: The Calendar wrapper instance to use.
        creds: Credentials to use if wrapper is not provided.

    Returns:
        An operator function that transforms the source observable.
    """
    if wrapper is None:
        if creds:
            wrapper = calendar_wrapper.CalendarWrap(creds=creds)
        else:
            wrapper = environment.shared().calendar_wrapper

    def _create_event(
        source: rx.Observable[calendar_types.Event],
    ) -> rx.Observable[calendar_types.Event]:
        def _process(event: calendar_types.Event) -> calendar_types.Event:
            return wrapper.create(event, calendar_id=calendar_id)

        return source.pipe(ops.map(_process))

    return _create_event


def update_event(
    calendar_id: str = "primary",
    creds: Optional[auth.Credentials] = None,
    wrapper: Optional[calendar_wrapper.CalendarWrap] = None,
) -> Callable[
    [rx.Observable[calendar_types.Event]], rx.Observable[calendar_types.Event]
]:
    """Update a Calendar event for each item in the source observable.

    Args:
        calendar_id: Calendar identifier. Defaults to 'primary'.
        wrapper: The Calendar wrapper instance to use.
        creds: Credentials to use if wrapper is not provided.

    Returns:
        An operator function that transforms the source observable.
    """
    if wrapper is None:
        if creds:
            wrapper = calendar_wrapper.CalendarWrap(creds=creds)
        else:
            wrapper = environment.shared().calendar_wrapper

    def _update_event(
        source: rx.Observable[calendar_types.Event],
    ) -> rx.Observable[calendar_types.Event]:
        def _process(event: calendar_types.Event) -> calendar_types.Event:
            return wrapper.update(event, calendar_id=calendar_id)

        return source.pipe(ops.map(_process))

    return _update_event
