"""Implementation of a cache for step computations.

`CacheInterface` provides access to a generic cache implementation.
Class `Cache` is the default implementation and allows to cache
and retreive values based on a key (usually the function or class
method) and the arguments of the function call.

`CacheEntry` represents a function, is looked up from `Cache`
using a key. `CachedCall` then stores a specific set of arguments
associated with a return value, and is accessed from cache entries.
"""

import dataclasses
from typing import Any, TypedDict, Protocol, TypeVar, Callable, cast
import hashlib
import datetime
import json
import threading
import jsonpickle  # type: ignore
import logging

from rxllmproc.core.infra import utilities
from rxllmproc.core.infra import containers


class CacheLoadError(Exception):
    """Raised when loading the cache fails."""


class CacheStoreError(Exception):
    """Raised when storing the cache fails."""


def _serialize_args(*args: Any, **kwargs: Any) -> Any:
    """Serialize arguments to identify cached calls."""
    value = {
        'args': args,
        'kwargs': kwargs,
    }
    return utilities.asdict(value)


def _calc_hash(value: Any) -> str:
    """Calculate the hash value for call arguments."""
    as_bytes = json.dumps(value, sort_keys=True).encode()
    hashed = hashlib.md5(usedforsecurity=False)
    hashed.update(as_bytes)
    return hashed.hexdigest()


def get_time_now() -> datetime.datetime:
    """Return the current time.

    Mainly used for testing purposes.
    """
    return datetime.datetime.now(datetime.timezone.utc)


