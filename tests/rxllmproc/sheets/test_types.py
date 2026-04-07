"""Tests for the GMail base types."""

import unittest
from typing import Any, Dict

from rxllmproc.sheets import types as sheets_types

TEST_ROW1: Dict[str, Any] = {
    'values': [
        {
            'effectiveValue': {
                'numberValue': None,
                'stringValue': None,
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            },
        },
        {
            'effectiveValue': {
                'numberValue': 22,
                'stringValue': None,
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            },
        },
        {
            'effectiveValue': {
                'numberValue': None,
                'stringValue': 'abc',
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            },
        },
        {
            'effectiveValue': {
                'numberValue': None,
                'stringValue': None,
                'boolValue': True,
                'formulaValue': None,
                'errorValue': None,
            },
        },
        {
            'effectiveValue': {
                'numberValue': None,
                'stringValue': None,
                'boolValue': None,
                'formulaValue': '=123',
                'errorValue': None,
            },
        },
        {
            'effectiveValue': {
                'numberValue': None,
                'stringValue': None,
                'boolValue': None,
                'formulaValue': None,
                'errorValue': {'type': '', 'message': 'xxx'},
            },
        },
    ]
}

TEST_ROW2: Dict[str, Any] = {
    'values': [
        {
            'effectiveValue': {
                'numberValue': 33,
                'stringValue': None,
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            },
        },
        {
            'effectiveValue': {
                'numberValue': 23,
                'stringValue': None,
                'boolValue': None,
                'formulaValue': None,
                'errorValue': None,
            },
        },
    ]
}


class TestRowdata(unittest.TestCase):
    """Test the RowData methods."""

    def setUp(self) -> None:
        """Set up providing a sample row."""
        self.row = sheets_types.RowData.model_validate(TEST_ROW1)

    def test_get_values(self):
        """Test converting values.

        This implicitly tests ExtendedValue.getMergedValue.
        """
        self.assertEqual(
            [
                None,
                22,
                'abc',
                True,
                sheets_types.Formula(formula='=123'),
                sheets_types.ErrorValue(type='', message='xxx'),
            ],
            self.row.getValues(),
        )

    def test_get_values_fails(self):
        """Test converting values.

        This implicitly tests ExtendedValue.getMergedValue.
        """
        row = sheets_types.RowData.model_validate(
            {
                'values': [
                    {
                        'effectiveValue': {
                            'numberValue': 1,
                            'stringValue': 'xx',
                            'boolValue': None,
                            'formulaValue': None,
                            'errorValue': None,
                        },
                    },
                ]
            },
        )
        self.assertRaisesRegex(ValueError, 'Only one', lambda: row.getValues())

    def test_normalize_shorter(self):
        """Test normalizing rows, making it shorter."""
        self.row.normalzeRows(2)
        self.assertEqual([None, 22], self.row.getValues())

    def test_normalize_wider(self):
        """Test normalizing rows, making it longer."""
        self.row.normalzeRows(7)
        self.assertEqual(
            [
                None,
                22,
                'abc',
                True,
                sheets_types.Formula(formula='=123'),
                sheets_types.ErrorValue(type='', message='xxx'),
                None,
            ],
            self.row.getValues(),
        )

    def test_normalize_zero_length(self):
        """Test normalizing rows, making it shorter."""
        self.row.normalzeRows(0)
        self.assertEqual([], self.row.getValues())


