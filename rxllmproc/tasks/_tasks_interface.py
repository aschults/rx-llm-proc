"""Types used with the Takss REST interface."""

from typing import Any, Protocol
import pydantic

from rxllmproc.tasks import types as tasks_types


class TaskResponse(pydantic.BaseModel):
    """Repsonse listing all tasks of a tasklist."""

    model_config = pydantic.ConfigDict(extra='ignore')

    kind: str
    etag: str
    items: list[tasks_types.Task] = pydantic.Field(default_factory=lambda: [])
    nextPageToken: str | None = None


class TaskListResponse(pydantic.BaseModel):
    """Response listing all tasklists found."""

    model_config = pydantic.ConfigDict(extra='ignore')

    kind: str
    etag: str
    items: list[tasks_types.TaskList] = pydantic.Field(
        default_factory=lambda: []
    )
    nextPageToken: str | None = None


class Request(Protocol):
    """Partial and type anostic request interface."""

    def execute(self) -> Any:
        """Execute the formed request."""


class TasksInterface(Protocol):
    """tasts() API part."""

    def clear(self, *, tasklist: str, **kwargs: Any) -> Request:
        """Remove all from tasklist."""
        ...

    def delete(self, *, tasklist: str, task: str, **kwargs: Any) -> Request:
        """Remove specific task from list."""
        ...

    def get(self, *, tasklist: str, task: str, **kwargs: Any) -> Request:
        """Get all tasks from tasklist."""
        ...

    def insert(
        self,
        *,
        tasklist: str,
        body: Any = ...,
        parent: str = ...,
        previous: str = ...,
        **kwargs: Any,
    ) -> Request:
        """Insert task into tasklist."""
        ...

    def list(
        self,
        *,
        tasklist: str,
        completedMax: str = ...,
        completedMin: str = ...,
        dueMax: str = ...,
        dueMin: str = ...,
        maxResults: int = ...,
        pageToken: str | None = ...,
        showCompleted: bool = ...,
        showDeleted: bool = ...,
        showHidden: bool = ...,
        updatedMin: str = ...,
        **kwargs: Any,
    ) -> Request:
        """List all tasks in a tasklist."""
        ...

    def move(
        self,
        *,
        tasklist: str,
        task: str,
        parent: str = ...,
        previous: str = ...,
        **kwargs: Any,
    ) -> Request:
        """Move task between tasklists."""
        ...

    def patch(
        self, *, tasklist: str, task: str, body: Any = ..., **kwargs: Any
    ) -> Request:
        """(unused)."""
        ...

    def update(
        self, *, tasklist: str, task: str, body: Any = ..., **kwargs: Any
    ) -> Request:
        """Update a task."""
        ...


class TasklistsInterface(Protocol):
    """tasklists() API part."""

    def delete(self, *, tasklist: str, **kwargs: Any) -> Request:
        """Delete a tasklist."""
        ...

    def get(self, *, tasklist: str, **kwargs: Any) -> Request:
        """Get a tasklist."""
        ...

    def insert(self, *, body: Any = ..., **kwargs: Any) -> Request:
        """Insert a new tasklist."""
        ...

    def list(
        self, *, maxResults: int = ..., pageToken: str = ..., **kwargs: Any
    ) -> Request:
        """List all tasklists."""
        ...

    def patch(
        self, *, tasklist: str, body: Any = ..., **kwargs: Any
    ) -> Request:
        """(unused)."""
        ...

    def update(
        self, *, tasklist: str, body: Any = ..., **kwargs: Any
    ) -> Request:
        """Update a tasklist."""
        ...


class TasksServiceInterface(Protocol):
    """Top level Tasks API."""

    def tasklists(self) -> TasklistsInterface:
        """Get tasklist part."""
        ...

    def tasks(self) -> TasksInterface:
        """Get tasts part."""
        ...
