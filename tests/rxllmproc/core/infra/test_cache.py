"""Test the cache classes."""

from typing import Any

import unittest
from unittest import mock
import datetime
from rxllmproc.core.infra import containers
from rxllmproc.core.infra import cache
import test_support


class TestCachedCall(unittest.TestCase):
    """Test Cached calls."""

    def setUp(self) -> None:
        """Provide a cache instance and patch the current time."""
        self.instance = cache.Cache()

        self.now_patch = mock.patch('rxllmproc.core.infra.cache.get_time_now')

        self.base_time = datetime.datetime(2024, 1, 1)
        self.now_time = self.base_time

        self.now_mock = self.now_patch.start()
        self.now_mock.side_effect = lambda: self.now_time

        self.addCleanup(self.now_patch.stop)

        return super().setUp()

    def test_create(self):
        """Test creating cached calls."""
        instance = cache.CachedCall.create('_val', a=111, b='vvv')
        self.assertEqual(
            instance.serialized_args,
            {'args': (), 'kwargs': {'a': 111, 'b': 'vvv'}},
        )
        self.assertEqual('_val', instance.value)

    def test_hashed(self):
        """Test hashing."""
        instance1 = cache.CachedCall.create('val', a=111, b='vvv')
        instance2 = cache.CachedCall.create('val', b='vvv', a=111)
        instance3 = cache.CachedCall.create('val', b='BAD', a=999)

        self.assertEqual(instance1.hashed_args, instance2.hashed_args)
        self.assertNotEqual(instance1.hashed_args, instance3.hashed_args)

    def test_added_set(self):
        """Test that the added timestamp is correct."""
        call = self.instance.add('some/func', 11, a=1)
        self.assertEqual(call.added, self.base_time)
        self.assertEqual(call.accessed, self.base_time)

    def test_accessed_set(self):
        """Test that the accessed timestamp is correct."""
        call = self.instance.add('some/func', 11, a=1)
        self.now_time = self.base_time + datetime.timedelta(hours=1)

        self.assertEqual(call.accessed, self.base_time)

        self.assertTrue(call.matches(a=1))

        self.assertEqual(call.accessed, self.now_time)
        self.assertEqual(call.added, self.base_time)

    def test_accessed_nomatch(self):
        """Test update of teh accessed time if not matched."""
        call = self.instance.add('some/func', 11, a=1)
        self.now_time = self.base_time + datetime.timedelta(hours=1)

        self.assertFalse(call.matches(a=2))

        self.assertEqual(call.accessed, self.base_time)
        self.assertEqual(call.added, self.base_time)


class TestCacheEntry(unittest.TestCase):
    """Test cache entries."""

    def test_simple(self):
        """Test simple insertion of a cached call."""
        instance = cache.CacheEntry()
        instance.add('_val', a=1)
        self.assertEqual(
            '_val', test_support.fail_none(instance.get(a=1)).value
        )

    def test_multiple(self):
        """Test insertion of multiple calls."""
        instance = cache.CacheEntry()
        instance.add('_val1', a=1)
        instance.add('_val2', a=2)
        self.assertEqual(
            '_val1', test_support.fail_none(instance.get(a=1)).value
        )
        self.assertEqual(
            '_val2', test_support.fail_none(instance.get(a=2)).value
        )
        self.assertIsNone(instance.get(a=3))

    def test_add_call(self):
        """Test adding a call directly."""
        instance = cache.CacheEntry()
        call = cache.CachedCall.create('val', a=1)
        instance.add_call(call)
        self.assertEqual(call, instance.get(a=1))


