# pyright: reportPrivateUsage=false
"""Tests for the Document model."""

import unittest
from unittest import mock
from rxllmproc.docs import docs_model
from rxllmproc.docs import types as docs_types
import test_support


class TestDocsModel(unittest.TestCase):
    """Test cases for Document model."""

    def setUp(self):
        self.mock_wrapper = mock.MagicMock()
        self.doc_id = "test_doc_id"
        self.mock_doc_entity = docs_types.Document(
            documentId=self.doc_id, body=docs_types.Body(content=[])
        )
        self.mock_wrapper.get.return_value = self.mock_doc_entity
        self.document = docs_model.Document(self.mock_wrapper, self.doc_id)

    def test_get_start(self):
        """Test get_start."""
        index = self.document.get_start()
        self.assertEqual(index, 1)

    def test_get_end(self):
        """Test get_end."""
        test_support.fail_none(self.mock_doc_entity.body).content = [
            docs_types.StructuralElement(endIndex=100)
        ]
        index = self.document.get_end()
        self.assertEqual(index, 99)

    def test_insert_at_simple(self):
        """Test simple insertion without marker."""
        index = 5
        self.document.insert_at(index, "Hello")

        self.mock_wrapper.batch_update.assert_called()
        args, _ = self.mock_wrapper.batch_update.call_args
        self.assertEqual(args[0], self.doc_id)
        requests = args[1]
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].insertText.text, "Hello")
        # Index should be adjusted (0 + 5)
        self.assertEqual(requests[0].insertText.location.index, 5)

    def test_insert_at_with_marker(self):
        """Test insertion with marker recovery."""
        index = 5
        marker_char = docs_model.MARKER_CHAR

        # Mock document state after insertion containing marker
        # We simulate that "Inserted" was inserted at 5.
        # "Inserted" length is 8. Marker is at 5+8=13.
        doc_with_marker = docs_types.Document(
            documentId=self.doc_id,
            body=docs_types.Body(
                content=[
                    docs_types.StructuralElement(
                        startIndex=1,
                        endIndex=20,
                        paragraph=docs_types.Paragraph(
                            elements=[
                                docs_types.ParagraphElement(
                                    startIndex=5,
                                    endIndex=20,
                                    textRun=docs_types.TextRun(
                                        content=f"Inserted{marker_char}"
                                    ),
                                )
                            ]
                        ),
                    )
                ]
            ),
        )

        doc_clean = docs_types.Document(
            documentId=self.doc_id, body=docs_types.Body(content=[])
        )

        self.mock_wrapper.get.side_effect = [
            self.mock_doc_entity,  # Init
            doc_with_marker,  # After insert
            doc_clean,  # After cleanup
        ]

        # Re-init to consume first side_effect
        self.document = docs_model.Document(
            self.mock_wrapper, self.doc_id, False
        )

        new_index = self.document.insert_at(index, "Inserted", get_end=True)

        # Verify calls
        # 1. Batch update with marker + content
        # 2. Batch update cleanup
        self.assertEqual(self.mock_wrapper.batch_update.call_count, 2)

        # Check first call (insert)
        insert_call_args = self.mock_wrapper.batch_update.call_args_list[0][0]
        requests = insert_call_args[1]
        # Marker request is prepended
        self.assertEqual(requests[0].insertText.text, marker_char)
        self.assertEqual(requests[0].insertText.location.index, 5)

        # Check second call (cleanup)
        cleanup_call_args = self.mock_wrapper.batch_update.call_args_list[1][0]
        cleanup_reqs = cleanup_call_args[1]
        # Marker found at 13
        self.assertEqual(
            cleanup_reqs[0].deleteContentRange.range.startIndex, 13
        )
        self.assertEqual(cleanup_reqs[0].deleteContentRange.range.endIndex, 14)

        self.assertEqual(new_index, 13)

    def test_ensure_newline(self):
        """Test ensure_newline logic."""
        # Mock content where index 5 is NOT after a paragraph (e.g. middle of text)
        # Paragraph ends at 10.
        test_support.fail_none(self.mock_doc_entity.body).content = [
            docs_types.StructuralElement(
                paragraph=docs_types.Paragraph(
                    elements=[
                        docs_types.ParagraphElement(startIndex=1, endIndex=10)
                    ]
                ),
                endIndex=10,
            )
        ]

        self.document = docs_model.Document(
            self.mock_wrapper, self.doc_id, False
        )

        index = 5
        new_index = self.document.ensure_newline_at_index(index)

        # Should have called batch_update with newline
        self.mock_wrapper.batch_update.assert_called()
        requests = self.mock_wrapper.batch_update.call_args[0][1]
        self.assertEqual(requests[0].insertText.text, "\n")
        self.assertEqual(requests[0].insertText.location.index, 5)
        self.assertEqual(new_index, 6)

    def test_ensure_newline_not_needed(self):
        """Test ensure_newline when not needed."""
        index = 10
        # Paragraph ends at 10.
        test_support.fail_none(self.mock_doc_entity.body).content = [
            docs_types.StructuralElement(
                paragraph=docs_types.Paragraph(
                    elements=[
                        docs_types.ParagraphElement(startIndex=1, endIndex=10)
                    ]
                ),
                endIndex=10,
            )
        ]
        self.document = docs_model.Document(
            self.mock_wrapper, self.doc_id, False
        )

        new_index = self.document.ensure_newline_at_index(index)
        self.mock_wrapper.batch_update.assert_not_called()
        self.assertEqual(new_index, 10)

    @mock.patch("rxllmproc.docs.docs_model.convert_markdown_to_requests")
    def test_insert_markdown_at(self, mock_convert: mock.MagicMock):
        """Test inserting markdown."""
        index = 10
        req1 = docs_types.DocsRequest(
            insertText=docs_types.InsertTextRequest(
                text="md", location=docs_types.Location(index=0)
            )
        )
        mock_convert.return_value = [req1]

        self.document.insert_markdown_at(index, "## md")

        self.mock_wrapper.batch_update.assert_called_once()
        args = self.mock_wrapper.batch_update.call_args[0]
        requests = args[1]
        # Index adjustment: 0 + 10 = 10
        self.assertEqual(requests[0].insertText.location.index, 10)

    def test_delete_range(self):
        """Test delete_range."""
        self.document.delete_range(10, 20)
        self.mock_wrapper.batch_update.assert_called()
        args, _ = self.mock_wrapper.batch_update.call_args
        requests = args[1]
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].deleteContentRange.range.startIndex, 10)
        self.assertEqual(requests[0].deleteContentRange.range.endIndex, 20)

    def test_find_section(self):
        """Test find_section method."""
        mock_section = mock.Mock()
        mock_section.level = "HEADING_1"
        mock_section.text = "My Heading"

        self.document.content = mock.Mock()
        self.document.content.sections = [mock_section]

        with mock.patch(
            "rxllmproc.docs.section.Section.find_sections"
        ) as mock_find:
            mock_find.return_value = [mock_section]

            # Test finding by heading_id argument
            self.assertEqual(
                self.document.find_section(heading_id="h.123"), mock_section
            )
            mock_find.assert_called_with([mock_section], heading_id="h.123")

            # Test finding by pattern "##id"
            self.assertEqual(
                self.document.find_section(patterns=["##h.123"]), mock_section
            )
            mock_find.assert_called_with(
                [mock_section],
                text_pattern=None,
                heading_pattern=None,
                heading_id="h.123",
            )

            # Test finding by pattern "Heading//Text"
            self.assertEqual(
                self.document.find_section(patterns=["H1//Text"]), mock_section
            )
            mock_find.assert_called_with(
                [mock_section],
                text_pattern="Text",
                heading_pattern="H1",
                heading_id=None,
            )

            # Test not found
            mock_find.return_value = []
            self.assertIsNone(self.document.find_section(heading_id="missing"))

    def test_on_load(self):
        """Test the on_load observable."""
        results: list[docs_model.DocumentContent] = []
        self.document.on_load.subscribe(results.append)

        # Trigger a reload
        self.document._load_doc()

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], docs_model.DocumentContent)
