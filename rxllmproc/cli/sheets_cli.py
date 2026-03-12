"""Sheets download CLI."""

import logging
import json
from typing import Dict, List, Iterable

from rxllmproc.cli import cli_base
from rxllmproc.core import auth
from rxllmproc.sheets import api as sheets_api
from rxllmproc.sheets import types as sheets_types


class SheetsCli(cli_base.CommonFileOutputCli):
    """Command line implementation for Sheets wrapper."""

    def _add_args(self):
        subparsers = self.arg_parser.add_subparsers(
            dest='command',
            help='Operation to perform on Sheets',
            metavar='OPERATION',
            description='Operations to perform on Sheets',
        )
        get_subcommand = subparsers.add_parser(
            'get',
            help='Get data from a sheet or range',
            description=(
                'Get data from a sheet and write it to stdout, as JSON or '
                'CSV. Use --field to define field names for each column'
            ),
        )
        get_subcommand.add_argument(
            '--id',
            metavar='SPREADSHEET_ID',
            help='The ID of the Spreadsheet as in its URL.',
        )
        get_subcommand.add_argument(
            '--output',
            '-o',
            type=str,
            metavar='FILENAME',
            help='Write to FILENAME, not STDOUT',
        )
        get_subcommand.add_argument(
            '--range',
            '-r',
            action='append',
            metavar='SHEET_RANGE',
            help=(
                'Range to pull the data from in A1 notation, '
                'including Sheet name'
            ),
        )
        field_source_group = get_subcommand.add_mutually_exclusive_group(
            required=True
        )
        field_source_group.add_argument(
            '--field',
            '-F',
            action='append',
            metavar='FIELD_NAME',
            help='Set field names, column by column',
        )
        field_source_group.add_argument(
            '--header_row',
            type=int,
            metavar='HEADER_ROW',
            help=(
                'Uses row number HEADER_ROW as header row, '
                'to derive field names.'
            ),
        )
        get_subcommand.add_argument(
            '--start_row',
            type=int,
            metavar='START_ROW',
            help=(
                'Start row or number of rows to skip on top, '
                'before processing data.'
            ),
        )

        super()._add_args()

    def __init__(
        self,
        creds: auth.CredentialsFactory | None = None,
        sheets_wrapper: sheets_api.SheetsWrapper | None = None,
    ) -> None:
        """Construct the instance, allowing for mocks (testing)."""
        super().__init__(creds)

        self.force = False
        self.field: List[str] = []
        self.range: List[str] = []
        self.header_row: int | None = None
        self.command: str = ''
        self.start_row: int | None = None
        self._wrapper = sheets_wrapper
        self.id: str | None = None

    @property
    def wrapper(self) -> sheets_api.SheetsWrapper:
        """Get the Drive wrapper."""
        if self._wrapper is None:
            self._wrapper = sheets_api.SheetsWrapper(self._get_credentials())
        return self._wrapper

    def run(self):
        """Execute the action, download messages."""
        if self.command == 'get':
            self.run_get()
        else:
            cli_base.UsageException('Only Get command is supported.')

    def _process_grid(
        self, grid: sheets_types.GridData
    ) -> Iterable[Dict[str, sheets_types.CellValueType]]:
        if self.header_row is not None:
            field_names = [
                str(item) for item in grid.getRow(self.header_row).getValues()
            ]
            start_row = self.header_row + 1
        else:
            field_names = self.field
            start_row = 0

        if self.start_row is not None:
            start_row = self.start_row

        return grid.iterateRows(
            sheets_types.makeRowDictConverter(*field_names), firstRow=start_row
        )

    def run_get(self):
        """Execute the get action, download messages."""
        if self.id is None:
            raise cli_base.UsageException('Need to set ID')

        logging.info('Loading from sheet with id %s', repr(self.id))
        spreadsheet = self.wrapper.get_sheet(self.id, *(self.range or []))

        result: List[Dict[str, sheets_types.CellValueType]] = []
        for sheet in spreadsheet.sheets:
            for grid in sheet.data:
                result.extend(self._process_grid(grid))

        self.write_output(json.dumps(result, indent=2))


def main():
    """Run the command line tool."""
    SheetsCli().main()


if __name__ == '__main__':
    main()
