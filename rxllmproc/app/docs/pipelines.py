"""Reactive pipeline for Google Docs processing."""

import logging
import re
from typing import Any, Callable
from abc import ABC, abstractmethod

import reactivex as rx
import sqlalchemy
from reactivex import operators as ops

from rxllmproc.docs import llm_updater
from rxllmproc.core.infra import utilities
from rxllmproc.database import api as database
from rxllmproc.database import operators as sql_operators
from rxllmproc.text_processing import jinja_processing
from rxllmproc.docs import operators as docs_operators
from rxllmproc.app import environment as app_environment
from rxllmproc.app.analysis import types as analysis_types
from rxllmproc.docs import docs_model
from rxllmproc.llm import commons as llm_commons
from rxllmproc.app.docs import types as docs_types

_TODO_MARKDOWN_TEMPLATE = """
{{item.priority|prio_emoji}} {{item.title}} [📧]({{item.source_url}})

{%- if item.due_date %}

. 📅 {{item.due_date}}

{% endif -%}
{%- if item.notes %}
\n
. {{item.notes}}\n
{% endif -%}
\n
\n
{%- if item.links and (item.links | length > 0) %}
. **Links**:\n

{%- for link in item.links %}
.. 🔗 [{{ link.title or 'link' }}]({{ link.url | replace(" ", "%20")}})\n\n
{%- endfor %}
{%- endif %}
\n
&nbsp;
\n
\n
"""


def prio_emoji(priority: str) -> str:
    """Get emoji for priority."""
    if not priority:
        return "\u26aa"  # White circle

    priority = priority.lower()

    if priority == "critical":
        return "\U0001f198"  # SOS button
    elif priority == "high":
        return "\U0001f534"  # Red circle
    elif priority == "medium":
        return "\U0001f535"  # Blue circle
    else:
        return "\u26aa"  # White circle


def make_query_dict(item: analysis_types.ActionItem) -> dict[str, Any]:
    """Create a dictionary for the template query."""
    return {
        "item": item,
    }


class MarkdownInserter(ABC):
    """Appends markdown content to a Google Doc."""

    def __init__(
        self,
        document: docs_model.Document,
        config: docs_types.DocsPipelineConfig,
        env: app_environment.RxEnvironment | None = None,
        db: sql_operators.RxDatabase | None = None,
    ) -> None:
        """Create an instance."""
        self.document = document
        self.config = config
        self.processed_placements: set[tuple[str, int | None]] = set()
        self.template = jinja_processing.JinjaProcessing()
        self.template.add_filter("prio_emoji", prio_emoji)
        self.template.set_template(
            config.todo_template or _TODO_MARKDOWN_TEMPLATE
        )
        self.env = env or app_environment.shared().update()
        self.db = db or self.env.db
        self.priority_re = (
            re.compile(config.priority_re, re.IGNORECASE)
            if isinstance(config.priority_re, str)
            else config.priority_re
        )

    def get_placement_ids(self) -> set[tuple[str, int | None]]:
        """Get the set of placement IDs that have already been processed."""
        placement_table = database.t(analysis_types.ActionItemPlacement)
        stmt = sqlalchemy.select(
            placement_table.c.analysis_id,
            placement_table.c.action_number,
        ).where(
            sqlalchemy.and_(
                placement_table.c.placement_container_url == self.document.url,
                placement_table.c.placement_id == '(None)',
            )
        )
        result = self.db.session.execute(stmt).tuples().all()
        return set((str(row[0]), int(row[1])) for row in result)

    def _refresh_processed_placements(self, _: Any) -> None:
        if self.config.force_all:
            self.processed_placements = set()
        else:
            self.processed_placements = self.get_placement_ids()

        logging.debug(
            "Refreshed processed placements: %s",
            self.processed_placements,
        )

    def _is_unprocessed(self, item: analysis_types.ActionItem) -> bool:
        return (
            item.analysis_id is not None
            and (
                item.analysis_id,
                item.action_number,
            )
            not in self.processed_placements
        )

    def _matches_priority(self, item: analysis_types.ActionItem) -> bool:
        return bool(self.priority_re.match(item.priority or ""))

    def _render_item(self, item: analysis_types.ActionItem) -> str:
        return self.template.render(
            item=item, **self.config.template_parameters
        )

    @abstractmethod
    def _generate_edits(
        self,
    ) -> Callable[
        [rx.Observable[analysis_types.ActionItem]],
        rx.Observable[docs_operators.EditOperation],
    ]:
        pass

    def _make_placements(
        self,
        modification_id: str,
    ) -> analysis_types.ActionItemPlacement | None:
        if not modification_id:
            return None
        analysis_id, action_number_str = modification_id.rsplit("|", 1)
        if not analysis_id:
            return None
        try:
            action_number = int(action_number_str)
        except ValueError:
            return None
        return analysis_types.ActionItemPlacement(
            analysis_id=analysis_id,
            action_number=action_number,
            placement_container_url=self.document.url,
            placement_id="(None)",  # Can't find the inserted element again.
        )

    def _add_processed(self, item: analysis_types.ActionItemPlacement) -> None:
        if item.analysis_id is not None:
            self.processed_placements.add(
                (item.analysis_id, item.action_number)
            )

    def _not_none(self, x: Any) -> bool:
        return x is not None

    def __call__(
        self, source: rx.Observable[analysis_types.ActionItem]
    ) -> rx.Observable[analysis_types.ActionItemPlacement]:
        """Build the pipeline."""
        return source.pipe(
            ops.do_action(self._refresh_processed_placements),
            ops.filter(self._is_unprocessed),
            ops.filter(self._matches_priority),
            ops.take(self.config.batch_size),
            self.env.collect("docs_insert / unprocessed action items"),
            self._generate_edits(),
        ).pipe(
            self.env.collect("docs_insert / number of docs edits"),
            docs_operators.apply_batch_edits(self.document),
            ops.map(self._make_placements),
            utilities.remove_none(),
            ops.do_action(self._add_processed),
            self.env.collect("docs_inserts / placed action items"),
            self.env.db.element_transaction().upsert_op(
                analysis_types.ActionItemPlacement
            ),
        )


