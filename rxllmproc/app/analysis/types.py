"""Domain entities and types for analysis."""

import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.ext import orderinglist

from rxllmproc.database import api as database


class Link(BaseModel):
    """Represent a link with a title and a URL."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    title: str = Field(description="Title of the link")
    url: str = Field(description="URL of the link")


class Identifier(BaseModel):
    """Represent an identifier in an email or text."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    name: str = Field(description="Name of the identifier")
    value: str = Field(description="Value of the identifier")


class Person(BaseModel):
    """Represent a person in an email or text."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    name: str = Field(description="Name of the person")
    role: str = Field(
        description="The role of the person in the text, e.g. recipient, sender, collaborator,..."
    )


class ActionItem(BaseModel):
    """Represent an action item in an email or text."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    analysis_id: Optional[str] = Field(default=None, description="Analysis ID")
    action_number: int = Field(
        default=0, description="Sequence number of the action item"
    )
    title: Optional[str] = Field(
        default=None, description="one line title or summary of the action item"
    )
    notes: Optional[str] = Field(
        default=None, description="Detailed notes for the action item"
    )
    priority: Optional[str] = Field(
        default=None,
        description="Priority of the action item (e.g., High, Medium, Low)",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Due date for the action item in YYYY-MM-DD format",
    )
    links: Optional[List[Link]] = Field(
        default=None,
        description="List of relevant links, each with 'title' and 'url'",
    )

    @property
    def source_url(self) -> str | None:
        """Get source URL from analysis ID."""
        return f'{self.analysis_id}#{self.action_number}'


class ActionItemDb:
    """Database mapped class for ActionItem."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize attributes from kwargs."""
        for k, v in kwargs.items():
            setattr(self, k, v)

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
            sqlalchemy.Column("links", database.PydanticJSONList(Link)),
            sqlalchemy.Column("source_url", sqlalchemy.String),
            sqlalchemy.ForeignKeyConstraint(["analysis_id"], ["analysis.id"]),
        )
        registry.map_imperatively(cls, table)


class ActionItemPlacement(BaseModel):
    """Tracks where an action item has been placed."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    analysis_id: Optional[str] = Field(default=None, description="Analysis ID")
    action_number: Optional[int] = Field(
        default=None, description="Sequence number of the action item"
    )
    placement_container_url: Optional[str] = Field(
        default=None,
        description="Reference to the container in the target system (e.g. Docs URL)",
    )
    placement_id: Optional[str] = Field(
        default=None,
        description="ID in the target system, i.e. how to find the item within the container",
    )


class ActionItemPlacementDb:
    """Database mapped class for ActionItemPlacement."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize attributes from kwargs."""
        for k, v in kwargs.items():
            setattr(self, k, v)

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


class Analysis(BaseModel):
    """Store all mail analysis results."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: Optional[str] = Field(default=None, description="Content Source ID.")
    category: Optional[str] = Field(
        default=None,
        description="Category of the email, format: 'this_is_a_category'",
    )
    noteworthy_details: List[str] = Field(
        default_factory=lambda: [],
        description="noteworthy details, bullet list style, one bullet per list item",
    )
    action_items: List[ActionItem] = Field(
        default_factory=lambda: [],
        description="List of action items extracted from the email",
    )
    people: List[Person] = Field(
        default_factory=lambda: [],
        description="Key people mentioned in the email and their roles",
    )
    identifiers: List[Identifier] = Field(
        default_factory=lambda: [],
        description="Key identifiers found in the email (e.g., ticket numbers, project codes, order numbers,...)",
    )


class AnalysisDb:
    """Database mapped class for Analysis."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize attributes from kwargs."""
        for k, v in kwargs.items():
            setattr(self, k, v)

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
            sqlalchemy.Column("people", database.PydanticJSONList(Person)),
            sqlalchemy.Column(
                "identifiers", database.PydanticJSONList(Identifier)
            ),
        )
        registry.map_imperatively(
            cls,
            table,
            properties={
                'action_items': sqlalchemy.orm.relationship(
                    ActionItemDb,
                    backref='analysis',
                    lazy="selectin",
                    collection_class=orderinglist.ordering_list(  # pyright: ignore
                        "action_number"
                    ),
                    primaryjoin="foreign(ActionItemDb.analysis_id) == AnalysisDb.id",
                ),
            },
        )


class Source(BaseModel):
    """Base source data."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: str = Field(description="The unique ID (url) of the content source.")
    created_time: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Time of creation.",
    )
    analysis: Optional[Analysis] = Field(
        default=None, description="Analysis of the content"
    )


class SourceDb:
    """Database mapped class for Source."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize attributes from kwargs."""
        for k, v in kwargs.items():
            setattr(self, k, v)

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
                    AnalysisDb,
                    uselist=False,
                    backref='source',
                    lazy="joined",
                    cascade="all, delete-orphan",
                ),
            },
        )
