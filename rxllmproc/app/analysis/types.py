"""Domain entities and types for analysis."""

import dataclasses
import datetime

import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.ext.orderinglist import ordering_list

from rxllmproc.database import api as database


@dataclasses.dataclass
class Link:
    """Represent a link with a title and a URL."""

    title: str = dataclasses.field(
        metadata={"description": "Title of the link"}
    )
    url: str = dataclasses.field(metadata={"description": "URL of the link"})


@dataclasses.dataclass
class Identifier:
    """Represent an identifier in an email or text."""

    name: str = dataclasses.field(
        metadata={"description": "Name of the identifier"}
    )
    value: str = dataclasses.field(
        metadata={"description": "Value of the identifier"}
    )


@dataclasses.dataclass
class Person:
    """Represent a person in an email or text."""

    name: str = dataclasses.field(
        metadata={"description": "Name of the person"}
    )
    role: str = dataclasses.field(
        metadata={
            "description": "The role of the person in the text, e.g. recipient, sender, collaborator,..."
        }
    )


@dataclasses.dataclass
class ActionItem:
    """Represent an action item in an email or text."""

    analysis_id: str | None = dataclasses.field(
        default=None, metadata={"description": "Analysis ID"}
    )
    action_number: int = dataclasses.field(
        default=0,
        metadata={"description": "Sequence number of the action item"},
    )
    title: str | None = dataclasses.field(
        default=None,
        metadata={
            "description": "one line title or summary of the action item"
        },
    )
    notes: str | None = dataclasses.field(
        default=None,
        metadata={"description": "Detailed notes for the action item"},
    )
    priority: str | None = dataclasses.field(
        default=None,
        metadata={
            "description": "Priority of the action item (e.g., High, Medium, Low)"
        },
    )
    due_date: str | None = dataclasses.field(
        default=None,
        metadata={
            "description": "Due date for the action item in YYYY-MM-DD format"
        },
    )
    links: list[Link] | None = dataclasses.field(
        default=None,
        metadata={
            "description": "List of relevant links, each with 'title' and 'url'"
        },
    )

    @property
    def source_url(self) -> str | None:
        """Get source URL from analysis ID."""
        return f'{self.analysis_id}#{self.action_number}'

    @classmethod
    def _register_entity(cls, registry: sqlalchemy.orm.registry):
        table = sqlalchemy.Table(
            "action_item",
            registry.metadata,
            sqlalchemy.Column(
                "analysis_id",
                sqlalchemy.String,
                primary_key=True,
            ),
            sqlalchemy.Column(
                "action_number", sqlalchemy.Integer, primary_key=True
            ),
            sqlalchemy.Column("title", sqlalchemy.String),
            sqlalchemy.Column("notes", sqlalchemy.String),
            sqlalchemy.Column("priority", sqlalchemy.String),
            sqlalchemy.Column("due_date", sqlalchemy.String),
            sqlalchemy.Column("links", database.DataclassJSONList(Link)),
            sqlalchemy.Column("source_url", sqlalchemy.String),
            sqlalchemy.ForeignKeyConstraint(["analysis_id"], ["analysis.id"]),
        )
        registry.map_imperatively(cls, table)