def _ensure_utc(dt: datetime.datetime) -> datetime.datetime:
    """Ensure the datetime is timezone-aware (UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt


@dataclasses.dataclass
class CachedCall:
    """Represents an individual, cached call."""

    # Arguments for the call in serialized form for reference.
    serialized_args: Any

    # Hash value of the call args.
    hashed_args: str

    # The return value associated with the arguments.
    value: Any

    # Time when the cached call was added.
    added: datetime.datetime

    # Time when the cached call last matched.
    accessed: datetime.datetime

    def matches(self, *args: Any, **kwargs: Any) -> bool:
        """Determine if the provided arguments match the cached call."""
        args_hash = _calc_hash(_serialize_args(*args, **kwargs))
        if self.hashed_args == args_hash:
            self.accessed = get_time_now()
            return True
        return False

    @classmethod
    def create(cls, value: Any, *args: Any, **kwargs: Any) -> 'CachedCall':
        """Create a cached call instance from args and result value."""
        args_as_dict = _serialize_args(*args, **kwargs)
        hashed_args = _calc_hash(args_as_dict)
        now = get_time_now()
        return CachedCall(
            args_as_dict,
            hashed_args,
            value,
            added=now,
            accessed=now,
        )


@dataclasses.dataclass
class CacheStats:
    """Collection of statistics for a cache entry."""

    num_calls: int = 0
    max_accessed: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.min.replace(
            tzinfo=datetime.timezone.utc
        )
    )
    min_accessed: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.max.replace(
            tzinfo=datetime.timezone.utc
        )
    )


@dataclasses.dataclass
class CacheEntry:
    """Represents a specific function to be cached."""

    # The individual cached calls (arguments -> return value)
    calls: dict[str, CachedCall] = dataclasses.field(
        default_factory=lambda: dict()
    )

    lock: threading.Lock = dataclasses.field(init=False)

    def __post_init__(self):
        """Add a lock instance on post init."""
        self.lock = threading.Lock()

    def get(self, *args: Any, **kwargs: Any) -> CachedCall | None:
        """Retreive a cached call if exists."""
        args_as_dict = _serialize_args(*args, **kwargs)
        args_hash = _calc_hash(args_as_dict)
        return self.calls.get(args_hash, None)

    def add(self, value: Any, *args: Any, **kwargs: Any) -> CachedCall:
        """Add a new cached call instance."""
        with self.lock:
            try:
                # Fail early if value is not serializable
                pickled: str = jsonpickle.dumps(value)  # type: ignore
                if '__orig_class__' in pickled:
                    logging.warning(
                        'Potential serialization issue: %s', pickled
                    )
            except Exception as e:
                logging.exception(
                    'Cannot pickle value for call: %s', repr(value)
                )
                raise CacheStoreError from e
            cached_call = CachedCall.create(value, *args, **kwargs)
            self.calls[cached_call.hashed_args] = cached_call
            return cached_call

    def add_call(self, cached_call: CachedCall) -> CachedCall:
        """Add a cached call directly."""
        with self.lock:
            try:
                # Fail early if value is not serializable
                pickled: str = jsonpickle.dumps(cached_call.value)  # type: ignore
                if '__orig_class__' in pickled:
                    logging.warning(
                        'Potential serialization issue: %s', pickled
                    )
            except Exception as e:
                logging.exception(
                    'Cannot pickle value for call: %s', repr(cached_call.value)
                )
                raise CacheStoreError from e
            self.calls[cached_call.hashed_args] = cached_call
            return cached_call

    def remove(self, cached_call: CachedCall) -> None:
        """Remove a cached call."""
        with self.lock:
            if cached_call.hashed_args in self.calls:
                del self.calls[cached_call.hashed_args]

    def get_keys(self) -> dict[str, Any]:
        """Get the serialized args for all cached calls."""
        return {key: call.serialized_args for key, call in self.calls.items()}

    def get_stats(self) -> CacheStats:
        """Collect the stats for the cache entry."""
        result = CacheStats()
        for call_ in self.calls.values():
            result.num_calls += 1
            accessed = _ensure_utc(call_.accessed)
            if accessed > result.max_accessed:
                result.max_accessed = accessed
            if accessed < result.min_accessed:
                result.min_accessed = accessed
        return result

    def __getstate__(self) -> Any:
        """Provide custom serialization to skip the lock attribute."""
        return {'calls': self.calls}

    def __setstate__(self, state: Any):
        """Provide custom deserialization, reinstating the lock attr."""
        self.calls = state['calls']
        self.lock = threading.Lock()


class CacheInterface(Protocol):
    """Implementation agnostic access to cache."""

    def get(self, reg_key: str, *args: Any, **kwargs: Any) -> CachedCall | None:
        """Get a specific return value from key and args."""
        ...

    def add(
        self, reg_key: str, value: Any, *args: Any, **kwargs: Any
    ) -> CachedCall:
        """Add a return value based on key and args."""
        ...

    def add_call(self, reg_key: str, cached_call: CachedCall) -> CachedCall:
        """Add a cached call directly."""
        ...

    def remove(self, reg_key: str, cached_call: CachedCall) -> None:
        """Remove a return value based on key and call."""
        ...


class NoCache:
    """Cache that never matches, used to prevent caching."""

    def get(self, reg_key: str, *args: Any, **kwargs: Any) -> CachedCall | None:
        """Get a value. Always returns None."""
        return None

    def add(
        self, reg_key: str, value: Any, *args: Any, **kwargs: Any
    ) -> CachedCall:
        """Pretend to add a value."""
        return CachedCall(
            None,
            '',
            None,
            datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
            datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        )

    def add_call(self, reg_key: str, cached_call: CachedCall) -> CachedCall:
        """Add a cached call directly."""
        return cached_call

    def remove(self, reg_key: str, cached_call: CachedCall) -> None:
        """Remove a value."""
        pass


@dataclasses.dataclass
class Cache:
    """Implementation of cache based on key and argument values."""

    # Contains the cache entries by key
    registry: dict[str, CacheEntry] = dataclasses.field(
        default_factory=lambda: dict()
    )

    def __post_init__(self):
        """Add a lock attribute after construction."""
        self.lock = threading.Lock()

    def get(self, reg_key: str, *args: Any, **kwargs: Any) -> CachedCall | None:
        """Get the cached value, if exists."""
        if reg_key not in self.registry:
            return None
        entry = self.registry[reg_key]
        return entry.get(*args, **kwargs)

    def get_or_create_entry(self, reg_key: str) -> CacheEntry:
        """Get or create a cache entry for a given key."""
        if reg_key not in self.registry:
            with self.lock:  # pytype: disable=attribute-error
                # Double-check after acquiring the lock
                if reg_key not in self.registry:
                    self.registry[reg_key] = CacheEntry()
        return self.registry[reg_key]

    def add(
        self, reg_key: str, value: Any, *args: Any, **kwargs: Any
    ) -> CachedCall:
        """Add a new cached value."""
        entry = self.get_or_create_entry(reg_key)
        return entry.add(value, *args, **kwargs)

    def add_call(self, reg_key: str, cached_call: CachedCall) -> CachedCall:
        """Add a cached call directly."""
        entry = self.get_or_create_entry(reg_key)
        return entry.add_call(cached_call)

    def remove(self, reg_key: str, cached_call: CachedCall) -> None:
        """Remove a cached value."""
        if reg_key in self.registry:
            self.registry[reg_key].remove(cached_call)

    def get_keys(self) -> dict[str, Any]:
        """Get all keys by which to look up cache entries."""
        return {key: entry.get_keys() for key, entry in self.registry.items()}

    def get_stats(self) -> dict[str, CacheStats]:
        """Get all keys by which to look up cache entries."""
        return {key: entry.get_stats() for key, entry in self.registry.items()}

    def __getstate__(self) -> Any:
        """Get the state for custom serialization, to skip lock."""
        return {'registry': self.registry}

    def __setstate__(self, state: Any):
        """Set the state for custom deserialization, to reinstate lock."""
        self.registry = state['registry']
        self.lock = threading.Lock()


class PrefixCache:
    """Cache proxy to manage a cache subtree, based on key prefix."""

    def __init__(self, upstream: 'Cache | PrefixCache', prefix: str) -> None:
        """Build an instance."""
        # Next delegate for cache operations.
        self.upstream = upstream

        # The prefix to prepend before keys.
        self.prefix = prefix

    def get(self, reg_key: str, *args: Any, **kwargs: Any) -> CachedCall | None:
        """Get an instance within the specified key prefix."""
        return self.upstream.get(self.prefix + reg_key, *args, **kwargs)

    def add(
        self, reg_key: str, value: Any, *args: Any, **kwargs: Any
    ) -> CachedCall:
        """Add an instance underneath the specified prefix."""
        return self.upstream.add(self.prefix + reg_key, value, *args, **kwargs)

    def add_call(self, reg_key: str, cached_call: CachedCall) -> CachedCall:
        """Add a cached call directly."""
        return self.upstream.add_call(self.prefix + reg_key, cached_call)

    def remove(self, reg_key: str, cached_call: CachedCall) -> None:
        """Remove a value."""
        self.upstream.remove(self.prefix + reg_key, cached_call)

    def get_keys(self) -> dict[str, Any]:
        """Get all keys under the prefix."""
        return {
            key[len(self.prefix) :]: entry
            for key, entry in self.upstream.get_keys().items()
            if key.startswith(self.prefix)
        }


class AgeSpec(TypedDict, total=False):
    """Configuration to specify maximum age for cache items.

    Mising dict entries are considered always matching.
    """

    # Maximum time span since last matched before the entry is
    # considered stale.
    max_age_accessed: datetime.timedelta

    # Maximum time span since the entry was added before the entry
    # is considered stale.
    max_age_added: datetime.timedelta


class TimeSpec:
    """Stores the earliest moments (access and creation) cache is not stale."""

    def __init__(
        self,
        min_access: datetime.datetime,
        min_added: datetime.datetime,
    ) -> None:
        """Create an instance."""
        # Time after which a cache entry is still valid.
        self.min_access = min_access.replace(tzinfo=datetime.timezone.utc)

        # Time after which a cache entry is still valid.
        self.min_added = min_added.replace(tzinfo=datetime.timezone.utc)

    @classmethod
    def from_age(
        cls,
        max_age: AgeSpec,
        reference_time: datetime.datetime | None = None,
    ) -> 'TimeSpec':
        """Convert an age specification into earliest valid times.

        Args:
            max_age: The age spec, i.e. the maximum allowed age.
            reference_time: Time for which to compute validity (default: now)
        """
        if reference_time is None:
            reference_time = get_time_now()

        reference_time = _ensure_utc(reference_time)

        min_access = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        if 'max_age_accessed' in max_age:
            min_access = reference_time - max_age['max_age_accessed']

        min_added = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        if 'max_age_added' in max_age:
            min_added = reference_time - max_age['max_age_added']

        return TimeSpec(min_access, min_added)

    def retain_call(self, call: CachedCall) -> bool:
        """Indicate if a cached call is stil valid and should be retained."""
        call.accessed = _ensure_utc(call.accessed)
        call.added = _ensure_utc(call.added)

        if call.accessed < self.min_access:
            return False
        if call.added < self.min_added:
            return False
        return True


class PurgeWalker:
    """Traverses the entire cache structure and purges entries."""

    def __init__(
        self,
        default_age: AgeSpec | None = None,
        prefix_age: dict[str, AgeSpec] | None = None,
        reference_time: datetime.datetime | None = None,
    ) -> None:
        """Create an instance.

        Args:
            default_age: Age spec used by default.
            prefix_age: Age spec for specific key prefixes.
            reference_time: Time for which the evalution is done
                (default: Now)
        """
        if prefix_age is None:
            prefix_age = dict()
        self.prefix_age = prefix_age

        self.default_age = default_age or AgeSpec()

        if reference_time is None:
            reference_time = get_time_now()
        self.reference_time = reference_time

    def get_max_age(self, key: str) -> AgeSpec:
        """Get the age spec per key, allowing prefix overrides."""
        result = AgeSpec()
        result.update(self.default_age)
        for prefix, age_spec in self.prefix_age.items():
            if key.startswith(prefix):
                result.update(age_spec)
                break
        return result

    def purge_call(self, call: CachedCall, min_time: TimeSpec) -> bool:
        """Determine if a cached call should be kept in the cache."""
        return not min_time.retain_call(call)

    def purge_entry(self, entry: CacheEntry, min_time: TimeSpec) -> bool:
        """Determine if a call entry should be kept in the cache.

        If no cached calls remain, the entry is reclaimed.
        """
        entry.calls = {
            k: v
            for k, v in entry.calls.items()
            if not self.purge_call(v, min_time)
        }
        return not entry.calls

    def purge_cache(self, cache_instance: Cache) -> bool:
        """Remove expired entries from entire cache."""
        to_delete: list[str] = []
        for key, item in cache_instance.registry.items():
            max_age = self.get_max_age(key)
            min_time = TimeSpec.from_age(max_age, self.reference_time)
            if self.purge_entry(item, min_time):
                to_delete.append(key)
        for key in to_delete:
            del cache_instance.registry[key]
        return len(cache_instance.registry) == 0


class CacheManager:
    """Load, save and purge cache instances."""

    def __init__(
        self,
        storage: containers.Container,
        default_age: AgeSpec | None = None,
        prefix_age: dict[str, AgeSpec] | None = None,
    ) -> None:
        """Create an instance.

        Args:
            storage: Container (local file, GDrive file,...) under which
                to store the serialized cache.
            default_age: Default age spec.
            prefix_age: Age spec by key prefix.
        """
        self.storage = storage
        self.purge_walker = PurgeWalker(default_age, prefix_age)

    def _format_stats(self, instance: Cache) -> str:
        entries = (
            f'   {k:40s}: {v.num_calls:6d}   {v.min_accessed}'
            for k, v in instance.get_stats().items()
        )

        entries_str = "\n".join(entries)
        headers = ['entry', 'count', 'oldest']
        headers_str = f'   {headers[0]:40s}: {headers[1]:6s}   {headers[2]}'
        return f'=== Cache stats ===\n{headers_str}\n{entries_str}\n'

    def load(self) -> Cache:
        """Load a cache instance from file storage."""
        if not self.storage.exists():
            raise CacheLoadError('storage container does not exist')
        content_str = self.storage.get()
        try:
            restored: object = cast(object, jsonpickle.loads(content_str))  # type: ignore
        except Exception as e:
            logging.error(
                'cache loading failed. cache content: %s', content_str
            )
            raise CacheLoadError("Failed to decode cache content") from e

        if not isinstance(restored, Cache):
            type_ = type(restored)
            raise CacheLoadError(f"Expected Cache, got {type_}")
        self.purge(restored)
        try:
            _ = jsonpickle.dumps(  # type: ignore
                restored,
                indent=2,
            )
        except Exception:  # pylint: disable=broad-except-clause
            logging.warning('Loaded cache cannot be pickled again.')
        logging.info(
            'Cache stats after loading:\n%s', self._format_stats(restored)
        )

        return restored

    def load_or_create(self) -> Cache:
        """Load if file exists, otherwise just create instance."""
        if not self.storage.exists():
            return Cache()
        return self.load()

    def purge(self, cache: Cache):
        """Perform a purge based on age specs in constructor."""
        self.purge_walker.purge_cache(cache)

    def store(self, cache: Cache):
        """Store a cache under the container specified in constructor."""
        logging.info('purging cache before saving')
        self.purge(cache)
        logging.info(
            'Cache stats before saving:\n%s', self._format_stats(cache)
        )
        try:
            content_str: str = jsonpickle.dumps(  # type: ignore
                cache,
                indent=2,
            )
        except Exception as e:
            self._inspect_bad_pickle_cache(cache)
            raise CacheStoreError(
                "Failed to serialize cache for storage"
            ) from e
        self.storage.put(content_str)
        logging.info('cache saved')

    def _inspect_bad_pickle_cache(self, cache: Cache):
        for key, entry in cache.registry.items():  # pragma: no cover
            try:
                _ = jsonpickle.dumps(  # type: ignore
                    entry,
                    indent=2,
                )
            except Exception:
                logging.error(f'Failed to pickle entry {repr(key)}')
                self._inspect_bad_pickle_entry(entry)

    def _inspect_bad_pickle_entry(self, entry: CacheEntry):
        for key, cached_call in entry.calls.items():  # pragma: no cover
            try:
                _ = jsonpickle.dumps(  # type: ignore
                    cached_call,
                    indent=2,
                )
            except Exception:
                logging.error(f'Failed to pickle call {repr(key)}')
                self._inspect_bad_pickle_call(cached_call)

    def _inspect_bad_pickle_call(self, cached_call: CachedCall):
        try:  # pragma: no cover
            _ = jsonpickle.dumps(  # type: ignore
                cached_call.serialized_args,
                indent=2,
            )
        except Exception:
            logging.error(
                f'Failed to pickle args {repr(cached_call.serialized_args)}'
            )
        try:
            _ = jsonpickle.dumps(  # type: ignore
                cached_call.value,
                indent=2,
            )
        except Exception:
            logging.error(f'Failed to pickle value {repr(cached_call.value)}')


_T = TypeVar('_T')


def cached_call(
    cache_instance: CacheInterface | None,
    key: str,
    func: Callable[..., _T],
    *args: Any,
    **kwargs: Any,
) -> _T:
    """Call a function, caching the result."""
    if not cache_instance:
        return func(*args, **kwargs)

    cached = cache_instance.get(key, *args, **kwargs)
    logging.debug('cache lookup for key %s', key)
    if cached:
        logging.debug('cache hit for key %s, hash %s', key, cached.hashed_args)
        return cast(_T, cached.value)

    # Create the cache before running the call as it may change the args.
    new_call = CachedCall.create(None, *args, **kwargs)

    result = func(*args, **kwargs)
    new_call.value = result
    cache_instance.add_call(key, new_call)

    return result
