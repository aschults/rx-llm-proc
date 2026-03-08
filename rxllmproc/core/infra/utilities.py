"""Various utility functions and classes."""

from email import message
import logging
import threading
import time
import collections
import reactivex as rx
from reactivex import operators as ops
import datetime
import pathlib
import inspect

from typing import (
    Any,
    cast,
    get_args,
    get_origin,
    Protocol,
    runtime_checkable,
    MutableMapping,
    TypeVar,
    Iterator,
    Callable,
    Generic,
    Union,
    TypedDict,
)
from types import UnionType
import dataclasses

# Types that asdict() does not need to convert.
_BASE_TYPES: Any = (int, float, complex, str, bytes, bool, bytearray, type)


@runtime_checkable
class AsDictConvertible(Protocol):
    """Interface to a class with custom asdict."""

    def asdict(self) -> Any:
        """Convert the instance to dict/list structure."""
        ...


def _asdict_primitive(value: Any) -> Any:
    """Convert primitive types."""
    if isinstance(value, _BASE_TYPES):
        return value
    return NotImplemented


def _asdict_container(value: Any) -> Any:
    """Convert container types."""
    if isinstance(value, list):
        return [asdict(v) for v in cast(list[Any], value)]
    if isinstance(value, tuple):
        return tuple(asdict(v) for v in cast(list[Any], value))
    if isinstance(value, dict):
        return {
            asdict(k): asdict(v) for k, v in cast(dict[Any, Any], value).items()
        }
    if isinstance(value, (set, frozenset)):
        value = cast(frozenset[Any], value)
        return set(asdict(v) for v in value)
    return NotImplemented


def _asdict_special(value: Any) -> Any:
    """Convert special types."""
    if isinstance(value, AsDictConvertible):
        return asdict(value.asdict())
    if hasattr(value, 'model_dump'):
        return asdict(value.model_dump())
    if dataclasses.is_dataclass(value):
        converted = dataclasses.asdict(cast(Any, value))
        return asdict(converted)
    if isinstance(value, datetime.datetime):
        # If the datetime object is naive, assume it's local time and convert to UTC.
        if value.tzinfo is None:
            value = value.astimezone()
        utc_value = value.astimezone(datetime.timezone.utc)
        return utc_value.strftime('%Y-%m-%dT%H:%M:%SZ')
    if isinstance(value, message.Message):
        return repr(value.as_string())
    if isinstance(value, pathlib.Path):
        return str(value)
    return NotImplemented


def asdict(value: Any) -> Any:
    """Convert a complex data structure to dicts/lists.

    Raises:
        ValueError: if the value cannot be converted.
    """
    if value is None:
        return None

    result = _asdict_primitive(value)
    if result is not NotImplemented:
        return result

    result = _asdict_special(value)
    if result is not NotImplemented:
        return result

    result = _asdict_container(value)
    if result is not NotImplemented:
        return result

    raise ValueError(f'Cannot make {type(value)} ({value}) into a tuple')


# Default samples for base types.
_BASE_TYPE_SAMPLES: dict[type[Any], Any] = {
    int: 123,
    float: 1.234,
    str: 'string here',
    bytes: b'bytes here',
    bool: False,
    type: list[str],
}
# complex, bytearray missing


def _build_sample_origin_types(cls: type[object]) -> Any:
    """Build a sample for parameterized types."""
    origin = get_origin(cls)

    if origin is None:
        raise ValueError(f'Cannot make sample for {cls} (no origin)')

    args = get_args(cls)

    if origin in (list, tuple, set, frozenset):
        return [build_sample(args[0])]
    if origin is dict:
        sample_key = None
        if args[0] is str:
            sample_key = 'some key'
        elif args[0] is int:
            sample_key = 345
        else:
            raise Exception('only accepting strings and ints as keys')

        return {sample_key: build_sample(args[1])}
    if origin is UnionType:
        for arg in args:
            if arg is None:
                continue
            return build_sample(arg)
        raise ValueError('No type found to produce sample')


