"""Types used with the Google Sheets REST interface."""

from typing import Any, Protocol, List


class SpreadsheetsHttpRequestInterface(Protocol):
    """Partial and type anostic request interface."""

    def execute(self) -> Any:
        """Execute the formed request."""


class SpreadsheetsInterface(Protocol):
    """spreadsheets() API part."""

    def get(
        self,
        *,
        spreadsheetId: str,
        ranges: List[str] | str = [],
        includeGridData: bool,
        **kwargs: Any,
    ) -> SpreadsheetsHttpRequestInterface:
        """Get a spreadsheet."""
        ...


class SheetsInterface(Protocol):
    """Top level GMail API interface."""

    def spreadsheets(self) -> SpreadsheetsInterface:
        """Get the users API part."""
        ...
