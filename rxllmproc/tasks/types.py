"""Google Tasks classes (from REST interface) used in steps."""

import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_serializer

import sqlalchemy
import sqlalchemy.orm


class TaskList(BaseModel):
    """Represents a task list."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    title: str
    kind: Literal['tasks#taskList'] = 'tasks#taskList'
    id: str | None = None
    etag: str | None = None
    updated: datetime.datetime | None = None
    selfLink: str | None = None

    @classmethod
    def register_entity(cls, registry: sqlalchemy.orm.registry):
        """Register the entity with the SQLAlchemy registry."""
        table = sqlalchemy.Table(
            "task_list",
            registry.metadata,
            sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
            sqlalchemy.Column("title", sqlalchemy.String),
            sqlalchemy.Column("kind", sqlalchemy.String),
            sqlalchemy.Column("etag", sqlalchemy.String),
            sqlalchemy.Column("updated", sqlalchemy.DateTime),
            sqlalchemy.Column("selfLink", sqlalchemy.String),
        )
        registry.map_imperatively(cls, table)


class TaskLink(BaseModel):
    """Represents a link attached to a task."""

    model_config = ConfigDict(extra='ignore')

    type: str | None = None
    description: str | None = None
    link: str | None = None


Status = Literal['completed', 'needsAction']


class Task(BaseModel):
    """Represents a single task."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    status: Status | None = None
    title: str | None = None
    kind: Literal['tasks#task'] = 'tasks#task'
    position: int = 0
    updated: datetime.datetime | None = None
    id: str | None = None
    etag: str | None = None
    selfLink: str | None = None
    links: list[TaskLink] = Field(default_factory=lambda: [])
    notes: str | None = None
    parent: str | None = None
    completed: datetime.datetime | None = None
    deleted: bool | None = None
    hidden: bool | None = None
    due: datetime.datetime | None = None

    @field_serializer('position')
    def serialize_position(self, position: int) -> str:
        """Convert position to string for JSON."""
        return str(position)

    @classmethod
    def register_entity(cls, registry: sqlalchemy.orm.registry):
        """Register the entity with the SQLAlchemy registry."""
        table = sqlalchemy.Table(
            "task",
            registry.metadata,
            sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
            sqlalchemy.Column("title", sqlalchemy.String),
            sqlalchemy.Column("status", sqlalchemy.String),
            sqlalchemy.Column("kind", sqlalchemy.String),
            sqlalchemy.Column("position", sqlalchemy.Integer),
            sqlalchemy.Column("updated", sqlalchemy.DateTime),
            sqlalchemy.Column("etag", sqlalchemy.String),
            sqlalchemy.Column("selfLink", sqlalchemy.String),
            sqlalchemy.Column("notes", sqlalchemy.String),
            sqlalchemy.Column("parent", sqlalchemy.String),
            sqlalchemy.Column("completed", sqlalchemy.DateTime),
            sqlalchemy.Column("deleted", sqlalchemy.Boolean),
            sqlalchemy.Column("hidden", sqlalchemy.Boolean),
            sqlalchemy.Column("due", sqlalchemy.DateTime),
            sqlalchemy.Column("type", sqlalchemy.String),
        )
        registry.map_imperatively(
            cls, table, polymorphic_on=table.c.type, polymorphic_identity='task'
        )


class ManagedTask(Task):
    """Represents a task managed with an external ID."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id_url: str | None = None
    tasklist_id: str | None = None

    @classmethod
    def register_entity(cls, registry: sqlalchemy.orm.registry):
        """Register the entity with the SQLAlchemy registry."""
        table = sqlalchemy.Table(
            "managed_task",
            registry.metadata,
            sqlalchemy.Column(
                "id",
                sqlalchemy.String,
                sqlalchemy.ForeignKey("task.id"),
                primary_key=True,
            ),
            sqlalchemy.Column("id_url", sqlalchemy.String),
            sqlalchemy.Column("tasklist_id", sqlalchemy.String),
        )
        registry.map_imperatively(
            cls, table, inherits=Task, polymorphic_identity='managed_task'
        )