def build_sample(cls: type[object], sample_value: Any = None) -> Any:
    """Build a sample dict structure.

    Args:
        cls: Type to create a sample for.
        sample_value: Optional sample value to use.

    Raises:
        ValueError: If the sample for cls cannot be built.
    """
    if sample_value is not None:
        return asdict(sample_value)
    if cls in _BASE_TYPE_SAMPLES:
        if sample_value is not None:
            return sample_value
        else:
            return _BASE_TYPE_SAMPLES[cls]

    if dataclasses.is_dataclass(cls):
        return {
            f.name: build_sample(cast(type, f.type), f.metadata.get('sample'))
            for f in dataclasses.fields(cls)
            if not f.metadata.get('skip_sample', False)
        }

    return _build_sample_origin_types(cls)


class JsonSchema(TypedDict, total=False):
    """JSON schema for dataclasses."""

    type: str
    properties: dict[str, Any]
    items: Any
    additionalProperties: Any
    anyOf: list[Any]
    description: str
    required: list[str]


_BASE_TYPE_SCHEMAS: dict[type[Any], JsonSchema] = {
    int: {'type': 'integer'},
    float: {'type': 'number'},
    str: {'type': 'string'},
    bytes: {'type': 'string'},
    bool: {'type': 'boolean'},
    type: {'type': 'string'},
}


def _build_json_schema_union(args: tuple[Any, ...]) -> JsonSchema:
    """Build a JSON schema for Union types."""
    # Filter out NoneType (Optional)
    non_none_args = [arg for arg in args if arg is not type(None)]
    if len(non_none_args) == 1:
        return build_json_schema(non_none_args[0])

    return {'anyOf': [build_json_schema(arg) for arg in non_none_args]}


def _build_json_schema_origin_types(cls: type[object]) -> JsonSchema:
    """Build a JSON schema for parameterized types."""
    origin = get_origin(cls)

    if origin is None:
        return {}

    args = get_args(cls)

    if origin in (list, tuple, set, frozenset):
        return {
            'type': 'array',
            'items': build_json_schema(args[0]),
        }
    if origin is dict:
        return {
            'type': 'object',
            'additionalProperties': build_json_schema(args[1]),
        }
    if origin is UnionType or origin is Union:
        return _build_json_schema_union(args)

    return {}


def build_json_schema(cls: type[object]) -> JsonSchema:
    """Build a JSON schema from a class structure.

    Args:
        cls: The class to build the schema for.

    Returns:
        A dictionary representing the JSON schema.
    """
    if cls in _BASE_TYPE_SCHEMAS:
        return _BASE_TYPE_SCHEMAS[cls].copy()

    if dataclasses.is_dataclass(cls):
        properties = {}
        required: list[str] = []
        for field in dataclasses.fields(cls):
            if field.metadata.get('skip_schema'):
                continue
            field_schema = build_json_schema(cast(type, field.type))
            if field.metadata.get('description'):
                field_schema['description'] = field.metadata['description']

            properties[field.name] = field_schema

            # Determine if required
            is_optional = False
            origin = get_origin(field.type)
            if origin is UnionType or origin is Union:
                if type(None) in get_args(field.type):
                    is_optional = True

            if (
                field.default is dataclasses.MISSING
                and field.default_factory is dataclasses.MISSING
                and not is_optional
            ):
                required.append(field.name)

        schema: JsonSchema = {
            'type': 'object',
            'properties': properties,
        }
        if cls.__doc__:
            schema['description'] = cls.__doc__.strip()
        if required:
            schema['required'] = required

        if hasattr(cls, '_adapt_json_schema'):
            schema_adapter = cast(
                Callable[[JsonSchema], JsonSchema], cls._adapt_json_schema  # type: ignore
            )
            schema = schema_adapter(schema)
        return schema

    return _build_json_schema_origin_types(cls)


_T = TypeVar('_T')
_V = TypeVar('_V')


