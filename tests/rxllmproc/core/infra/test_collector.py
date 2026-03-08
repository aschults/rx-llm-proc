"""Test collector classes."""

import unittest
from typing import Any

from reactivex import from_list

from rxllmproc.core.infra import collector

from test_support import RecordingObserver


class TestMemoryCollector(unittest.TestCase):
    """Test the memory collector class."""

    def test_touch(self):
        """Test that touching inits the keys."""
        coll = collector.MemoryCollector()
        coll.touch('a')
        coll.touch('b')

        self.assertEqual({'a': 0, 'b': 0}, coll.data)

    def test_counter(self):
        """Test that increase works."""
        coll = collector.MemoryCollector()
        coll.increase('a')
        coll.increase('a')
        coll.increase('b')

        self.assertEqual({'a': 2, 'b': 1}, coll.data)

    def test_sample(self):
        """Test that the collector stores samples and emits them."""
        coll = collector.MemoryCollector()

        recorder = RecordingObserver[Any]()
        coll.sample_observable.subscribe(recorder)

        coll.sample('a', 'xxx')
        coll.sample('b', 'yyy')

        self.assertEqual({'a': 'xxx', 'b': 'yyy'}, coll.samples)
        self.assertEqual([('a', 'xxx'), ('b', 'yyy')], recorder.result)

    def test_exception(self):
        """Test that exceptions are processed."""
        coll = collector.MemoryCollector()
        coll.sample('a', 'xxx')
        coll.sample('b', 'yyy')

        recorder = RecordingObserver[Any]()
        coll.exception_observable.subscribe(recorder)

        self.assertEqual({'a': 'xxx', 'b': 'yyy'}, coll.samples)


class TestCollectingObserver(unittest.TestCase):
    """Test the Collecting observer class."""

    def test_counter(self):
        """Test that each passed item is counted."""
        coll = collector.MemoryCollector()
        from_list([1, 2]).subscribe(collector.CollectingObserver('x', coll))
        self.assertEqual({'x': 2}, coll.data)

    def test_counter_name_function(self):
        """Test that a function can be passed as key."""
        coll = collector.MemoryCollector()
        from_list([1, 2]).subscribe(
            collector.CollectingObserver(lambda: 'yyy', coll)
        )
        self.assertEqual({'yyy': 2}, coll.data)

    def test_sample(self):
        """Test that each passing item is counted."""
        coll = collector.MemoryCollector()
        recorder = RecordingObserver[Any]()
        coll.sample_observable.subscribe(recorder)

        from_list([5, 6, 7, 8]).subscribe(
            collector.CollectingObserver('x', coll, 2)
        )

        self.assertEqual({'x': 8}, coll.samples)
        self.assertEqual([('x', 6), ('x', 8)], recorder.result)

    def test_exception(self):
        """Test that each passing item is counted."""
        coll = collector.MemoryCollector()
        recorder = RecordingObserver[Any]()
        coll.exception_observable.subscribe(recorder)
        exc = Exception('xxx')
        collector.CollectingObserver('x', coll).on_error(exc)
        self.assertEqual([exc], recorder.result)
