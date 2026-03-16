"""Test the Tasks reactive operators."""

import unittest
from unittest import mock
import reactivex as rx

from rxllmproc.tasks import operators as tasks_operators
from rxllmproc.core import environment
from rxllmproc.tasks import api as tasks_wrapper
from rxllmproc.tasks import types as tasks_types


class TestTasksOperators(unittest.TestCase):
    """Test the Tasks reactive operators."""

    def setUp(self):
        self.managed_tasks_mock = mock.Mock(spec=tasks_wrapper.ManagedTasks)

        self.creds_patcher = mock.patch(
            'rxllmproc.core.auth.CredentialsFactory.shared_instance'
        )
        self.creds_patcher.start()
        self.env = environment.Environment({})
        self.env.__enter__()

    def tearDown(self):
        self.env.__exit__(None, None, None)
        self.creds_patcher.stop()

    def test_upsert_managed_task(self):
        """Test upserting a managed task."""
        task = tasks_types.ManagedTask(
            id_url="http://example.com/1",
            title="Test Task",
            tasklist_id="list1",
        )
        results: list[tasks_types.ManagedTask] = []
        source = rx.of(task)

        source.pipe(
            tasks_operators.upsert_managed_task(self.managed_tasks_mock)
        ).subscribe(results.append)

        self.assertEqual(results, [task])
        self.managed_tasks_mock.upsert_managed_task.assert_called_with(
            task, None
        )

    @mock.patch('rxllmproc.tasks.api.TasksWrap')
    @mock.patch('rxllmproc.tasks.api.ManagedTasks')
    def test_upsert_managed_task_default_wrapper(
        self, mock_managed_cls: mock.MagicMock, mock_wrap_cls: mock.MagicMock
    ):
        """Test upserting using a default wrapper created from creds."""
        mock_managed_instance: mock.MagicMock = mock_managed_cls.return_value
        task = tasks_types.ManagedTask(title="Test")

        source = rx.of(task)
        source.pipe(tasks_operators.upsert_managed_task()).subscribe()

        mock_wrap_cls.assert_called_once()
        mock_managed_cls.assert_called_with(mock_wrap_cls.return_value)
        mock_managed_instance.upsert_managed_task.assert_called_with(task, None)
