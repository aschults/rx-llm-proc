"""Types used with the Google Docs REST interface."""

from abc import abstractmethod
from typing import Any, Protocol


class DocsHttpRequestInterface(Protocol):
    """Partial and type anostic request interface."""

    def execute(self) -> Any:
        """Execute the formed request."""


class DocsDocumentsInterface(Protocol):
    """documents() API part."""

    @abstractmethod
    def batchUpdate(
        self,
        *,
        documentId: str,
        body: Any,
        **kwargs: Any,
    ) -> DocsHttpRequestInterface:
        """Update a document."""

    @abstractmethod
    def get(
        self, *, documentId: str, **kwargs: Any
    ) -> DocsHttpRequestInterface:
        """Get a document."""


class DocsInterface(Protocol):
    """Top level Docs API interface."""

    @abstractmethod
    def documents(self) -> DocsDocumentsInterface:
        """Get the documents API part."""
