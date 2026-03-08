"""Types for the docs app."""

import re
from typing import Any
import dataclasses


@dataclasses.dataclass(kw_only=True)
class DocsPipelineConfig:
    """Configuration for Docs pipelines."""

    todo_template: str | None = dataclasses.field(
        default=None,
        metadata={'expand_file': True, 'flag_name': 'docs_todo_template'},
    )
    insertion_instructions: str | None = dataclasses.field(
        default=None,
        metadata={
            'expand_file': True,
            'flag_name': 'docs_insertion_instructions',
        },
    )

    define: dict[str, Any] | None = dataclasses.field(
        default=None,
        metadata={
            'expand_dict': True,
            'expand_values': 'expand_args_typed',
        },
    )

    @property
    def template_parameters(self) -> dict[str, Any]:
        """Get template parameters."""
        return (self.define or {}).copy()

    priority_re: str | re.Pattern[str] = r'.*'
    batch_size: int = dataclasses.field(
        default=5,
        metadata={'flag_name': 'docs_batch_size'},
    )

    force_all: bool = False


@dataclasses.dataclass(kw_only=True)
class DocsConfig(DocsPipelineConfig):
    """Configuration for Docs processing."""

    todo_doc_id: str | None = None
    interval: int = 60
