# pyright: basic
"""Test general utilities."""

import unittest
from unittest import mock
from typing import Any, Mapping, MutableMapping
import dataclasses
import threading
from email import message
import logging
import reactivex as rx
from parameterized import parameterized

from rxllmproc.core.infra import utilities


@dataclasses.dataclass
class SampleClass:
    """Sample class used for the tests."""

    a: int
    b: set[str]


@dataclasses.dataclass
class SampleClass1:
    """Another sample class, with annotation."""

    s: dict[str, SampleClass]

    # Annotated to be skipped during sample creation.
    t: str | None = dataclasses.field(
        default=None, metadata={'skip_sample': True}
    )


@dataclasses.dataclass
class SampleClassProtocol(utilities.AsDictConvertible):
    """Another sample class, using asdict() to convert."""

    # Annotated to be skipped during sample creation.
    t: str | None = dataclasses.field(
        default=None, metadata={'skip_sample': True}
    )

    def asdict(self) -> Any:
        return {'_t': self.t}


@dataclasses.dataclass
class SampleClassSkipSchema:
    """Sample class with skip_schema."""

    a: int
    b: str = dataclasses.field(metadata={'skip_schema': True})


def _mk_message() -> message.Message:
    msg = message.Message()
    msg.add_header('To', 'a@b.ch')
    return msg


class TestAsdict(unittest.TestCase):
    """Test conversion to dict structure."""

    @parameterized.expand(
        [
            (101,),
            (int,),
            ({'a': 1, 'b': 2},),
            ([1, 2, 3],),
            ({'a': [1, 2, 3], 'b': set([4, 1])},),
            ([1, [2, 2.1], 3],),
        ]
    )
    def test_astuple_identical(self, value: Any):
        """Test inputs that are not converted."""
        self.assertEqual(value, utilities.asdict(value))

    @parameterized.expand(
        [
            (
                SampleClass(10, {'a', 'b'}),
                {'a': 10, 'b': {'a', 'b'}},
            ),
            (
                SampleClass1({'v': SampleClass(10, {'a', 'b'})}),
                {
                    's': {'v': {'a': 10, 'b': {'a', 'b'}}},
                    't': None,
                },
            ),
            (
                SampleClassProtocol('ttt'),
                {'_t': 'ttt'},
            ),
            (
                _mk_message(),
                '\'To: a@b.ch\\n\\n\'',
            ),
        ]
    )
    def test_astuple_dataclass(self, value: Any, expected: Any):
        """Test conversion of dataclasses."""
        self.assertEqual(expected, utilities.asdict(value))


class TestBuildSample(unittest.TestCase):
    """Test building sample data from classes."""

    @parameterized.expand(
        [
            (int, 123),
            (str, 'string here'),
            (list[int], [123]),
            (dict[int, int], {345: 123}),
            (
                SampleClass1,
                {'s': {'some key': {'a': 123, 'b': ['string here']}}},
            ),
        ]
    )
    def test_without_sample(self, cls: type[object], expected: Any):
        """Test conversion where no samples are provided."""
        self.assertEqual(expected, utilities.build_sample(cls))

    @parameterized.expand(
        [
            (int, 999, 999),
            (str, 'blah', 'blah'),
            (list[int], [1, 2, 3], [1, 2, 3]),
            (
                dict[str, int],
                {'key1': 999, 'key2': 888},
                {'key1': 999, 'key2': 888},
            ),
            (
                SampleClass1,
                SampleClass1({'key3': SampleClass(444, {'abc'})}),
                {
                    's': {'key3': {'a': 444, 'b': {'abc'}}},
                    't': None,
                },
            ),
        ]
    )
    def test_with_sample(self, cls: type[object], sample: Any, expected: Any):
        """Test creation where a sample value is provided."""
        self.assertEqual(expected, utilities.build_sample(cls, sample))


class DummyOverlay(utilities.OverlayDict[str, int]):
    """Test only class, implementing the overlay as simple dict."""

    def __init__(
        self,
        base: dict[str, int] | None = None,
        overlay: Mapping[str, int] | None = None,
        /,
        **kwargs: Any,
    ):
        """Create an instance."""
        super().__init__(base, **kwargs)
        self.overlay: dict[str, int] = dict(overlay) if overlay else {}

    def _overlay_data(self) -> MutableMapping[str, int]:
        """Return the overlay dict, stored in the object."""
        return self.overlay