class OverlayDict(collections.UserDict[_T, _V]):
    """Dict that allows overlay of key-values with another mapping.

    The underlying `data` attribute from `UserDict` is used for the
    base dict, the default values when no matching key is present in the
    overlay data.
    """

    def __init__(self, base: dict[_T, _V] | None = None, /, **kwargs: _V):
        """Create an instance."""
        super().__init__()
        if base is None:
            base = dict()
        self.data = base
        self.data.update(**kwargs)  # type: ignore

    def _overlay_data(self) -> MutableMapping[_T, _V]:
        """Provide the overlay data for the dict."""
        raise NotImplementedError()

    def __getitem__(self, key: _T) -> _V:
        """Get an item by first looking in the overlay, then data."""
        overlay = self._overlay_data()
        if key in overlay:
            return overlay[key]
        else:
            return self.data[key]

    def __contains__(self, key: object) -> bool:
        """Check if key is in overlay or data."""
        overlay = self._overlay_data()
        if key in overlay:
            return True
        else:
            return super().__contains__(key)

    def __setitem__(self, key: _T, item: _V) -> None:
        """Set an item, in the overlay, leaving data unchanged."""
        self._overlay_data().__setitem__(key, item)

    def __delitem__(self, key: _T) -> None:
        """Delete an item from the overlay.

        Raises:
            ValueError if key isn't found in the overlay.
        """
        overlay = self._overlay_data()
        if key in overlay:
            overlay.__delitem__(key)
        else:
            raise KeyError('Can only remove keys from overlay dict')

    def __iter__(self) -> Iterator[_T]:
        """Create an iterator for keys from overlay and base."""
        return iter(set(self._overlay_data().keys() | self.data.keys()))

    def __eq__(self, __other: object) -> bool:
        """Compare to other dict-like by combining overlay and data."""
        merged = dict(self._overlay_data()) | self.data
        return merged == __other

    def __len__(self) -> int:
        """Determine the size, using the set of all keys, overlay and data."""
        return len(self._overlay_data().keys() | self.data.keys())

    def __repr__(self) -> str:
        """Convert to string, merging overlay and base data."""
        merged = dict(self._overlay_data()) | self.data
        return repr(merged)


class ThreadOverlayDict(OverlayDict[_T, _V]):
    """Overlay dict that manages thread-local overlays."""

    def __init__(self, base: dict[_T, _V] | None = None, /, **kwargs: Any):
        """Create an instance."""
        super().__init__(base, **kwargs)
        self._thread_map: dict[int, dict[_T, _V]] = {}
        self._lock = threading.Lock()

    def _overlay_data(self) -> MutableMapping[_T, _V]:
        """Return the overlay data, depending on the current thread."""
        tid = threading.get_ident()
        with self._lock:
            if tid in self._thread_map:
                overlay: dict[_T, _V] = self._thread_map[tid]
            else:
                overlay = {}
                self._thread_map[tid] = overlay

        return overlay


class ThreadLocalValue(Generic[_T]):
    """A class that provides a thread-local property."""

    def __init__(self, factory: Callable[[], _T]):
        """Create an instance."""
        self._factory = factory
        self._local = threading.local()

    def get(self) -> _T:
        """Get the value for the current thread."""
        # Check if this thread already has an instance
        if not hasattr(self._local, "value"):
            # First time access for this thread: run the factory
            self._local.value = self._factory()

        return self._local.value


def dataclass_from_assignments(
    tp: type[_T],
    data: list[tuple[str, str]],
    ignore_unmatched: bool = False,
) -> _T:
    """Convert assignment-form list to dataclass."""
    result = tp()
    if not dataclasses.is_dataclass(result):
        raise TypeError('not a dataclass')

    field_dict = {field.name: field for field in dataclasses.fields(result)}
    for name, value_str in data:
        try:
            field = field_dict.get(name)
            if field is None:
                if ignore_unmatched:
                    continue
                else:
                    raise KeyError(
                        (
                            f'field {name} to be assigned, '
                            f'but not in dataclass {tp}'
                        )
                    )
            value: Any = None
            if field.type is str:
                value = value_str
            elif field.type is int:
                value = int(value_str)
            else:
                raise Exception(
                    'unexpected type {field.type} when assigning {name}'
                )

            setattr(result, field.name, value)
        except Exception as exc:
            raise ValueError(
                f'failed to set field {name} in type {tp}: {exc}'
            ) from exc
    return result


