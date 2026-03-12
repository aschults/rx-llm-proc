"""Provides a class for processing emails using a reactive pipeline."""

import logging
import threading

import reactivex as rx
from reactivex import operators as ops
from reactivex.internal import exceptions as rx_exc
from reactivex import scheduler

from rxllmproc.app import environment as app_environment
from rxllmproc.database import operators as sql_operators
from rxllmproc.app.mail import types as mail_types
from rxllmproc.app.mail import pipelines as mail_pipelines


class MailProcessing:
    """Manages the processing of emails through a reactive pipeline.

    This class sets up and runs a pipeline for fetching emails from a source,
    analyzing them using an LLM, and storing the results in a database.
    It can be run once or periodically in a separate thread.

    Attributes:
        model: The name of the LLM to use for analysis.
        db: An instance of RxDatabase for database operations.
        env: An Environment object for managing execution context.
        config: A ProcessingConfig object with configuration for the pipeline.
        execution_config: An ExecutionConfig object with execution parameters.
        results: A list to store the results of the pipeline execution.
        pipeline_thread: The thread running the pipeline.
        pipeline_instance: An instance of MailPipeline used for processing.
    """

    def __init__(
        self,
        config: mail_types.MailConfig,
        pipeline_instance: mail_pipelines.MailPipeline | None = None,
        env: app_environment.RxEnvironment | None = None,
        db: sql_operators.RxDatabase | None = None,
    ):
        """Initializes the MailProcessing class.

        Args:
            model: The name of the LLM to use for analysis.
            db: An instance of RxDatabase for database operations.
            env: An Environment object for managing execution context.
            config: A ProcessingConfig object with configuration for the pipeline.
            execution_config: An ExecutionConfig object with execution parameters.
            pipeline_instance: An optional instance of MailPipeline. If not
                provided, a new one is created.
        """
        self.env = env or app_environment.shared().update()
        self.db = db or self.env.db
        self.config = config
        self.pipeline_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._scheduler = scheduler.ThreadPoolScheduler(5)

        if not self.config.gmail_query:
            raise ValueError("Query must be provided in the configuration.")
        with self.env:
            self.pipeline_instance = (
                pipeline_instance
                or mail_pipelines.MailPipeline(
                    env=self.env,
                    config=self.config,
                    scheduler=self._scheduler,
                )
            )

    def start_pipeline(self):
        """Starts the email processing pipeline in a separate thread.

        The pipeline can be configured to run once or at a specified interval.
        """
        self._stop_event.clear()

        def _run():
            try:
                if self.config.interval == 0:
                    self.load_emails()
                else:
                    while not self._stop_event.is_set():
                        self.load_emails()
                        if self._stop_event.wait(self.config.interval):
                            break
            except Exception as e:
                logging.error("Error in pipeline execution", exc_info=e)
                self.env.error_handler(e)

        self.pipeline_thread = threading.Thread(target=_run)
        self.pipeline_thread.start()

    def join_pipeline(self):
        """Waits for the pipeline thread to complete."""
        if self.pipeline_thread:
            self.pipeline_thread.join()

    def stop_pipeline(self, safe: bool = True):
        """Stops the pipeline execution.

        Args:
            safe: If True, waits for the current tasks to complete before
                shutting down. Otherwise, it cancels them.
        """
        self._stop_event.set()
        if safe:
            self._scheduler.executor.shutdown(wait=True)
        else:
            self._scheduler.executor.shutdown(wait=False, cancel_futures=True)

    def _make_pipeline(
        self, source: rx.Observable[str]
    ) -> rx.Observable[mail_types.MailSource]:
        """Creates the reactive pipeline for email processing."""
        with self.env as env:
            return source.pipe(
                self.pipeline_instance.load_new_messages(),
                self.pipeline_instance.analyze_email(),
                self.db.element_transaction().upsert_op(mail_types.MailSource),
                env.collect("mail_loading / upserted analysis"),
                ops.do_action(on_error=self.env.error_handler),
            )

    def load_emails(self):
        """Executes one run of the mail processing pipeline.

        This method sets up the reactive pipeline with all the necessary
        operators to load new messages, analyze them, and store the results.
        It handles errors and ensures that the pipeline runs within the correct
        environment.

        Raises:
            ValueError: If the database is not initialized or the query is not set.
        """
        if not self.db:
            raise ValueError("Database not initialized.")
        if not self.config.gmail_query:
            raise ValueError("Query not set.")

        pipeline = self._make_pipeline(rx.just("start"))

        try:
            pipeline.run()
        except rx_exc.SequenceContainsNoElementsError:
            logging.info("No emails to be processed.")