class TestDictConverter(unittest.TestCase):
    """Test the row to dict converter."""

    def setUp(self) -> None:
        """Set up providing a sample row."""
        self.row = sheets_types.RowData.model_validate(TEST_ROW1)

    def test_make_converter(self):
        """Test producing and using a dict converter."""
        converter = sheets_types.makeRowDictConverter('a', 'b', 'c')
        self.assertEqual(
            {'a': None, 'b': 22, 'c': 'abc'}, converter(self.row, 1)
        )

    def test_make_converter_overlength(self):
        """Test when not enough columns in the provided row."""
        self.row.normalzeRows(2)
        converter = sheets_types.makeRowDictConverter('a', 'b', 'c')
        self.assertEqual(
            {'a': None, 'b': 22, 'c': None}, converter(self.row, 1)
        )

    def test_make_converter_all_fields(self):
        """Test all field decriptor attributes."""
        self.row.normalzeRows(2)
        converter = sheets_types.makeRowDictConverter(
            {'name': 'x', 'defaultValue': 333},
            {
                'name': 'y',
                'defaultValue': 333,
                'valueConverter': lambda v: (
                    (
                        v.effectiveValue or sheets_types.ExtendedValue()
                    ).numberValue
                    or 0
                )
                + 1,
            },
            {'name': 'z', 'defaultValue': 333},
        )
        self.assertEqual({'x': None, 'y': 23, 'z': 333}, converter(self.row, 1))

    def test_make_converter_skip(self):
        """Test Skipping on None fields."""
        self.row.normalzeRows(2)
        converter = sheets_types.makeRowDictConverter(None, 'b', 'c')
        self.assertEqual({'b': 22, 'c': None}, converter(self.row, 1))

    def test_make_converter_row_field(self):
        """Test Skipping on None fields."""
        self.row.normalzeRows(2)
        converter = sheets_types.makeRowDictConverter(
            None, 'b', rowNumberField='r'
        )
        self.assertEqual({'b': 22, 'r': 99}, converter(self.row, 99))