class TestOverlayDict(unittest.TestCase):
    """Test the OverlayDict class using DummyOverlay above."""

    def test_base_only(self):
        """Test base dict functionality with only base items set."""
        d = DummyOverlay({'a': 1, 'b': 2})
        self.assertEqual(1, d['a'])
        self.assertEqual(2, len(d))
        self.assertEqual({'a', 'b'}, set(iter(d)))
        d.data['c'] = 3
        self.assertEqual(3, d['c'])
        self.assertTrue('a' in d)

    def test_base_update(self):
        """Test base dict update with only base items set."""
        b = {'a': 1, 'b': 2}
        d = DummyOverlay(b)
        self.assertEqual(1, d['a'])

        b['a'] = 11
        self.assertEqual(11, d['a'])

    def test_overlay_only(self):
        """Test base dict functionality with only overlay items set."""
        d = DummyOverlay({}, {'a': 1, 'b': 2})
        self.assertEqual(1, d['a'])
        self.assertEqual(2, len(d))
        self.assertEqual({'a', 'b'}, set(iter(d)))
        d['c'] = 3
        self.assertEqual({}, d.data)
        self.assertEqual(3, d['c'])
        self.assertTrue('a' in d)

    def test_mixed(self):
        """Test mixed base and overlay items."""
        d = DummyOverlay({'a': 1}, {'b': 2})
        self.assertEqual(1, d['a'])
        self.assertEqual(2, len(d))
        self.assertEqual({'a', 'b'}, set(iter(d)))
        d['c'] = 3
        self.assertEqual({'a': 1}, d.data)
        self.assertEqual(3, d['c'])
        self.assertTrue('a' in d)
        self.assertTrue('b' in d)

    def test_delete(self):
        """Test deleting from the overlay."""
        d = DummyOverlay({'a': 1}, {'b': 2, 'c': 3})
        del d['c']
        self.assertEqual({'a': 1, 'b': 2}, d)

    def test_delete_from_base(self):
        """Test deleting non-existent key from overlay."""
        d = DummyOverlay({'a': 1}, {'b': 2})

        def f():
            del d['a']

        self.assertRaisesRegex(KeyError, '.*only.*overlay.*', f)


class TestThreadOverlayDict(unittest.TestCase):
    """Test the thread-local overlay dict."""

    def setUp(self) -> None:
        """Set up items needed in both threads."""
        self.continue_threads = threading.Event()

        base = {'s1': 1}
        self.d = utilities.ThreadOverlayDict(base)

        self.failed: str = ''
        return super().setUp()

    def run_a(self):
        """Run in thread A."""
        self.d['a1'] = 11
        self.d.data['sa'] = 111
        if not self.continue_threads.wait(5):
            self.failed = 'Thread A timed out'
            return
        if 'b1' in self.d:
            self.failed = 'Found b key in a thread.'
            return

        v = self.d.get('s1', 99)
        if v != 1:
            self.failed = f's1 key has unexpected value {v}.'
            return

        v = self.d.get('sa', 99)
        if v != 111:
            self.failed = f'sa key has unexpected value {v}.'
            return

        v = self.d.get('sb', 99)
        if v != 222:
            self.failed = f'sb key has unexpected value {v}.'
            return

        v = self.d.get('a1', 99)
        if v != 11:
            self.failed = f'a1 key has unexpected value {v}.'
            return

    def run_b(self):
        """Run in thread B."""
        self.d['b1'] = 22
        self.d.data['sb'] = 222
        if not self.continue_threads.wait(5):
            self.failed = 'Thread B timed out'
            return
        if 'a1' in self.d:
            self.failed = 'Found a key in a thread.'
            return

        v = self.d.get('s1', 99)
        if v != 1:
            self.failed = f's1 key has unexpected value {v}.'
            return

        v = self.d.get('sa', 99)
        if v != 111:
            self.failed = f'sa key has unexpected value {v}.'
            return

        v = self.d.get('sb', 99)
        if v != 222:
            self.failed = f'sb key has unexpected value {v}.'
            return

        v = self.d.get('b1', 99)
        if v != 22:
            self.failed = f'b1 key has unexpected value {v}.'
            return

    def test_two(self):
        """Test two threads."""
        a_thread = threading.Thread(target=self.run_a)
        b_thread = threading.Thread(target=self.run_b)

        a_thread.start()
        b_thread.start()
        self.assertEqual({'s1': 1, 'sa': 111, 'sb': 222}, self.d)
        self.continue_threads.set()
        a_thread.join(5)
        b_thread.join(5)
        if a_thread.is_alive():
            self.fail('a thread still alive')
        if b_thread.is_alive():
            self.fail('b thread still alive')

        if self.failed:
            self.fail(f'failed in threads: {self.failed}')


