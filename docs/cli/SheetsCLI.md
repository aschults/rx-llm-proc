# `sheets_cli`: Google Sheets Tool

## Introduction

The `sheets_cli` tool provides a command-line interface for fetching data from
Google Sheets. It allows you to specify a spreadsheet and range, and retrieve
the data in JSON or CSV format.

NOTE: This tool is still under development and will be expanded with more
functionality.

- **See Also**: [[CommandLineExamples]]

## Authentication

All `sheets_cli` commands require authentication. The tool uses the standard
`rxllmproc` authentication flow.

---

## `get` Command

Retrieves data from a Google Sheet.

### Usage

```shell
sheets_cli get [OPTIONS]
```

### Arguments and Options

| Argument/Option          | Description                                                          |
| :----------------------- | :------------------------------------------------------------------- |
| `--id <SPREADSHEET_ID>`  | **(Required)** The unique ID of the Google Sheet (found in the URL). |
| `--range <SHEET_RANGE>`  | **(Required)** The A1 notation range (e.g., `Sheet1!A1:Z100`).       |
| `--field <FIELD_NAME>`   | Define field names for each column. Can be used multiple times.      |
| `--header_row <ROW_NUM>` | Uses row number `<ROW_NUM>` as a header row to derive field names.   |
| `--start_row <ROW_NUM>`  | The row number to start reading from (skips rows before this).       |
| `--output <FILE>`        | Path to a file to write the output.                                  |

### Example

Retrieve data from "Sheet1" of a spreadsheet, using the first row as headers.

```bash
sheets_cli get --id "1abc123..." --range "Sheet1!A1:C3" --header_row 1
```

**Sample Output (JSON):**

```json
[
  {
    "Name": "John Doe",
    "Email": "john@example.com",
    "Status": "Active"
  },
  {
    "Name": "Jane Smith",
    "Email": "jane@example.com",
    "Status": "Pending"
  }
]
```
