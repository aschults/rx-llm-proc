"""Test the Sheets API wrapper."""

import unittest
from unittest import mock
from typing import Dict, Any

from google.oauth2 import credentials  # type: ignore

from rxllmproc.sheets import api as sheets_wrapper
from rxllmproc.sheets import _interface as _sheets_interface

ROW: Dict[str, Any] = {
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

GRID: Dict[str, Any] = {'rowData': [ROW], 'startRow': 22}
SPREADSHEET: Dict[str, Any] = {
    'spreadsheetId': 'theSheet',
    'sheets': [{'data': [GRID]}],
}


class TestWrapper(unittest.TestCase):
    """Test the wrapper class."""

    def setUp(self) -> None:
        """Provide mock cerds, service and user."""
        self.creds = mock.Mock(spec=credentials.Credentials)
        self.service = mock.Mock(spec=_sheets_interface.SheetsInterface)
        self.service.spreadsheets().get().execute.return_value = SPREADSHEET
        return super().setUp()

    def test_get_sheet(self):
        """Test getting a message."""
        wrapper = sheets_wrapper.SheetsWrapper(
            creds=self.creds, service=self.service
        )

        result = wrapper.get_sheet('theid', 'A:X')

        self.assertEqual([999], result.sheets[0].data[0].getRow(22).getValues())
        self.service.spreadsheets().get.assert_called_with(
            spreadsheetId='theid', includeGridData=True, ranges=['A:X']
        )
