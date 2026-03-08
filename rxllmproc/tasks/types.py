"""Google Tasks classes (from REST interface) used in steps."""

import dataclasses
import datetime
from typing import Literal
from typing import Any

import dacite
import dateutil.parser
import sqlalchemy
import sqlalchemy.orm


def as_dict_factory(args: list[tuple[str, Any]]) -> dict[str, Any]:
    """Dataclass helper to convert datatypes to REST compatible form."""
    val = dict(args)
    for field_name in ('updated', 'due', 'completed'):
        field_val = val.get(field_name, None)
        if field_val is not None:
            if not isinstance(field_val, datetime.datetime):
                raise ValueError(f'expecting datetime object for {field_name}')
            val[field_name] = field_val.isoformat()
    position = val.get('position')
    if position is not None:
        val['position'] = f'{position}'
    return val


@dataclasses.dataclass(kw_only=True)
class TaskList:
    """Represents a task list."""

    title: str
    kind: Literal['tasks#taskList'] = 'tasks#taskList'
    id: str | None = None
    etag: str | None = None
    updated: datetime.datetime | None = None
    selfLink: str | None = None

    @classmethod
    def _convert_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Convert fields from API representation."""
        if data.get('updated'):
            # The API may not include timezone info, so we can't assume UTC here.
            data['updated'] = dateutil.parser.parse(data['updated'])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskList":
        """Create a TaskList from a dictionary."""
        return dacite.from_dict(
            cls, cls._convert_fields(data), config=dacite.Config(strict=False)
        )

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


@dataclasses.dataclass(kw_only=True)
class TaskLink:
    """Represents a link attached to a task."""

    type: str | None = None
    description: str | None = None
    link: str | None = None


Status = Literal['completed', 'needsAction']


@dataclasses.dataclass(kw_only=True)
class Task:
    """Represents a single task."""

    status: Status | None = None
    title: str | None = None
    kind: Literal['tasks#task'] = 'tasks#task'
    position: int = 0
    updated: datetime.datetime | None = None
    id: str | None = None
    etag: str | None = None
    selfLink: str | None = None
    links: list[TaskLink] = dataclasses.field(default_factory=lambda: [])
    notes: str | None = None
    parent: str | None = None
    completed: datetime.datetime | None = None
    deleted: bool | None = None
    hidden: bool | None = None
    due: datetime.datetime | None = None

    @classmethod
    def _convert_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Convert fields from API representation."""
        utc_tz = {"UTC": datetime.timezone.utc}
        for field_name in ("due", "updated", "completed"):
            if field_val := data.get(field_name):
                if isinstance(field_val, str):
                    data[field_name] = dateutil.parser.parse(
                        field_val, tzinfos=utc_tz
                    )
        if position_val := data.get('position'):
            if isinstance(position_val, str):
                data['position'] = int(position_val)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Create a Task from a dictionary."""
        return dacite.from_dict(
            cls, cls._convert_fields(data), config=dacite.Config(strict=False)
        )

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


@dataclasses.dataclass(kw_only=True)
class ManagedTask(Task):
    """Represents a task managed with an external ID."""

    id_url: str | None = None
    tasklist_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ManagedTask":
        """Create a ManagedTask from a dictionary, converting date strings."""
        # Use dacite for robust conversion from dict to dataclass
        return dacite.from_dict(
            data_class=cls,
            data=cls._convert_fields(data),
            config=dacite.Config(strict=False),
        )

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