class TestCache(unittest.TestCase):
    """Test the cache class."""

    def test_simple(self):
        """Test simple additon of a cached call."""
        instance = cache.Cache()
        instance.add('some/func', 333, 100, a=1)

        self.assertEqual(
            333,
            test_support.fail_none(instance.get('some/func', 100, a=1)).value,
        )

    def test_multiple(self):
        """Test addition of multiple calls on different keys."""
        instance = cache.Cache()
        instance.add('some/func', 333, 100, a=1)
        instance.add('some/other', 222, 100, a=1)
        instance.add('some/func', 444, a=2)
        self.assertEqual(
            333,
            test_support.fail_none(instance.get('some/func', 100, a=1)).value,
        )
        self.assertEqual(
            222,
            test_support.fail_none(instance.get('some/other', 100, a=1)).value,
        )
        self.assertEqual(
            444, test_support.fail_none(instance.get('some/func', a=2)).value
        )

    def test_bad_keys(self):
        """Test correctly responding to bad keys."""
        instance = cache.Cache()
        instance.add('some/func', 333, 100, a=1)
        self.assertIsNone(instance.get('some/func'))
        self.assertIsNone(instance.get('some/other', a=2))
        self.assertIsNone(instance.get('some/func', a=1))

    def test_get_keys(self):
        """Test getting all keys."""
        instance = cache.Cache()
        instance.add('some/func', 333, 100, a=1)
        instance.add('other/func', 111, 200)

        actual = instance.get_keys()

        expected: Any = {
            'some/func': {
                '7176e150963e2229c37127e144ebf1d4': {
                    'args': (100,),
                    'kwargs': {'a': 1},
                }
            },
            'other/func': {
                'bc7b933da0f31dba3781f5a69da5c794': {
                    'args': (200,),
                    'kwargs': {},
                }
            },
        }
        self.assertEqual(actual, expected)

    def test_stats(self):
        """Test that collection of the cache stats works."""
        self.now_patch = mock.patch('rxllmproc.core.infra.cache.get_time_now')
        base_time = datetime.datetime(2024, 1, 1)
        now_time = base_time

        with self.now_patch as now_mock:
            now_mock.side_effect = lambda: now_time
            instance = cache.Cache()
            instance.add('xxx', 1, 1)
            instance.add('yyy', 1)
            now_time = base_time + datetime.timedelta(hours=1)
            now_time_utc = now_time.replace(tzinfo=datetime.timezone.utc)
            base_time_utc = base_time.replace(tzinfo=datetime.timezone.utc)

            instance.add('xxx', 1, 2)
            self.assertEqual(
                {
                    'xxx': cache.CacheStats(2, now_time_utc, base_time_utc),
                    'yyy': cache.CacheStats(1, base_time_utc, base_time_utc),
                },
                instance.get_stats(),
            )

    def test_add_call(self):
        """Test adding a call directly."""
        instance = cache.Cache()
        call = cache.CachedCall.create('val', a=1)
        instance.add_call('key', call)
        self.assertEqual(call, instance.get('key', a=1))


