"""Types used for Google Sheets."""

import dataclasses
from typing import (
    Literal,
    Callable,
    TypeVar,
    Iterator,
    Dict,
    Any,
    Generic,
    TypedDict,
)

_T = TypeVar('_T')


class Formula:
    """Represents a Sheets formula."""

    def __init__(self, formula: str) -> None:
        """Create an instance."""
        self.formula = formula

    def __eq__(self, value: object) -> bool:
        """Compare with other Formula."""
        if isinstance(value, Formula):
            return self.formula == value.formula
        return False


@dataclasses.dataclass
class ErrorValue:
    """Represents error value, as read from the API.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#ErrorValue.
    """

    type: Literal['']
    message: str


# All types a cell value can be.
CellValueType = float | str | bool | ErrorValue | Formula | None


@dataclasses.dataclass
class ExtendedValue:
    """Cell value, as read from the API.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#ExtendedValue.
    """

    numberValue: float | None = None
    stringValue: str | None = None
    boolValue: bool | None = None
    formulaValue: str | None = None
    errorValue: ErrorValue | None = None

    def _checkValid(self) -> CellValueType:
        """Check if the value is valid."""
        numSet = 0
        if self.numberValue is not None:
            numSet += 1
        if self.stringValue is not None:
            numSet += 1
        if self.boolValue is not None:
            numSet += 1
        if self.errorValue is not None:
            numSet += 1
        if self.formulaValue is not None:
            numSet += 1

        if numSet > 1:
            raise ValueError(f'Only one value type should be set {self}')

    def getMergedValue(self) -> CellValueType:
        """Convert an extended value object into the actual, typed values."""
        self._checkValid()
        if self.numberValue is not None:
            return self.numberValue
        if self.stringValue is not None:
            return self.stringValue
        if self.boolValue is not None:
            return self.boolValue
        if self.errorValue is not None:
            return self.errorValue
        if self.formulaValue is not None:
            return Formula(self.formulaValue)
        return None


@dataclasses.dataclass
class Color:
    """Representation of a color.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#Color
    """

    red: float
    green: float
    blue: float


@dataclasses.dataclass
class Link:
    """Representation of Link in the API.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#link
    """

    uri: str


@dataclasses.dataclass
class TextFormat:
    """Format of one run of the cell text.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#TextFormat
    """

    foregroundColor: Color | None = None
    fontFamily: str | None = None
    fontSize: int | None = None
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    link: Link | None = None


@dataclasses.dataclass
class TextFormatRun:
    """Text format for a fragment of the text.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/cells#TextFormatRun
    """

    format: TextFormat
    startIndex: int = 0


@dataclasses.dataclass
class CellData:
    """Data for a single cell, as returned from the API.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/cells#CellData.
    """

    userEnteredValue: ExtendedValue | None = None
    effectiveValue: ExtendedValue | None = None
    formattedValue: str | None = None
    hyperlink: str | None = None
    note: str | None = None
    textFormatRuns: list[TextFormatRun] = dataclasses.field(
        default_factory=lambda: []
    )


@dataclasses.dataclass
class RowData:
    """Data for a row witin a GridData, as returned from the API.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#RowData.
    """

    values: list[CellData] = dataclasses.field(default_factory=lambda: [])

    def normalzeRows(self, width: int):
        """Bring the cells in the row to the indicated number of columns.

        Args:
            width: The number of columns. Short rows are extended with empty
                values, and long columns are clipped.
        """
        self.values = self.values[:width]
        while len(self.values) < width:
            self.values.append(CellData())

    def getValues(self) -> list[CellValueType]:
        """Convert the entire row."""
        return getEffectiveValueRow(self)

    def getLength(self) -> int:
        """Get the number of columns in the row."""
        return len(self.values)


def getEffectiveValueFromCell(cell: CellData) -> CellValueType:
    """Extract the effecive value from a cell."""
    if cell.effectiveValue is None:
        return None
    return cell.effectiveValue.getMergedValue()


def getEffectiveValueRow(
    row: RowData,
    valueConverter: Callable[[CellData], _T] = getEffectiveValueFromCell,
) -> list[_T]:
    """Get all effective values in a row, convering them along.

    Args:
        row: The row to convert.
        valueConverter: Callback to turn a cell(CellData) into the templated
            type.
    """
    return [valueConverter(value) for value in row.values]


@dataclasses.dataclass
class NamedRange:
    """Named range in the sheet.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets#NamedRange.
    """

    namedRangeId: str
    name: str
    range: 'GridRange'


@dataclasses.dataclass
class GridRange:
    """Range reference in a sheet.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#GridRange.
    """

    sheetId: int
    startRowIndex: int
    endRowIndex: int
    startColumnIndex: int
    endColumnIndex: int


@dataclasses.dataclass
class Sheet:
    """Single sheet in a spreadsheet.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#Sheet.
    """

    data: 'list[GridData]'


@dataclasses.dataclass
class Spreadsheet:
    """Response for spreadsheets().get().

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets#Spreadsheet.
    """

    spreadsheetId: str
    sheets: list[Sheet]
    namedRanges: list[NamedRange] = dataclasses.field(
        default_factory=lambda: []
    )


