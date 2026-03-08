# pyright: basic
# pyright: reportUnknownLambdaType=false
"""Test Mail Pipeline."""

import unittest
from unittest import mock
import reactivex as rx
from reactivex import scheduler, operators as ops

from rxllmproc.app.mail import pipelines, types
from rxllmproc.app.analysis import types as analysis_types
from rxllmproc.app import environment as app_environment
from rxllmproc.database import operators as sql_operators


class TestMailPipeline(unittest.TestCase):
    """Test the mail processing pipeline."""

    def setUp(self):

        self.mock_db = mock.Mock(spec=sql_operators.RxDatabase)
        self.mock_db.session = mock.Mock()
        self.mock_db.session.execute.return_value.scalars.return_value.all.return_value = [
            "id2"
        ]

        sqlalchemy_patch = mock.patch("rxllmproc.app.mail.pipelines.sqlalchemy")
        self.mock_sqlalchemy = sqlalchemy_patch.start()
        self.addCleanup(sqlalchemy_patch.stop)

        gmail_patch = mock.patch("rxllmproc.app.mail.pipelines.gmail_operators")
        self.mock_gmail = gmail_patch.start()
        self.addCleanup(gmail_patch.stop)

        fetch_return_values = [mock.Mock(id="id1"), mock.Mock(id="id2")]

        self.mock_gmail.fetch_ids.return_value = ops.flat_map(
            lambda x: rx.from_iterable(fetch_return_values)
        )

        download_return_values: dict[str, types.gmail_types.Message] = {
            "id1": mock.Mock(id="msg1", spec=types.gmail_types.Message),
            "id2": mock.Mock(id="msg2", spec=types.gmail_types.Message),
        }

        def _get_download_message(
            msg: types.gmail_types.Message,
        ) -> types.gmail_types.Message:
            if not msg.id:
                raise ValueError("Message must have an id")
            if msg.id not in download_return_values:
                raise ValueError(f"No download return value for id {msg.id}")
            return download_return_values[msg.id]

        self.mock_gmail.download_message.return_value = ops.map(
            _get_download_message
        )

        self.upsert_args = []

        # Mock DB Transaction and Upsert
        self.mock_tx = mock.Mock()
        self.mock_db.element_transaction.return_value = self.mock_tx
        self.mock_tx.upsert_op.return_value = ops.map(
            lambda s: self.upsert_args.append(s) or s
        )

        self.shared_env_patch = mock.patch(
            "rxllmproc.app.mail.pipelines.app_environment.environment.shared"
        )
        self.mock_shared_env = self.shared_env_patch.start()
        self.addCleanup(self.shared_env_patch.stop)

        self.mock_env = mock.Mock(spec=app_environment.RxEnvironment)
        self.mock_shared_env.return_value = self.mock_env
        self.mock_env.template_globals = {}
        self.mock_env.template_filters = {}

        self.mock_env.update.return_value = self.mock_env

        self.mock_env.collect.return_value = ops.map(lambda s: s)
        self.errors = []
        self.mock_env.error_handler = self.errors.append

    def test_pipeline_load_messages(self):
        """Test loading new messages."""
        # Build pipeline
        config = types.MailPipelineConfig(
            gmail_query="query",
            categorization_template="template",
        )
        pipeline_inst = pipelines.MailPipeline(
            config=config,
            db=self.mock_db,
            scheduler=scheduler.ImmediateScheduler(),
        )

        with mock.patch.object(
            pipeline_inst, "get_gmail_ids", return_value={"id2"}
        ):
            # Run pipeline
            result = []
            rx.of("start").pipe(pipeline_inst.load_new_messages()).subscribe(
                result.append
            )

        if self.errors:
            raise self.errors[0]

        # Verify
        # Should only process id1 because id2 is in DB
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "msg1")

    def test_pipeline_analyze_email(self):
        """Test analyzing an email."""
        with mock.patch(
            "rxllmproc.app.mail.pipelines.llm_operators"
        ) as mock_llm, mock.patch(
            "rxllmproc.text_processing.operators.TemplateBuilder"
        ) as mock_template_builder_cls, mock.patch(
            "rxllmproc.app.mail.types.MailMetadata.from_msg"
        ) as mock_from_msg:

            # Mock Metadata creation
            mock_metadata = types.MailMetadata(
                id="id1", path="path", received_date="2023-01-01"
            )
            mock_from_msg.return_value = mock_metadata

            # Mock Template
            mock_template_builder_cls.return_value.create.return_value = (
                lambda s: rx.from_iterable(["prompt"])
            )

            # Mock LLM
            analysis = analysis_types.Analysis(category="cat")
            mock_llm.generate_object.return_value = lambda s: rx.from_iterable(
                [analysis]
            )

            # Build pipeline
            config = types.MailPipelineConfig(
                gmail_query="query",
                categorization_template="template",
            )
            self.mock_env.model_name = "model"
            pipeline_inst = pipelines.MailPipeline(
                config=config,
                db=self.mock_db,
                scheduler=scheduler.ImmediateScheduler(),
            )

            # Run pipeline
            result = []
            msg_mock = mock.Mock()
            rx.just(msg_mock).pipe(pipeline_inst.analyze_email()).subscribe(
                result.append
            )

            if self.errors:
                raise self.errors[0]

            # Verify
            self.assertEqual(len(result), 1)
            self.assertIsInstance(result[0], types.MailSource)
            self.assertEqual(result[0].analysis, analysis)
            self.assertEqual(
                result[0].id, "https://mail.google.com/mail/u/0/#inbox/id1"
            )

    def test_pipeline_force_all(self):
        """Test that the pipeline processes all emails when force_all is True."""
        # Build pipeline
        config = types.MailPipelineConfig(
            gmail_query="query",
            categorization_template="template",
            force_all=True,
        )
        pipeline_inst = pipelines.MailPipeline(
            config=config,
            db=self.mock_db,
            scheduler=scheduler.ImmediateScheduler(),
        )

        # Run pipeline - only load_new_messages
        result = []
        rx.of("start").pipe(pipeline_inst.load_new_messages()).subscribe(
            result.append
        )

        if self.errors:
            raise self.errors[0]

        # Verify
        # Should process both id1 and id2 because force_all is True
        self.assertEqual(len(result), 2)

    def test_pipeline_template_params(self):
        """Test that template parameters are passed to the template builder."""
        with mock.patch(
            "rxllmproc.app.mail.pipelines.app_environment"
        ), mock.patch(
            "rxllmproc.app.mail.pipelines.gmail_operators"
        ), mock.patch(
            "rxllmproc.app.mail.pipelines.llm_operators"
        ) as mock_llm, mock.patch(
            "rxllmproc.app.mail.pipelines.template_operators"
        ) as mock_tmpl, mock.patch(
            "rxllmproc.app.mail.types.MailMetadata.from_msg"
        ) as mock_from_msg:

            # Mock Template Builder
            mock_builder = mock_tmpl.TemplateBuilder.return_value
            mock_builder.add_globals.return_value = mock_builder
            mock_builder.create.return_value = lambda s: rx.from_iterable(
                ["prompt"]
            )

            mock_llm.generate_object.return_value = lambda s: rx.from_iterable(
                [analysis_types.Analysis(category="cat")]
            )
            mock_from_msg.return_value = types.MailMetadata(
                id="id", path="p", received_date="d"
            )

            params = {"foo": "bar"}
            config = types.MailPipelineConfig(
                gmail_query="query",
                categorization_template="template",
                define=params,
            )
            self.mock_env.model_name = "model"
            pipeline_inst = pipelines.MailPipeline(
                config=config,
                db=self.mock_db,
                scheduler=scheduler.ImmediateScheduler(),
            )

            # Run pipeline
            rx.just(mock.Mock()).pipe(pipeline_inst.analyze_email()).subscribe()

            # Verify add_globals called with params
            mock_builder.add_globals.assert_called_with(**params)

    def test_pipeline_analyze_email_error(self):
        """Test error handling in analyze_email."""
        with mock.patch(
            "rxllmproc.app.mail.pipelines.llm_operators"
        ) as mock_llm, mock.patch(
            "rxllmproc.text_processing.operators"
        ) as mock_tmpl, mock.patch(
            "rxllmproc.app.mail.types.MailMetadata.from_msg"
        ) as mock_from_msg:

            # Mock Metadata creation
            mock_from_msg.return_value = types.MailMetadata(
                id="id1", path="path", received_date="2023-01-01"
            )

            # Mock Template
            mock_tmpl.TemplateBuilder.return_value.create.return_value = (
                lambda s: rx.from_iterable(["prompt"])
            )

            # Mock LLM to raise error
            mock_llm.generate_object.return_value = lambda s: rx.throw(
                Exception("LLM Error")
            )

            # Build pipeline
            config = types.MailPipelineConfig(
                gmail_query="query",
                categorization_template="template",
            )
            self.mock_env.model_name = "model"
            pipeline_inst = pipelines.MailPipeline(
                config=config,
                db=self.mock_db,
                scheduler=scheduler.ImmediateScheduler(),
            )

            # Run pipeline
            rx.just(mock.Mock()).pipe(pipeline_inst.analyze_email()).subscribe()

            # Verify error was caught
            self.assertEqual(len(self.errors), 1)
            self.assertEqual(str(self.errors[0]), "LLM Error")