def with_backoff_retry(
    func: Callable[..., _T],
    retry_exception_type: type[Exception] = Exception,
    num_retries: int = 3,
    initial_delay: int = 10,
    delay_factor: int = 2,
    delay_func: Callable[[float], None] = time.sleep,
) -> Callable[..., _T]:
    """Wrap `func` to retry with increasing delays.

    This decorator retries the decorated function `func` up to `num_retries`
    times if it raises an exception of type `retry_exception_type`.
    Each retry attempt is delayed by an exponentially increasing amount of time,
    starting with `initial_delay` and multiplied by `delay_factor` for each
    subsequent attempt.

    Args:
        func: The function to be wrapped and retried.
        retry_exception_type: The type of exception that should trigger a retry.
            Defaults to `Exception`.
        num_retries: The maximum number of retry attempts. Defaults to 3.
        initial_delay: The initial delay in seconds before the first retry.
            Defaults to 10 seconds.
        delay_factor: The factor by which the delay is multiplied for each
            subsequent retry. Defaults to 2.
        delay_func: A callable that accepts a delay in seconds as its argument
            and performs the actual delay. Defaults to `time.sleep`.

    Returns:
        A wrapped version of the `func` that retries with backoff.
    """

    def _func(*args: Any, **kwargs: Any) -> _T:
        delay = initial_delay
        i = 0
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                if i >= num_retries:
                    raise exc
                elif isinstance(exc, retry_exception_type):
                    logging.debug(
                        'Retrying function %r, iteration: %d, delay=%d',
                        func,
                        i,
                        delay,
                    )
                    delay_func(delay)
                    delay *= delay_factor
                else:
                    raise exc
            i += 1

    return _func


def identity(value: _T) -> _T:
    """Return the passed argument."""
    return value


def no_op(input: rx.Observable[_T]) -> rx.Observable[_T]:
    """Return same observable, to perform no operation."""
    return input


def remove_none() -> Callable[[rx.Observable[_T | None]], rx.Observable[_T]]:
    """Filter out None values from an observable stream."""

    def _not_none(value: _T | None) -> bool:
        return value is not None

    return rx.compose(
        ops.filter(_not_none),
        ops.map(lambda x: cast(_T, x)),
    )


def log(
    level: int,
    format_string: str,
    logger: str | logging.Logger | None = None,
    stack_level: int = 1,
    mapper: Callable[[_T], list[Any]] | None = None,
) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
    """Log elements passing through.

    Args:
        format_string: String to format the log entry with.
        level: Logging level to use.
        logger: Logger instance or name to use. If None, the logger of the
            calling module is used.
        stack_level: How many stack frames to go up to find the caller's module.
        mapper: Optional function to map the value before logging.
            Defaults to repr(), wrapped in a list.
    """
    if logger is None:
        logger_name = 'root'
        try:
            frame = inspect.currentframe()
            for _ in range(stack_level):
                if frame is not None:
                    frame = frame.f_back
            if frame is not None:
                logger_name = frame.f_globals.get('__name__', 'root')
        except Exception:
            pass
        log_instance = logging.getLogger(logger_name)
    elif isinstance(logger, str):
        log_instance = logging.getLogger(logger)
    else:
        log_instance = logger

    if mapper is None:

        def _mapper(x: _T) -> list[Any]:
            return [repr(x)]

        mapper = _mapper

    return ops.do_action(
        lambda value: log_instance.log(level, format_string, *mapper(value))
    )


def debug(
    format_string: str,
    logger: str | logging.Logger | None = None,
    mapper: Callable[[_T], list[Any]] | None = None,
) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
    """Log elements passing through with DEBUG level."""
    return log(
        logging.DEBUG, format_string, logger, stack_level=2, mapper=mapper
    )


def info(
    format_string: str,
    logger: str | logging.Logger | None = None,
    mapper: Callable[[_T], list[Any]] | None = None,
) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
    """Log elements passing through with INFO level."""
    return log(
        logging.INFO, format_string, logger, stack_level=2, mapper=mapper
    )


def warning(
    format_string: str,
    logger: str | logging.Logger | None = None,
    mapper: Callable[[_T], list[Any]] | None = None,
) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
    """Log elements passing through with WARNING level."""
    return log(
        logging.WARNING, format_string, logger, stack_level=2, mapper=mapper
    )


def warn(
    format_string: str,
    logger: str | logging.Logger | None = None,
    mapper: Callable[[_T], list[Any]] | None = None,
) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
    """Log elements passing through with WARNING level."""
    return log(
        logging.WARNING, format_string, logger, stack_level=2, mapper=mapper
    )


def error(
    format_string: str,
    logger: str | logging.Logger | None = None,
    mapper: Callable[[_T], list[Any]] | None = None,
) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
    """Log elements passing through with ERROR level."""
    return log(
        logging.ERROR, format_string, logger, stack_level=2, mapper=mapper
    )
