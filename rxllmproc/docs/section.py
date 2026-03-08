"""Document section model for Google Docs."""

import dataclasses
from typing import Any
import re

from rxllmproc.docs import types as docs_types


@dataclasses.dataclass(kw_only=True)
class Section:
    """A document section to be used ease of searching."""

    HEADING_STYLES = [
        "TITLE",
        "HEADING_1",
        "HEADING_2",
        "HEADING_3",
        "HEADING_4",
        "HEADING_5",
        "HEADING_6",
        "text",
    ]

    # Heading level, Regular content if None
    level: str | None
    elements: list[docs_types.StructuralElement]
    subsections: list["Section"] = dataclasses.field(default_factory=lambda: [])
    text: str = "<not set>"

    @property
    def start(self) -> int:
        """Returns the start index of the section."""
        if not self.elements or not self.elements[0]:
            return 0
        return self.elements[0].startIndex or 0

    @property
    def end(self) -> int:
        """Returns the end index of the section."""
        if not self.elements or not self.elements[-1]:
            return 0
        end_index = self.elements[-1].endIndex
        if end_index is None:
            raise ValueError("End index is None")
        return end_index

    @property
    def subsections_start(self) -> int:
        """Returns the start index of the section including all subsections."""
        if not self.subsections:
            return self.end
        # The last subsection should be the furthest point
        return self.subsections[0].subsections_start

    @property
    def subsections_end(self) -> int:
        """Returns the end index of the section including all subsections."""
        if not self.subsections:
            return self.end
        # The last subsection should be the furthest point
        return self.subsections[-1].subsections_end

    def _set_text_from(self, doc_text: str):
        self.text = doc_text[self.start : self.end]

    @property
    def heading_id(self) -> str | None:
        """Returns the heading ID of the section."""
        if not self.elements or not self.elements[0]:
            return None
        first_element = self.elements[0]
        if not first_element.paragraph:
            return None
        if not first_element.paragraph.paragraphStyle:
            return None
        return first_element.paragraph.paragraphStyle.headingId

    @classmethod
    def get_heading(cls, element: docs_types.StructuralElement) -> str | None:
        """Gets the heading level from a structural element."""
        if not element.paragraph:
            return None
        if not element.paragraph.paragraphStyle:
            return None
        if not element.paragraph.paragraphStyle.namedStyleType:
            return None
        return element.paragraph.paragraphStyle.namedStyleType

    @classmethod
    def next_heading_level(cls, level: str) -> str:
        """Returns the next heading level.

        Args:
            level: The current heading level.

        Returns:
            The next heading level.

        Raises:
            ValueError: If the current level is not a valid heading level or
                if it is the highest level (`text`) already.
        """
        current_index = cls.HEADING_STYLES.index(level)
        if current_index < 0:
            raise ValueError(f"Invalid heading level: {level}")
        if current_index == len(cls.HEADING_STYLES) - 1:
            raise ValueError("We should never try to go below text level.")
        return cls.HEADING_STYLES[current_index + 1]

    @classmethod
    def create_from(
        cls,
        content: list[docs_types.StructuralElement],
        doc_text: str,
        level: str = "TITLE",
    ) -> list["Section"]:
        """Creates a section from a list of structural elements."""
        # Down to text level, so just add and return.
        if level == "text":
            new_section = Section(
                level=level,
                elements=content.copy(),
            )
            new_section._set_text_from(doc_text)
            return [new_section]

        next_level = cls.next_heading_level(level)

        # Initialize with empty item to capture any elements before the first
        # heading.
        result: list["Section"] = [
            Section(
                level=level,
                elements=[],
            )
        ]

        # Stores all structural elements of the current section.
        subsection_elements: list[docs_types.StructuralElement] = []

        for element in content:
            named_style = cls.get_heading(element)
            if named_style == level:
                result[-1].subsections = cls.create_from(
                    subsection_elements,
                    doc_text,
                    next_level,
                )

                # Start a new section, so reset the elements inside of it
                subsection_elements = []
                new_section = Section(
                    level=level,
                    elements=[element],
                )
                result.append(new_section)
            else:
                subsection_elements.append(element)
        if subsection_elements:
            result[-1].subsections = cls.create_from(
                subsection_elements,
                doc_text,
                next_level,
            )

        if not result[0].elements:
            # We didn't find any heading of the current level at the start
            # of the content

            first_subsections = result[0].subsections

            # We'll replace the first item anyway, so let't remove it.
            result.pop(0)

            # We found higher level headings or paragraph text, so directly
            # add it in the result.
            if first_subsections:
                result = first_subsections + result

        for section in result:
            section._set_text_from(doc_text)

        return result

    def as_dict(self, with_elements: bool = False) -> Any:
        """Returns a dictionary representation of the section."""
        result = {
            "level": self.level,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "heading_id": self.heading_id,
            "subsections": [
                section_.as_dict() for section_ in self.subsections
            ],
        }
        if with_elements:
            result["elements"] = self.elements
        return result

    @classmethod
    def find_sections(
        cls,
        sections: list["Section"],
        text_pattern: str | re.Pattern[str] | None = None,
        heading_pattern: str | re.Pattern[str] | None = None,
        heading_id: str | None = None,
    ) -> "list[Section]":
        """Finds sections by regex match on their heading texts, recursively.

        Args:
            sections: The sections to search.
            pattern: The regex pattern to match.
                The match is performed against the section's text.
            heading_pattern: regex to match against the heading type.
            heading_id: The heading ID to match.

        Returns:
            A list of sections that match the pattern.
        """
        result: list[Section] = []

        matchall = re.compile(".*")

        text_regex = matchall
        if isinstance(text_pattern, str):
            text_regex = re.compile(text_pattern, re.S)
        if isinstance(text_pattern, re.Pattern):
            text_regex = text_pattern

        heading_regex = matchall
        if isinstance(heading_pattern, str):
            heading_regex = re.compile(heading_pattern, re.S)
        elif isinstance(heading_pattern, re.Pattern):
            heading_regex = heading_pattern

        for section_ in sections:
            match = True
            if heading_id:
                match = section_.heading_id == heading_id

            match = match and heading_regex.search(section_.level or "")
            match = match and text_regex.search(section_.text)

            if match:
                result.append(section_)
            else:
                # Check subsections
                subsection_result = cls.find_sections(
                    section_.subsections,
                    text_pattern,
                    heading_pattern,
                    heading_id,
                )
                result.extend(subsection_result)

        return result
