"""Tests for docs operators."""

import unittest
from unittest import mock
import reactivex as rx
from rxllmproc.docs import operators, docs_model


class TestBatchEditor(unittest.TestCase):
    """Test the BatchEditor class."""

    def setUp(self):
        self.mock_doc = mock.Mock(spec=docs_model.Document)
        self.editor = operators.BatchEditor(self.mock_doc)

    def test_add_and_execute_simple(self):
        """Test adding and executing a single operation."""
        op1 = operators.InsertOperation(
            index=10, content="text", origin_ids=["1"]
        )
        self.editor.add(op1)

        ids = self.editor.execute()

        self.mock_doc.insert_markdown_at.assert_called_with(10, "text")
        self.assertEqual(ids, ["1"])
        self.assertEqual(self.editor.ops, [])

    def test_sorting_order(self):
        """Test that operations are sorted by index descending."""
        # Op at 5
        op1 = operators.InsertOperation(index=5, content="A", origin_ids=["A"])
        # Op at 10
        op2 = operators.DeleteOperation(start=10, end=15, origin_ids=["B"])

        self.editor.add(op1)
        self.editor.add(op2)

        self.editor.execute()

        # Should execute op2 (index 10) then op1 (index 5)
        call_args = self.mock_doc.mock_calls
        self.assertEqual(len(call_args), 2)
        self.assertEqual(call_args[0][0], 'delete_range')  # 10
        self.assertEqual(call_args[1][0], 'insert_markdown_at')  # 5

    def test_sorting_same_index(self):
        """Test that Delete comes before Insert at same index."""
        # Insert at 10
        op1 = operators.InsertOperation(index=10, content="A", origin_ids=["A"])
        # Delete at 10
        op2 = operators.DeleteOperation(start=10, end=15, origin_ids=["B"])

        self.editor.add(op1)
        self.editor.add(op2)

        self.editor.execute()

        # Delete (priority 1) should come before Insert (priority 0) at same index
        call_args = self.mock_doc.mock_calls
        self.assertEqual(len(call_args), 2)
        self.assertEqual(call_args[0][0], 'delete_range')
        self.assertEqual(call_args[1][0], 'insert_markdown_at')


class TestApplyBatchEdits(unittest.TestCase):
    """Test the apply_batch_edits operator."""

    def setUp(self):
        self.mock_doc = mock.Mock(spec=docs_model.Document)

    def test_apply(self):
        """Test applying a stream of edits."""
        op1 = operators.InsertOperation(index=10, content="A", origin_ids=["1"])
        op2 = operators.InsertOperation(index=20, content="B", origin_ids=["2"])

        source = rx.from_iterable([op1, op2])
        results: list[str] = []

        source.pipe(operators.apply_batch_edits(self.mock_doc)).subscribe(
            results.append
        )

        # Should have executed both
        self.assertEqual(self.mock_doc.insert_markdown_at.call_count, 2)
        # Results should contain origin ids
        self.assertEqual(set(results), {"1", "2"})


class TestInsertMarkdown(unittest.TestCase):
    """Test the insert_markdown operator."""

    def setUp(self):
        self.mock_doc = mock.Mock(spec=docs_model.Document)

    def test_insert_static(self):
        """Test insertion without moving index."""
        # Index doesn't move forward
        self.mock_doc.insert_markdown_at.return_value = 10

        source = rx.from_iterable(["A", "B"])
        results: list[int] = []

        source.pipe(
            operators.insert_markdown(
                self.mock_doc, index=10, insert_forward=False
            )
        ).subscribe(results.append)

        # Should call insert at 10 twice
        self.mock_doc.insert_markdown_at.assert_has_calls(
            [
                mock.call(10, "A", get_end=False),
                mock.call(10, "B", get_end=False),
            ]
        )
        self.assertEqual(results, [10, 10])

    def test_insert_forward(self):
        """Test insertion with moving index."""
        # First call returns 15, second call returns 20
        self.mock_doc.insert_markdown_at.side_effect = [15, 20]

        source = rx.from_iterable(["A", "B"])
        results: list[int] = []

        source.pipe(
            operators.insert_markdown(
                self.mock_doc, index=10, insert_forward=True
            )
        ).subscribe(results.append)

        # First call at 10, second call at 15 (result of first)
        self.mock_doc.insert_markdown_at.assert_has_calls(
            [mock.call(10, "A", get_end=True), mock.call(15, "B", get_end=True)]
        )
        self.assertEqual(results, [15, 20])
