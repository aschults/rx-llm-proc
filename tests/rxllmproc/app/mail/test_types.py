# pyright: basic
"""Test Mail Types."""

import unittest
from email import message

import reactivex as rx
from reactivex import operators as ops
import sqlalchemy
import sqlalchemy.orm

from rxllmproc.app.mail import types
from rxllmproc.app.analysis import types as analysis_types
from rxllmproc.gmail import types as gmail_types
from rxllmproc.database import operators as sql_operators

REF_DATE_STR = "Tue, 15 Feb 2024 10:00:00 +0100"
REF_DATE_ISO = "2024-02-15T09:00:00Z"


class TestMailMetadata(unittest.TestCase):
    """Test MailMetadata."""

    def _create_mock_message(
        self, msg_id: str, subject: str, email_date: str | None = None
    ) -> gmail_types.Message:
        """Helper to create a mock gmail_types.Message."""
        email_msg = message.EmailMessage()
        email_msg["Subject"] = subject
        email_msg["From"] = "sender@example.com"
        email_msg["To"] = "receiver@example.com"
        email_msg["Cc"] = "cc@example.com"
        email_msg["Bcc"] = "bcc@example.com"
        email_msg["Date"] = email_date or REF_DATE_STR

        msg = gmail_types.Message(id=msg_id, snippet="a snippet")
        # We assign the email message to the underlying variable to be initialize.
        msg._parsed_msg = email_msg  # pylint: disable=protected-access

        return msg

    def test_from_msg(self):
        """Test the MailMetadata.from_msg class method directly."""
        mock_msg = self._create_mock_message("test_id", "My Subject")

        entry = types.MailMetadata.from_msg(mock_msg)

        self.assertEqual(entry.id, "test_id")
        self.assertEqual(entry.subject, "My Subject")
        self.assertEqual(entry.senders, "sender@example.com")
        self.assertEqual(entry.recipients, "receiver@example.com")
        self.assertEqual(entry.cc, "cc@example.com")
        self.assertEqual(entry.bcc, "bcc@example.com")
        self.assertEqual(entry.snippet, "a snippet")
        self.assertEqual(entry.received_date, REF_DATE_ISO)
        self.assertEqual(entry.path, "test_id.msg")
        self.assertIn("test_id", entry.url)


class TestMailSource(unittest.TestCase):
    """Test the MailSource and related types."""

    def setUp(self) -> None:
        sqlalchemy.orm.clear_mappers()
        self.db = sql_operators.RxDatabase(
            'sqlite:///:memory:',
            engine_args={'echo': True},
            entities=[
                types.MailMetadata,
                analysis_types.Source,
                types.MailSource,
                analysis_types.ActionItem,
                analysis_types.Analysis,
                gmail_types.Message,
            ],
        )
        self.addCleanup(self.db.close)
        self.addCleanup(sqlalchemy.orm.clear_mappers)

        return super().setUp()

    def test_db_storage(self):
        self.maxDiff = None

        analysis = analysis_types.Analysis(
            id='mdid',
            category='category',
            noteworthy_details=['detail'],
            action_items=[analysis_types.ActionItem(title='title')],
            people=[analysis_types.Person(name='name', role='role')],
            identifiers=[analysis_types.Identifier(name='name', value='value')],
        )

        mail_metadata = types.MailMetadata(
            id='gmid',
            path='path',
            received_date='2023-01-01',
            subject='subject',
            snippet='snippet',
        )

        mail_source = types.MailSource(
            id='mdid',
            mail_metadata=mail_metadata,
            analysis=analysis,
        )

        rx.just(mail_source).subscribe(
            self.db.element_transaction().insert_sink(types.MailSource)
        )

        mail_metadata2 = types.MailMetadata(
            id='gmid',
            path='pathx',
            received_date='2023-01-01',
            subject='subject',
            snippet='snippet',
        )

        mail_source2 = types.MailSource(
            id='mdid',
            mail_metadata=mail_metadata2,
            analysis=analysis,
        )

        rx.just(mail_source2).subscribe(
            self.db.element_transaction().upsert_sink(types.MailSource)
        )

        result = []
        self.db.element_transaction().query_src(
            sqlalchemy.select(types.MailSource),
            types.MailSource,
        ).pipe(ops.do_action(on_next=lambda x: result.append(x))).run()
        self.assertEqual(result[0].analysis, analysis)
        self.assertEqual(result[0].mail_metadata.path, 'pathx')


class TestMailConfig(unittest.TestCase):
    """Test MailConfig."""

    def test_template_parameters(self):
        """Test template parameters property."""
        config = types.MailConfig(
            define={"key": "value"},
            categories_instructions="cat_instr",
            action_items_instructions="act_instr",
            context_instructions="ctx_instr",
        )
        params = config.template_parameters
        self.assertEqual(params["key"], "value")
        self.assertEqual(params["categories_instructions"], "cat_instr")
        self.assertEqual(params["action_items_instructions"], "act_instr")
        self.assertEqual(params["context_instructions"], "ctx_instr")

    def test_template_parameters_defaults(self):
        """Test template parameters with defaults."""
        config = types.MailConfig()
        params = config.template_parameters
        self.assertEqual(params, {})
