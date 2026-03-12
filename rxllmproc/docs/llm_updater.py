"""LLM-based document updater."""

import dataclasses
import json
import logging
from typing import Any, Callable

import reactivex as rx
from reactivex import operators as ops

from rxllmproc.core.infra import utilities
from rxllmproc.docs import docs_model
from rxllmproc.docs import operators as doc_ops
from rxllmproc.llm import commons as llm_commons
from rxllmproc.text_processing import jinja_processing

_GENERIC_UPDATE_PROMPT = """
## Goal

You are an agent managing the content of a a Google Doc. Your task is to generate update
operations (inserts and deletes) to edit the Google Doc based on the the instructions
below.

## Edit Instructions

{{edit_instructions | render}}

## Tools

To find the indices to modify the document, the following tools are available:

- `get_sections`: Returns a hierarchical representation of all headings and paragraph texts
  including their start and end indices. The sections structure contains field `level`
  describing the heading level, analogous to the level to use in markdown, e.g. level HEADING_2
  equating to HTML H2.

  This can help when you need to insert text relative to a specific heading in the doc.
  Note that the `text` in the heading object represents the actual title, while the `end`
  index represents the end of the entire section, including all sub section titles and paragraphs.
  Accordingly, when inserting "directly after the heading", use the start of the first subsection
  as starting point if available. If no subsections are available, the `end` index actually represents
  the end of the heading, so adding text there will work in this case.

- `get_doc_bounds`: Returns the start and end indices of the entire document.
  This can be useful for inserting content at the very beginning or end of the document.
  The `start_index` is the index before the first valid character position as there is a "hidden"
  newline at the beginning, and `end_index` is the character position after the last valid
  character.

## Result

Generate a JSON structure that containing the edit operations with the following structure:

```json
{
  "deletes": [
    {
      # Delete the doc's content from 5 to 11 (i.e. excluding the end index char)
      "start": 5,
      "end": 12
    },
    ...
  ]
  "inserts": [
    {
      # Insert at the start of the document.
      "index": 1,
      "content": "Hello World\\n"
    },
    ...
  ],
}
```

Details:
- Indices, i.e. `start` and `end` are offsets in the google doc, where the start of
  the document is 1 (not 0).
- The `end` index (for edit operations and returned by tools) always refers to the
  character *after* the last character in scope.
- To insert at the end of the document, point to the char *before* the end of the
  document.
"""


@dataclasses.dataclass
class UpdateItem:
    """Item to be processed by the LLM."""

    origin_id: str
    original_data: Any
    rendered_markdown: str


@dataclasses.dataclass
class UpdateInstructions:
    """List of update operations to perform on the document."""

    error: str = dataclasses.field(
        default="",
        metadata={
            "description": (
                "Error message. Add if the instructions can't be executed. "
                "If an error is present, no other fields will be processed."
            )
        },
    )

    inserts: list[doc_ops.InsertOperation] = dataclasses.field(
        default_factory=lambda: [],
        metadata={"description": "List of insert operations."},
    )
    deletes: list[doc_ops.DeleteOperation] = dataclasses.field(
        default_factory=lambda: [],
        metadata={"description": "List of delete operations."},
    )


_GET_SECTIONS_DESCRIPTION = """
Args:
- `with_texts`: If true, include section texts, not only titles.


Returns a list of all sections in the document, including their content and metadata.

Sections can be of two flavors, with the following attributes:

1) Text paragraph sections, representing the (non-title) text content of the section:
- `text_start`: The start index of the section in the document.
- `text_end`: The end index of the section in the document.
- `text`: The raw text content of the section.

2) Heading sections, representing section titles:
- `level`: The heading level of the section as in the Google Doc, e.g. `HEADING_1` for HTML H1.
- `title`: The raw text title of the section at specified level, i.e. without any formatting.
  NOTE: This does NOT include paragraph texts.
- `title_start`: The start index of the section title in the document.
  Note that indices in Google docs are 1 based.
- `title_end`: The end index of the section title in the document.
- `content_start`: The start index of the section content in the document.
  Note: content_start is immediately after the section title.
  Section content may be sections with titles below the current heading level or plain text
  paragraphs.
- `content_end`: The end index of the section content in the document.
- `heading_id`: The unique ID of the heading as it is used in the Google Doc.
- `subsections`: List of subsections of the section.
  The list can contain sections of a lower heading level, e.g. a section of `HEADING_1` may
  have subsections of `HEADING_2`, `HEADING_3`, etc. as well as `text` level sections.
  This allows to hierarchically determine the start and end points of all section titles and
  their content, e.g. the `end` index of a section with level `HEADING_2` will be the index
  before the start of the next `HEADING_2`, `HEADING_1` section, or the end of the document.
"""