class TestTimeSpec(unittest.TestCase):
    """Test the time spec class."""

    def setUp(self) -> None:
        """Patch the current time."""
        self.now_patch = mock.patch('rxllmproc.core.infra.cache.get_time_now')

        self.base_time = datetime.datetime(2024, 1, 1)
        self.now_time = self.base_time

        self.now_mock = self.now_patch.start()
        self.now_mock.side_effect = lambda: self.now_time

        self.addCleanup(self.now_patch.stop)

        return super().setUp()

    def test_retain_access(self):
        """Test retaining an entry based on access time."""
        hours1 = datetime.timedelta(hours=1)
        spec = cache.TimeSpec(self.base_time + hours1, datetime.datetime.min)

        self.now_time = self.base_time
        instance = cache.CachedCall.create(11, a=1)

        self.now_time = self.base_time + hours1 + hours1

        self.assertFalse(spec.retain_call(instance))
        self.assertTrue(instance.matches(a=1))
        self.assertTrue(spec.retain_call(instance))

    def test_no_retain_access(self):
        """Test dropping an entry based on access time."""
        hours1 = datetime.timedelta(hours=1)
        spec = cache.TimeSpec(self.base_time + hours1, datetime.datetime.min)

        self.now_time = self.base_time
        instance = cache.CachedCall.create(11, a=1)

        self.assertFalse(spec.retain_call(instance))
        self.assertTrue(instance.matches(a=1))
        self.assertFalse(spec.retain_call(instance))

    def test_retain_added(self):
        """Test retaining an entry based on added time."""
        hours1 = datetime.timedelta(hours=1)
        spec = cache.TimeSpec(datetime.datetime.min, self.base_time + hours1)

        self.now_time = self.base_time
        instance = cache.CachedCall.create(11, a=1)
        self.assertFalse(spec.retain_call(instance))

        self.now_time = self.base_time + hours1 + hours1
        instance = cache.CachedCall.create(11, a=1)
        self.assertTrue(spec.retain_call(instance))

    def test_no_retain_both_full_spec(self):
        """Test dropping an entry when older than access and added time."""
        hours1 = datetime.timedelta(hours=1)
        spec = cache.TimeSpec(self.base_time + hours1, self.base_time - hours1)

        self.now_time = self.base_time - hours1
        instance = cache.CachedCall.create(11, a=1)
        # Not accessed
        self.assertFalse(spec.retain_call(instance))

        self.now_time = self.base_time
        instance = cache.CachedCall.create(11, a=1)
        # Not accessed
        self.assertFalse(spec.retain_call(instance))

        self.now_time = self.base_time
        instance = cache.CachedCall.create(11, a=1)
        self.assertTrue(instance.matches(a=1))
        self.assertFalse(spec.retain_call(instance))

        self.now_time = self.base_time + hours1
        instance = cache.CachedCall.create(11, a=1)
        self.assertTrue(instance.matches(a=1))
        self.assertTrue(spec.retain_call(instance))


class TestPurgeWalker(unittest.TestCase):
    """Test the purge walker class."""

    def setUp(self) -> None:
        """Provide a cache instane and patch the current time."""
        self.instance = cache.Cache()

        self.now_patch = mock.patch('rxllmproc.core.infra.cache.get_time_now')

        self.base_time = datetime.datetime(2024, 1, 1)
        self.now_time = self.base_time

        self.now_mock = self.now_patch.start()
        self.now_mock.side_effect = lambda: self.now_time

        self.addCleanup(self.now_patch.stop)

        return super().setUp()

    def test_no_params(self):
        """Test purging without expiration."""
        call_instance = self.instance.add('some/call', 11, a=1)

        self.assertFalse(cache.PurgeWalker().purge_cache(self.instance))
        self.assertEqual(call_instance, self.instance.get('some/call', a=1))

    def test_added_age_no_purge(self):
        """Test purging on non-expired added entry."""
        hours1 = datetime.timedelta(hours=1)
        call_instance = self.instance.add('some/call', 11, a=1)

        self.assertFalse(
            cache.PurgeWalker(
                default_age={
                    'max_age_added': hours1,
                },
                reference_time=self.base_time + hours1,
            ).purge_cache(self.instance)
        )
        self.assertEqual(call_instance, self.instance.get('some/call', a=1))

    def test_added_age_purge(self):
        """Test purging on expired added entry."""
        hours1 = datetime.timedelta(hours=1)
        self.instance.add('some/call', 11, a=1)

        self.assertTrue(
            cache.PurgeWalker(
                default_age={
                    'max_age_added': hours1,
                },
                reference_time=self.base_time + hours1 + hours1,
            ).purge_cache(self.instance)
        )
        self.assertIsNone(self.instance.get('some/call', a=1))

    def test_accessed_age_no_purge(self):
        """Test purging on non-expired accessed entry."""
        hours1 = datetime.timedelta(hours=1)
        call_instance = self.instance.add('some/call', 11, a=1)
        self.assertTrue(
            call_instance.matches(a=1)
        )  # Trigger new accessed timestamp

        self.assertFalse(
            cache.PurgeWalker(
                default_age={
                    'max_age_accessed': hours1,
                },
                reference_time=self.base_time + hours1,
            ).purge_cache(self.instance)
        )
        self.assertEqual(call_instance, self.instance.get('some/call', a=1))

    def test_accessed_age_purge(self):
        """Test purging on expired accessed entry."""
        hours1 = datetime.timedelta(hours=1)
        self.instance.add('some/call', 11, a=1)

        self.assertTrue(
            cache.PurgeWalker(
                default_age={
                    'max_age_accessed': hours1,
                },
                reference_time=self.base_time + hours1 + hours1,
            ).purge_cache(self.instance)
        )
        self.assertIsNone(self.instance.get('some/call', a=1))

    def test_retain_good(self):
        """Test retaining non-expired entries."""
        hours1 = datetime.timedelta(hours=1)
        self.instance.add('some/call', 11, a=1)

        self.now_time = self.base_time + hours1
        call_instance1 = self.instance.add('some/call', 11, a=2)
        call_instance2 = self.instance.add('other/call', 11, a=2)

        self.assertFalse(
            cache.PurgeWalker(
                default_age={
                    'max_age_added': hours1,
                },
                reference_time=self.base_time + hours1 + hours1,
            ).purge_cache(self.instance)
        )

        self.assertIsNone(self.instance.get('some/call', a=1))
        self.assertEqual(call_instance1, self.instance.get('some/call', a=2))
        self.assertEqual(call_instance2, self.instance.get('other/call', a=2))


