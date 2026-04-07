# pyright: basic
"""Test Sheets CLI class."""

from unittest import mock
import json
from typing import Any, Dict

from pyfakefs import fake_filesystem_unittest

from rxllmproc.sheets import api as sheets_wrapper
from rxllmproc.sheets import types as sheets_types
from rxllmproc.cli import sheets_cli

ROW1: Dict[str, Any] = {
    'values': [
        {
            'effectiveValue': {
                'numberValue': 999,
                'stringValue': None,
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            }
        }
    ]
}

ROW2: Dict[str, Any] = {
    'values': [
        {
            'effectiveValue': {
                'numberValue': 888,
                'stringValue': None,
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            }
        },
        {
            'effectiveValue': {
                'numberValue': None,
                'stringValue': 'some_text',
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            }
        },
    ]
}

HEADER_ROW: Dict[str, Any] = {
    'values': [
        {
            'effectiveValue': {
                'numberValue': None,
                'stringValue': 'header_1',
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            }
        },
        {
            'effectiveValue': {
                'numberValue': None,
                'stringValue': 'header_2',
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            }
        },
    ]
}

GRID: Dict[str, Any] = {'rowData': [ROW1, ROW2], 'startRow': 0}
SPREADSHEET: Dict[str, Any] = {
    'spreadsheetId': 'theSheet',
    'sheets': [{'data': [GRID]}],
}


class TestSheetsCli(fake_filesystem_unittest.TestCase):
    """Test the Gmail CLI class."""

    def setUp(self) -> None:
        """Set up fake filesystem and mocks."""
        super().setUp()
        self.setUpPyfakefs()

        self.creds = mock.Mock()
        self.wrap = mock.Mock(sheets_wrapper.SheetsWrapper)
        self.instance = sheets_cli.SheetsCli(self.creds, self.wrap)
        self.sheet = sheets_types.Spreadsheet.model_validate(SPREADSHEET)
        self.wrap.get_sheet.return_value = self.sheet

    def test_get_sheet(self):
        """Test a writing a single column."""
        self.instance.main(
            ['get', '--id', 'theId', '--output=file.json', '-F', 'field_1']
        )

        self.wrap.get_sheet.assert_called_with('theId')
        msg_file = self.fs.get_object('file.json')
        self.assertIsNotNone(msg_file)
        self.assertEqual(
            json.loads(msg_file.contents or ''),
            [
                {
                    'field_1': 999,
                },
                {
                    'field_1': 888,
                },
            ],
        )

    def test_get_sheet_start_row(self):
        """Test a writing a single column."""
        self.instance.main(
            [
                'get',
                '--id',
                'theId',
                '--output=file.json',
                '-F',
                'field_1',
                '--start_row',
                '1',
            ]
        )

        self.wrap.get_sheet.assert_called_with('theId')
        msg_file = self.fs.get_object('file.json')
        self.assertIsNotNone(msg_file)
        self.assertEqual(
            json.loads(msg_file.contents or ''),
            [
                {
                    'field_1': 888,
                }
            ],
        )

    def test_get_sheet_with_range(self):
        """Test passing a range to the wrapper."""
        self.instance.main(
            [
                'get',
                '--id',
                'theId',
                '--range',
                'X:X',
                '--output=file.json',
                '-F',
                'field_1',
            ]
        )

        self.wrap.get_sheet.assert_called_with('theId', 'X:X')

    def test_get_sheet_2_col(self):
        """Test reading two columns."""
        self.instance.main(
            [
                'get',
                '--id',
                'theId',
                '--output=file.json',
                '-F',
                'field_1',
                '-F',
                'field_2',
            ]
        )

        self.wrap.get_sheet.assert_called_with('theId')
        output_file = self.fs.get_object('file.json')
        self.assertIsNotNone(output_file)
        self.assertEqual(
            json.loads(output_file.contents or ''),
            [
                {'field_1': 999, 'field_2': None},
                {'field_1': 888, 'field_2': 'some_text'},
            ],
        )

    def test_get_sheet_with_header(self):
        """Test reading from sheet with header row."""
        self.sheet.sheets[0].data[0].rowData.insert(
            0, sheets_types.RowData.model_validate(HEADER_ROW)
        )
        self.instance.main(
            ['get', '--id', 'theId', '--output=file.json', '--header_row', '0']
        )

        self.wrap.get_sheet.assert_called_with('theId')
        msg_file = self.fs.get_object('file.json')
        self.assertIsNotNone(msg_file)
        self.assertEqual(
            json.loads(msg_file.contents or ''),
            [
                {'header_1': 999, 'header_2': None},
                {'header_1': 888, 'header_2': 'some_text'},
            ],
        )
