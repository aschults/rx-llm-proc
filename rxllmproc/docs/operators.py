"""Reactive operators for Google Docs."""

from typing import Callable
import dataclasses
import reactivex as rx
from reactivex import operators as ops
from rxllmproc.docs import docs_model


@dataclasses.dataclass(kw_only=True)
class EditOperation:
    """Base class for edit operations."""

    origin_ids: list[str] = dataclasses.field(
        default_factory=lambda: [],
        metadata={"description": "Unique ID for this modification."},
    )


@dataclasses.dataclass(kw_only=True)
class InsertOperation(EditOperation):
    """Instruction to insert markdown content."""

    index: int = dataclasses.field(
        metadata={"description": "Index to insert at (integer)."}
    )
    content: str = dataclasses.field(
        metadata={"description": "Markdown content to insert."}
    )


@dataclasses.dataclass(kw_only=True)
class DeleteOperation(EditOperation):
    """Instruction to delete a range."""

    start: int = dataclasses.field(
        metadata={"description": "Start index of the range (integer)."}
    )
    end: int = dataclasses.field(
        metadata={"description": "End index of the range (integer)."}
    )


class BatchEditor:
    """Accumulates edits and executes them in correct order."""

    def __init__(self, doc: docs_model.Document):
        """Initialize the BatchEditor."""
        self.doc = doc
        self.ops: list[EditOperation] = []

    def add(self, op: EditOperation):
        """Add an operation to the batch."""
        self.ops.append(op)

    def execute(self) -> list[str]:
        """Execute all operations and return their modification IDs."""

        def sort_key(op: EditOperation):
            """Sort operations descending by index to avoid shifting issues.

            Priority: Delete (1) > Insert (0) at same index.
            """
            if isinstance(op, InsertOperation):
                return (op.index, 0)
            elif isinstance(op, DeleteOperation):
                return (op.start, 1)
            return (-1, -1)

        self.ops.sort(key=sort_key, reverse=True)
        executed_ids: set[str] = set()

        for op in self.ops:
            if isinstance(op, DeleteOperation):
                self.doc.delete_range(op.start, op.end)
            elif isinstance(op, InsertOperation):
                self.doc.insert_markdown_at(op.index, op.content)
            executed_ids.update(op.origin_ids)

        self.ops.clear()
        return list(executed_ids)


def apply_batch_edits(
    doc: docs_model.Document,
) -> Callable[[rx.Observable[EditOperation]], rx.Observable[str]]:
    """Collects all edits and applies them in reverse order of doc offset."""

    def _apply(source: rx.Observable[EditOperation]) -> rx.Observable[str]:
        def _execute(ops_list: list[EditOperation]) -> rx.Observable[str]:
            editor = BatchEditor(doc)
            for op in ops_list:
                editor.add(op)
            return rx.from_iterable(editor.execute())

        return source.pipe(
            ops.to_list(),
            ops.flat_map(_execute),
        )

    return _apply


def insert_markdown(
    doc: docs_model.Document,
    index: int,
    insert_forward: bool = False,
) -> Callable[[rx.Observable[str]], rx.Observable[int]]:
    """Insert markdown content into a Google Doc.

    NOTE: The insertion in on_next is always done at the initial index, so
    multiple on_next calls will insert content at the same position. This results in
    reversed order of content among the requests that are sent.

    See insert_forward to change this behavior.

    Args:
        doc: The document to insert into.
        index: The index position to insert at.
        insert_forward: If true, the index is moved forward after each insertion, putting
        inserted content in order of insertion.

    Returns:
        An operator function that returns the inserted content (passed through).
    """
    index_ = index

    def _do_insert(content: str) -> rx.Observable[int]:
        try:
            nonlocal index_
            index_ = doc.insert_markdown_at(
                index_, content, get_end=insert_forward
            )
            return rx.just(index_)
        except Exception as e:
            return rx.throw(e)

    def _insert_markdown(source: rx.Observable[str]) -> rx.Observable[int]:
        return source.pipe(
            ops.flat_map(_do_insert),
        )

    return _insert_markdown
