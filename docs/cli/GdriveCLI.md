# `gdrive_cli`: Google Drive Tool

## Introduction

The `gdrive_cli` tool provides a command-line interface for interacting with
files in Google Drive. It allows you to list, download (`get`), and upload
(`put`) files, making it a crucial component for workflows that need to source
data from or save artifacts to Google Drive.

- **See Also**: [[CommandLineExamples]]

## Authentication

All `gdrive_cli` commands require authentication. The tool uses the standard
`rxllmproc` authentication flow.

> For a full explanation, please read **[[CommandLineCredentialsManagement]]**.

---

## `list` Command

Searches for files in your Google Drive and lists their metadata.

### Usage

```shell
gdrive_cli list [OPTIONS] "DRIVE_QUERY"
```

### Arguments and Options

| Argument/Option      | Description                                                                                                                                                 |
| :------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DRIVE_QUERY`        | **(Required)** The search query string. Uses the same syntax as the [Google Drive API search](https://developers.google.com/drive/api/guides/search-files). |
| `--delimiter <CHAR>` | Put <CHAR> between fields in the output table.                                                                                                              |
| `--as_json`          | Output the list of files as a JSON array (mutually exclusive with `--delimiter`).                                                                           |
| `--output <FILE>`    | Path to a file to write the output to, instead of standard output.                                                                                          |

### Example

List all Google Docs modified in the last 7 days and format the output as a CSV.

```bash
gdrive_cli list \
  --delimiter "," \
  "mimeType='application/vnd.google-apps.document' and modifiedTime > '2024-01-01T00:00:00Z'"
```

**Sample Output:**

```csv
id,name,fileExtension,mimeType,description,md5Checksum,modifiedTime
1Bz...P02,Project Plan,,application/vnd.google-apps.document,,...,2024-01-21T22:11:00.083Z
```

---

## `get` Command

Downloads a file from Google Drive by its unique ID.

### Usage

```shell
gdrive_cli get [OPTIONS]
```

### Arguments and Options

| Argument/Option      | Description                                                                                                                                                             |
| :------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--id <DRIVE_ID>`    | **(Required)** The unique ID of the file to download. You can get this from the `list` command or from the file's URL in Google Drive.                                  |
| `--as_html`          | For Google Workspace files (Docs, Sheets), exports the content as HTML.                                                                                                 |
| `--as_markdown`      | Downloads as Markdown, converting from HTML.                                                                                                                            |
| `--export_as <MIME>` | For Google Workspace files, exports the content to a specific [MIME type](https://developers.google.com/drive/api/guides/ref-export-formats) (e.g., `application/pdf`). |
| `--output <FILE>`    | Path to a file to save the content to, instead of printing to standard output.                                                                                          |
| `--dry_run`          | Execute but don't change anything.                                                                                                                                      |

---

## `get_all` Command

Downloads all files matching a query to a specified directory.

### Usage

```shell
gdrive_cli get_all --output_dir <DIR> [OPTIONS] "DRIVE_QUERY"
```

### Arguments and Options

| Argument/Option      | Description                                                   |
| :------------------- | :------------------------------------------------------------ |
| `DRIVE_QUERY`        | **(Required)** The search query string.                       |
| `--output_dir <DIR>` | **(Required)** Directory under which the results are written. |
| `--force` / `-f`     | If set, overwrite existing files.                             |
| `--as_html`          | Download as HTML.                                             |
| `--as_markdown`      | Download as Markdown, converting from HTML.                   |
| `--export_as <MIME>` | Convert to specific Mime type during download.                |
| `--dry_run`          | Execute but don't change anything.                            |

---

## `put` Command

Creates a new file or updates an existing file in Google Drive. The content can
be read from a local file or from standard input.

### Usage

```shell
gdrive_cli put [OPTIONS] [INPUT_FILE]
```

If `INPUT_FILE` is omitted, the command will read content from standard input.

### Arguments and Options

| Argument/Option            | Description                                                                                                   |
| :------------------------- | :------------------------------------------------------------------------------------------------------------ |
| `--create_name <FILENAME>` | Create a new file on Drive with the specified name.                                                           |
| `--update_id <DRIVE_ID>`   | Update the content of an existing file identified by its unique ID.                                           |
| `--update_name <FILENAME>` | Update the content of an existing file identified by its name.                                                |
| `--mime_type <MIME>`       | Manually specify the MIME type for the uploaded file (e.g., `text/plain`, `application/pdf`).                 |
| `--dry_run`                | Execute but don't change anything.                                                                            |
| `[INPUT_FILE]`             | (Optional) The path to a local file whose content will be uploaded. If omitted, content is read from `stdin`. |

> **Important**: When using `--update_name`, the operation will fail if the name
> is not unique. If you expect name collisions, use `gdrive_cli list` to find
> the unique file ID first, then update with `--update_id`.
