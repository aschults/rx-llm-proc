# pyright: basic
# pyright: reportPrivateUsage=false
"""Test Tasks CLI class."""

import contextlib
import io
import json
from unittest import mock

from pyfakefs import fake_filesystem_unittest

from rxllmproc.cli import tasks_cli
from rxllmproc.tasks import types as tasks_types
from rxllmproc.core import auth
from rxllmproc.tasks import api as tasks_wrapper


class TestTasksCli(fake_filesystem_unittest.TestCase):
    """Test the Tasks CLI class."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

        self.creds = mock.Mock(spec=auth.CredentialsFactory)
        self.wrap = mock.Mock(spec=tasks_wrapper.TasksWrap)
        self.managed_tasks_mock = mock.Mock(spec=tasks_wrapper.ManagedTasks)

        self.instance = tasks_cli.TasksCli(
            creds=self.creds, tasks_wrapper=self.wrap
        )
        # We can mock ManagedTasks directly on the instance after it's created
        self.instance._managed_tasks = self.managed_tasks_mock

    def test_list_tasklists_json(self):
        """Test listing tasklists as JSON."""
        tasklists = [
            tasks_types.TaskList(id="list1", title="List 1"),
            tasks_types.TaskList(id="list2", title="List 2"),
        ]
        self.wrap.generate_lists.return_value = iter(tasklists)

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.instance.main(["list_tasklists", "--as_json"])

        self.wrap.generate_lists.assert_called_once()
        result = json.loads(stdout_capture.getvalue())
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "List 1")

    def test_list_tasklists_plain(self):
        """Test listing tasklists as plain text."""
        tasklists = [
            tasks_types.TaskList(id="list1", title="List 1"),
            tasks_types.TaskList(id="list2", title="List 2"),
        ]
        self.wrap.generate_lists.return_value = iter(tasklists)

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.instance.main(["list_tasklists"])

        self.wrap.generate_lists.assert_called_once()
        output = stdout_capture.getvalue()
        self.assertIn("list1\tList 1", output)
        self.assertIn("list2\tList 2", output)

    def test_list_tasks_json(self):
        """Test listing tasks as JSON."""
        tasks = [
            tasks_types.ManagedTask(
                id="task1",
                title="Task 1",
                status="needsAction",
                id_url="http://example.com/1",
                tasklist_id="list1",
            )
        ]
        self.managed_tasks_mock.generate_managed_tasks.return_value = iter(
            tasks
        )

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.instance.main(["list", "--tasklist_id=list1", "--as_json"])

        self.managed_tasks_mock.generate_managed_tasks.assert_called_once_with(
            "list1", include_plain=False
        )
        result = json.loads(stdout_capture.getvalue())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Task 1")

    def test_list_tasks_plain(self):
        """Test listing tasks as plain text."""
        tasks = [
            tasks_types.ManagedTask(
                id="task1",
                title="Task 1",
                status="needsAction",
                id_url="http://example.com/1",
                tasklist_id="list1",
            )
        ]
        self.managed_tasks_mock.generate_managed_tasks.return_value = iter(
            tasks
        )

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            self.instance.main(["list"])

        self.managed_tasks_mock.generate_managed_tasks.assert_called_once_with(
            None, include_plain=False
        )
        output = stdout_capture.getvalue()
        self.assertIn(
            "task1\tTask 1\tneedsAction\thttp://example.com/1", output
        )

    def test_add_task(self):
        """Test adding a new managed task."""
        self.instance.main(
            [
                "add",
                "--tasklist_id=list1",
                "--title=New Task",
                "--notes=Some notes",
                "--id_url=http://example.com/new",
            ]
        )

        self.managed_tasks_mock.upsert_managed_task.assert_called_once()
        called_task = self.managed_tasks_mock.upsert_managed_task.call_args[0][
            0
        ]
        self.assertIsInstance(called_task, tasks_types.ManagedTask)
        self.assertEqual(called_task.title, "New Task")
        self.assertEqual(called_task.id_url, "http://example.com/new")
        self.assertEqual(called_task.tasklist_id, "list1")

    def test_add_task_dry_run(self):
        """Test adding a task with --dry_run."""
        stderr_capture = io.StringIO()
        with contextlib.redirect_stderr(stderr_capture):
            self.instance.main(
                [
                    "add",
                    "--dry_run",
                    "--tasklist_id=list1",
                    "--title=New Task",
                    "--id_url=http://example.com/new",
                ]
            )

        self.managed_tasks_mock.upsert_managed_task.assert_not_called()
        self.assertIn("**DRY RUN**", stderr_capture.getvalue())

    def test_update_task(self):
        """Test updating an existing task."""
        existing_task = tasks_types.ManagedTask(
            id="task1",
            title="Old Title",
            status="needsAction",
            id_url="http://example.com/1",
            tasklist_id="list1",
        )
        self.managed_tasks_mock.find_by_id_url.return_value = existing_task

        self.instance.main(
            [
                "update",
                "--id_url=http://example.com/1",
                "--title=New Title",
                "--status=completed",
            ]
        )

        self.managed_tasks_mock.find_by_id_url.assert_called_once_with(
            "http://example.com/1"
        )
        self.managed_tasks_mock.upsert_managed_task.assert_called_once()
        updated_task = self.managed_tasks_mock.upsert_managed_task.call_args[0][
            0
        ]
        self.assertEqual(updated_task.title, "New Title")
        self.assertEqual(updated_task.status, "completed")

    def test_update_task_move_list(self):
        """Test moving a task to a new tasklist during update."""
        existing_task = tasks_types.ManagedTask(
            id="task1",
            title="My Task",
            status="needsAction",
            id_url="http://example.com/1",
            tasklist_id="list1",
        )
        self.managed_tasks_mock.find_by_id_url.return_value = existing_task

        self.instance.main(
            [
                "update",
                "--id_url=http://example.com/1",
                "--tasklist_id=list2",
            ]
        )

        self.managed_tasks_mock.upsert_managed_task.assert_called_once()
        updated_task = self.managed_tasks_mock.upsert_managed_task.call_args[0][
            0
        ]
        self.assertEqual(updated_task.tasklist_id, "list2")

    def test_batch_upsert_from_file(self):
        """Test batch upserting tasks from a JSON file."""
        tasks_data = [
            {
                "title": "Batch Task 1",
                "id_url": "http://example.com/batch/1",
                "tasklist_id": "list1",
            },
            {
                "title": "Batch Task 2",
                "id_url": "http://example.com/batch/2",
                "tasklist_id": "list2",
                "status": "completed",
            },
        ]
        self.fs.create_file("tasks.json", contents=json.dumps(tasks_data))

        self.instance.main(["batch", "tasks.json"])

        self.assertEqual(
            self.managed_tasks_mock.upsert_managed_task.call_count, 2
        )
        first_call_task = (
            self.managed_tasks_mock.upsert_managed_task.call_args_list[0][0][0]
        )
        self.assertEqual(first_call_task.title, "Batch Task 1")
        self.assertEqual(first_call_task.status, None)

        second_call_task = (
            self.managed_tasks_mock.upsert_managed_task.call_args_list[1][0][0]
        )
        self.assertEqual(second_call_task.title, "Batch Task 2")
        self.assertEqual(second_call_task.status, "completed")

    @mock.patch("sys.stdin", new_callable=io.StringIO)
    def test_batch_upsert_from_stdin(self, mock_stdin):
        """Test batch upserting tasks from stdin."""
        tasks_data = [
            {
                "title": "Stdin Task",
                "id_url": "http://example.com/stdin/1",
                "tasklist_id": "list1",
            }
        ]
        mock_stdin.write(json.dumps(tasks_data))
        mock_stdin.seek(0)

        self.instance.main(["batch"])

        self.managed_tasks_mock.upsert_managed_task.assert_called_once()
        called_task = self.managed_tasks_mock.upsert_managed_task.call_args[0][
            0
        ]
        self.assertEqual(called_task.title, "Stdin Task")
