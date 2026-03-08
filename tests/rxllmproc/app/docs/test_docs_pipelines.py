# pyright: reportPrivateUsage=false
"""Test Docs Processing."""

import unittest
from unittest import mock

import reactivex as rx
from reactivex import operators as ops

from rxllmproc.app.docs import pipelines
from rxllmproc.app.docs import types as docs_types
from rxllmproc.app import environment
from rxllmproc.database import operators as sql_operators
from rxllmproc.app.analysis import types as analysis_types
from rxllmproc.docs import operators as docs_operators
from rxllmproc.core.infra import utilities


class TestDocsPipeline(unittest.TestCase):
    """Test the docs processing pipeline."""

    def setUp(self):
        """Set up the test environment.

        Mocks the database, environment, document model, and various
        dependencies required for the DocsPipeline and MarkdownIndexInserter.
        """
        self.mock_db = mock.Mock(spec=sql_operators.RxDatabase)
        self.mock_db.session = mock.Mock()
        # Mock result for get_placement_ids
        self.mock_db.session.execute.return_value.tuples.return_value.all.return_value = [
            ("doc_id_2", 2)
        ]

        # Mock transaction and upsert
        self.mock_transaction = mock.Mock()
        self.mock_transaction.upsert_op.return_value = utilities.identity
        self.mock_db.element_transaction.return_value = self.mock_transaction

        # Mock Environment
        self.shared_env_patch = mock.patch(
            "rxllmproc.app.docs.pipelines.app_environment.shared"
        )
        self.mock_shared_env = self.shared_env_patch.start()
        self.addCleanup(self.shared_env_patch.stop)
        self.mock_env = mock.Mock(spec=environment.RxEnvironment)
        self.mock_shared_env.return_value = self.mock_env

        self.mock_local_env = mock.Mock()
        self.mock_env.update.return_value = self.mock_local_env
        self.mock_local_env.collect.return_value = ops.map(lambda x: x)
        self.mock_local_env.db = self.mock_db

        # Mock Document
        self.document = mock.Mock(spec=pipelines.docs_model.Document)
        self.document.url = "http://mock-doc-url"

        # Config
        self.config = docs_types.DocsPipelineConfig()

        # Instantiate the Inserter
        self.inserter = pipelines.MarkdownIndexInserter(
            document=self.document,
            config=self.config,
            insert_index=10,
        )

        self.patch_database_t = mock.patch(
            "rxllmproc.app.docs.pipelines.database.t"
        )
        self.mock_database_t = self.patch_database_t.start()
        self.addCleanup(self.patch_database_t.stop)

        # Configure the mock_database_t to return a mock table object
        mock_table_returned_by_t = mock.Mock()
        mock_table_returned_by_t.c.analysis_id = mock.Mock()
        mock_table_returned_by_t.c.action_number = mock.Mock()
        mock_table_returned_by_t.c.placement_container_url = mock.Mock()
        mock_table_returned_by_t.c.placement_id = mock.Mock()
        self.mock_database_t.return_value = mock_table_returned_by_t

        self.sqlalchemy_patch = mock.patch(
            "rxllmproc.app.docs.pipelines.sqlalchemy"
        )
        self.mock_sqlalchemy = self.sqlalchemy_patch.start()
        self.addCleanup(self.sqlalchemy_patch.stop)
        self.mock_sqlalchemy.select.return_value.where.return_value = (
            self.mock_sqlalchemy.select.return_value
        )

        # Patch docs_operators.apply_batch_edits
        self.apply_batch_edits_patch = mock.patch(
            "rxllmproc.app.docs.pipelines.docs_operators.apply_batch_edits"
        )
        self.mock_apply_batch_edits = self.apply_batch_edits_patch.start()
        self.addCleanup(self.apply_batch_edits_patch.stop)

    def test_get_placement_ids(self):
        """Test retrieving placement IDs from the database."""
        ids = self.inserter.get_placement_ids()
        self.assertEqual(ids, {("doc_id_2", 2)})
        self.mock_db.session.execute.assert_called()

    def test_pipeline_append_markdown(self):
        """Test appending markdown content to the document."""
        item = analysis_types.ActionItem(
            analysis_id="doc_id_1",
            action_number=1,
            title="Test Item",
            priority="high",
            notes='some notes',
        )

        captured_edits: list[docs_operators.EditOperation] = []

        def _mock_apply_op(source: rx.Observable[docs_operators.EditOperation]):
            return source.pipe(
                ops.do_action(captured_edits.append),
                ops.map(lambda _: "doc_id_1|1"),
            )

        self.mock_apply_batch_edits.return_value = _mock_apply_op

        result: list[analysis_types.ActionItemPlacement] = []
        rx.just(item).pipe(self.inserter).subscribe(
            on_next=result.append,
            on_error=lambda e: self.fail(f"Pipeline raised an error: {e}"),
        )

        self.mock_apply_batch_edits.assert_called_once_with(self.document)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].placement_container_url, self.document.url)
        self.assertEqual(result[0].placement_id, '(None)')
        self.assertEqual(result[0].analysis_id, "doc_id_1")

        self.assertEqual(len(captured_edits), 1)
        first_edit = captured_edits[0]
        if not isinstance(first_edit, docs_operators.InsertOperation):
            self.fail("First edit should be an InsertOperation")
        self.assertEqual(first_edit.index, 10)

    def test_pipeline_append_markdown_skips_existing(self):
        """Test that existing items are skipped."""
        item = analysis_types.ActionItem(
            analysis_id="doc_id_2",
            action_number=2,
            title="Existing Item",
            priority="low",
            notes='notes',
        )

        self.mock_apply_batch_edits.return_value = ops.map(lambda x: x)

        result: list[analysis_types.ActionItemPlacement] = []
        rx.just(item).pipe(self.inserter).subscribe(
            on_next=result.append, on_error=lambda e: self.fail(f"Error: {e}")
        )
        self.assertEqual(len(result), 0)
