"""Helper classes for testing."""

from typing import TypeVar, List, Generic
import base64
import threading

from reactivex.abc.observer import ObserverBase

from email import message

_T = TypeVar('_T')


def fail_none(value: _T | None) -> _T:
    """Raise excepption if none, otherwise passes the value."""
    if value is None:
        raise Exception('is NONE')
    return value


class RecordingObserver(ObserverBase[_T], Generic[_T]):
    """Observer that records all incoming items."""

    def __init__(self, assert_on_exception: bool = True) -> None:
        """Create an instance."""
        self.result: List[_T] = []
        self.length_at_completion = -1
        super().__init__()
        self.assert_on_exception = assert_on_exception
        self.exception = None
        self.completion = threading.Event()

    def on_next(self, value: _T) -> None:
        """Record a value."""
        if self.length_at_completion >= 0:
            raise ValueError(
                'Only expecting calls to on_next before completion'
                + f'.... at {self.length_at_completion}'
            )
        self.result.append(value)

    def on_completed(self) -> None:
        """Close the observable and record index at closure."""
        if self.length_at_completion >= 0:
            raise ValueError(
                'Only expecting one call to on_complete.... before'
                + f' at {self.length_at_completion}, now {len(self.result)}'
            )
        self.length_at_completion = len(self.result)
        self.completion.set()

    def on_error(self, error: Exception) -> None:
        """Raise exception on getting an error."""
        self.exception = error
        if self.assert_on_exception:
            raise AssertionError('Not expecting on_error') from error


def make_raw_email(subject: str, msgid: str, date: str | None = None) -> str:
    """Create dummy email message and encode for GMail raw field."""
    msg = message.Message()
    msg['Subject'] = subject
    msg['Message-id'] = msgid
    if date:
        msg['Date'] = date
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()
