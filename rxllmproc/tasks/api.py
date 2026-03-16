"""Google Tasks REST interface wrapper."""

from typing import Any, cast, Generator, Iterator
import dataclasses
import re
import logging
import threading

import dacite
from googleapiclient import discovery, errors

from rxllmproc.tasks import types as tasks_types
from rxllmproc.core import auth, api_base
from rxllmproc.tasks import _tasks_interface


class TaskNotFoundError(Exception):
    """Raised when a task is not found."""


class TasksWrap(api_base.ApiBase):
    """Wrapper around Tasks API."""

    def __init__(
        self,
        creds: auth.Credentials | None = None,
        service: _tasks_interface.TasksServiceInterface | None = None,
    ):
        """Create an instance.

        Args:
            creds: Credentials to be used for the requests.
            service: Optionally provide service instance (mailnly for testing.)
                Note: If provided, this instance is shared across threads and
                is not thread-safe.
        """
        super().__init__(creds)
        self._service_arg = service
        self._local = threading.local()

    def generate_lists(self) -> Generator[tasks_types.TaskList, None, None]:
        """Generate all tasklists."""
        result = self._service.tasklists().list(maxResults=100).execute()

        cfg = dacite.Config(
            type_hooks={tasks_types.TaskList: tasks_types.TaskList.from_dict}
        )
        response_obj = dacite.from_dict(
            _tasks_interface.TaskListResponse,
            result,
            config=cfg,
        )
        for item in response_obj.items:
            yield item

    def list_lists(self) -> list[tasks_types.TaskList]:
        """Return a list of all tasklists."""
        return list(self.generate_lists())

    def generate_tasks(
        self,
        tasklist_id: str | None = None,
        showCompleted: bool = False,
        showDeleted: bool = False,
        showHidden: bool = False,
    ) -> Generator[tuple[str, tasks_types.Task], None, None]:
        """Generate all tasks for a tasklist, or all tasks if no tasklist is specified."""

        def _generate_for_list(current_tasklist_id: str):
            pageToken: str | None = None
            while True:
                result = (
                    self._service.tasks()
                    .list(
                        showCompleted=showCompleted,
                        showDeleted=showDeleted,
                        showHidden=showHidden,
                        tasklist=current_tasklist_id,
                        maxResults=100,
                        pageToken=pageToken,
                    )
                    .execute()
                )

                cfg = dacite.Config(
                    type_hooks={tasks_types.Task: tasks_types.Task.from_dict}
                )
                response_obj = dacite.from_dict(
                    _tasks_interface.TaskResponse,
                    result,
                    config=cfg,
                )
                for item in response_obj.items:
                    yield current_tasklist_id, item

                pageToken = response_obj.nextPageToken
                if not pageToken:
                    break

        if tasklist_id:
            yield from _generate_for_list(tasklist_id)  # type: ignore
        else:
            for tasklist in self.generate_lists():
                if tasklist.id:
                    yield from _generate_for_list(tasklist.id)

    def list_tasks(
        self,
        tasklist: str,
        showCompleted: bool = False,
        showDeleted: bool = False,
        showHidden: bool = False,
    ) -> list[tuple[str, tasks_types.Task]]:
        """Return a list of all tasks for a tasklist."""
        return list(
            self.generate_tasks(
                tasklist, showCompleted, showDeleted, showHidden
            )  # type: ignore
        )

    def get_task(self, tasklist_id: str, task_id: str) -> tasks_types.Task:
        """Get a specific task by its ID."""
        try:
            result = (
                self._service.tasks()
                .get(tasklist=tasklist_id, task=task_id)
                .execute()
            )
            # The result is a single task dictionary, which can be mangled directly.
            return tasks_types.Task.from_dict(result)
        except errors.HttpError as e:
            if e.status_code == 404:
                raise TaskNotFoundError(
                    f"Task with ID '{task_id}' not found in list '{tasklist_id}'."
                ) from e
            raise

    def delete_task(self, tasklist_id: str, task_id: str) -> None:
        """Delete a specific task by its ID."""
        self._service.tasks().delete(
            tasklist=tasklist_id, task=task_id
        ).execute()

    def add_task(
        self,
        task: tasks_types.Task,
        tasklist: tasks_types.TaskList,
        previous: tasks_types.Task | None = None,
    ):
        """Add a single task to a tasklist."""
        if task.id:
            raise ValueError('Task needs to be without ID')

        if not tasklist.id:
            raise Exception()

        if previous and not previous.id:
            raise Exception()

        kwargs: dict[str, Any] = {}
        if previous:
            kwargs['previous'] = previous.id
        if task.parent:
            kwargs['parent'] = task.parent

        try:
            result = (
                self._service.tasks()
                .insert(
                    body=dataclasses.asdict(
                        task,
                        dict_factory=tasks_types.as_dict_factory,
                    ),
                    tasklist=tasklist.id,
                    **kwargs,
                )
                .execute()
            )

            response_obj = tasks_types.Task.from_dict(result)

        except Exception:
            logging.error("Failure to add task: %s", task, exc_info=True)
            raise

        task.id = response_obj.id
        task.etag = response_obj.etag
        task.updated = response_obj.updated
        task.position = response_obj.position

    def update_task(
        self,
        task: tasks_types.Task,
        tasklist_id: str,
    ):
        """Update an existing task.

        The task object must have an ID.
        """
        if not task.id:
            raise ValueError('Task must have an ID to be updated.')

        result = (
            self._service.tasks()
            .update(
                tasklist=tasklist_id,
                task=task.id,
                body=dataclasses.asdict(
                    task,
                    dict_factory=tasks_types.as_dict_factory,
                ),
            )
            .execute()
        )

        response_obj = tasks_types.Task.from_dict(result)
        # Update the task object with the new state from the server
        task.etag = response_obj.etag
        task.updated = response_obj.updated

    def move_task(
        self, task_id: str, current_tasklist_id: str, new_tasklist_id: str
    ) -> tasks_types.Task:
        """Move a task to a different tasklist."""
        if not task_id:
            raise ValueError("Task must have an ID to be moved.")

        result = (
            self._service.tasks()
            .move(
                tasklist=current_tasklist_id,
                task=task_id,
                destinationTasklist=new_tasklist_id,
            )
            .execute()
        )

        return tasks_types.Task.from_dict(result)

    def upsert_task(
        self,
        task: tasks_types.Task,
        tasklist_id: str,
    ) -> None:
        """Create a task if it doesn't exist, otherwise update it.

        The function first checks for existence by task.id. If no ID is present,
        it searches for a task with the same title within the tasklist.

        An update is only performed if there are changes between the provided
        task object and the one on the server.

        Args:
            task: The task to upsert.
            tasklist_id: The ID of the tasklist.
        """
        existing_task: tasks_types.Task | None = None

        if task.id:
            existing_task = self.get_task(tasklist_id, task.id)

        if not existing_task:
            logging.debug(f"Task does not exist, create it: {task!r}.")
            dummy_tasklist = tasks_types.TaskList(id=tasklist_id, title="")
            self.add_task(task, dummy_tasklist)
            return

        # Task exists, check for differences before updating.
        # Create a copy of the existing task to compare against,
        # ignoring fields that are managed by the server.
        comparable_existing = dataclasses.replace(
            existing_task, etag=None, updated=None, selfLink=None, position=0
        )
        comparable_new = dataclasses.replace(
            task, etag=None, updated=None, selfLink=None, position=0
        )

        if comparable_new == comparable_existing:
            logging.debug("No changes detected, skipping update: {task!r}.")
            return
        self.update_task(task, tasklist_id)

    @property
    def _service(self) -> _tasks_interface.TasksServiceInterface:
        if self._service_arg:
            return self._service_arg
        if not hasattr(self._local, 'service'):
            self._local.service = cast(
                _tasks_interface.TasksServiceInterface,
                discovery.build(
                    "tasks",
                    "v1",
                    credentials=self._creds,
                    requestBuilder=self.build_request,
                ),
            )
        return self._local.service


