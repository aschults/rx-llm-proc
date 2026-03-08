# pyright: reportPrivateUsage=false, reportUnknownLambdaType=false
"""Test Mail Processing."""

import unittest
from unittest import mock
import reactivex as rx
from reactivex import operators as ops

from rxllmproc.app.mail import pipelines, processing
from rxllmproc.app.mail import types as mail_types
from rxllmproc.app.analysis import types as analysis_types
from rxllmproc.database import operators as sql_operators
from rxllmproc.app import environment as app_environment


class TestMailProcessing(unittest.TestCase):
    """Test the MailProcessing class."""

    def setUp(self):
        self.mock_db = mock.Mock(spec=sql_operators.RxDatabase)
        self.mock_tx = mock.Mock()
        self.mock_db.element_transaction.return_value = self.mock_tx
        # upsert_op returns an operator
        self.mock_tx.upsert_op.return_value = ops.map(lambda s: s)

        self.mock_creds_factory = mock.Mock()
        self.mock_cache = mock.Mock()

        self.mock_pipeline_instance = mock.Mock(spec=pipelines.MailPipeline)
        self.mock_pipeline_instance.load_new_messages.return_value = ops.map(
            lambda _: "dummy"
        )

        self.pipeline_patch = mock.patch(
            "rxllmproc.app.mail.processing.mail_pipelines.MailPipeline"
        )
        self.mock_pipeline_cls = self.pipeline_patch.start()
        self.addCleanup(self.pipeline_patch.stop)

        self.shared_env_patch = mock.patch(
            "rxllmproc.app.mail.processing.app_environment.shared"
        )
        self.mock_shared_env = self.shared_env_patch.start()
        self.addCleanup(self.shared_env_patch.stop)

        self.mock_env_instance = mock.MagicMock(
            spec=app_environment.RxEnvironment
        )
        self.mock_env_instance.update.return_value = self.mock_env_instance
        self.mock_env_instance.__enter__.return_value = self.mock_env_instance
        self.mock_shared_env.return_value = self.mock_env_instance

        self.mock_env_instance.collect.return_value = ops.map(lambda x: x)
        self.mock_env_instance.create_doc_model.return_value = mock.Mock()

        self.mock_pipeline_cls.return_value = self.mock_pipeline_instance

    def test_execute_pipeline(self):
        """Test that the pipeline is built and executed."""
        # Pipeline Mock
        # Create a fake pipeline operator that emits one item
        mock_mail_source = mail_types.MailSource(
            id="id1",
            mail_metadata=mail_types.MailMetadata(
                id="id1", path="path", received_date="2023-01-01"
            ),
            analysis=analysis_types.Analysis(),
        )

        self.mock_pipeline_instance.analyze_email.return_value = ops.map(
            lambda _: mock_mail_source
        )

        config = mail_types.MailConfig(
            gmail_query="query",
            categorization_template="template",
            define={"param": "val"},
            force_all=True,
            interval=0,
        )
        processor = processing.MailProcessing(
            db=self.mock_db,
            env=self.mock_env_instance,
            config=config,
        )

        pipeline = processor._make_pipeline(rx.just("start"))
        results: list[mail_types.MailSource] = []
        pipeline.subscribe(results.append)

        # Verify MailPipeline called with correct args
        self.mock_pipeline_cls.assert_called_once()
        _, kwargs = self.mock_pipeline_cls.call_args
        self.assertEqual(kwargs["config"], config)

        # Verify results were collected
        self.assertEqual(self.mock_tx.upsert_op.call_count, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], mock_mail_source)

    def test_execute_pipeline_error(self):
        """Test that pipeline errors are handled."""
        # Simulate an error in the pipeline
        self.mock_pipeline_instance.load_new_messages.return_value = (
            lambda s: rx.throw(Exception("Pipeline failed"))
        )
        self.mock_pipeline_instance.analyze_email.return_value = lambda s: s

        errors: list[Exception] = []

        self.mock_env_instance.error_handler = errors.append

        config = mail_types.MailConfig(
            gmail_query="query",
            categorization_template="template",
            define={"param": "val"},
            force_all=True,
            interval=0,
        )
        processor = processing.MailProcessing(
            db=self.mock_db,
            env=self.mock_env_instance,
            config=config,
        )

        with self.assertRaises(Exception) as cm:
            processor._make_pipeline(rx.just("start")).run()

        self.assertEqual(str(cm.exception), "Pipeline failed")
        # Verify error was caught by on_error handler
        self.assertEqual(len(errors), 1)
        self.assertEqual(str(errors[0]), "Pipeline failed")

    def test_start_pipeline_interval_zero(self):
        """Test start_pipeline with interval 0."""
        config = mail_types.MailConfig(
            gmail_query="query",
            categorization_template="template",
            define={"param": "val"},
            force_all=True,
            interval=0,
        )
        processor = processing.MailProcessing(
            db=self.mock_db,
            env=self.mock_env_instance,
            config=config,
        )

        with mock.patch.object(processor, "load_emails") as mock_load:
            processor.start_pipeline()
            processor.join_pipeline()
            mock_load.assert_called_once()

    def test_start_pipeline_interval_positive(self):
        """Test start_pipeline with interval > 0."""

        self.mock_pipeline_instance.analyze_email.return_value = ops.map(
            lambda _: "blah"
        )

        self.mock_pipeline_instance.load_new_messages.side_effect = [
            ops.map(lambda x: x),
            TimeoutError('breaking loop'),
        ]
        config = mail_types.MailConfig(
            gmail_query="query",
            categorization_template="template",
            define={"param": "val"},
            force_all=True,
            interval=0.1,
        )
        processor = processing.MailProcessing(
            db=self.mock_db,
            env=self.mock_env_instance,
            config=config,
            pipeline_instance=self.mock_pipeline_instance,
        )

        processor.start_pipeline()
        processor.join_pipeline()

        self.mock_pipeline_instance.load_new_messages.assert_called()
        self.mock_pipeline_instance.analyze_email.assert_called()
        self.mock_tx.upsert_op.assert_called_once()
