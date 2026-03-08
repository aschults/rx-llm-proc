# pyright: basic
"""Test GMail CLI class."""

import json
from unittest import mock
from email import message

from pyfakefs import fake_filesystem_unittest

from rxllmproc.gmail import api as gmail_wrapper
from rxllmproc.core import auth
from rxllmproc.gmail.types import Message
from rxllmproc.cli import gmail_cli

from test_support import fail_none

INDEX_CONTENT_THE_ID = [
    {
        "id": "the_id",
        "subject": "old subject",
        "path": "the_id.msg",
        "received_date": "2023-01-01T00:00:00Z",
    }
]


class TestGmailCli(fake_filesystem_unittest.TestCase):
    """Test the Gmail CLI class."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

        self.creds = mock.Mock(spec=auth.CredentialsFactory)
        self.wrap = mock.Mock(gmail_wrapper.GMailWrap)
        self.instance = gmail_cli.GmailCli(
            creds=self.creds, gmail_wrap=self.wrap
        )

    def _create_message(
        self,
        msg_id: str = "the_id",
        subject: str = "Test Subject",
        sender: str = "sender@example.com",
        recipient: str = "recipient@example.com",
        date: str = "Tue, 15 Feb 2024 10:00:00 +0100",
        snippet: str = "snippet",
        thread_id: str | None = None,
    ) -> Message:
        msg = message.EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        msg["Date"] = date

        gmail_msg = Message(id=msg_id, snippet=snippet, threadId=thread_id)
        gmail_msg._parsed_msg = msg
        return gmail_msg

    def test_write_path(self):
        """Test a writing to different output_dir."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        self.wrap.get.return_value = self._create_message(
            "the_id", sender="some_sender"
        )
        self.fs.create_dir("/thedir")

        self.instance.main(["get_all", "--output_dir=/thedir", "the_query"])

        self.wrap.search.assert_called_with("the_query")
        self.wrap.get.assert_called_with("the_id")
        msg_file = self.fs.get_object("/thedir/the_id.msg")
        self.assertIsNotNone(msg_file)
        self.assertIn("some_sender", msg_file.contents or "")

    def test_write(self):
        """Test a simple fetch and write."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        self.wrap.get.return_value = self._create_message(
            "the_id", sender="some_sender"
        )

        self.instance.main(["get_all", "--output_dir=.", "the_query"])

        self.wrap.search.assert_called_with("the_query")
        self.wrap.get.assert_called_with("the_id")
        msg_file = self.fs.get_object("the_id.msg")
        self.assertIsNotNone(msg_file)
        self.assertIn("some_sender", msg_file.contents or "")

    def test_no_rewrite(self):
        """Ensure that existing files are not overwritten."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        self.wrap.get.return_value = self._create_message(
            "the_id", sender="some_sender"
        )

        self.fs.create_file("the_id.msg", contents="whatever")
        self.instance.main(["get_all", "--output_dir=.", "the_query"])

        self.wrap.search.assert_called_with("the_query")
        self.wrap.get.assert_not_called()
        msg_file = self.fs.get_object("the_id.msg")
        self.assertIsNotNone(msg_file)
        self.assertIn("whatever", msg_file.contents or "")

    def test_force_rewrite(self):
        """Ensure that existing files are not overwritten."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        self.wrap.get.return_value = self._create_message(
            "the_id", sender="some_sender"
        )

        self.fs.create_file("the_id.msg", contents="whatever")
        self.instance.main(
            ["get_all", "--output_dir=.", "--force", "the_query"]
        )

        self.wrap.search.assert_called_with("the_query")
        self.wrap.get.assert_called_with("the_id")
        msg_file = self.fs.get_object("the_id.msg")
        self.assertIsNotNone(msg_file)
        self.assertIn("some_sender", msg_file.contents or "")

    def test_no_rewrite_with_index_and_file(self):
        """Ensure that existing and indexed files are not overwritten."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        # The index already contains the message ID
        self.fs.create_file(
            "index.json",
            contents=json.dumps(INDEX_CONTENT_THE_ID),
        )
        self.fs.create_file("the_id.msg", contents="whatever")

        self.instance.main(
            ["get_all", "--output_dir=.", "--with_index", "the_query"]
        )

        self.wrap.search.assert_called_with("the_query")
        self.wrap.get.assert_not_called()

        # Check that the file and index were not modified
        msg_file = self.fs.get_object("the_id.msg")
        self.assertIn("whatever", msg_file.contents or "")
        index_file = fail_none(self.fs.get_object("index.json"))
        index_content = json.loads(fail_none(index_file.contents))
        self.assertEqual(index_content[0]["subject"], "old subject")

    def test_rewrite_with_index_but_no_file(self):
        """Ensure that if the file is missing, it's re-downloaded even if indexed."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        self.wrap.get.return_value = self._create_message(
            "the_id",
            subject="new subject",
            sender="some_sender",
            snippet="a snippet",
        )

        # The index exists, but the message file does not
        self.fs.create_file(
            "index.json",
            contents=json.dumps(INDEX_CONTENT_THE_ID),
        )

        self.instance.main(
            ["get_all", "--output_dir=.", "--with_index", "the_query"]
        )

        self.wrap.get.assert_called_with("the_id")

        # Check that the file was created and the index was updated
        msg_file = self.fs.get_object("the_id.msg")
        self.assertIn("new subject", msg_file.contents or "")
        index_file = fail_none(self.fs.get_object("index.json"))
        index_content = json.loads(fail_none(index_file.contents))
        self.assertEqual(index_content[0]["subject"], "new subject")

    def test_rewrite_with_file_but_no_index(self):
        """Ensure that if the file exists but is not indexed, it's re-downloaded."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        self.wrap.get.return_value = self._create_message(
            "the_id",
            subject="new subject",
            sender="some_sender",
            snippet="a snippet",
        )

        self.fs.create_file("the_id.msg", contents="old content")

        self.instance.main(
            ["get_all", "--output_dir=.", "--with_index", "the_query"]
        )

        self.wrap.get.assert_called_with("the_id")
        msg_file = self.fs.get_object("the_id.msg")
        self.assertIn("new subject", msg_file.contents or "")

    def test_saves_meta_json(self):
        """Test that a .meta.json file is created with headers."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        self.wrap.get.return_value = self._create_message(
            "the_id",
            subject="Test Subject",
            sender="sender@example.com",
            recipient="recipient@example.com",
            date="Thu, 15 Feb 2024 10:00:00 +0100",
            snippet="snippet",
        )

        self.instance.main(["get_all", "--output_dir=.", "the_query"])

        self.wrap.search.assert_called_with("the_query")
        self.wrap.get.assert_called_with("the_id")

        # Check that the metadata file was written
        meta_file = fail_none(self.fs.get_object("the_id.meta.json"))
        self.assertIsNotNone(meta_file)
        meta_content = json.loads(fail_none(meta_file.contents))
        self.assertEqual(
            meta_content["headers"],
            [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Thu, 15 Feb 2024 10:00:00 +0100"},
            ],
        )
        self.assertIn("api_response", meta_content)
        self.assertEqual(meta_content["api_response"]['id'], "the_id")
        self.assertEqual(meta_content["api_response"]['snippet'], "snippet")

    @mock.patch("rxllmproc.cli.gmail_cli.email_processing")
    def test_to_markdown(self, mock_email_processing: mock.Mock):
        """Test that --to_markdown flag saves a .md file."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        gmail_msg = self._create_message("the_id", subject="Test Subject")
        self.wrap.get.return_value = gmail_msg

        mock_email_processing.get_email_content.return_value = (
            "# Test Subject\n\nBody"
        )

        self.instance.main(
            ["get_all", "--output_dir=.", "--to_markdown", "the_query"]
        )

        self.wrap.search.assert_called_with("the_query")
        self.wrap.get.assert_called_with("the_id")

        # Check that email processing was called for markdown
        mock_email_processing.get_email_content.assert_called_once_with(
            gmail_msg.parsed_msg, output="md"
        )

        # Check that the markdown file was written
        md_file = self.fs.get_object("the_id.md")
        self.assertIsNotNone(md_file)
        self.assertEqual(md_file.contents, "# Test Subject\n\nBody")

        # Check that the raw message file was NOT written
        self.assertFalse(self.fs.exists("the_id.msg"))

    def test_dry_run(self):
        """Ensure that existing files are not overwritten."""
        id_mock = mock.Mock()
        id_mock.id = "the_id"
        self.wrap.search.return_value = [id_mock]

        self.wrap.get.return_value = self._create_message(
            "the_id", sender="some_sender"
        )

        self.instance.main(
            ["get_all", "--output_dir=.", "--dry_run", "the_query"]
        )

        self.wrap.search.assert_called_with("the_query")
        self.wrap.get.assert_not_called()
        self.assertFalse(self.fs.exists("the_id.msg"))

    @mock.patch("rxllmproc.cli.cli_base.sys.exit")
    def test_fail_bad_command(self, exit_mock: mock.Mock):
        """Ensure that unknown commands fail."""
        self.instance.main(["some_command"])
        exit_mock.assert_called_with(2)

    @mock.patch("rxllmproc.cli.cli_base.sys.exit")
    def test_fail_no_output(self, exit_mock: mock.Mock):
        """Ensure that missing output dir fails."""
        self.instance.main(["get_all"])
        exit_mock.assert_called_with(2)

    @mock.patch("rxllmproc.cli.cli_base.sys.exit")
    def test_fail_no_prompt(self, exit_mock: mock.Mock):
        """Ensure that missing prompt fails."""
        self.instance.main(["get_all", "--output_dir=."])
        exit_mock.assert_called_with(2)

    def test_threaded_storage(self):
        """Test storing messages in thread directories."""
        id_mock = mock.Mock()
        id_mock.id = "msg_id_1"
        id_mock.threadId = "thread_id_A"
        self.wrap.search.return_value = [id_mock]

        self.wrap.get.return_value = self._create_message(
            "msg_id_1",
            subject="Threaded Subject",
            sender="sender@example.com",
            date="Wed, 16 Feb 2024 10:00:00 +0100",
            snippet="snippet",
            thread_id="thread_id_A",
        )

        self.instance.main(
            [
                "get_all",
                "--output_dir=.",
                "--by_thread",
                "--with_index",
                "the_query",
            ]
        )

        self.wrap.search.assert_called_with("the_query")
        self.wrap.get.assert_called_with("msg_id_1")

        # Check file existence in thread directory
        expected_path = "thread_id_A/msg_id_1.msg"
        msg_file = self.fs.get_object(expected_path)
        self.assertIsNotNone(msg_file)
        self.assertIn("Threaded Subject", msg_file.contents or "")

        # Check index entry path
        index_file = fail_none(self.fs.get_object("index.json"))
        index_content = json.loads(fail_none(index_file.contents))
        self.assertEqual(len(index_content), 1)
        self.assertEqual(index_content[0]["id"], "msg_id_1")
        self.assertEqual(index_content[0]["path"], expected_path)