_GET_SECTION_PARAM_WITH_TEXT = """
If set to false, only includes title sections, not the text paragraphs.
This allows to only get titles, if you are not interested in the actual text content.
default: True
"""


def _section2dict(
    section: docs_model.Section, with_texts: bool = True
) -> dict[str, Any]:
    subsections = [
        _section2dict(sub, with_texts)
        for sub in section.subsections
        if with_texts or sub.level != "text"
    ]
    if section.level == "text":
        result = {
            "text_start": section.start,
            "text_end": section.end,
            "text": section.text,
        }
    else:
        result = {
            "level": section.level,
            "title": section.text,
            "title_start": section.start,
            "title_end": section.end,
            "content_start": section.subsections_start,
            "content_end": section.subsections_end,
            "heading_id": section.heading_id,
            "subsections": subsections,
        }
    return result


def _make_get_sections(document: docs_model.Document):

    def _callback(*args: Any, with_texts: bool = True, **kwargs: Any) -> Any:
        if args:
            logging.warning(
                'get_sections LLM function called with args %s', args
            )
        if kwargs:
            logging.warning(
                'get_sections LLM function called with kwargs %s', kwargs
            )
        sections_desc = [
            _section2dict(section, with_texts)
            for section in document.content.sections
        ]

        return {'sections_desc': sections_desc}

    return llm_commons.BasicLlmFunction(
        name="get_sections",
        description=_GET_SECTIONS_DESCRIPTION,
        callback=_callback,
        with_texts={
            "description": _GET_SECTION_PARAM_WITH_TEXT,
            "type": "boolean",
        },
    )


def _make_get_doc_bounds(document: docs_model.Document):

    def _callback() -> Any:
        return {
            'start_index': document.get_start(),
            'end_index': document.get_end(),
        }

    return llm_commons.BasicLlmFunction(
        callback=_callback,
        name="get_doc_bounds",
        description=_GET_SECTIONS_DESCRIPTION,
    )


class DocUpdater:
    """Generic class to modify docs using LLM."""

    def __init__(
        self,
        document: docs_model.Document,
        edit_instructions: str,
        llm: llm_commons.LlmBase | str | None = None,
    ) -> None:
        """Initialize the generic updater.

        Args:
            document: The document model to update.
            edit_instructions: The prompt template/instructions.
            llm: Optional LLM instance.
        """
        self.document = document
        self.template = jinja_processing.JinjaProcessing()
        self.template.set_template(_GENERIC_UPDATE_PROMPT)
        self.template.add_global("edit_instructions", edit_instructions)
        self.template.add_global("document", document)

        if isinstance(llm, llm_commons.LlmBase):
            self.llm = llm
        elif isinstance(llm, str):
            self.llm = llm_commons.LlmModelFactory.shared_instance().create(llm)
        else:
            self.llm = llm_commons.LlmModelFactory.shared_instance().create()

        self.llm.add_function(_make_get_sections(self.document))
        self.llm.add_function(_make_get_doc_bounds(self.document))

    def _correct_insert_offsets(
        self, insert_operation: doc_ops.InsertOperation
    ) -> doc_ops.InsertOperation:
        if insert_operation.index > self.document.get_end() + 3:
            raise ValueError(
                f'Insert index far beyond document end: {insert_operation.index}.'
            )
        if insert_operation.index < -3:
            raise ValueError(
                f'Insert index far before document start: {insert_operation.index}.'
            )

        if insert_operation.index > self.document.get_end() - 1:
            insert_operation.index = self.document.get_end() - 1
        if insert_operation.index < 1:
            insert_operation.index = 1
        return insert_operation

    def _correct_delete_offsets(
        self, delete_operation: doc_ops.DeleteOperation
    ) -> doc_ops.DeleteOperation:
        if delete_operation.start > self.document.get_end() + 3:
            raise ValueError(
                f'Delete start index far beyond document end: {delete_operation.start}.'
            )
        if delete_operation.end > self.document.get_end() + 3:
            raise ValueError(
                f'Delete end index far beyond document end: {delete_operation.end}.'
            )
        if delete_operation.start < -3:
            raise ValueError(
                f'Delete start index far before document start: {delete_operation.start}.'
            )
        if delete_operation.end < -3:
            raise ValueError(
                f'Delete end index far before document start: {delete_operation.end}.'
            )

        if delete_operation.start > self.document.get_end() - 1:
            delete_operation.start = self.document.get_end() - 1
        if delete_operation.end > self.document.get_end() - 1:
            delete_operation.end = self.document.get_end() - 1
        if delete_operation.start < 1:
            delete_operation.start = 1
        if delete_operation.end < 1:
            delete_operation.end = 1
        if delete_operation.start > delete_operation.end:
            delete_operation.start, delete_operation.end = (
                delete_operation.end,
                delete_operation.start,
            )
        return delete_operation

    def generate(self, **kwargs: Any) -> list[doc_ops.EditOperation]:
        """Generate update operations."""
        prompt = self.template.render(**kwargs)

        instructions = self.llm.query_json_object(UpdateInstructions, prompt)

        if instructions.error:
            raise ValueError(
                f"LLM Updater unable to execute: {instructions.error}"
            )

        operations: list[doc_ops.EditOperation] = []
        operations.extend(
            self._correct_delete_offsets(op) for op in instructions.deletes
        )
        operations.extend(
            self._correct_insert_offsets(op) for op in instructions.inserts
        )

        logging.info('Got edits %s', repr(operations))

        return operations


