"""Reactive operators for GMail."""

from typing import Callable, Any
import reactivex as rx
from reactivex import operators as ops
from reactivex import Observable
from rxllmproc.gmail import types as gmail_types
from rxllmproc.gmail import api as gmail_wrapper
from rxllmproc.core import auth
from rxllmproc.core import environment


def fetch_messages(
    query: str,
    creds: auth.Credentials | None = None,
    wrapper: gmail_wrapper.GMailWrap | None = None,
) -> Callable[[Observable[Any]], Observable[gmail_types.Message]]:
    """Fetch GMail messages based on a trigger from the source observable.

    Args:
        query: The query string to search for messages.
        wrapper: The GMail wrapper instance to use.
        creds: Credentials to use if wrapper is not provided.

    Returns:
        An operator function that transforms the source observable.
    """
    if wrapper is None:
        if creds:
            wrapper = gmail_wrapper.GMailWrap(creds=creds)
        else:
            wrapper = environment.shared().gmail_wrapper

    def _fetch_messages(
        source: Observable[object],
    ) -> Observable[gmail_types.Message]:
        def _search_and_expand(_: Any) -> Observable[gmail_types.Message]:
            try:
                return rx.from_iterable(wrapper.search_expand(query))
            except Exception as e:
                return rx.throw(e)

        return source.pipe(ops.flat_map(_search_and_expand))

    return _fetch_messages


def fetch_ids(
    query: str,
    creds: auth.Credentials | None = None,
    wrapper: gmail_wrapper.GMailWrap | None = None,
) -> Callable[[Observable[object]], Observable[gmail_types.MessageId]]:
    """Fetch GMail message IDs based on a trigger from the source observable.

    Args:
        query: The query string to search for messages.
        wrapper: The GMail wrapper instance to use.
        creds: Credentials to use if wrapper is not provided.

    Returns:
        An operator function that transforms the source observable.
    """
    if wrapper is None:
        if creds:
            wrapper = gmail_wrapper.GMailWrap(creds=creds)
        else:
            wrapper = environment.shared().gmail_wrapper

    def _fetch_ids(
        source: Observable[object],
    ) -> Observable[gmail_types.MessageId]:
        def _search(_: Any) -> Observable[gmail_types.MessageId]:
            try:
                return rx.from_iterable(wrapper.search(query))
            except Exception as e:
                return rx.throw(e)

        return source.pipe(ops.flat_map(_search))

    return _fetch_ids


def download_message(
    creds: auth.Credentials | None = None,
    wrapper: gmail_wrapper.GMailWrap | None = None,
) -> Callable[
    [Observable[gmail_types.MessageId | str]], Observable[gmail_types.Message]
]:
    """Download a GMail message based on the input ID.

    The input stream is expected to emit message IDs (str or MessageId).

    Args:
        wrapper: The GMail wrapper instance to use.
        creds: Credentials to use if wrapper is not provided.

    Returns:
        An operator function that transforms the source observable.
    """
    if wrapper is None:
        if creds:
            wrapper = gmail_wrapper.GMailWrap(creds=creds)
        else:
            wrapper = environment.shared().gmail_wrapper

    def _download_message(
        source: Observable[gmail_types.MessageId | str],
    ) -> Observable[gmail_types.Message]:
        def _process(item: gmail_types.MessageId | str) -> gmail_types.Message:
            if isinstance(item, str):
                msg_id = item
            elif isinstance(item, gmail_types.MessageId):  # type: ignore
                msg_id = item.id
            else:
                raise ValueError(f"Unsupported type: {type(item)}")
            return wrapper.get(str(msg_id))

        return source.pipe(ops.map(_process))

    return _download_message