@dataclasses.dataclass
class SampleClass2:
    """Sample class used for the tests."""

    a: int = 0
    b: str = ''


class TestDataclassFromAssignments(unittest.TestCase):
    """Test building a dataclass from a list of assignments."""

    @parameterized.expand(
        [
            ([('a', 22)], SampleClass2(22)),
            ([('a', 22), ('a', 33)], SampleClass2(33)),
            ([], SampleClass2()),
            ([('b', 'xx'), ('a', 22)], SampleClass2(22, 'xx')),
        ]
    )
    def test_simple(self, data: list[tuple[str, str]], expected: SampleClass2):
        """Test simple case."""
        result = utilities.dataclass_from_assignments(SampleClass2, data)
        self.assertEqual(expected, result)

    def test_unknown(self):
        """Test failing on setting an unknown property."""
        data = [('x', 'blah')]
        self.assertRaisesRegex(
            ValueError,
            'failed to set field',
            lambda: utilities.dataclass_from_assignments(SampleClass2, data),
        )

    def test_unknown_accepted(self):
        """Test ignoring setting an unknown property."""
        data = [('x', 'blah')]
        result = utilities.dataclass_from_assignments(
            SampleClass2,
            data,
            ignore_unmatched=True,
        )
        self.assertEqual(SampleClass2(), result)

    def test_not_dataclass(self):
        """Test failing if not going for dataclass."""
        data = [('x', 'blah')]
        self.assertRaisesRegex(
            TypeError,
            'not a dataclass',
            lambda: utilities.dataclass_from_assignments(int, data),
        )


class TestRetryBackoff(unittest.TestCase):

    def test_simple(self):
        sleep_mock = mock.Mock()
        num = 3

        def _func_to_run(rv: str) -> str:
            nonlocal num
            num -= 1
            if num == 0:
                return rv
            raise KeyError()

        self.assertEqual(
            'DONE',
            utilities.with_backoff_retry(
                _func_to_run, KeyError, delay_func=sleep_mock
            )('DONE'),
        )

        self.assertEqual(
            [mock.call(10), mock.call(20)], sleep_mock.call_args_list
        )

    def test_direct(self):
        sleep_mock = mock.Mock()

        def _func_to_run():
            return 'DONE'

        self.assertEqual(
            'DONE',
            utilities.with_backoff_retry(
                _func_to_run, KeyError, delay_func=sleep_mock
            )(),
        )

        sleep_mock.assert_not_called()

    def test_retries_exhausted(self):
        sleep_mock = mock.Mock()
        num = 3

        def _func_to_run(rv: str) -> str:
            nonlocal num
            num -= 1
            if num == 0:
                return rv
            raise KeyError('xxxx')

        self.assertRaisesRegex(
            KeyError,
            'xxxx',
            lambda: utilities.with_backoff_retry(
                _func_to_run, KeyError, num_retries=1, delay_func=sleep_mock
            )('DONE'),
        )

        self.assertEqual([mock.call(10)], sleep_mock.call_args_list)


