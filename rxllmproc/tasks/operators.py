"""Reactive operators for Google Tasks."""

from typing import Callable
import reactivex as rx
from reactivex import operators as ops
from reactivex import Observable
from rxllmproc.tasks import api as tasks_wrapper
from rxllmproc.core import auth
from rxllmproc.tasks import types as tasks_types
from rxllmproc.core import environment


def upsert_managed_task(
    managed_tasks: tasks_wrapper.ManagedTasks | None = None,
    default_tasklist_id: str | None = None,
    creds: auth.Credentials | None = None,
) -> Callable[
    [Observable[tasks_types.ManagedTask]], Observable[tasks_types.ManagedTask]
]:
    """Upsert a managed task based on the input.

    The input stream is expected to emit `tasks_types.ManagedTask` objects
    or dictionaries that can be converted to `ManagedTask`.

    Args:
        managed_tasks: The ManagedTasks wrapper instance.
        default_tasklist_id: Optional default tasklist ID if not specified in the task.

    Returns:
        An operator function that returns the upserted task (passed through).
    """
    if managed_tasks is None:
        managed_tasks = environment.shared().managed_tasks

    def _upsert_managed_task(
        source: Observable[tasks_types.ManagedTask],
    ) -> Observable[tasks_types.ManagedTask]:
        def _process(
            item: tasks_types.ManagedTask,
        ) -> Observable[tasks_types.ManagedTask]:
            try:
                task = item
                managed_tasks.upsert_managed_task(task, default_tasklist_id)
                return rx.just(task)
            except Exception as e:
                return rx.throw(e)

        return source.pipe(ops.flat_map(_process))

    return _upsert_managed_task
