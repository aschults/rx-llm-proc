"""Docs processing logic."""

import logging
import threading

import reactivex as rx
from reactivex import operators as ops
from reactivex.internal import exceptions as rx_exc
import sqlalchemy

from rxllmproc.app import environment as app_environment
from rxllmproc.app.docs import types as docs_types
from rxllmproc.app.docs.pipelines import (
    MarkdownIndexInserter,
    MarkdownLlmInserter,
)
from rxllmproc.app.analysis import types as analysis_types


class DocsProcessing:
    """Docs processing class."""

    def __init__(
        self,
        env: app_environment.RxEnvironment,
        config: docs_types.DocsConfig,
    ):
        """Initialize the docs processing."""
        self.env = env
        self.config = config
        self.pipeline_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        if not self.config.todo_doc_id:
            raise ValueError("Doc ID not set")
        self.doc_model = env.create_doc_model(self.config.todo_doc_id)
        with self.env:

            if config.insertion_instructions:
                logging.info('Using LLM inserter for docs.')
                self.inserter = MarkdownLlmInserter(
                    document=self.doc_model,
                    config=self.config,
                )
            else:
                logging.info(
                    'Using index inserter for docs. (No instructions provided)'
                )
                # If we don't provide instructions, just add at the end.
                self.inserter = MarkdownIndexInserter(
                    self.doc_model,
                    self.config,
                    self.doc_model.get_end(),
                )

    def start_pipeline(self):
        """Execute the docs pipeline."""
        self._stop_event.clear()

        def _run():
            while not self._stop_event.is_set():
                self.append_todos()
                if self._stop_event.wait(self.config.interval):
                    break

        if self.config.interval == 0:
            self.append_todos()
        else:
            self.pipeline_thread = threading.Thread(target=_run)
            self.pipeline_thread.start()

    def join_pipeline(self):
        """Join the pipeline thread."""
        if self.pipeline_thread:
            self.pipeline_thread.join()

    def stop_pipeline(self, safe: bool = True):
        """Stop the pipeline execution."""
        self._stop_event.set()

    def _make_pipeline(
        self, source: rx.Observable[str]
    ) -> rx.Observable[analysis_types.ActionItemPlacement]:
        return source.pipe(
            self.env.db.element_transaction().query_op(
                sqlalchemy.select(analysis_types.ActionItem),
                analysis_types.ActionItem,
            ),
            self.env.collect("docs_inserter / fetched all action items"),
            self.inserter,
            ops.do_action(on_error=self.env.error_handler),
        )

    def append_todos(self):
        """Execute the docs pipeline."""
        with self.env:
            pipeline = self._make_pipeline(rx.just("start"))

            try:
                pipeline.run()
            except rx_exc.SequenceContainsNoElementsError:
                logging.info("No todos to be processed.")