class TestGridData(unittest.TestCase):
    """Test the GridData methods."""

    def setUp(self) -> None:
        """Set up the grid."""
        grid_dict: Dict[str, Any] = {
            'startRow': 0,
            'startColumn': 0,
            'rowData': [TEST_ROW1, TEST_ROW2],
        }
        self.grid = sheets_types.GridData.model_validate(grid_dict)

    def test_normalze(self):
        """Check that normalization to the largest works."""
        self.assertEqual(
            [33, 23, None, None, None, None], self.grid.getRow(1).getValues()
        )

    def test_normalze_shorten(self):
        """Check that normalization to the largest works."""
        self.grid.normalzeRows(1)
        self.assertEqual([None], self.grid.getRow(0).getValues())
        self.assertEqual([33], self.grid.getRow(1).getValues())

    def test_normalze_longer(self):
        """Check that normalization to the largest works."""
        self.grid.normalzeRows(7)
        self.assertEqual(7, len(self.grid.getRow(0).getValues()))
        self.assertEqual(
            [33, 23, None, None, None, None, None],
            self.grid.getRow(1).getValues(),
        )

    def test_iterate(self):
        """Check iteration."""

        def _get_second_col(row: sheets_types.RowData, rowNum: int):
            return row.getValues()[1]

        self.assertEqual([22, 23], list(self.grid.iterateRows(_get_second_col)))

    def test_iterate_row_num(self):
        """Check iteration, getting row number."""

        def _get_row_num(row: sheets_types.RowData, rowNum: int):
            return rowNum

        self.assertEqual([0, 1], list(self.grid.iterateRows(_get_row_num)))

    def test_iterate_start_row(self):
        """Check iteration with start row."""

        def _convert(row: sheets_types.RowData, rowNum: int):
            return (rowNum, row.getValues()[1])

        self.assertEqual(
            [(1, 23)], list(self.grid.iterateRows(_convert, firstRow=1))
        )

    def test_iterate_grid_start_row(self):
        """Check iteration with grid start row."""

        def _convert(row: sheets_types.RowData, rowNum: int):
            return (rowNum, row.getValues()[1])

        self.grid.startRow = 5

        self.assertEqual(
            [(5, 22), (6, 23)],
            list(self.grid.iterateRows(_convert, firstRow=5)),
        )

    def test_iterate_grid_start_row_fail(self):
        """Check iteration with grid start row."""

        def _convert(row: sheets_types.RowData, rowNum: int):
            return (rowNum, row.getValues()[1])

        self.grid.startRow = 5

        self.assertRaisesRegex(
            IndexError,
            'grid start row',
            lambda: self.grid.iterateRows(_convert, firstRow=4),
        )

    def test_iterate_grid_empty_rows(self):
        """Check iteration with grid start row."""

        def _convert(row: sheets_types.RowData, rowNum: int):
            return (rowNum, row.getValues()[1])

        self.grid.rowData.append(sheets_types.RowData(values=[]))
        self.grid.rowData.append(sheets_types.RowData(values=[]))

        self.assertEqual(
            [(0, 22), (1, 23)], list(self.grid.iterateRows(_convert))
        )

    def test_iterate_grid_empty_rows_intermediate(self):
        """Check iteration with grid start row."""

        def _convert(row: sheets_types.RowData, rowNum: int):
            return (rowNum, row.getValues()[1])

        self.grid.rowData.append(sheets_types.RowData(values=[]))
        self.grid.rowData.append(self.grid.rowData[0])
        self.grid.normalzeRows()

        self.assertEqual(
            [(0, 22), (1, 23), (3, 22)],
            list(self.grid.iterateRows(_convert, acceptedEmptyRows=1)),
        )

    def test_iterate_grid_empty_rows_intermediate2(self):
        """Check iteration with grid start row."""

        def _convert(row: sheets_types.RowData, rowNum: int):
            return (rowNum, row.getValues()[1])

        self.grid.rowData.append(sheets_types.RowData(values=[]))
        self.grid.rowData.append(sheets_types.RowData(values=[]))
        self.grid.rowData.append(self.grid.rowData[0])
        self.grid.normalzeRows()

        self.assertEqual(
            [(0, 22), (1, 23)],
            list(self.grid.iterateRows(_convert, acceptedEmptyRows=1)),
        )

    def test_iterate_grid_empty_rows_intermediate2_2(self):
        """Check iteration with grid start row."""

        def _convert(row: sheets_types.RowData, rowNum: int):
            return (rowNum, row.getValues()[1])

        self.grid.rowData.append(sheets_types.RowData(values=[]))
        self.grid.rowData.append(sheets_types.RowData(values=[]))
        self.grid.rowData.append(self.grid.rowData[0])
        self.grid.normalzeRows()

        self.assertEqual(
            [(0, 22), (1, 23), (4, 22)],
            list(self.grid.iterateRows(_convert, acceptedEmptyRows=2)),
        )

    def test_iterate_grid_empty_rows_intermediate_include(self):
        """Check iteration with grid start row."""

        def _convert(row: sheets_types.RowData, rowNum: int):
            return (rowNum, row.getValues()[1])

        self.grid.rowData.append(sheets_types.RowData(values=[]))
        self.grid.rowData.append(self.grid.rowData[0])
        self.grid.normalzeRows()

        self.assertEqual(
            [(0, 22), (1, 23), (2, None), (3, 22)],
            list(
                self.grid.iterateRows(
                    _convert, acceptedEmptyRows=1, includeEmptyRows=True
                )
            ),
        )

    def test_iterate_grid_empty_rows_intermediate_include2(self):
        """Check iteration with grid start row."""

        def _convert(row: sheets_types.RowData, rowNum: int):
            return (rowNum, row.getValues()[1])

        self.grid.rowData.append(sheets_types.RowData(values=[]))
        self.grid.rowData.append(sheets_types.RowData(values=[]))
        self.grid.rowData.append(self.grid.rowData[0])
        self.grid.normalzeRows()

        self.assertEqual(
            [(0, 22), (1, 23), (2, None), (3, None), (4, 22)],
            list(
                self.grid.iterateRows(
                    _convert, acceptedEmptyRows=2, includeEmptyRows=True
                )
            ),
        )