class MarkdownIndexInserter(MarkdownInserter):
    """Appends markdown at a specific index."""

    def __init__(
        self,
        document: docs_model.Document,
        config: docs_types.DocsPipelineConfig,
        insert_index: int,
    ) -> None:
        """Initialize the MarkdownIndexInserter."""
        super().__init__(document, config)
        self.insert_index = insert_index

    def _make_edit(
        self,
        items: analysis_types.ActionItem,
    ) -> docs_operators.EditOperation:
        return docs_operators.InsertOperation(
            origin_ids=[f"{items.analysis_id}|{items.action_number}"],
            index=self.insert_index,
            content=self._render_item(items),
        )

    def _generate_edits(
        self,
    ) -> Callable[
        [rx.Observable[analysis_types.ActionItem]],
        rx.Observable[docs_operators.EditOperation],
    ]:
        return ops.map(self._make_edit)


class MarkdownLlmInserter(MarkdownInserter):
    """Appends markdown based on LLM evaluation."""

    def __init__(
        self,
        document: docs_model.Document,
        config: docs_types.DocsPipelineConfig,
        llm: llm_commons.LlmBase | str | None = None,
        env: app_environment.RxEnvironment | None = None,
    ) -> None:
        """Initialize the MarkdownLlmInserter."""
        super().__init__(document, config, env=env)
        self.llm = llm or self.env.create_model()

    def _make_update_item(
        self,
        item: analysis_types.ActionItem,
    ) -> llm_updater.UpdateItem:
        return llm_updater.UpdateItem(
            origin_id=f"{item.analysis_id}|{item.action_number}",
            original_data=item,
            rendered_markdown=self._render_item(item),
        )

    def _generate_edits(
        self,
    ) -> Callable[
        [rx.Observable[analysis_types.ActionItem]],
        rx.Observable[docs_operators.EditOperation],
    ]:
        return rx.compose(
            ops.map(self._make_update_item),
            llm_updater.generate_edits(
                self.document,
                self.config.insertion_instructions or "",
                self.llm,
                self.config.batch_size,
            ),
        )
