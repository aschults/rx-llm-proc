"""Test the email processing functions."""

import unittest
from email import message

from rxllmproc.text_processing import email_processing


class TestEmailProcessingFunctions(unittest.TestCase):
    """Test other functions in the module."""

    def test_get_email_content_plain(self):
        """Test extracting the content from an email."""
        msg = message.EmailMessage()
        msg['Subject'] = 'blah'
        text = '<b>some_content</b><div></div>'
        msg.set_content(text)

        self.assertEqual(
            text, email_processing.get_email_content(msg, 'raw').strip()
        )
        self.assertEqual(
            '<b>some_content</b>',
            email_processing.get_email_content(msg, 'clean').strip(),
        )
        self.assertEqual(
            '**some\\_content**',
            email_processing.get_email_content(msg, 'md').strip(),
        )

    def test_get_email_content_no_content(self):
        """Test with no content."""
        msg = message.EmailMessage()
        msg['Subject'] = 'blah'

        self.assertEqual(
            '', email_processing.get_email_content(msg, 'raw').strip()
        )

    def test_get_email_content_multipart(self):
        """Test with multipart message."""
        msg = message.EmailMessage()
        msg.set_content('the_content')
        msg.make_mixed()
        msg['Subject'] = 'blah'

        self.assertEqual(
            'the_content',
            email_processing.get_email_content(msg, 'raw').strip(),
        )
