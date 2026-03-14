"""Google Docs REST interface wrapper."""

import logging
import dataclasses
from typing import Any

import dacite
import dacite.exceptions
from googleapiclient import discovery

from rxllmproc.docs import types as docs_types
from rxllmproc.core import auth, api_base
from rxllmproc.docs import _interface


def _as_dict_factory(args: list[tuple[str, Any]]) -> dict[str, Any]:
    """Dataclass helper to convert datatypes to REST compatible form."""
    val = {k: v for k, v in args if v is not None}
    return val


class DocsWrapper(api_base.ApiBase):
    """Wrapper around Google Docs API."""

    def __init__(
        self,
        creds: auth.Credentials | None = None,
        service: _interface.DocsInterface | None = None,
    ):
        """Create an instance.

        Args:
            creds: Credentials to be used for the requests.
            service: Optionally provide service instance (mailnly for testing.)
                Note: If provided, this instance is shared across threads and
                is not thread-safe.
        """
        super().__init__(creds)
        self._service: _interface.DocsInterface = service or discovery.build(
            "docs",
            "v1",
            credentials=self._creds,
            requestBuilder=self.build_request,
        )

    def batch_update(self, document_id: str, requests: docs_types.DocsRequests):
        """Applies a series of updates to a document.

        Args:
            document_id: The ID of the document to update.
            requests: A list of requests to be applied to the document.
        """
        logging.info(
            "Applying %d updates to document %s", len(requests), document_id
        )
        body = {
            "requests": [
                dataclasses.asdict(
                    request,
                    dict_factory=_as_dict_factory,
                )
                for request in requests
            ]
        }
        self._service.documents().batchUpdate(
            documentId=document_id,
            body=body,
        ).execute()

    def get(self, document_id: str) -> docs_types.Document:
        """Retrieves a document.

        Args:
            document_id: The ID of the document to retrieve.

        Returns:
            A Document object.
        """
        logging.info("Retrieving document %s", document_id)
        request = self._service.documents().get(documentId=document_id)
        doc_dict = request.execute()
        try:
            return dacite.from_dict(
                data_class=docs_types.Document, data=doc_dict
            )
        except dacite.exceptions.DaciteError:
            logging.error("failed to deserialize", exc_info=True)
            logging.error("doc: %s", doc_dict)
            raise
