"""Tests for the GMail base types."""

import unittest
import base64

from rxllmproc.gmail import types as gmail_types


class TestMessage(unittest.TestCase):
    """Test the meesage class."""

    def setUp(self) -> None:
        """Provide a message to test."""
        self.msg = gmail_types.Message(
            payload=gmail_types.MessagePart(
                mimeType='text/html',
                headers=[gmail_types.Header('Subject', 'thesubject')],
                body=gmail_types.MessagePartBody(
                    data=base64.urlsafe_b64encode(b'thecontent').decode()
                ),
            )
        )

    def test_get_subject(self):
        """Test reteriving the subject."""
        self.assertEqual('thesubject', self.msg.subject)

    def test_get_content_main(self):
        """Test retreiving the main content (from single part)."""
        self.assertEqual(('text/html', 'thecontent'), self.msg.main_message)

    def test_get_content_part(self):
        """Test retreiving the main content (from multipart)."""
        payload = self.msg.payload
        if payload is None:
            raise ValueError("Payload should not be None")
        payload.mimeType = 'multipart/alternative'
        payload.parts.append(
            gmail_types.MessagePart(
                mimeType='text/html',
                body=gmail_types.MessagePartBody(
                    data=base64.urlsafe_b64encode(b'thecontent2').decode()
                ),
            )
        )
        self.assertEqual(('text/html', 'thecontent2'), self.msg.main_message)
