# `gmail_cli`: Gmail Tool

## Introduction

The `gmail_cli` tool provides a command-line interface for searching and
retrieving emails from a Google Gmail account. It is a fundamental building
block for any workflow that begins with an email, allowing you to find specific
messages and download them for further processing.

- **See Also**: [[CommandLineExamples]]

## Authentication

All `gmail_cli` commands require authentication to access your Gmail data. The
tool uses the standard `rxllmproc` authentication flow.

> For a full explanation, please read **[[CommandLineCredentialsManagement]]**.

---

## `get_all` Command

Searches for emails matching a query and downloads them to a specified
directory.

### Usage

```shell
gmail_cli get_all [OPTIONS] "GMAIL_SEARCH_QUERY"
```

### Arguments and Options

| Argument/Option      | Description                                                                                                                                                                       |
| :------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GMAIL_SEARCH_QUERY` | **(Required)** The search query string, using the same syntax as the [Gmail search box](https://support.google.com/mail/answer/7190) (e.g., `"from:boss@example.com is:unread"`). |
| `--output_dir <DIR>` | **(Required)** Directory under which the results are written.                                                                                                                     |
| `--force` / `-f`     | If set, overwrite files if they exist.                                                                                                                                            |
| `--by_thread`        | If set, create subdirectories for each thread.                                                                                                                                    |
| `--to_markdown`      | If set, convert email body to Markdown and save as .md files.                                                                                                                     |
| `--with_index`       | If set, create an `index.json` file in the output directory with metadata for all downloaded messages.                                                                            |
| `--dry_run`          | Execute but don't change anything.                                                                                                                                                |

### Example

Download all unread emails from the last 24 hours to a directory named
`unread_emails`, converting them to Markdown.

```bash
gmail_cli get_all "is:unread newer_than:1d" --output_dir unread_emails --to_markdown --with_index
```

The tool will create the `unread_emails` directory (if it doesn't exist) and
save each email as a file, named by its Gmail message ID. If `--to_markdown` is
used, the files will have a `.md` extension.

**Sample `index.json` content:**

```json
[
  {
    "id": "18d6b1d034b7f8b9",
    "path": "18d6b1d034b7f8b9.md",
    "subject": "Project Update",
    "received_date": "2024-02-15T09:00:00Z",
    "snippet": "Here is the latest update on the project...",
    "senders": "boss@example.com",
    "recipients": "me@example.com",
    "cc": "",
    "bcc": "",
    "url": "https://mail.google.com/mail/u/0/#inbox/18d6b1d034b7f8b9"
  }
]
```
