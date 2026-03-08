# pyright: reportPrivateUsage=false
"""Test Docs Processing."""

import unittest
from unittest import mock
from typing import Any, Callable

import reactivex as rx
from reactivex import operators as ops

from rxllmproc.app.docs import processing
from rxllmproc.app.docs import types as docs_types
from rxllmproc.app.analysis import types as analysis_types
from rxllmproc.database import operators as sql_operators
from rxllmproc.app import environment


class TestDocsProcessing(unittest.TestCase):
    """Test the DocsProcessing class."""

    def setUp(self):
        self.mock_env = mock.Mock(spec=environment.RxEnvironment)
        self.mock_db = mock.Mock(spec=sql_operators.RxDatabase)
        self.mock_env.db = self.mock_db

        self.mock_tx = mock.Mock()
        self.mock_db.element_transaction.return_value = self.mock_tx

        # Mock query_op to return an operator that emits a dummy item
        def _query_op(
            *args: Any, **kwargs: Any
        ) -> Callable[
            [rx.Observable[Any]], rx.Observable[analysis_types.ActionItem]
        ]:
            return ops.map(
                lambda _: analysis_types.ActionItem(
                    title="todo", analysis_id="1", action_number=1
                )
            )

        self.mock_tx.query_op.side_effect = _query_op

        self.mock_env.collect.return_value = ops.map(lambda x: x)
        self.mock_env.create_doc_model.return_value = mock.Mock()
        self.mock_env.update.return_value = self.mock_env
        self.mock_env.__enter__ = mock.Mock(return_value=self.mock_env)
        self.mock_env.__exit__ = mock.Mock(return_value=None)
        self.mock_env.error_handler = lambda: None

    def test_execute_pipeline(self):
        """Test that the pipeline is built and executed."""
        with mock.patch(
            "rxllmproc.app.docs.processing.MarkdownIndexInserter"
        ) as mock_inserter_cls, mock.patch(
            "rxllmproc.app.docs.processing.sqlalchemy"
        ) as mock_sqlalchemy:
            mock_sqlalchemy.select.return_value = mock.Mock()

            # Setup the mock inserter instance to behave like an operator
            mock_inserter_instance = mock_inserter_cls.return_value

            # The inserter is used in .pipe(), so it must be callable and return an observable
            def _inserter_side_effect(
                source: rx.Observable[analysis_types.ActionItem],
            ) -> rx.Observable[analysis_types.ActionItemPlacement]:
                return source.pipe(
                    ops.map(
                        lambda x: analysis_types.ActionItemPlacement(
                            analysis_id=x.analysis_id,
                            action_number=x.action_number,
                            placement_container_url="url",
                        )
                    )
                )

            mock_inserter_instance.side_effect = _inserter_side_effect

            config = docs_types.DocsConfig(
                todo_doc_id="doc_id",
                define={"param": "val"},
                interval=0,
            )

            processor = processing.DocsProcessing(
                env=self.mock_env,
                config=config,
            )

            results: list[analysis_types.ActionItemPlacement] = []
            processor._make_pipeline(rx.just("start")).pipe(
                ops.do_action(on_next=results.append)
            ).run()

            # Verify DocsPipeline called with correct args
            mock_inserter_cls.assert_called_once()

            # Verify results were collected
            self.assertEqual(len(results), 1)
            self.assertIsInstance(
                results[0], analysis_types.ActionItemPlacement
            )
            self.assertEqual(results[0].placement_container_url, "url")
