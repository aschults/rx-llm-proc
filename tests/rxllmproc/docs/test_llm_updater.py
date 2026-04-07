# pyright: reportPrivateUsage=false
"""Tests for LLM updater."""

from typing import Any, cast
import unittest
from unittest import mock
import reactivex as rx
from rxllmproc.docs import llm_updater
from rxllmproc.docs import docs_model
from rxllmproc.docs import operators as doc_ops
from rxllmproc.llm import api as llm_api


class TestDocUpdater(unittest.TestCase):
    """Test the DocUpdater class."""

    def setUp(self):
        self.mock_doc = mock.Mock(spec=docs_model.Document)
        self.mock_doc.content = mock.Mock()
        self.mock_doc.content.sections = []
        self.mock_doc.get_end.return_value = 100

        # Ensure the mock passes isinstance check
        self.mock_llm = mock.Mock(spec=llm_api.LlmBase)
        self.updater = llm_updater.DocUpdater(
            self.mock_doc, "instructions", self.mock_llm
        )

    def test_init_adds_tools(self):
        """Test that tools are added to the LLM."""
        self.mock_llm.add_function.assert_called()
        call_args_list = self.mock_llm.add_function.call_args_list
        tool_names = [c[0][0].name for c in call_args_list]
        self.assertIn("get_sections", tool_names)
        self.assertIn("get_doc_bounds", tool_names)

    def test_generate(self):
        """Test generating edits."""
        instructions = llm_updater.UpdateInstructions(
            inserts=[doc_ops.InsertOperation(index=1, content="foo")],
            deletes=[doc_ops.DeleteOperation(start=5, end=10)],
        )
        self.mock_llm.query_json_object.return_value = instructions

        ops = self.updater.generate(some_var="value")

        self.assertEqual(len(ops), 2)
        # Deletes are added first in generate()
        self.assertIsInstance(ops[0], doc_ops.DeleteOperation)
        self.assertIsInstance(ops[1], doc_ops.InsertOperation)

        self.mock_llm.query_json_object.assert_called_once()
        call_args = self.mock_llm.query_json_object.call_args
        self.assertEqual(call_args[0][0], llm_updater.UpdateInstructions)
        prompt = call_args[0][1]
        # The prompt is rendered from _GENERIC_UPDATE_PROMPT
        self.assertIn("instructions", prompt)

    def test_tools_implementation(self):
        """Test the implementation of the tools."""
        # Retrieve get_sections function
        get_sections_tool = llm_updater._make_get_sections(self.mock_doc)

        # Mock document content for get_sections
        mock_section = mock.Mock()
        mock_section.level = "text"
        mock_section.start = 10
        mock_section.end = 20
        mock_section.text = "Sec1"
        mock_section.subsections = []
        self.mock_doc.content.sections = [mock_section]

        result = get_sections_tool.function(cast(Any, None))
        expected = {"text_start": 10, "text_end": 20, "text": "Sec1"}
        self.assertEqual(result, {'sections_desc': [expected]})

        # Retrieve get_doc_bounds function
        get_bounds_tool = llm_updater._make_get_doc_bounds(self.mock_doc)
        self.mock_doc.get_start.return_value = 1
        self.mock_doc.get_end.return_value = 100

        result = get_bounds_tool.function(cast(Any, None))
        self.assertEqual(result, {'start_index': 1, 'end_index': 100})


class TestItemsEditGenerator(unittest.TestCase):
    """Test the LlmEditGenerator class."""

    def setUp(self):
        self.mock_doc = mock.Mock(spec=docs_model.Document)
        self.mock_doc.content = mock.Mock()
        self.mock_doc.content.sections = []
        self.mock_doc.get_end.return_value = 100
        self.mock_llm = mock.Mock(spec=llm_api.LlmBase)
        # Mock content for get_sections which is called in generate
        self.mock_doc.content.sections = []
        self.generator = llm_updater.ItemsEditGenerator(
            self.mock_doc, "placement", self.mock_llm
        )

    def test_generate(self):
        """Test generating edits from items."""
        instructions = llm_updater.UpdateInstructions(
            inserts=[
                doc_ops.InsertOperation(
                    index=1, content="foo", origin_ids=["id1"]
                )
            ],
            deletes=[],
        )
        self.mock_llm.query_json_object.return_value = instructions

        items = [
            llm_updater.UpdateItem(
                origin_id="id1", original_data={"a": 1}, rendered_markdown="md"
            )
        ]

        ops = self.generator.generate(items)

        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0].origin_ids, ["id1"])

        call_args = self.mock_llm.query_json_object.call_args
        prompt = call_args[0][1]
        self.assertIn('"origin_id": "id1"', prompt)
        self.assertIn('"markdown": "md"', prompt)

    def test_generate_missing_ids_warning(self):
        """Test warning when origin IDs are missing."""
        instructions = llm_updater.UpdateInstructions(
            inserts=[
                doc_ops.InsertOperation(
                    index=1, content="foo", origin_ids=["other"]
                )
            ],
            deletes=[],
        )
        self.mock_llm.query_json_object.return_value = instructions

        items = [
            llm_updater.UpdateItem(
                origin_id="id1", original_data={}, rendered_markdown="md"
            )
        ]

        with self.assertLogs(level='WARNING') as cm:
            self.generator.generate(items)
            self.assertTrue(any("id1" in o for o in cm.output))


class TestGenerateEditsOperator(unittest.TestCase):
    """Test the generate_edits operator."""

    def setUp(self):
        self.mock_doc = mock.Mock(spec=docs_model.Document)
        self.mock_doc.content = mock.Mock()
        self.mock_doc.content.sections = []
        self.mock_doc.get_end.return_value = 100
        self.mock_llm = mock.Mock(spec=llm_api.LlmBase)

    def test_operator(self):
        """Test the operator flow."""
        instructions = llm_updater.UpdateInstructions(
            inserts=[doc_ops.InsertOperation(index=1, content="foo")],
            deletes=[],
        )
        self.mock_llm.query_json_object.return_value = instructions

        items = [
            llm_updater.UpdateItem(
                origin_id="id1", original_data={}, rendered_markdown="md"
            )
        ]

        source = rx.from_iterable(items)
        results: list[doc_ops.EditOperation] = []

        op = llm_updater.generate_edits(
            self.mock_doc, "instr", self.mock_llm, batch_size=1
        )
        source.pipe(op).subscribe(
            on_next=results.append, on_error=lambda e: self.fail(f"Error: {e}")
        )

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], doc_ops.InsertOperation)
