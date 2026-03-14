"""Google Sheets REST interface wrapper."""

import logging

from googleapiclient import discovery
import dacite

from rxllmproc.sheets import types as sheets_types
from rxllmproc.core import auth
from rxllmproc.core import api_base
from rxllmproc.sheets import _interface


class SheetsWrapper(api_base.ApiBase):
    """Wrapper around Google Sheets API."""

    def __init__(
        self,
        creds: auth.Credentials | None = None,
        service: _interface.SheetsInterface | None = None,
    ):
        """Create an instance.

        Args:
            creds: Credentials to be used for the requests.
            service: Optionally provide service instance (mailnly for testing.)
                Note: If provided, this instance is shared across threads and
                is not thread-safe.
        """
        super().__init__(creds)
        self._service: _interface.SheetsInterface = service or discovery.build(
            "sheets",
            "v4",
            credentials=self._creds,
            requestBuilder=self.build_request,
        )

    def get_sheet(
        self, spreadsheet_id: str, *ranges: str, includeGridData: bool = True
    ) -> sheets_types.Spreadsheet:
        """Get a spreadsheet by ID."""
        logging.info(
            'Fetching data from sheets: id=%s, ranges=%s',
            repr(spreadsheet_id),
            repr(ranges),
        )
        result_dict = (
            self._service.spreadsheets()
            .get(
                spreadsheetId=spreadsheet_id,
                includeGridData=includeGridData,
                ranges=list(ranges),
            )
            .execute()
        )
        config = dacite.Config(strict=False)
        spreadsheet = dacite.from_dict(
            sheets_types.Spreadsheet, result_dict, config=config
        )

        return spreadsheet