class TestBuildJsonSchema(unittest.TestCase):
    """Test building JSON schema from classes."""

    def test_simple(self):
        """Test simple dataclass."""
        schema = utilities.build_json_schema(SampleClass)
        expected = {
            'type': 'object',
            'description': 'Sample class used for the tests.',
            'properties': {
                'a': {'type': 'integer'},
                'b': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['a', 'b'],
        }
        self.assertEqual(expected, schema)

    def test_nested(self):
        """Test nested dataclass."""
        self.maxDiff = None
        schema = utilities.build_json_schema(SampleClass1)
        expected = {
            'type': 'object',
            'description': 'Another sample class, with annotation.',
            'properties': {
                's': {
                    'type': 'object',
                    'additionalProperties': {
                        'type': 'object',
                        'description': 'Sample class used for the tests.',
                        'properties': {
                            'a': {'type': 'integer'},
                            'b': {
                                'type': 'array',
                                'items': {'type': 'string'},
                            },
                        },
                        'required': ['a', 'b'],
                    },
                },
                't': {'type': 'string'},
            },
            'required': ['s'],
        }
        self.assertEqual(expected, schema)

    def test_list(self):
        """Test list type."""
        schema = utilities.build_json_schema(list[int])
        expected = {
            'type': 'array',
            'items': {'type': 'integer'},
        }
        self.assertEqual(expected, schema)

    def test_skip_schema(self):
        """Test skip_schema metadata."""
        schema = utilities.build_json_schema(SampleClassSkipSchema)
        expected = {
            'type': 'object',
            'description': 'Sample class with skip_schema.',
            'properties': {
                'a': {'type': 'integer'},
            },
            'required': ['a'],
        }
        self.assertEqual(expected, schema)


class TestRxLog(unittest.TestCase):
    """Test the reactive logging operators."""

    def test_log_explicit_logger(self):
        """Test logging with an explicit logger instance."""
        mock_logger = mock.Mock()
        source = rx.from_iterable([1, 2])

        source.pipe(
            utilities.log(logging.INFO, 'Value: %s', logger=mock_logger)
        ).subscribe()

        self.assertEqual(
            [
                mock.call(logging.INFO, 'Value: %s', '1'),
                mock.call(logging.INFO, 'Value: %s', '2'),
            ],
            mock_logger.log.call_args_list,
        )

    def test_log_logger_name(self):
        """Test logging with a logger name."""
        with mock.patch('logging.getLogger') as mock_get_logger:
            mock_logger = mock.Mock()
            mock_get_logger.return_value = mock_logger

            source = rx.from_iterable(['a'])
            source.pipe(
                utilities.log(logging.DEBUG, 'Msg: %s', logger='my.logger')
            ).subscribe()

            mock_get_logger.assert_called_with('my.logger')
            mock_logger.log.assert_called_with(logging.DEBUG, 'Msg: %s', "'a'")

    def test_log_default_logger(self):
        """Test logging with default logger (caller module)."""
        with mock.patch('logging.getLogger') as mock_get_logger:
            mock_logger = mock.Mock()
            mock_get_logger.return_value = mock_logger

            source = rx.from_iterable([1])
            # stack_level=1 in log() means it looks at caller of log().
            # Here we call utilities.log directly.
            source.pipe(utilities.log(logging.WARNING, 'Warn: %s')).subscribe()

            # The logger name should be the name of the current module (tests...)
            mock_get_logger.assert_called()
            args, _ = mock_get_logger.call_args
            self.assertEqual(__name__, args[0])

            mock_logger.log.assert_called_with(logging.WARNING, 'Warn: %s', '1')

    def test_log_mapper(self):
        """Test logging with a custom mapper."""
        mock_logger = mock.Mock()
        source = rx.from_iterable([{'a': 1}])

        source.pipe(
            utilities.log(
                logging.INFO,
                'Val: %s',
                logger=mock_logger,
                mapper=lambda x: [x['a']],
            )
        ).subscribe()

        mock_logger.log.assert_called_with(logging.INFO, 'Val: %s', 1)

    def test_helpers(self):
        """Test debug, info, warning, error helpers."""
        mock_logger = mock.Mock()
        source = rx.from_iterable([1])

        source.pipe(utilities.debug('D: %s', logger=mock_logger)).subscribe()
        mock_logger.log.assert_called_with(logging.DEBUG, 'D: %s', '1')

        source.pipe(utilities.info('I: %s', logger=mock_logger)).subscribe()
        mock_logger.log.assert_called_with(logging.INFO, 'I: %s', '1')

        source.pipe(utilities.warning('W: %s', logger=mock_logger)).subscribe()
        mock_logger.log.assert_called_with(logging.WARNING, 'W: %s', '1')

        source.pipe(utilities.error('E: %s', logger=mock_logger)).subscribe()
        mock_logger.log.assert_called_with(logging.ERROR, 'E: %s', '1')

    def test_helpers_stack_level(self):
        """Test that helpers use the correct stack level for logger name."""
        with mock.patch('logging.getLogger') as mock_get_logger:
            mock_logger = mock.Mock()
            mock_get_logger.return_value = mock_logger

            source = rx.from_iterable([1])
            source.pipe(utilities.debug('D: %s')).subscribe()

            mock_get_logger.assert_called()
            args, _ = mock_get_logger.call_args
            self.assertEqual(__name__, args[0])

    def test_helpers_mapper(self):
        """Test helpers with custom mapper."""
        mock_logger = mock.Mock()
        source = rx.from_iterable([{'a': 1}])

        source.pipe(
            utilities.info(
                'I: %s', logger=mock_logger, mapper=lambda x: [x['a']]
            )
        ).subscribe()
        mock_logger.log.assert_called_with(logging.INFO, 'I: %s', 1)


class TestRemoveNone(unittest.TestCase):
    """Test the remove_none operator."""

    def test_remove_none(self):
        """Test that None values are removed."""
        source = rx.from_iterable([1, None, 2, None, 3])
        results = []
        source.pipe(utilities.remove_none()).subscribe(results.append)
        self.assertEqual([1, 2, 3], results)