class ManagedTasks:
    """Manages tasks with an external ID stored in the notes field."""

    _ID_URL_PREFIX = '\U0001f517'  # Link symbol unicode
    _ID_URL_RE = re.compile(f'^{re.escape(_ID_URL_PREFIX)}(.*)')

    def __init__(self, tasks_wrapper: TasksWrap):
        """Create an instance.

        Args:
            tasks_wrapper: An instance of TasksWrap to interact with the API.
        """
        self._tasks_wrapper = tasks_wrapper

    def _get_id_url(self, task: tasks_types.Task) -> str | None:
        """Extracts the external ID from a task's notes."""
        if not task.notes:
            return None

        for line in task.notes.splitlines():
            match = self._ID_URL_RE.match(line)
            if match:
                return match.group(1).strip()
        return None

    def _set_id_url(self, task: tasks_types.Task, id_url: str):
        """Sets the external ID in a task's notes."""
        notes_lines = (task.notes or '').splitlines()
        # Remove existing external ID if present
        new_notes_lines = [
            line for line in notes_lines if not self._ID_URL_RE.match(line)
        ]
        # Prepend new external ID
        new_notes_lines.insert(0, f'{self._ID_URL_PREFIX}{id_url}')
        task.notes = '\n'.join(new_notes_lines)

    def find_by_id_url(
        self, id_url: str | None, tasklist_id: str | None = None
    ) -> tasks_types.ManagedTask | None:
        """Finds a task by its ID URL, optionally within a specific tasklist."""
        for current_tasklist_id, task in self._tasks_wrapper.generate_tasks(
            tasklist_id
        ):
            if task.id:
                found_id_url = self._get_id_url(task)
                if found_id_url == id_url:
                    task_dict = dataclasses.asdict(task)
                    # Use the tasklist ID from the generator, which is always correct.
                    return tasks_types.ManagedTask(
                        id_url=id_url,
                        tasklist_id=current_tasklist_id,
                        **task_dict,
                    )
        return None

    _SKIP_FIELDS_ON_MANAGED_UPSERT = (
        "id",
        "etag",
        "updated",
        "selfLink",
        "position",
        "id_url",
        "tasklist_id",
    )

    def _patch_managed_task(
        self,
        target: tasks_types.ManagedTask,
        updates: tasks_types.ManagedTask,
    ) -> bool:
        is_dirty = False
        for field in dataclasses.fields(updates):
            if field.name in self._SKIP_FIELDS_ON_MANAGED_UPSERT:
                continue
            value: Any = getattr(updates, field.name)
            if value is None:
                continue
            target_value = getattr(target, field.name)
            if value != target_value:
                is_dirty = True
            setattr(target, field.name, value)

        return is_dirty

    def upsert_managed_task(
        self,
        managed_task: tasks_types.ManagedTask,
        default_tasklist_id: str | None = None,
    ) -> None:
        """Creates or updates a task with an external ID."""
        default_tasklist_id = default_tasklist_id or "@default"
        id_url = managed_task.id_url
        if not id_url:
            raise ValueError(
                f"Managed task must have an ID URL: {managed_task!r}"
            )
        existing_task = self.find_by_id_url(id_url)

        logging.debug("Existing task found: %s", existing_task)
        target_task = existing_task

        if not target_task:
            if not managed_task.tasklist_id:
                managed_task.tasklist_id = default_tasklist_id

            self._set_id_url(managed_task, id_url)
            self._tasks_wrapper.upsert_task(
                managed_task, managed_task.tasklist_id
            )
            return

        if (
            managed_task.tasklist_id
            and target_task.tasklist_id != managed_task.tasklist_id
        ):
            if not target_task.id:
                raise ValueError(
                    f"Target task must have an ID to move: {target_task!r}"
                )
            if not target_task.tasklist_id:
                raise ValueError(
                    f"Target task must have a tasklist ID to move: {target_task!r}"
                )
            logging.debug(
                "Moving task %s to tasklist %s",
                target_task.id,
                managed_task.tasklist_id,
            )
            self._tasks_wrapper.move_task(
                target_task.id,
                target_task.tasklist_id,
                managed_task.tasklist_id,
            )
            target_task.tasklist_id = managed_task.tasklist_id

        self._set_id_url(target_task, id_url)
        self._set_id_url(managed_task, id_url)
        if not self._patch_managed_task(target_task, managed_task):
            logging.debug(
                "No changes detected, skipping upsert: %s.", repr(target_task)
            )
            return
        if not target_task.tasklist_id:
            raise ValueError(
                f"Target task must have a tasklist ID to update: {target_task!r}"
            )

        self._tasks_wrapper.upsert_task(target_task, target_task.tasklist_id)

    def generate_managed_tasks(
        self,
        tasklist_id: str | None = None,
        include_plain: bool = False,
    ) -> Iterator[tasks_types.ManagedTask]:
        """Generates all managed tasks, optionally from a specific tasklist."""
        for current_tasklist_id, task in self._tasks_wrapper.generate_tasks(
            tasklist_id
        ):
            id_url = self._get_id_url(task)
            task_dict = dataclasses.asdict(task)
            if id_url:
                yield tasks_types.ManagedTask(
                    id_url=id_url, tasklist_id=current_tasklist_id, **task_dict
                )
            elif include_plain:
                yield tasks_types.ManagedTask(
                    tasklist_id=current_tasklist_id, **task_dict
                )
