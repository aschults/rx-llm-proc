"""Text rendering functions for Google Docs elements."""

import json
import logging
from typing import Any
from rxllmproc.docs import types as docs_types
from rxllmproc.core.infra import utilities

NON_CHAR = "\U0001ffff"
TABLE_START = "\U0002ffff"
TABLE_ROW = "\U0003ffff"
TABLE_CELL = "\U0004ffff"
DATE_FILLER = "\U0005ffff"
CHIP_FILLER = "\U0006ffff"
TEXT_RUN_FILLER = "\U0007ffff"


class VerifyError(Exception):
    """An error during verification."""

    pass


class NestedVerifyError(Exception):
    """A nested error during verification."""

    pass


class TextRenderer:
    """Renders text from Google Docs elements."""

    def __init__(self) -> None:
        """Initializes the TextRenderer."""
        self.text: str = ""

    def len(self) -> int:
        """Returns the length of the rendered text."""
        return len(self.text)

    def _init_range(self, start: int, end: int, char: str = NON_CHAR) -> None:
        if end > self.len():
            self.text += NON_CHAR * (end - self.len())
            assert self.len() == end
        len_before = self.len()
        self.text = self.text[:start] + char * (end - start) + self.text[end:]
        assert self.len() == len_before

    def _insert(self, index: int, text: str) -> None:
        len_before = self.len()
        text_len = len(text)
        if index > self.len():
            raise IndexError(
                f"Index {index} out of bounds for buffer length {self.len()}"
            )
        end = index + text_len
        if end > self.len():
            raise IndexError(
                f"Index {end} out of bounds for buffer length {self.len()}"
            )
        self.text = self.text[:index] + text + self.text[end:]
        assert self.len() == len_before

    def as_string(self, start: int = 0, end: int | None = None) -> str:
        """Returns the rendered text as a string."""
        return self.text[start:end]

    def _at(self, index: int) -> str:
        return self.text[index]

    def render_table_cell(
        self,
        element: docs_types.TableCell,
    ) -> None:
        """Renders the text content of a TableCell."""
        self._init_range(element.startIndex, element.endIndex, TABLE_CELL)
        for content_element in element.content:
            self.render_structural_element(content_element)

    def render_table_row(
        self,
        element: docs_types.TableRow,
    ) -> None:
        """Renders the text content of a TableRow."""
        self._init_range(element.startIndex, element.endIndex, TABLE_ROW)
        for cell in element.tableCells:
            self.render_table_cell(cell)

    def render_table(
        self,
        element: docs_types.Table,
    ) -> None:
        """Renders the text content of a Table."""
        for row in element.tableRows:
            self.render_table_row(row)

    def render_table_of_contents(
        self,
        element: docs_types.TableOfContents,
    ) -> None:
        """Renders the text content of a TableOfContents."""
        for content_element in element.content:
            self.render_structural_element(content_element)

    def render_paragraph_element(
        self,
        element: docs_types.ParagraphElement,
    ) -> None:
        """Renders the text content of a ParagraphElement."""
        self._init_range(element.startIndex, element.endIndex)
        filler = _get_filler(element)
        if filler:
            self._init_range(element.startIndex, element.endIndex, filler)

        if element.textRun:
            self._init_range(
                element.startIndex, element.endIndex, TEXT_RUN_FILLER
            )
            if element.textRun.content:
                self._insert(element.startIndex, element.textRun.content)

    def render_structural_element(
        self,
        element: docs_types.StructuralElement,
    ) -> None:
        """Renders the text content of a StructuralElement."""
        if element.startIndex is None:
            raise ValueError("startIndex cannot be None")
        if element.endIndex is None:
            raise ValueError("endIndex cannot be None")

        self._init_range(element.startIndex, element.endIndex)

        if element.paragraph:
            for content_element in element.paragraph.elements:
                self.render_paragraph_element(content_element)
        elif element.sectionBreak:
            pass
        elif element.table:
            self._init_range(element.startIndex, element.endIndex, TABLE_START)
            self.render_table(element.table)
        elif element.tableOfContents:
            self.render_table_of_contents(element.tableOfContents)

    def render_body(
        self,
        element: docs_types.Body,
    ) -> None:
        """Renders the text content of a Body."""
        self._init_range(0, 1, NON_CHAR)
        if not element.content:
            return
        end_of_doc_index = element.content[-1].endIndex or 0
        self._init_range(0, end_of_doc_index, NON_CHAR)
        for content_element in element.content:
            self.render_structural_element(content_element)


