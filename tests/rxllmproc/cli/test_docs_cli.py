# pyright: reportPrivateUsage=false
"""Tests for Docs CLI."""

import json
import unittest
from unittest import mock

from unittest.mock import MagicMock, patch
from rxllmproc.cli import docs_cli


class TestDocsCli(unittest.TestCase):
    """Test cases for Docs CLI."""

    def setUp(self):
        self.mock_wrapper = MagicMock()
        self.cli = docs_cli.DocsCli(docs_wrapper=self.mock_wrapper)
        self.cli.document_id = "test_doc"
        self.document_patcher = patch("rxllmproc.docs.docs_model.Document")
        self.mock_document_cls = self.document_patcher.start()
        self.addCleanup(self.document_patcher.stop)
        self.mock_doc_instance = self.mock_document_cls.return_value

    def test_insert_at_start(self):
        """Test insert at start."""
        self.mock_doc_instance.get_start.return_value = 1

        self.cli.command = "insert"
        self.cli.at_start = True
        self.cli.plaintext = True

        with patch("sys.stdin.read", return_value="content"):
            self.cli.run()

        self.mock_doc_instance.get_start.assert_called_once()
        self.mock_doc_instance.insert_at.assert_called_with(
            1, "content", ensure_newline=False
        )

    @patch("rxllmproc.docs.docs_model.DocumentContent")
    def test_get_nested(self, mock_doc_content_cls: mock.MagicMock):
        """Test get command with --nested flag."""
        self.cli.command = "get"
        self.cli.nested = True

        # Mock the document returned by wrapper
        mock_doc_entity = MagicMock()
        mock_doc_entity.body = MagicMock()
        self.mock_wrapper.get.return_value = mock_doc_entity

        # Mock DocumentContent instance and sections
        mock_content_instance: mock.MagicMock = (
            mock_doc_content_cls.return_value
        )
        mock_section = MagicMock()
        mock_section.as_dict.return_value = {
            "level": "TITLE",
            "text": "My Title",
        }
        mock_content_instance.sections = [mock_section]

        with patch.object(self.cli, "write_output") as mock_write:
            self.cli.run()

            self.mock_wrapper.get.assert_called_with("test_doc")
            mock_doc_content_cls.assert_called_with(mock_doc_entity.body)
            mock_write.assert_called_with(
                json.dumps([{"level": "TITLE", "text": "My Title"}], indent=2)
            )

    def test_insert_markdown(self):
        """Test insert markdown."""
        self.mock_doc_instance.get_at_index.return_value = 10

        self.cli.command = "insert"
        self.cli.at_index = 10
        self.cli.plaintext = False  # Markdown

        with patch("sys.stdin.read", return_value="# Heading"):
            self.cli.run()

        self.mock_doc_instance.insert_markdown_at.assert_called_with(
            10, "# Heading", ensure_newline=False
        )

    def test_determine_insert_index_section_start(self):
        """Test _determine_insert_index with section_start."""
        self.cli.section_start = True
        mock_section = MagicMock()
        mock_section.end = 50

        index = self.cli._determine_insert_index(
            self.mock_doc_instance, mock_section
        )
        self.assertEqual(index, 50)

    def test_determine_insert_index_section_start_missing_section(self):
        """Test _determine_insert_index with section_start but no section."""
        self.cli.section_start = True
        with self.assertRaises(docs_cli.cli_base.UsageException):
            self.cli._determine_insert_index(self.mock_doc_instance, None)

    def test_determine_insert_index_section_end(self):
        """Test _determine_insert_index with section_end."""
        self.cli.section_end = True
        mock_section = MagicMock()
        mock_section.subsections_end = 100

        index = self.cli._determine_insert_index(
            self.mock_doc_instance, mock_section
        )
        self.assertEqual(index, 100)

    def test_determine_insert_index_section_replace_text(self):
        """Test _determine_insert_index with section_replace on text."""
        self.cli.section_replace = True
        mock_section = MagicMock()
        mock_section.level = "text"
        mock_section.start = 10
        mock_section.end = 20

        index = self.cli._determine_insert_index(
            self.mock_doc_instance, mock_section
        )
        self.assertEqual(index, 10)
        self.mock_doc_instance.delete_range.assert_called_with(10, 20)

    def test_determine_insert_index_section_replace_heading(self):
        """Test _determine_insert_index with section_replace on heading."""
        self.cli.section_replace = True
        mock_section = MagicMock()
        mock_section.level = "HEADING_1"
        mock_section.end = 30
        mock_section.subsections_end = 60

        index = self.cli._determine_insert_index(
            self.mock_doc_instance, mock_section
        )
        self.assertEqual(index, 30)
        self.mock_doc_instance.delete_range.assert_called_with(30, 60)

    def test_determine_insert_index_section_replace_dry_run(self):
        """Test _determine_insert_index with section_replace in dry_run."""
        self.cli.section_replace = True
        self.cli.dry_run = True
        mock_section = MagicMock()
        mock_section.level = "text"
        mock_section.start = 10
        mock_section.end = 20

        with patch.object(self.cli, "_log_dry_run") as mock_log:
            index = self.cli._determine_insert_index(
                self.mock_doc_instance, mock_section
            )
            self.assertEqual(index, 10)
            self.mock_doc_instance.delete_range.assert_not_called()
            mock_log.assert_called()

    def test_determine_insert_index_at_start(self):
        """Test _determine_insert_index with at_start."""
        self.cli.at_start = True
        self.mock_doc_instance.get_start.return_value = 1

        index = self.cli._determine_insert_index(self.mock_doc_instance, None)
        self.assertEqual(index, 1)

    def test_determine_insert_index_at_end(self):
        """Test _determine_insert_index with at_end."""
        self.cli.at_end = True
        self.mock_doc_instance.get_end.return_value = 99

        index = self.cli._determine_insert_index(self.mock_doc_instance, None)
        self.assertEqual(index, 99)

    def test_determine_insert_index_at_index(self):
        """Test _determine_insert_index with at_index."""
        self.cli.at_index = 42

        index = self.cli._determine_insert_index(self.mock_doc_instance, None)
        self.assertEqual(index, 42)

    def test_determine_insert_index_default(self):
        """Test _determine_insert_index default behavior."""
        self.mock_doc_instance.get_start.return_value = 1
        index = self.cli._determine_insert_index(self.mock_doc_instance, None)
        self.assertEqual(index, 1)
