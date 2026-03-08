# `tasks_cli`: Google Tasks Tool

## Introduction

The `tasks_cli` tool provides a command-line interface for managing your Google
Tasks. It allows you to list task lists, list tasks within those lists, and add
or update tasks.

- **See Also**: [[CommandLineExamples]]

## Authentication

All `tasks_cli` commands require authentication. The tool uses the standard
`rxllmproc` authentication flow.

---

## `list_tasklists` Command

Lists all available task lists in your Google account.

### Usage

```shell
tasks_cli list_tasklists [OPTIONS]
```

### Arguments and Options

| Argument/Option   | Description                         |
| :---------------- | :---------------------------------- |
| `--as_json`       | Output the list as a JSON array.    |
| `--output <FILE>` | Path to a file to write the output. |

### Example

```bash
tasks_cli list_tasklists
```

**Sample Output:**

```
ID                                      Title
MTM1...zYy                              My Tasks
ZDEw...xMj                              Work Projects
```

---

## `list` Command

Lists tasks from one or all task lists.

### Usage

```shell
tasks_cli list [OPTIONS]
```

### Arguments and Options

| Argument/Option      | Description                                                                |
| :------------------- | :------------------------------------------------------------------------- |
| `--tasklist_id <ID>` | ID of the task list. If omitted, tasks from all lists are shown.           |
| `--as_json`          | Output the tasks as a JSON array.                                          |
| `--include_plain`    | Include tasks that are not "managed" (those without an external `id_url`). |
| `--output <FILE>`    | Path to a file to write the output.                                        |

### Example

```bash
tasks_cli list --tasklist_id MTM1...zYy
```

**Sample Output:**

```
ID                                      Title                 Status
TVRB...zE1                              Call client           needsAction
TVRB...zE2                              Review PR             completed
```

---

## `add` Command

Adds a new task to a specific task list.

### Usage

```shell
tasks_cli add --tasklist_id <ID> --title <TITLE> --id_url <URL> [OPTIONS]
```

### Arguments and Options

| Argument/Option      | Description                                               |
| :------------------- | :-------------------------------------------------------- |
| `--tasklist_id <ID>` | **(Required)** ID of the task list to add the task to.    |
| `--title <TITLE>`    | **(Required)** Title of the task.                         |
| `--id_url <URL>`     | **(Required)** External ID URL for identifying the task.  |
| `--notes <NOTES>`    | Optional notes/description for the task.                  |
| `--due <DATE>`       | Due date for the task in ISO format (e.g., `2024-12-31`). |
| `--dry_run`          | Log actions without executing.                            |

---

## `update` Command

Updates an existing task, identified by its `id_url`.

### Usage

```shell
tasks_cli update --id_url <URL> [OPTIONS]
```

### Arguments and Options

| Argument/Option      | Description                                                           |
| :------------------- | :-------------------------------------------------------------------- |
| `--id_url <URL>`     | **(Required)** The external ID URL of the task to update.             |
| `--tasklist_id <ID>` | Optional ID of the task list. If omitted, all lists will be searched. |
| `--title <TITLE>`    | New title for the task.                                               |
| `--notes <NOTES>`    | New notes for the task.                                               |
| `--due <DATE>`       | New due date for the task.                                            |
| `--status <STATUS>`  | New status: `needsAction` or `completed`.                             |
| `--dry_run`          | Log actions without executing.                                        |

---

## `batch` Command

Batch upserts managed tasks from a JSON file or standard input.

### Usage

```shell
tasks_cli batch [OPTIONS] [INPUT_FILE]
```

### Arguments and Options

| Argument/Option              | Description                                                                      |
| :--------------------------- | :------------------------------------------------------------------------------- |
| `[INPUT_FILE]`               | Path to a JSON file containing an array of tasks. Reads from `stdin` if omitted. |
| `--default_tasklist_id <ID>` | Default task list ID to use for new tasks in the batch.                          |
| `--dry_run`                  | Log actions without executing.                                                   |