@dataclasses.dataclass
class ActionItemPlacement:
    """Tracks where an action item has been placed."""

    analysis_id: str | None = dataclasses.field(
        default=None, metadata={"description": "Analysis ID"}
    )
    action_number: int | None = dataclasses.field(
        default=None,
        metadata={"description": "Sequence number of the action item"},
    )
    placement_container_url: str | None = dataclasses.field(
        default=None,
        metadata={
            "description": "Reference to the container in the target system (e.g. Docs URL)"
        },
    )
    placement_id: str | None = dataclasses.field(
        default=None,
        metadata={
            "description": "ID in the target system, i.e. how to find the item within the container"
        },
    )

    @classmethod
    def _register_entity(cls, registry: sqlalchemy.orm.registry):
        table = sqlalchemy.Table(
            "action_item_placement",
            registry.metadata,
            sqlalchemy.Column(
                "analysis_id", sqlalchemy.String, primary_key=True
            ),
            sqlalchemy.Column(
                "action_number", sqlalchemy.Integer, primary_key=True
            ),
            sqlalchemy.Column(
                "placement_container_url", sqlalchemy.String, primary_key=True
            ),
            sqlalchemy.Column(
                "placement_id", sqlalchemy.String, primary_key=True
            ),
            sqlalchemy.ForeignKeyConstraint(
                ["analysis_id", "action_number"],
                ["action_item.analysis_id", "action_item.action_number"],
            ),
        )
        registry.map_imperatively(cls, table)


@dataclasses.dataclass
class Analysis:
    """Store all mail analysis results."""

    id: str | None = dataclasses.field(
        default=None, metadata={"description": "Content Source ID."}
    )
    category: str | None = dataclasses.field(
        default=None,
        metadata={
            "description": "Category of the email, format: 'this_is_a_category'"
        },
    )
    noteworthy_details: list[str] = dataclasses.field(
        default_factory=lambda: [],
        metadata={
            "description": "noteworthy details, bullet list style, one bullet per list item"
        },
    )
    action_items: list[ActionItem] = dataclasses.field(
        default_factory=lambda: [],
        metadata={
            "description": "List of action items extracted from the email"
        },
    )
    people: list[Person] = dataclasses.field(
        default_factory=lambda: [],
        metadata={
            "description": "Key people mentioned in the email and their roles"
        },
    )
    identifiers: list[Identifier] = dataclasses.field(
        default_factory=lambda: [],
        metadata={
            "description": "Key identifiers found in the email (e.g., ticket numbers, project codes, order numbers,...)"
        },
    )

    @classmethod
    def _register_entity(cls, registry: sqlalchemy.orm.registry):
        id_column = sqlalchemy.Column(
            "id",
            sqlalchemy.String,
            sqlalchemy.ForeignKey("source.id"),
            primary_key=True,
        )

        table = sqlalchemy.Table(
            "analysis",
            registry.metadata,
            id_column,
            sqlalchemy.Column("category", sqlalchemy.String),
            sqlalchemy.Column("noteworthy_details", database.StringListJSON),
            sqlalchemy.Column("people", database.DataclassJSONList(Person)),
            sqlalchemy.Column(
                "identifiers", database.DataclassJSONList(Identifier)
            ),
        )
        registry.map_imperatively(
            cls,
            table,
            properties={
                'action_items': sqlalchemy.orm.relationship(
                    "ActionItem",
                    backref='analysis',
                    lazy="selectin",
                    collection_class=ordering_list("action_number"),
                    primaryjoin="foreign(ActionItem.analysis_id) == Analysis.id",
                ),
            },
        )


@dataclasses.dataclass(kw_only=True)
class Source:
    """Base source data."""

    id: str = dataclasses.field(
        metadata={"description": "The unique ID (url) of the content source."}
    )
    created_time: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        metadata={"description": "Time of creation."},
    )
    analysis: Analysis | None = dataclasses.field(
        default=None, metadata={"description": "Analysis of the content"}
    )

    @classmethod
    def _register_entity(cls, registry: sqlalchemy.orm.registry):
        table = sqlalchemy.Table(
            "source",
            registry.metadata,
            sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
            sqlalchemy.Column("created_time", sqlalchemy.DateTime),
            sqlalchemy.Column("type", sqlalchemy.String),
        )
        registry.map_imperatively(
            cls,
            table,
            polymorphic_on=table.c.type,
            polymorphic_identity="source",
            properties={
                'analysis': sqlalchemy.orm.relationship(
                    "Analysis",
                    uselist=False,
                    backref='source',
                    lazy="joined",
                    cascade="all, delete-orphan",
                ),
            },
        )