@dataclasses.dataclass
class GridData:
    """Grid cell data for a sheet or a section of a sheet.

    See Also:
    https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/sheets#GridData.
    """

    rowData: list[RowData]
    startRow: int = 0
    startColumn: int = 0

    def __post_init__(self):
        """Post-Init by normalizing rows to the widest row."""
        self.normalzeRows()

    def normalzeRows(self, width: int | None = None):
        """Bring all rows in the grid to the specified width.

        Add empty values and remove excessive ones.

        Args:
            width: Width to trim/extend to. If omited, all rows are extended to
                the largest row.
        """
        if width is None:
            width = max(row.getLength() for row in self.rowData)
        for row in self.rowData:
            row.normalzeRows(width)

    def getRow(self, rowNum: int) -> RowData:
        """Get the row at `rowNum`, considering any offest from `startRow`."""
        rowNum -= self.startRow
        return self.rowData[rowNum]

    def iterateRows(
        self,
        rowConverter: Callable[[RowData, int], _T],
        isRowEmpty: Callable[[RowData], bool] | None = None,
        acceptedEmptyRows: int = 0,
        includeEmptyRows: bool = False,
        firstRow: int | None = None,
    ) -> Iterator[_T]:
        """Emit an object for each row of the grid."""
        return GridRowIterator(
            self,
            rowConverter,
            isRowEmpty,
            acceptedEmptyRows,
            includeEmptyRows,
            firstRow,
        )


# Converter function from Row to Dict.
DictConverterFunction = Callable[[RowData, int], Dict[str, Any]]


class DictFieldDescriptor(TypedDict, total=False):
    """Description on how to convert a Sheets value/columns to a dict value."""

    # The name of the column, i.e. the key to use when storing in the dict.
    # None indicates to skip the column.
    name: str

    # Optional function to convert the entire CellData.
    valueConverter: Callable[[CellData], Any]

    # Optional: Default Value
    defaultValue: Any


def makeRowDictConverter(
    *fields: str | None | DictFieldDescriptor, rowNumberField: str | None = None
) -> DictConverterFunction:
    """Define a converter function that converts rows into dicts.

    Args:
        fields: List of str or FieldDescriptor, each corresponding to one
            sheets column, starting at column A:
            - str: Dict key to use for the current column.
            - FieldDescriptor: Additional field settings for the conversion.
        rowNumberField: If set, adds the row number under this key in the dict.

    Return:
         Dict converter function.
    """

    def _converter(row: RowData, rowNum: int) -> Dict[str, CellValueType]:

        result: Dict[str, Any] = {}

        cleanedFields = [
            DictFieldDescriptor(name=field) if isinstance(field, str) else field
            for field in fields
        ]
        for fieldNum, field in enumerate(cleanedFields):
            if field is None:
                continue

            name = field.get('name', None)
            if name is None:
                continue

            converter: Callable[[CellData], Any] = field.get(
                'valueConverter', getEffectiveValueFromCell
            )
            cell = None
            if fieldNum < len(row.values):
                cell = row.values[fieldNum]
                value = converter(cell)
            else:
                value = field.get('defaultValue', None)

            result[name] = value
        if rowNumberField is not None:
            result[rowNumberField] = rowNum

        return result

    return _converter


class GridRowIterator(Generic[_T], Iterator[_T]):
    """Iterator returning an object for every row in the grid."""

    @staticmethod
    def _defaultIsRowEmpty(row: RowData) -> bool:
        """Determine if a row is empty, default behavior.

        Only None and '' is considered empty.
        """
        return all(
            value is None or value == '' for value in getEffectiveValueRow(row)
        )

    def __init__(
        self,
        gridData: GridData,
        rowConverter: Callable[[RowData, int], _T],
        isRowEmpty: Callable[[RowData], bool] | None = None,
        acceptedEmptyRows: int = 0,
        includeEmptyRows: bool = False,
        firstRow: int | None = None,
    ) -> None:
        """Create an instance.

        Args:
            gridData: The grid instance supplying the data.
            rowConverter: Callback to turn a row into a specific type.
            isRowEmpty: Optional callback to determine if a row is empty.
            acceptedEmptyRows: Number of rows that can be empty before
                considering a row the last one.
            includeEmptyRows: If set adds empty rows if accepting.
                Note: Empty rows at the end of the sheet are never included.
            firstRow: Row at which to start extracting.
        """
        super().__init__()
        self.gridData = gridData
        if firstRow is None:
            firstRow = gridData.startRow
        if firstRow < gridData.startRow:
            raise IndexError(
                f'first row {firstRow} < grid start row {gridData.startRow}'
            )

        self._acceptedEmptyRows = acceptedEmptyRows

        self.rowIndex = firstRow - gridData.startRow
        self._rowConverter = rowConverter
        self._isRowEmpty = isRowEmpty or self._defaultIsRowEmpty
        self._numEmptyRows = 0
        self._includeEmptyRows = includeEmptyRows

    def __iter__(self) -> Iterator[_T]:
        """Return the iterator."""
        return self

    def __next__(self) -> _T:
        """Advance to the next item."""
        if self.rowIndex >= len(self.gridData.rowData):
            raise StopIteration()

        row = self.gridData.rowData[self.rowIndex]
        self.rowIndex += 1
        while self._isRowEmpty(row):
            self._numEmptyRows += 1
            if self._numEmptyRows > self._acceptedEmptyRows:
                raise StopIteration
            if self._includeEmptyRows:
                return self._rowConverter(
                    row,
                    self.rowIndex + self.gridData.startRow - 1,
                )
            row = self.gridData.rowData[self.rowIndex]
            self.rowIndex += 1

        self._numEmptyRows = 0
        return self._rowConverter(
            row,
            self.rowIndex + self.gridData.startRow - 1,
        )