class AlignmentVerifier:
    """Verifies the alignment of text content in a document."""

    def __init__(self, content: str):
        """Initializes the AlignmentVerifier."""
        self.content = content

    def _handle_verify_error(
        self,
        element: Any,
        start_index: int,
        end_index: int,
        e: VerifyError,
    ) -> None:
        obj = json.dumps(utilities.asdict(element), indent=2)
        name = type(element).__name__
        logging.error(
            "Alignment error for %s, indices %d, %d",
            name,
            start_index,
            end_index,
        )
        logging.error("In object: %s", obj)
        log_start_ix = max(0, start_index - 5)
        log_end_ix = min(len(self.content), end_index + 10)
        logging.error(
            "In text (from %d): %r",
            log_start_ix,
            self.content[log_start_ix:log_end_ix],
        )
        raise NestedVerifyError("Alignment error") from e

    def _verify_table_cell(
        self,
        element: docs_types.TableCell,
    ) -> None:
        try:
            for content_element in element.content:
                self._verify_structural_element(content_element)
        except VerifyError as e:
            self._handle_verify_error(
                element, element.startIndex, element.endIndex, e
            )

    def _verify_table_row(
        self,
        element: docs_types.TableRow,
    ) -> None:
        try:
            for cell in element.tableCells:
                self._verify_table_cell(cell)
        except VerifyError as e:
            self._handle_verify_error(
                element, element.startIndex, element.endIndex, e
            )

    def _verify_paragraph_element(
        self,
        element: docs_types.ParagraphElement,
    ) -> None:
        try:
            if element.textRun:
                self._verify_text(
                    element.textRun.content,
                    element.startIndex,
                    element.endIndex,
                )
                return

            filler = _get_filler(element)
            if filler:
                expected = filler * (element.endIndex - element.startIndex)
                found = self.content[element.startIndex : element.endIndex]
                if found != expected:
                    raise VerifyError(
                        f"Mismatch at index {element.startIndex}: expected {repr(expected)}, found {repr(found)}"
                    )
        except VerifyError as e:
            self._handle_verify_error(
                element, element.startIndex, element.endIndex, e
            )

    def _verify_text(
        self,
        text: str,
        start_index: int,
        end_index: int,
    ) -> None:
        current_idx = start_index
        for char in text:
            if current_idx >= len(self.content):
                raise VerifyError(
                    f"Index {current_idx} out of bounds for text length {len(self.content)}"
                )
            if self.content[current_idx] != char:
                raise VerifyError(
                    f"Mismatch at index {current_idx}: "
                    f"expected {repr(char)}, found {repr(self.content[current_idx])}"
                )
            current_idx += len(char)
        while current_idx < end_index:
            if self.content[current_idx] != TEXT_RUN_FILLER:
                raise VerifyError(
                    f"Unexpected character at index {current_idx}: "
                    f"{repr(self.content[current_idx])}"
                )
            current_idx += 1

    def _verify_structural_element(
        self,
        element: docs_types.StructuralElement,
    ) -> None:
        start_index = element.startIndex
        end_index = element.endIndex
        if start_index is None:
            raise VerifyError("StructuralElement start index is None")
        if end_index is None:
            raise VerifyError("StructuralElement end index is None")
        try:
            if element.paragraph:
                for content_element in element.paragraph.elements:
                    self._verify_paragraph_element(content_element)
            elif element.sectionBreak:
                pass
            elif element.table:
                for row in element.table.tableRows:
                    self._verify_table_row(row)
            elif element.tableOfContents:
                for content_element in element.tableOfContents.content:
                    self._verify_structural_element(content_element)
        except VerifyError as e:
            self._handle_verify_error(element, start_index, end_index, e)

    def verify_body(
        self,
        element: docs_types.Body,
    ) -> None:
        """Verifies the alignment of the document body."""
        if not element.content:
            return
        for content_element in element.content:
            self._verify_structural_element(content_element)


def _get_filler(element: docs_types.ParagraphElement) -> str | None:
    filler = CHIP_FILLER
    if element.dateElement:
        filler = DATE_FILLER
    elif element.textRun:
        filler = None
    return filler