class TestPrefixCache(unittest.TestCase):
    """Test the prefix cache class."""

    def setUp(self) -> None:
        """Provide a cache instance."""
        self.instance = cache.Cache()
        return super().setUp()

    def test_add(self):
        """Test adding an entry."""
        prefixed = cache.PrefixCache(self.instance, 'a/')

        cached_call = prefixed.add('b', 1)

        self.assertEqual(cached_call, self.instance.get('a/b'))

    def test_get(self):
        """Test retreiving an entry."""
        cached_call = self.instance.add('xxx/y', 1)

        prefixed = cache.PrefixCache(self.instance, 'xxx/')

        self.assertEqual(cached_call, prefixed.get('y'))

    def test_nested(self):
        """Test nested prefix caches."""
        prefixed1 = cache.PrefixCache(self.instance, 'a/')
        prefixed2 = cache.PrefixCache(prefixed1, 'b/')
        cached_call = prefixed2.add('c', 1)

        self.assertEqual(cached_call, self.instance.get('a/b/c'))
        self.assertEqual(cached_call, prefixed1.get('b/c'))

    def test_get_keys(self):
        """Test getting keys of prefix caches."""
        prefixed1 = cache.PrefixCache(self.instance, 'a/')
        prefixed2 = cache.PrefixCache(prefixed1, 'b/')
        prefixed1.add('x', 1)
        prefixed2.add('y', 1)

        self.assertEqual(set(prefixed1.get_keys().keys()), {'b/y', 'x'})
        self.assertEqual(set(prefixed2.get_keys().keys()), {'y'})

    def test_add_call(self):
        """Test adding a call directly."""
        prefixed = cache.PrefixCache(self.instance, 'a/')
        call = cache.CachedCall.create('val', a=1)
        prefixed.add_call('b', call)
        self.assertEqual(call, self.instance.get('a/b', a=1))


SAVED_DATA = '''
{
  "py/object": "rxllmproc.core.infra.cache.Cache",
  "py/state": {
    "registry": {
      "some_key": {
        "py/object": "rxllmproc.core.infra.cache.CacheEntry",
        "py/state": {
          "calls": {
            "8cc0c43bbf128d9a716f2a9107bc4812": {
              "py/object": "rxllmproc.core.infra.cache.CachedCall",
              "serialized_args": {
                "args": {
                  "py/tuple": []
                },
                "kwargs": {
                  "a": 1
                }
              },
              "hashed_args": "8cc0c43bbf128d9a716f2a9107bc4812",
              "value": 123,
              "added": {
                "py/object": "datetime.datetime",
                "__reduce__": [
                  {
                    "py/type": "datetime.datetime"
                  },
                  [
                    "B+gBAQAAAAAAAA==",
                    {
                      "py/reduce": [
                        {
                          "py/type": "datetime.timezone"
                        },
                        {
                          "py/tuple": [
                            {
                              "py/reduce": [
                                {
                                  "py/type": "datetime.timedelta"
                                },
                                {
                                  "py/tuple": [
                                    0,
                                    0,
                                    0
                                  ]
                                }
                              ]
                            }
                          ]
                        }
                      ]
                    }
                  ]
                ]
              },
              "accessed": {
                "py/object": "datetime.datetime",
                "__reduce__": [
                  {
                    "py/type": "datetime.datetime"
                  },
                  [
                    "B+gBAQAAAAAAAA==",
                    {
                      "py/id": 10
                    }
                  ]
                ]
              }
            }
          }
        }
      }
    }
  }
}
'''.strip('\n')


