"""Functionality to collect statistics from steps."""

from typing import Protocol, Any, TypeVar, Callable, Generic, cast
import threading
import time
import logging
import atexit

from reactivex import Observer, Observable, Subject, empty


class Collector(Protocol):
    """Interface to collector facility."""

    def touch(self, key: str):
        """Create the key."""

    def increase(self, key: str):
        """Increase the counter in key."""

    def sample(self, key: str, value: Any):
        """Provide a new sample for key."""

    def exception(self, key: str, error: Exception):
        """Record an exception for the key."""

    @property
    def exception_observable(self) -> Observable[Exception]:
        """Return the observable for exceptions."""
        ...

    @property
    def sample_observable(self) -> Observable[tuple[str, Any]]:
        """Return the observable for samples."""
        ...

    _shared_instance: 'Collector | None' = None

    @classmethod
    def shared_instance(cls) -> 'Collector':
        """Create a shared instance."""
        if cls._shared_instance is None:
            cls._shared_instance = MemoryCollector()
        return cls._shared_instance


class NoCollector(Collector):
    """No action collector, simply ignores all calls."""

    def touch(self, key: str):
        """Create the key."""

    def increase(self, key: str):
        """Increase the counter in key."""

    def sample(self, key: str, value: Any):
        """Provide a new sample for key."""

    def exception(self, key: str, error: Exception):
        """Record an exception for the key."""

    def start(self):
        """Start the automated printing."""

    @property
    def exception_observable(self) -> Observable[Exception]:
        """Return the observable for exceptions."""
        return empty()

    @property
    def sample_observable(self) -> Observable[tuple[str, Any]]:
        """Return the observable for samples."""
        return empty()


class MemoryCollector(threading.Thread, Collector):
    """Collector that stores all data in memory only."""

    def __init__(self, period: float = 20) -> None:
        """Create an instance."""
        super().__init__(daemon=True)
        self.lock = threading.Lock()
        self.data: dict[str, int] = {}
        self.exceptions: dict[str, int] = {}
        self.samples: dict[str, Any] = {}
        self.period = period

        self._exception_observable = Subject[Exception]()
        self._sample_observable = Subject[tuple[str, Any]]()

    def touch(self, key: str):
        """Create the key."""
        with self.lock:
            if key not in self.data:
                self.data[key] = 0

    def increase(self, key: str):
        """Increase the counter in key."""
        with self.lock:
            if key not in self.data:
                self.data[key] = 1
            else:
                self.data[key] += 1

    def sample(self, key: str, value: Any):
        """Provide a new sample for key."""
        self._sample_observable.on_next((key, value))
        self.samples[key] = value

    def exception(self, key: str, error: Exception):
        """Record an exception for the key."""
        with self.lock:
            if key not in self.exceptions:
                self.exceptions[key] = 1
            else:
                self.exceptions[key] += 1
        self._exception_observable.on_next(error)

    def start(self) -> None:
        """Log stats regularly and at termination."""
        atexit.register(
            lambda: logging.info('Collector statistics:%s', str(self))
        )
        return super().start()

    def __str__(self) -> str:
        """Pretty-print the collected data."""
        emission_str = '\n'.join(
            (
                f'      {name:50s}: {counter:6d},'
                + f' exc: {self.exceptions.get(name, 0):6d}'
            )
            for name, counter in sorted(self.data.items())
        )

        samples_str = '\n'.join(
            f'      {name:50s}: {repr(sample)[:50]}'
            for name, sample in sorted(self.samples.items())
        )

        return f'''
   Emmission counts:
{emission_str}

   Samples:
{samples_str}
'''

    def run(self) -> None:
        """Log statistics periodically."""
        while True:
            logging.info('Collector statistics:%s', str(self))
            time.sleep(self.period)

    @property
    def exception_observable(self) -> Observable[Exception]:
        """Return the observable for exceptions."""
        return self._exception_observable

    @property
    def sample_observable(self) -> Observable[tuple[str, Any]]:
        """Return the observable for samples."""
        return self._sample_observable


_T = TypeVar('_T')


class CollectingObserver(Observer[_T], Generic[_T]):
    """Observer that reports into a collector."""

    def __init__(
        self,
        key: str | Callable[[], str],
        collector: Collector | None = None,
        sample_interleave: int = 0,
    ) -> None:
        """Create an instance."""
        super().__init__()
        if isinstance(key, str):
            self.key: Callable[[], str] = lambda: key
        else:
            self.key: Callable[[], str] = key
        self.collector = collector or Collector.shared_instance()
        self.sample_interleave = sample_interleave
        self.sample_counter = 0

    def _on_next_core(self, value: _T) -> None:
        """Record next value, including sampling."""
        self.collector.increase(self.key())
        self.sample_counter += 1
        if (
            self.sample_interleave > 0
            and self.sample_counter >= self.sample_interleave
        ):
            self.collector.sample(self.key(), value)
            self.sample_counter = 0

    def _on_error_core(self, error: Exception) -> None:
        """Record exceptions."""
        self.collector.exception(self.key(), error)


def exception_handler_collect(
    source: Any, error: Exception, values: dict[str, Any], _: dict[str, Any]
) -> None:
    """Collect exceptions but don't raise them."""
    name = getattr(source, 'name', str(type(cast(object, source))))
    Collector.shared_instance().exception(name, error)
