"""Test the GMail API wrapper."""

import unittest
from unittest import mock

from google.oauth2 import credentials  # type: ignore

from rxllmproc.gmail import api as gmail_wrapper
from rxllmproc.gmail import _interface as _gmail_interface

from test_support import make_raw_email


class TestWrapper(unittest.TestCase):
    """Test the wrapper class."""

    def setUp(self) -> None:
        """Provide mock cerds, service and user."""
        self.creds = mock.Mock(spec=credentials.Credentials)
        self.service = mock.Mock(spec=_gmail_interface.GmailInterface)
        self.service.users().getProfile().execute.return_value = {
            "emailAddress": "theuser"
        }
        return super().setUp()

    def test_get_message(self):
        """Test getting a message."""
        wrapper = gmail_wrapper.GMailWrap(
            creds=self.creds, service=self.service
        )
        self.service.users().messages().get().execute.return_value = {
            "subject": "testsubject",
            "raw": make_raw_email("testsubject", "msgd"),
        }

        result = wrapper.get("theid")

        self.assertEqual("testsubject", result.parsed_msg["Subject"])
        self.service.users().messages().get.assert_called_with(
            userId="theuser", id="theid", format="raw"
        )

    def test_list_messages(self):
        """Test querying for message IDs."""
        wrapper = gmail_wrapper.GMailWrap(
            creds=self.creds, service=self.service
        )
        self.service.users().messages().list().execute.return_value = {
            "messages": [{"id": "messageid"}]
        }

        result = wrapper.search("thequery")

        self.assertEqual("messageid", result[0].id)
        self.service.users().messages().list.assert_called_with(
            userId="theuser", q="thequery", maxResults=500
        )

    def test_generate_ids(self):
        """Test generator function for IDs."""
        wrapper = gmail_wrapper.GMailWrap(
            creds=self.creds, service=self.service
        )
        self.service.users().messages().list().execute.return_value = {
            "messages": [{"id": "messageid"}, {"id": "messageid2"}],
        }

        result = list(wrapper.generate_ids("thequery"))

        self.assertEqual("messageid", result[0].id)
        self.assertEqual("messageid2", result[1].id)
        self.service.users().messages().list.assert_has_calls(
            [
                mock.call(
                    userId="theuser", q="thequery", maxResults=500, pageToken=""
                ),
                mock.call().execute(),
            ]
        )

    def test_generate_ids_paged(self):
        """Test generator function with multiple pages."""
        wrapper = gmail_wrapper.GMailWrap(
            creds=self.creds, service=self.service
        )
        self.service.users().messages().list().execute.side_effect = [
            {
                "messages": [{"id": "messageid"}],
                "nextPageToken": "sometoken",
            },
            {
                "messages": [{"id": "messageid2"}],
            },
        ]

        result = list(wrapper.generate_ids("thequery"))

        self.assertEqual("messageid", result[0].id)
        self.assertEqual("messageid2", result[1].id)
        self.service.users().messages().list.assert_has_calls(
            [
                mock.call(
                    userId="theuser", q="thequery", maxResults=500, pageToken=""
                ),
                mock.call().execute(),
                mock.call(
                    userId="theuser",
                    q="thequery",
                    maxResults=500,
                    pageToken="sometoken",
                ),
                mock.call().execute(),
            ]
        )
