"""Document model for Google Docs."""

import logging

import reactivex as rx

from rxllmproc.docs import types as docs_types
from rxllmproc.docs import docs_text
from .markdown_to_gdocs import convert_markdown_to_requests
from .section import Section
from rxllmproc.docs import api as docs_wrapper

MARKER_CHAR = "\u2063"


class Document:
    """A robust Document model."""

    def __init__(
        self,
        wrapper: "docs_wrapper.DocsWrapper",
        document_id: str,
        ensure_alignment: bool = True,
    ):
        """Initialize the document model."""
        self.wrapper = wrapper
        self.document_id = document_id
        self.ensure_alignment = ensure_alignment
        self._on_load = rx.Subject['DocumentContent']()
        self._load_doc()

    @property
    def on_load(self) -> 'rx.Observable[DocumentContent]':
        """Returns an observable that fires when the document is loaded."""
        return self._on_load

    def _load_doc(self) -> None:
        """Loads the document and refreshes content."""
        self.model: docs_types.Document = self.wrapper.get(self.document_id)
        if not self.model.body:
            raise ValueError("Document body is empty.")
        self.content = DocumentContent(self.model.body)
        if self.ensure_alignment:
            self.content.verify_alignment()
        self._on_load.on_next(self.content)

    @property
    def url(self) -> str:
        """Returns the URL of the document."""
        return f"https://docs.google.com/document/d/{self.document_id}"

    def adjust_requests_indices(
        self, requests: docs_types.DocsRequests, index: int
    ) -> docs_types.DocsRequests:
        """Adjusts the indices of all requests to a new starting point."""
        offset = index

        if offset <= 0:
            raise ValueError(f"Offset cannot be less than 1, was {offset}.")

        for req in requests:
            for value in req.__dict__.values():
                if value is None:
                    continue
                if hasattr(value, "location") and value.location is not None:
                    value.location.index += offset
                if hasattr(value, "range") and value.range is not None:
                    value.range.startIndex += offset
                    value.range.endIndex += offset
        return requests

    def ensure_newline_at_index(self, index: int) -> int:
        """Ensures the insertion happens on a new line."""
        if index <= 1:
            raise ValueError(
                "Cannot insert before the start of the document content."
            )

        content = []
        if self.model.body and self.model.body.content:
            content = self.model.body.content

        # A paragraph's endIndex is right after its implicit newline.
        # If our index matches an endIndex of a paragraph, we are on a new line.
        is_after_paragraph = any(
            el.endIndex == index for el in content if el.paragraph
        )

        if not is_after_paragraph:
            logging.info(
                "Insertion point is not at the end of a paragraph. Inserting newline before index %d...",
                index,
            )
            self.wrapper.batch_update(
                self.document_id,
                [
                    docs_types.DocsRequest(
                        insertText=docs_types.InsertTextRequest(
                            text="\n",
                            location=docs_types.Location(index=index),
                        )
                    )
                ],
            )
            self._load_doc()
            return index + 1
        return index

    def _find_closest_marker(self, start_index: int) -> int | None:
        """Finds the closest marker character in the document."""
        if not self.model.body or not self.model.body.content:
            return None

        candidates: list[int] = []
        for element in self.model.body.content:
            if element.paragraph:
                for elem in element.paragraph.elements:
                    if elem.textRun and elem.textRun.content:
                        content = elem.textRun.content
                        base_index = elem.startIndex

                        # Find all occurrences
                        pos = content.find(MARKER_CHAR)
                        while pos != -1:
                            abs_index = base_index + pos
                            if abs_index >= start_index:
                                candidates.append(abs_index)
                            pos = content.find(MARKER_CHAR, pos + 1)

        if not candidates:
            return None
        return min(candidates)

    def apply_batch_updates(
        self,
        index: int,
        *requests: docs_types.DocsRequest,
        ensure_newline: bool = False,
        get_end: bool = False,
    ) -> int:
        """Applies a list of requests to the document, at index.

        Note: The requests' indices will be adjusted to start at the index
        and executed in order. So the second request will be applied in front of the
        first one, etc. Accordingly, insert requests are ending up in reversed order
        in the document.
        """
        working_index = index

        if ensure_newline:
            working_index = self.ensure_newline_at_index(working_index)

        requests_list = list(requests)
        self.adjust_requests_indices(requests_list, working_index)

        if not get_end:
            self.wrapper.batch_update(self.document_id, requests_list)
            return working_index

        # Insert marker at the indexed position
        marker_request = docs_types.DocsRequest(
            insertText=docs_types.InsertTextRequest(
                text=MARKER_CHAR,
                location=docs_types.Location(index=working_index),
            )
        )

        # Prepend marker request so it's inserted first (and pushed down by subsequent inserts at same index)
        full_requests = [marker_request] + requests_list

        self.wrapper.batch_update(self.document_id, full_requests)

        # Refresh model to find marker
        self._load_doc()

        # Find marker and update index
        new_index = self._find_closest_marker(working_index)
        if new_index is not None:
            # Cleanup marker
            cleanup_request = docs_types.DocsRequest(
                deleteContentRange=docs_types.DeleteContentRangeRequest(
                    range=docs_types.Range(
                        startIndex=new_index, endIndex=new_index + 1
                    )
                )
            )
            self.wrapper.batch_update(self.document_id, [cleanup_request])
            # Refresh again to ensure model is clean
            self._load_doc()
            return new_index
        else:
            logging.warning("Marker recovery failed: Marker not found.")

        return working_index

    def get_start(self) -> int:
        """Returns an index at the start of the document body."""
        return 1

    def get_end(self) -> int:
        """Returns an index at the end of the document body."""
        index = 1
        if self.model.body:
            index = (self.model.end_of_body_index or 2) - 1
        return index

    def insert_at(
        self,
        index: int,
        content: str,
        ensure_newline: bool = False,
        get_end: bool = False,
    ) -> int:
        """Generates a basic text insertion request and executes it."""
        request = docs_types.DocsRequest(
            insertText=docs_types.InsertTextRequest(
                text=content, location=docs_types.Location(index=0)
            )
        )
        return self.apply_batch_updates(
            index, request, ensure_newline=ensure_newline, get_end=get_end
        )

    def insert_markdown_at(
        self,
        index: int,
        content: str,
        ensure_newline: bool = False,
        get_end: bool = False,
    ) -> int:
        """Inserts markdown content at the index."""
        logging.debug("Converting markdown content to Google Docs requests...")
        logging.debug("Original markdown content:\n%s", content)
        requests = convert_markdown_to_requests(content)
        logging.debug("Converted markdown to %d requests.", len(requests))
        logging.debug("Requests: %s", requests)
        return self.apply_batch_updates(
            index, *requests, ensure_newline=ensure_newline, get_end=get_end
        )

    def delete_range(self, start: int, end: int) -> None:
        """Deletes a range of content."""
        request = docs_types.DocsRequest(
            deleteContentRange=docs_types.DeleteContentRangeRequest(
                range=docs_types.Range(startIndex=start, endIndex=end)
            )
        )
        self.wrapper.batch_update(self.document_id, [request])
        self._load_doc()

    def find_section(
        self,
        patterns: list[str] | None = None,
        heading_id: str | None = None,
    ) -> Section | None:
        """Finds a section based on patterns or heading ID.

        Args:
            patterns: A list of regex patterns to identify a section hierarchy.
                Patterns can be:
                - "##<heading_id>" to match by heading ID.
                - "<heading_regex>//<text_regex>" to match by heading type and text.
                - "<text_regex>" to match by text.
            heading_id: A direct heading ID to search for.

        Returns:
            The found Section or None.
        """
        if not self.content:
            return None

        matching_sections = self.content.sections

        if patterns:
            for pattern in patterns:
                heading_id = None
                heading_pattern = None
                text_pattern = None

                if pattern.startswith("##"):
                    heading_id = pattern[2:]
                elif "//" in pattern:
                    heading_pattern, text_pattern = pattern.split("//", 1)
                else:
                    text_pattern = pattern

                matching_sections = Section.find_sections(
                    matching_sections,
                    text_pattern=text_pattern,
                    heading_pattern=heading_pattern,
                    heading_id=heading_id,
                )
                if not matching_sections:
                    logging.warning("Section matching %r not found.", pattern)
                    return None
                logging.info(
                    "Sections matched: %s",
                    ",".join(
                        f"{s.level}//{s.text}##{s.heading_id}"
                        for s in matching_sections
                    ),
                )
            return matching_sections[0]

        if heading_id:
            matching_sections = Section.find_sections(
                self.content.sections, heading_id=heading_id
            )
            if not matching_sections:
                return None
            return matching_sections[0]

        return None


class DocumentContent:
    """Text only version of the document content."""

    def __init__(self, body: docs_types.Body):
        """Initialize the document content."""
        self.body = body
        text_renderer = docs_text.TextRenderer()
        text_renderer.render_body(self.body)
        self.text = text_renderer.as_string()

        self.sections = Section.create_from(self.body.content, self.text)

    def verify_alignment(self):
        """Verify the alignment of the document content."""
        docs_text.AlignmentVerifier(self.text).verify_body(self.body)