class TestCacheManager(unittest.TestCase):
    """Test the cache manager class."""

    def setUp(self) -> None:
        """Provide a cache instance and patch now time."""
        self.instance = cache.Cache()

        self.now_patch = mock.patch('rxllmproc.core.infra.cache.get_time_now')

        self.base_time = datetime.datetime(2024, 1, 1)
        self.now_time = self.base_time

        self.now_mock = self.now_patch.start()
        self.now_mock.side_effect = lambda: self.now_time

        self.addCleanup(self.now_patch.stop)

        self.mock_container = mock.Mock(spec=containers.Container)

        return super().setUp()

    def test_store(self):
        """Test storing the cache instance."""
        hours1 = datetime.timedelta(hours=1)

        self.mock_container.exists.return_value = False

        mgr = cache.CacheManager(
            storage=self.mock_container,
            default_age={'max_age_accessed': hours1},
        )
        self.instance.add('some_key', 123, a=1)

        mgr.store(self.instance)

        self.mock_container.put.assert_called_with(SAVED_DATA)

    def test_load(self):
        """Test loading the cache instance."""
        hours1 = datetime.timedelta(hours=1)

        self.mock_container.exists.return_value = True
        self.mock_container.get.return_value = SAVED_DATA

        mgr = cache.CacheManager(
            storage=self.mock_container,
            default_age={'max_age_accessed': hours1},
        )

        new_instance = mgr.load()

        call = new_instance.get('some_key', a=1)
        if call is None:
            self.fail()
        self.assertEqual(123, call.value)

    def test_load_nonexisting(self):
        """Test loading from non-existing Container."""
        hours1 = datetime.timedelta(hours=1)

        self.mock_container.exists.return_value = False

        mgr = cache.CacheManager(
            storage=self.mock_container,
            default_age={'max_age_accessed': hours1},
        )

        self.assertRaisesRegex(
            Exception, '.*container does not exist.*', lambda: mgr.load()
        )
        self.mock_container.get.assert_not_called()

    def test_create(self):
        """Test creating a cache instance."""
        hours1 = datetime.timedelta(hours=1)

        self.mock_container.exists.return_value = False

        mgr = cache.CacheManager(
            storage=self.mock_container,
            default_age={'max_age_accessed': hours1},
        )

        new_instance = mgr.load_or_create()

        self.assertFalse(new_instance.get_keys())
        self.mock_container.get.assert_not_called()


class TestCachedCallFunction(unittest.TestCase):
    """Test the cached_call function."""

    def test_exception(self):
        """Test that exceptions remove the cache entry."""
        instance = cache.Cache()

        def failing_func(a: Any):
            raise ValueError('Boom')

        with self.assertRaises(ValueError):
            cache.cached_call(instance, 'key', failing_func, a=1)

        # Verify it's gone
        self.assertIsNone(instance.get('key', a=1))

    def test_success(self):
        """Test that successful calls are cached."""
        instance = cache.Cache()

        def success_func(a: int) -> int:
            return a + 1

        result = cache.cached_call(instance, 'key', success_func, a=1)
        self.assertEqual(2, result)

        # Verify it's cached
        self.assertEqual(
            2, test_support.fail_none(instance.get('key', a=1)).value
        )
