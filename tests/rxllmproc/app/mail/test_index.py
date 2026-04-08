# pyright: basic
"""Test the GMail Index Manager class."""

import json
from email import message
from pyfakefs import fake_filesystem_unittest

import test_support

from rxllmproc.app.mail import index
from rxllmproc.gmail import types as gmail_types

# A reference date for mocking
REF_DATE_STR = "Tue, 15 Feb 2024 10:00:00 +0100"
REF_DATE_ISO = "2024-02-15T09:00:00Z"


class TestGmailIndexManager(fake_filesystem_unittest.TestCase):
    """Test the GmailIndexManager class."""

    def setUp(self):
        """Set up the fake filesystem."""
        self.setUpPyfakefs()

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

    def test_init_no_index_file(self):
        """Test initialization when no index.json file exists."""
        manager = index.GmailIndexManager("/test_dir")
        self.assertEqual(manager.email_index, {})

    def test_init_with_existing_index(self):
        """Test initialization with a valid, existing index.json file."""
        self.fs.create_dir("/test_dir")
        index_content = [
            {
                "id": "123",
                "path": "123.msg",
                "subject": "Test Subject",
                "received_date": REF_DATE_ISO,
                "snippet": "snippet",
                "senders": "sender",
                "recipients": "recipient",
                "cc": "cc",
                "bcc": "bcc",
                "url": "url",
            }
        ]
        self.fs.create_file(
            "/test_dir/index.json", contents=json.dumps(index_content)
        )

        manager = index.GmailIndexManager("/test_dir")
        self.assertIn("123", manager.email_index)
        self.assertEqual(manager.email_index["123"].subject, "Test Subject")

    def test_init_with_corrupt_index(self):
        """Test initialization with a corrupt index.json file."""
        self.fs.create_dir("/test_dir")
        self.fs.create_file("/test_dir/index.json", contents="not a valid json")

        with self.assertRaises(Exception):
            index.GmailIndexManager("/test_dir")

    def test_add_and_save_index(self):
        """Test adding a message and saving the index."""
        self.fs.create_dir("/test_dir")
        manager = index.GmailIndexManager("/test_dir")

        mock_msg = self._create_mock_message("msg1", "New Email")
        manager.add(mock_msg)

        self.assertIn("msg1", manager.email_index)
        self.assertEqual(manager.email_index["msg1"].subject, "New Email")

        manager.save_index()

        self.assertTrue(self.fs.exists("/test_dir/index.json"))
        index_file = test_support.fail_none(
            self.fs.get_object("/test_dir/index.json")
        )
        saved_data = json.loads(test_support.fail_none(index_file.contents))

        self.assertEqual(len(saved_data), 1)
        self.assertEqual(saved_data[0]["id"], "msg1")
        self.assertEqual(saved_data[0]["subject"], "New Email")
        self.assertEqual(saved_data[0]["received_date"], REF_DATE_ISO)

    def test_add_no_id(self):
        """Test that adding a message with no ID raises an error."""
        manager = index.GmailIndexManager("/test_dir")
        mock_msg = self._create_mock_message("msg1", "subject")
        mock_msg.id = None

        with self.assertRaises(ValueError):
            manager.add(mock_msg)

    def test_contains(self):
        """Test the __contains__ method with various input types."""
        self.fs.create_dir("/test_dir")
        manager = index.GmailIndexManager("/test_dir")
        mock_msg = self._create_mock_message("msg_exists", "Subject")
        manager.add(mock_msg)

        # Test with string ID
        self.assertIn("msg_exists", manager)
        self.assertNotIn("msg_does_not_exist", manager)

        # Test with Message object
        self.assertIn(mock_msg, manager)
        other_mock_msg = self._create_mock_message("other_id", "Other")
        self.assertNotIn(other_mock_msg, manager)

        # Test with MessageId object
        msg_id_obj = gmail_types.MessageId(id="msg_exists")
        self.assertIn(msg_id_obj, manager)
        other_msg_id_obj = gmail_types.MessageId(id="other_id")
        self.assertNotIn(other_msg_id_obj, manager)

    def test_save_index_is_sorted(self):
        """Test that save_index writes a sorted list."""
        self.fs.create_dir("/test_dir")
        manager = index.GmailIndexManager("/test_dir")

        # Add messages in non-sorted order
        msg_c = self._create_mock_message(
            "msg_c", "C", "Fri, 1 Mar 2024 12:00:00 +0000"
        )

        msg_a = self._create_mock_message(
            "msg_a", "A", "Mon, 1 Jan 2024 12:00:00 +0000"
        )

        msg_b = self._create_mock_message(
            "msg_b", "B", "Thu, 1 Feb 2024 12:00:00 +0000"
        )

        manager.add(msg_c)
        manager.add(msg_a)
        manager.add(msg_b)

        manager.save_index()

        index_file = test_support.fail_none(
            self.fs.get_object("/test_dir/index.json")
        )
        saved_data = json.loads(test_support.fail_none(index_file.contents))

        # Check if the saved data is sorted by received_date
        self.assertEqual(saved_data[0]["id"], "msg_a")
        self.assertEqual(saved_data[1]["id"], "msg_b")
        self.assertEqual(saved_data[2]["id"], "msg_c")