_EDIT_INSTRUCTIONS = """

### Item Placement instructions

{{placement_instructions | render}}

### Data

Below the items to process, including the  original Data and the pre-rendered
markdown to be inserted.

```json
{{items_json}}
```

### Consistency checking

Origin IDs are used to track the reason for an edit (e.g. a todo item)
across to the actual edit in the document. Instructions for Origin IDs are accordingly:
1. Carry over the `origin_id` from the input items as elements of `origin_ids`
   in the generated operations.
2. If an operation combines edits from multiple items, add all `origin_id`s as elements to `origin_ids`
   in the generated operations.
3. If an operation is not related to a specific item, leave the operation's `origin_ids` empty.
"""


class ItemsEditGenerator:
    """Class to generate document edits from individual UpdateItems."""

    def __init__(
        self,
        document: docs_model.Document,
        placement_instructions: str,
        llm: llm_commons.LlmBase | str | None = None,
    ) -> None:
        """Initialize the updater.

        Args:
            document: The document model to update.
            placement_instructions: User text instructions.
            llm: Optional LLM instance. If not provided, one will be created.
        """
        self.updater = DocUpdater(document, _EDIT_INSTRUCTIONS, llm)
        self.updater.template.add_global(
            "placement_instructions", placement_instructions
        )
        self.document = document

    def generate(self, items: list[UpdateItem]) -> list[doc_ops.EditOperation]:
        """Generate update operations."""
        items_list: list[dict[str, Any]] = []
        for item in items:
            data = item.original_data
            data = utilities.asdict(data)

            items_list.append(
                {
                    "origin_id": item.origin_id,
                    "data": data,
                    "markdown": item.rendered_markdown,
                }
            )

        operations = self.updater.generate(
            items_json=json.dumps(items_list, indent=2),
        )

        # Cross-reference generated operations with input items
        input_ids = {item.origin_id for item in items}
        processed_ids: set[str] = set()
        for op in operations:
            processed_ids.update(op.origin_ids)

        missing = input_ids - processed_ids
        if missing:
            logging.warning(
                "The following items were not processed by LLM: %s", missing
            )

        return operations


def generate_edits(
    document: docs_model.Document,
    instructions: str,
    llm: llm_commons.LlmBase | str | None = None,
    batch_size: int = 5,
) -> Callable[
    [rx.Observable[UpdateItem]], rx.Observable[doc_ops.EditOperation]
]:
    """Process UpdateItems in batches as using LLM Rx operator."""

    def _operator(
        source: rx.Observable[UpdateItem],
    ) -> rx.Observable[doc_ops.EditOperation]:
        generator = ItemsEditGenerator(document, instructions, llm)

        def _process_batch(
            items: list[UpdateItem],
        ) -> rx.Observable[doc_ops.EditOperation]:
            if not items:
                return rx.empty()
            try:
                ops_list = generator.generate(items)
                return rx.from_iterable(ops_list)
            except Exception as e:
                logging.exception("Error processing batch")
                return rx.throw(e)

        return source.pipe(
            ops.buffer_with_count(batch_size),
            ops.flat_map(_process_batch),
        )

    return _operator
