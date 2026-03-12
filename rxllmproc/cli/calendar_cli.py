"""Google Calendar CLI."""

import json
import sys
import csv
import io
import dataclasses
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from rxllmproc.calendar.api import CalendarWrap
from rxllmproc.calendar import types
from rxllmproc.cli import cli_base
from rxllmproc.core.auth import CredentialsFactory


class CalendarCli(cli_base.CommonFileOutputCli):
    """Command line implementation for Google Calendar."""

    def _add_args(self):
        self.arg_parser.description = "Access Google Calendar via Command line."

        subparsers = self.arg_parser.add_subparsers(
            dest="command",
            help="Operation to perform on Calendar",
            metavar="OPERATION",
            description="Operation to perform on Calendar.",
        )

        # List command
        list_subcommand = subparsers.add_parser(
            "list",
            help="List calendar events.",
            description="Search for calendar events and return a list.",
        )
        list_subcommand.add_argument(
            "query",
            nargs="?",
            metavar="QUERY",
            help="Free text search terms to find events.",
        )
        list_subcommand.add_argument(
            "--calendar_id",
            default="primary",
            help="Calendar identifier. Defaults to 'primary'.",
        )
        list_subcommand.add_argument(
            "--time_min",
            help="Lower bound (exclusive) for an event's end time to filter by (RFC3339).",
        )
        list_subcommand.add_argument(
            "--time_max",
            help="Upper bound (exclusive) for an event's start time to filter by (RFC3339). Defaults to 90 days in the future.",
        )
        list_subcommand.add_argument(
            "--max_results",
            type=int,
            help="Maximum number of results to return.",
        )
        list_subcommand.add_argument(
            "--single_events",
            action="store_true",
            help="Whether to expand recurrent events into instances.",
        )
        list_subcommand.add_argument(
            "--i_cal_uid",
            help="Specifies an event's iCalendar UID to filter by.",
        )
        list_subcommand.add_argument(
            "--max_attendees",
            type=int,
            help="The maximum number of attendees to include in the response.",
        )
        list_format_group = list_subcommand.add_mutually_exclusive_group()
        list_format_group.add_argument(
            "--delimiter",
            default="\t",
            metavar="SINGLE_CHAR",
            help="Put SINGLE_CHAR between fields in output.",
        )
        list_format_group.add_argument(
            "--as_json",
            action="store_true",
            help="Output the list of events as a JSON array.",
        )

        # Create command
        create_subcommand = subparsers.add_parser(
            "create",
            help="Create a new calendar event.",
            description="Create a new calendar event from JSON input.",
        )
        create_subcommand.add_argument(
            "--calendar_id",
            default="primary",
            help="Calendar identifier. Defaults to 'primary'.",
        )
        create_subcommand.add_argument(
            "file",
            nargs="?",
            metavar="INPUT_FILE",
            help="Read event JSON from file, not STDIN.",
        )

        # Update command
        update_subcommand = subparsers.add_parser(
            "update",
            help="Update an existing calendar event.",
            description="Update an existing calendar event from JSON input.",
        )
        update_subcommand.add_argument(
            "--calendar_id",
            default="primary",
            help="Calendar identifier. Defaults to 'primary'.",
        )
        update_subcommand.add_argument(
            "file",
            nargs="?",
            metavar="INPUT_FILE",
            help="Read event JSON from file, not STDIN.",
        )

        cli_base.CliBase._add_args(self)

    def __init__(
        self,
        creds: CredentialsFactory | None = None,
        calendar_wrap: CalendarWrap | None = None,
    ) -> None:
        """Construct the instance."""
        super().__init__(creds)

        self.command: Literal["list", "create", "update"] | None = None
        self.query: str | None = None
        self.calendar_id: str = "primary"
        self.time_min: str | None = None
        self.time_max: str | None = None
        self.max_results: int | None = None
        self.single_events: bool = False
        self.i_cal_uid: str | None = None
        self.max_attendees: int | None = None
        self.delimiter: str = "\t"
        self.as_json: bool = False
        self.file: str | None = None

        self._wrapper = calendar_wrap

    @property
    def wrapper(self) -> CalendarWrap:
        """Get the Calendar wrapper."""
        if self._wrapper is None:
            self._wrapper = CalendarWrap(self._get_credentials())
        return self._wrapper

    def run_list(self):
        """List events."""
        time_max = self.time_max
        if not time_max:
            # Default to 90 days in the future
            now = datetime.now(timezone.utc)
            future = now + timedelta(days=90)
            time_max = future.isoformat().replace("+00:00", "Z")

        events = self.wrapper.search(
            q=self.query,
            calendar_id=self.calendar_id,
            time_min=self.time_min,
            time_max=time_max,
            max_results=self.max_results,
            single_events=self.single_events or None,
            i_cal_uid=self.i_cal_uid,
            max_attendees=self.max_attendees,
        )

        if self.as_json:
            self.write_output(
                json.dumps([dataclasses.asdict(e) for e in events], indent=2)
            )
            return

        fields = ["id", "summary", "start", "end", "location"]
        csv_content = io.StringIO()
        writer = csv.DictWriter(
            csv_content,
            fields,
            delimiter=self.delimiter,
            lineterminator="\n",
        )
        writer.writeheader()

        for event in events:
            row = {
                "id": event.id,
                "summary": event.summary,
                "start": event.start.dateTime if event.start else "",
                "end": event.end.dateTime if event.end else "",
                "location": event.location,
            }
            writer.writerow(row)

        self.write_output(csv_content.getvalue())

    def _read_input(self) -> dict[str, Any]:
        """Read JSON input from file or STDIN."""
        if self.file:
            with open(self.file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return json.load(sys.stdin)

    def run_create(self):
        """Create an event."""
        event_dict = self._read_input()
        # Basic conversion from dict to Event dataclass (nesting handled by CalendarWrap/dacite)
        # However, for the CLI we might just pass the dict if we want to be flexible,
        # but the wrapper expects an Event object.
        # We'll use a simple way to create the Event object.
        import dacite

        event = dacite.from_dict(types.Event, event_dict)

        if self.dry_run:
            self._log_dry_run(f"Creating event: {event.summary}")
            return

        result = self.wrapper.create(event, calendar_id=self.calendar_id)
        print(result.id)

    def run_update(self):
        """Update an event."""
        event_dict = self._read_input()
        import dacite

        event = dacite.from_dict(types.Event, event_dict)

        if not event.id:
            raise cli_base.UsageException(
                "Event JSON must contain an 'id' for update."
            )

        if self.dry_run:
            self._log_dry_run(f"Updating event: {event.id}")
            return

        result = self.wrapper.update(event, calendar_id=self.calendar_id)
        print(result.id)

    def run(self):
        """Execute the action."""
        if self.command == "list":
            self.run_list()
        elif self.command == "create":
            self.run_create()
        elif self.command == "update":
            self.run_update()
        else:
            raise cli_base.UsageException("No command given")


def main():
    """Run the command line tool."""
    CalendarCli().main()


if __name__ == "__main__":
    main()
