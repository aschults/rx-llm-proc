# `calendar_cli`: Google Calendar Tool

## Introduction

The `calendar_cli` tool provides a command-line interface for managing Google Calendar events. It allows you to search for, create, and update events, making it easy to integrate calendar management into your automated workflows.

- **See Also**: [[CommandLineExamples]]

## Authentication

All `calendar_cli` commands require authentication to access your Google Calendar data. The tool uses the standard `rxllmproc` authentication flow.

> For a full explanation, please read **[[CommandLineCredentialsManagement]]**.

---

## `list` Command

Searches for calendar events and returns a list.

### Usage

```shell
calendar_cli list [OPTIONS] [QUERY]
```

### Arguments and Options

| Argument/Option         | Description                                                                 |
| :---------------------- | :-------------------------------------------------------------------------- |
| `QUERY`                 | (Optional) Free text search terms to find events.                           |
| `--calendar_id <ID>`    | Calendar identifier. Defaults to `primary`.                                 |
| `--time_min <RFC3339>`  | Lower bound (exclusive) for an event's end time to filter by.               |
| `--time_max <RFC3339>`  | Upper bound (exclusive) for an event's start time to filter by. Defaults to 90 days in the future. |
| `--max_results <INT>`   | Maximum number of results to return.                                        |
| `--single_events`       | Whether to expand recurrent events into instances.                          |
| `--i_cal_uid <UID>`     | Specifies an event's iCalendar UID to filter by.                           |
| `--max_attendees <INT>` | The maximum number of attendees to include in the response.                |
| `--as_json`             | Output the list of events as a JSON array.                                  |
| `--delimiter <CHAR>`    | Character to use as a separator in the default CSV-like output (default: TAB). |
| `--output <FILE>` / `-o` | Write output to FILE instead of STDOUT.                                     |

### Example

List all events in the next week containing the word "Meeting".

```bash
calendar_cli list "Meeting" --time_min "2024-03-10T00:00:00Z" --time_max "2024-03-17T00:00:00Z"
```

---

## `create` Command

Creates a new calendar event from JSON input.

### Usage

```shell
calendar_cli create [OPTIONS] [INPUT_FILE]
```

### Arguments and Options

| Argument/Option      | Description                                          |
| :------------------- | :--------------------------------------------------- |
| `INPUT_FILE`         | (Optional) Read event JSON from file. If omitted, reads from STDIN. |
| `--calendar_id <ID>` | Calendar identifier. Defaults to `primary`.          |

### Example

Create an event from a file named `event.json`.

```bash
calendar_cli create event.json
```

**Sample `event.json`:**

```json
{
  "summary": "Project Sync",
  "location": "Virtual",
  "description": "Weekly sync on the new project.",
  "start": {
    "dateTime": "2024-03-11T10:00:00Z"
  },
  "end": {
    "dateTime": "2024-03-11T11:00:00Z"
  },
  "attendees": [
    {"email": "colleague@example.com"}
  ]
}
```

---

## `update` Command

Updates an existing calendar event from JSON input. The JSON must include the `id` of the event to be updated.

### Usage

```shell
calendar_cli update [OPTIONS] [INPUT_FILE]
```

### Arguments and Options

| Argument/Option      | Description                                          |
| :------------------- | :--------------------------------------------------- |
| `INPUT_FILE`         | (Optional) Read event JSON from file. If omitted, reads from STDIN. |
| `--calendar_id <ID>` | Calendar identifier. Defaults to `primary`.          |

### Example

Update an existing event.

```bash
calendar_cli update updated_event.json
```
