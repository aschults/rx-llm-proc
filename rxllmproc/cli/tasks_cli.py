"""Google Tasks CLI."""

import json
import logging
import sys
from typing import Optional, Any, cast

from rxllmproc.cli import cli_base
from rxllmproc.tasks import types as tasks_types
from rxllmproc.core.infra.utilities import asdict
from rxllmproc.core.auth import CredentialsFactory
from rxllmproc.tasks.api import ManagedTasks, TasksWrap


class TasksCli(cli_base.CommonFileOutputCli):
    """Command line implementation for Tasks wrapper."""

    def _add_args(self):
        self.arg_parser.description = "Access Google Tasks via Command line."
        subparsers = self.arg_parser.add_subparsers(
            dest="command",
            help="Operation to perform on Tasks",
            metavar="OPERATION",
            description="Operations to perform on Tasks.",
        )

        # List subcommand
        list_subcommand = subparsers.add_parser(
            "list", help="List tasks from a tasklist."
        )
        list_subcommand.add_argument(
            "--tasklist_id",
            required=False,
            help="ID of the tasklist. If not provided, tasks from all lists are shown.",
        )
        list_subcommand.add_argument(
            "--as_json", action="store_true", help="Output as JSON."
        )
        list_subcommand.add_argument(
            "--include_plain",
            action="store_true",
            help="Include tasks that are not managed (have no id_url).",
        )
        list_subcommand.add_argument(
            "--output", "-o", help="Output file, default is STDOUT."
        )

        # List tasklists subcommand
        list_tasklists_subcommand = subparsers.add_parser(
            "list_tasklists", help="List all available tasklists."
        )
        list_tasklists_subcommand.add_argument(
            "--as_json", action="store_true", help="Output as JSON."
        )
        list_tasklists_subcommand.add_argument(
            "--output", "-o", help="Output file, default is STDOUT."
        )

        # Add subcommand
        add_subcommand = subparsers.add_parser("add", help="Add a new task.")
        add_subcommand.add_argument(
            "--tasklist_id", required=True, help="ID of the tasklist."
        )
        add_subcommand.add_argument(
            "--title", required=True, help="Title of the task."
        )
        add_subcommand.add_argument("--notes", help="Notes for the task.")
        add_subcommand.add_argument(
            "--due", help="Due date for the task (ISO format)."
        )
        add_subcommand.add_argument(
            "--id_url", required=True, help="External ID URL for managed tasks."
        )
        add_subcommand.add_argument(
            "--dry_run",
            action="store_true",
            help="Log actions without executing.",
        )

        # Update subcommand
        update_subcommand = subparsers.add_parser(
            "update", help="Update an existing task."
        )
        update_subcommand.add_argument(
            "--tasklist_id",
            help="ID of the tasklist. If not provided, the task will be searched across all lists.",
        )
        update_subcommand.add_argument(
            "--id_url",
            required=True,
            help="External ID URL of the managed task to update.",
        )
        update_subcommand.add_argument(
            "--title", help="New title for the task."
        )
        update_subcommand.add_argument(
            "--notes", help="New notes for the task."
        )
        update_subcommand.add_argument(
            "--due", help="New due date for the task."
        )
        update_subcommand.add_argument(
            "--status",
            choices=["needsAction", "completed"],
            help="New status for the task.",
        )

        update_subcommand.add_argument(
            "--dry_run",
            action="store_true",
            help="Log actions without executing.",
        )

        # Batch subcommand
        batch_subcommand = subparsers.add_parser(
            "batch",
            help="Batch upsert managed tasks from a JSON file or stdin.",
        )
        batch_subcommand.add_argument(
            "input_file",
            nargs="?",
            metavar="INPUT_FILE",
            help="Path to a JSON file containing an array of managed tasks. Reads from stdin if not provided.",
        )
        batch_subcommand.add_argument(
            "--default_tasklist_id",
            help="Default tasklist_id for new tasks in the batch.",
        )
        batch_subcommand.add_argument(
            "--dry_run",
            action="store_true",
            help="Log actions without executing.",
        )

        super()._add_args()

    def __init__(
        self,
        creds: CredentialsFactory | None = None,
        tasks_wrapper: TasksWrap | None = None,
    ) -> None:
        """Construct the instance, allowing for mocks (testing)."""
        super().__init__(creds)
        self.command: Optional[str] = None
        self.tasklist_id: Optional[str] = None
        self.as_json: bool = False
        self.title: Optional[str] = None
        self.notes: Optional[str] = None
        self.due: Optional[str] = None
        self.id_url: Optional[str] = None
        self.task_id: Optional[str] = None
        self.status: Optional[tasks_types.Status] = None
        self.default_tasklist_id: Optional[str] = None
        self.input_file: Optional[str] = None
        self.include_plain: bool = False

        self._wrapper = tasks_wrapper
        self._managed_tasks: Optional[ManagedTasks] = None

    @property
    def wrapper(self) -> TasksWrap:
        """Get the Tasks wrapper."""
        if self._wrapper is None:
            self._wrapper = TasksWrap(self._get_credentials())
        return self._wrapper

    @property
    def managed_tasks(self) -> ManagedTasks:
        """Get the ManagedTasks wrapper."""
        if self._managed_tasks is None:
            self._managed_tasks = ManagedTasks(self.wrapper)
        return self._managed_tasks

    def _run_list(self):
        tasks = self.managed_tasks.generate_managed_tasks(
            self.tasklist_id, include_plain=self.include_plain
        )

        if self.as_json:
            self.write_output(
                json.dumps([asdict(task) for task in tasks], indent=2)
            )
        else:
            for task in tasks:
                self.write_output(
                    f"{task.id}\t{task.title}\t{task.status}\t{task.id_url}\n"
                )

    def _run_list_tasklists(self):
        """Handles the 'list_tasklists' command."""
        tasklists = self.wrapper.generate_lists()

        if self.as_json:
            self.write_output(
                json.dumps([asdict(tl) for tl in tasklists], indent=2)
            )
        else:
            for tasklist in tasklists:
                self.write_output(f"{tasklist.id}\t{tasklist.title}\n")

    def _run_add(self):
        if not self.tasklist_id or not self.title:
            raise cli_base.UsageException(
                "tasklist_id and title are required for add command."
            )

        task = tasks_types.ManagedTask(
            title=self.title,
            notes=self.notes,
            status="needsAction",
            id_url=self.id_url,
            tasklist_id=self.tasklist_id,
        )
        if self.dry_run:
            self._log_dry_run(f"Upserting managed task: {task.title}")
            print(json.dumps(asdict(task), indent=2))
        else:
            self.managed_tasks.upsert_managed_task(task)
            logging.info(
                "Upserted managed task '%s' with id_url '%s'.",
                task.title,
                task.id_url,
            )

    def _run_update(self):
        if not self.id_url:
            raise cli_base.UsageException("id_url is required for update.")

        task_to_update = self.managed_tasks.find_by_id_url(self.id_url)

        if not task_to_update:
            raise cli_base.UsageException(
                f"No managed task found with id_url: {self.id_url}"
            )

        if self.title:
            task_to_update.title = self.title
        # If a new tasklist_id is provided, update the task's destination
        if self.tasklist_id and self.tasklist_id != task_to_update.tasklist_id:
            task_to_update.tasklist_id = self.tasklist_id
        if self.notes is not None:  # Support empty notes.
            task_to_update.notes = self.notes
        if self.status:
            task_to_update.status = self.status
        if self.due:
            # This will need parsing from string to datetime
            # For now, assuming it's handled elsewhere or is a simple string.
            # A more robust solution would use dateutil.parser
            pass

        if self.dry_run:
            self._log_dry_run(f"Updating task: {task_to_update.id}")
            print(json.dumps(asdict(task_to_update), indent=2))
            return

        self.managed_tasks.upsert_managed_task(task_to_update)
        logging.info("Updated managed task '%s'.", task_to_update.title)

    def _run_batch(self):
        """Handles the 'batch' command."""
        if self.input_file:
            with open(self.input_file, "r") as f:
                content = f.read()
        else:
            content = sys.stdin.read()

        try:
            tasks_data: Any = json.loads(content)
        except json.JSONDecodeError as e:
            raise cli_base.UsageException(f"Invalid JSON provided: {e}")

        if not isinstance(tasks_data, list):
            raise cli_base.UsageException(
                f"Input for batch command must be a JSON array: {tasks_data}"
            )
        task_data_list = cast(list[dict[str, Any]], tasks_data)
        logging.info("Starting batch upsert for %s tasks.", len(task_data_list))

        for task_dict in task_data_list:
            task = tasks_types.ManagedTask.from_dict(task_dict)
            if self.dry_run:
                self._log_dry_run(f"Upserting managed task: {task.title}")
                continue

            logging.info("Upserting task with id_url: %s", task.id_url)
            self.managed_tasks.upsert_managed_task(
                task, default_tasklist_id=self.default_tasklist_id
            )
        logging.info("Batch upsert completed.")

    def run(self):
        """Execute the action."""
        if self.command == "list":
            self._run_list()
        elif self.command == "list_tasklists":
            self._run_list_tasklists()
        elif self.command == "add":
            self._run_add()
        elif self.command == "update":
            self._run_update()
        elif self.command == "batch":
            self._run_batch()
        else:
            raise cli_base.UsageException(f"Unknown command: {self.command}")


def main():
    """Run the command line tool."""
    TasksCli().main()


if __name__ == "__main__":
    main()
