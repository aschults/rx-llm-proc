# pyright: basic
# pyright: reportPrivateUsage=false
"""Tests for AlignmentVerifier using sample_doc2."""

import unittest
from rxllmproc.docs import docs_text
from rxllmproc.docs import types as docs_types
import sample_doc2


class TestDocsAlignment(unittest.TestCase):
    """Test cases for AlignmentVerifier."""

    def test_verify_sample_doc2(self):
        """Test verification of sample_doc2."""
        body = sample_doc2.DOC_BODY
        renderer = docs_text.TextRenderer()
        renderer.render_body(body)
        text = renderer.as_string()

        # Should not raise any exception
        docs_text.AlignmentVerifier(text).verify_body(body)

    def test_verify_sample_doc2_failure(self):
        """Test verification failure when text is modified."""
        body = sample_doc2.DOC_BODY
        renderer = docs_text.TextRenderer()
        renderer.render_body(body)
        text = renderer.as_string()

        # Modify text to induce error
        # Replace a character at a known position.
        # "All Elements Doc" starts at 1.
        # We replace the character at index 2 (which is 'l') with 'X'
        modified_text = text[:2] + "X" + text[3:]

        verifier = docs_text.AlignmentVerifier(modified_text)

        with self.assertRaises(docs_text.NestedVerifyError):
            verifier.verify_body(body)


class TestTextRenderer(unittest.TestCase):
    """Test cases for TextRenderer."""

    def test_render_simple_paragraph(self):
        """Test rendering a simple text paragraph."""
        body = docs_types.Body(
            content=[
                docs_types.StructuralElement(
                    startIndex=1,
                    endIndex=6,
                    paragraph=docs_types.Paragraph(
                        elements=[
                            docs_types.ParagraphElement(
                                startIndex=1,
                                endIndex=6,
                                textRun=docs_types.TextRun(content="Hello"),
                            )
                        ]
                    ),
                )
            ]
        )
        renderer = docs_text.TextRenderer()
        renderer.render_body(body)
        expected = docs_text.NON_CHAR + "Hello"
        self.assertEqual(renderer.as_string(), expected)

    def test_render_multiple_elements(self):
        """Test rendering multiple text runs."""
        body = docs_types.Body(
            content=[
                docs_types.StructuralElement(
                    startIndex=1,
                    endIndex=6,
                    paragraph=docs_types.Paragraph(
                        elements=[
                            docs_types.ParagraphElement(
                                startIndex=1,
                                endIndex=6,
                                textRun=docs_types.TextRun(content="Hello"),
                            )
                        ]
                    ),
                ),
                docs_types.StructuralElement(
                    startIndex=6,
                    endIndex=12,
                    paragraph=docs_types.Paragraph(
                        elements=[
                            docs_types.ParagraphElement(
                                startIndex=6,
                                endIndex=12,
                                textRun=docs_types.TextRun(content=" World"),
                            )
                        ]
                    ),
                ),
            ]
        )
        renderer = docs_text.TextRenderer()
        renderer.render_body(body)
        expected = docs_text.NON_CHAR + "Hello World"
        self.assertEqual(renderer.as_string(), expected)

    def test_render_table(self):
        """Test rendering a table structure."""
        body = docs_types.Body(
            content=[
                docs_types.StructuralElement(
                    startIndex=1,
                    endIndex=9,
                    table=docs_types.Table(
                        rows=1,
                        columns=1,
                        tableRows=[
                            docs_types.TableRow(
                                startIndex=2,
                                endIndex=9,
                                tableCells=[
                                    docs_types.TableCell(
                                        startIndex=3,
                                        endIndex=8,
                                        content=[
                                            docs_types.StructuralElement(
                                                startIndex=4,
                                                endIndex=8,
                                                paragraph=docs_types.Paragraph(
                                                    elements=[
                                                        docs_types.ParagraphElement(
                                                            startIndex=4,
                                                            endIndex=8,
                                                            textRun=docs_types.TextRun(
                                                                content="Cell"
                                                            ),
                                                        )
                                                    ]
                                                ),
                                            )
                                        ],
                                    )
                                ],
                            )
                        ],
                    ),
                )
            ]
        )

        renderer = docs_text.TextRenderer()
        renderer.render_body(body)

        expected = (
            docs_text.NON_CHAR
            + docs_text.TABLE_START
            + docs_text.TABLE_ROW
            + docs_text.TABLE_CELL
            + "Cell"
            + docs_text.TABLE_ROW
        )

        self.assertEqual(renderer.as_string(), expected)

    def test_render_special_elements(self):
        """Test rendering elements that use fillers (Date, etc)."""
        body = docs_types.Body(
            content=[
                docs_types.StructuralElement(
                    startIndex=1,
                    endIndex=2,
                    paragraph=docs_types.Paragraph(
                        elements=[
                            docs_types.ParagraphElement(
                                startIndex=1,
                                endIndex=2,
                                dateElement=docs_types.DateElement(
                                    dateId="d1",
                                    dateElementProperties=docs_types.DateElementProperties(
                                        timestamp="2023-01-01",
                                        locale="en",
                                        dateFormat="YMD",
                                        timeFormat="",
                                        displayText="2023-01-01",
                                    ),
                                ),
                            )
                        ]
                    ),
                )
            ]
        )
        renderer = docs_text.TextRenderer()
        renderer.render_body(body)

        expected = docs_text.NON_CHAR + docs_text.DATE_FILLER
        self.assertEqual(renderer.as_string(), expected)

    def test_buffer_expansion(self):
        """Test that buffer expands correctly if indices have gaps."""
        body = docs_types.Body(
            content=[
                docs_types.StructuralElement(
                    startIndex=1,
                    endIndex=2,
                    paragraph=docs_types.Paragraph(
                        elements=[
                            docs_types.ParagraphElement(
                                startIndex=1,
                                endIndex=2,
                                textRun=docs_types.TextRun(content="A"),
                            )
                        ]
                    ),
                ),
                docs_types.StructuralElement(
                    startIndex=5,
                    endIndex=6,
                    paragraph=docs_types.Paragraph(
                        elements=[
                            docs_types.ParagraphElement(
                                startIndex=5,
                                endIndex=6,
                                textRun=docs_types.TextRun(content="B"),
                            )
                        ]
                    ),
                ),
            ]
        )

        renderer = docs_text.TextRenderer()
        renderer.render_body(body)

        expected = docs_text.NON_CHAR + "A" + docs_text.NON_CHAR * 3 + "B"
        self.assertEqual(renderer.as_string(), expected)

    def test_index_error(self):
        """Test that invalid indices raise IndexError."""
        renderer = docs_text.TextRenderer()
        # Manually trigger insert out of bounds
        with self.assertRaises(IndexError):
            renderer._insert(10, "Fail")

    def test_sample_doc2(self):
        """Test rendering sample_doc2."""
        renderer = docs_text.TextRenderer()
        renderer.render_body(sample_doc2.DOC_BODY)
        result = renderer.as_string()

        print(repr(result))
        self.assertEqual(result, sample_doc2.DOCS_TEXT)
