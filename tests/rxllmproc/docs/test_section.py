"""Tests for the Section class."""

import unittest
import re

import sample_doc
import sample_doc2

from rxllmproc.docs import section
from rxllmproc.docs import docs_text
from rxllmproc.docs import types as docs_types


class TestSection(unittest.TestCase):
    """Test cases for Section."""

    def _get_text_from_body(self, body: docs_types.Body) -> str:
        """Gets the document text from the body elements."""
        renderer = docs_text.TextRenderer()
        renderer.render_body(body)
        return renderer.as_string()

    def test_next_heading_level(self):
        """Test next_heading_level method."""
        self.assertEqual(
            section.Section.next_heading_level("TITLE"), "HEADING_1"
        )
        self.assertEqual(
            section.Section.next_heading_level("HEADING_1"), "HEADING_2"
        )
        self.assertEqual(
            section.Section.next_heading_level("HEADING_6"), "text"
        )
        with self.assertRaises(ValueError):
            section.Section.next_heading_level("INVALID")

    def test_get_heading(self):
        """Test get_heading method."""
        el = docs_types.StructuralElement(
            paragraph=docs_types.Paragraph(
                elements=[],
                paragraphStyle=docs_types.ParagraphStyle(
                    namedStyleType="HEADING_1"
                ),
            )
        )
        self.assertEqual(section.Section.get_heading(el), "HEADING_1")

        el_normal = docs_types.StructuralElement(
            paragraph=docs_types.Paragraph(
                elements=[],
                paragraphStyle=docs_types.ParagraphStyle(
                    namedStyleType="NORMAL_TEXT"
                ),
            )
        )
        self.assertEqual(section.Section.get_heading(el_normal), "NORMAL_TEXT")

        el_none = docs_types.StructuralElement()
        self.assertIsNone(section.Section.get_heading(el_none))

    def test_section_properties(self):
        """Test start and end properties."""
        el = docs_types.StructuralElement(startIndex=10, endIndex=20)
        sec = section.Section(level="HEADING_1", elements=[el])
        self.assertEqual(sec.start, 10)
        self.assertEqual(sec.end, 20)

        sec_empty = section.Section(level="HEADING_1", elements=[])
        self.assertEqual(sec_empty.start, 0)
        self.assertEqual(sec_empty.end, 0)

    def test_create_from_sample_doc(self):
        """Test create_from using the sample document structure."""
        doc_text = self._get_text_from_body(sample_doc.DOC_BODY)
        sections = section.Section.create_from(
            sample_doc.DOC_BODY.content, doc_text
        )
        self.maxDiff = None
        self.assertEqual(
            [section_.as_dict() for section_ in sections],
            sample_doc.SAMPLE_DOC_JSON,
        )

    def test_create_from_simple_structure(self):
        """Test create_from with a manually constructed simple structure."""
        el1 = docs_types.StructuralElement(
            startIndex=1,
            endIndex=5,
            paragraph=docs_types.Paragraph(
                elements=[
                    docs_types.ParagraphElement(
                        startIndex=1,
                        endIndex=5,
                        textRun=docs_types.TextRun(content="H1a\n"),
                    )
                ],
                paragraphStyle=docs_types.ParagraphStyle(
                    namedStyleType="HEADING_1"
                ),
            ),
        )
        el2 = docs_types.StructuralElement(
            startIndex=5,
            endIndex=10,
            paragraph=docs_types.Paragraph(
                elements=[
                    docs_types.ParagraphElement(
                        startIndex=5,
                        endIndex=10,
                        textRun=docs_types.TextRun(content="Text\n"),
                    )
                ],
                paragraphStyle=docs_types.ParagraphStyle(
                    namedStyleType="NORMAL_TEXT"
                ),
            ),
        )

        body = [el1, el2]
        text = " H1a\nText\n"

        sections = section.Section.create_from(body, text, level="HEADING_1")
        as_struct = [section_.as_dict() for section_ in sections]
        self.assertEqual(
            as_struct,
            [
                {
                    'level': 'HEADING_1',
                    'text': 'H1a\n',
                    'start': 1,
                    'end': 5,
                    'heading_id': None,
                    'subsections': [
                        {
                            'level': 'text',
                            'text': 'Text\n',
                            'start': 5,
                            'end': 10,
                            'heading_id': None,
                            'subsections': [],
                        }
                    ],
                }
            ],
        )

    def test_create_from_sample_doc2(self):
        """Test create_from using sample_doc2."""
        doc_text = self._get_text_from_body(sample_doc2.DOC_BODY)
        sections = section.Section.create_from(
            sample_doc2.DOC_BODY.content, doc_text
        )

        self.maxDiff = None
        self.assertEqual(
            [section_.as_dict() for section_ in sections],
            sample_doc2.SAMPLE_DOC_JSON,
        )

    def test_find_sections(self):
        """Test find_section method."""
        doc_text = self._get_text_from_body(sample_doc.DOC_BODY)
        sections = section.Section.create_from(
            sample_doc.DOC_BODY.content, doc_text
        )

        # Test finding by text
        found = section.Section.find_sections(
            sections, text_pattern="Heading3c"
        )
        self.assertIn(found[0].heading_id, "h.s94p0purx9bu")

        # Test not found
        self.assertEqual(
            section.Section.find_sections(sections, "Non Existent Section"), []
        )

        found = section.Section.find_sections(
            sections, text_pattern="Heading3c", heading_pattern="HEADING_3"
        )
        self.assertIn(found[0].heading_id, "h.s94p0purx9bu")

        # Test finding by text and heading regex
        found = section.Section.find_sections(
            sections,
            text_pattern=re.compile(r"Heading.[b-c]"),
            heading_pattern="HEAD..._3",
        )
        print([s.text for s in found])
        self.assertEqual(
            [s.text for s in found], ['Heading3b\n', 'Heading3c\n']
        )
