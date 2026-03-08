"""Tests for docs_wrapper."""

import unittest
from unittest import mock

from google.oauth2 import credentials
from rxllmproc.docs import _interface, types as docs_types
from rxllmproc.docs import api as docs_wrapper


class TestWrapper(unittest.TestCase):
    """Test the wrapper class."""

    def setUp(self) -> None:
        """Provide mock creds and service, and a wrapper instance."""
        self.creds = mock.Mock(spec=credentials.Credentials)
        self.service = mock.Mock(spec=_interface.DocsInterface)
        self.documents_service = mock.Mock(
            spec=_interface.DocsDocumentsInterface
        )
        self.service.documents.return_value = self.documents_service
        self.wrapper = docs_wrapper.DocsWrapper(self.creds, self.service)
        return super().setUp()

    def test_batch_update(self):
        """Test that DocsWrapper can be instantiated."""

        request = [
            docs_types.DocsRequest(
                insertText=docs_types.InsertTextRequest(
                    text="test", location=docs_types.Location(index=22)
                )
            )
        ]
        self.wrapper.batch_update(document_id="theid", requests=request)
        self.documents_service.batchUpdate.assert_called_with(
            documentId="theid",
            body={
                "requests": [
                    {"insertText": {"text": "test", "location": {'index': 22}}}
                ]
            },
        )
