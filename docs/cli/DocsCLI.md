# `docs_cli`: Google Docs Tool

## Introduction

The `docs_cli` tool provides a command-line interface for interacting with
Google Docs. It allows you to download documents as JSON and insert content
(including Markdown) into existing documents at specific locations.

- **See Also**: [[CommandLineExamples]]

## Authentication

All `docs_cli` commands require Google OAuth authentication. The tool uses the standard `rxllmproc` authentication flow.

> For a full explanation, please read **[[CommandLineCredentialsManagement]]**.

For operations that use the LLM (specifically the `--instructions` flag in the `insert` command), you also need a Gemini API key. It is recommended to set this via the `GEMINI_API_KEY` environment variable:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

---

## `get` Command


Downloads the full document object as JSON.

### Usage

```shell
docs_cli get --document_id <DOC_ID> [OPTIONS]
```

### Arguments and Options

| Argument/Option          | Description                                                        |
| :----------------------- | :----------------------------------------------------------------- |
| `--document_id <ID>`     | **(Required)** The unique ID of the Google Doc (found in the URL). |
| `--output` / `-o <FILE>` | Path to a file to write the JSON output.                           |
| `--nested`               | Output the document structure as a hierarchy of nested sections.   |

### Example

Get a document as JSON.

```bash
docs_cli get --document_id "1abc123..."
```

**Sample Output (simplified):**

```json
{
  "documentId": "1abc123...",
  "title": "Meeting Notes",
  "body": {
    "content": [
      {
        "startIndex": 1,
        "endIndex": 15,
        "paragraph": {
          "elements": [
            {
              "startIndex": 1,
              "endIndex": 15,
              "textRun": {
                "content": "Meeting Notes\n"
              }
            }
          ]
        }
      }
    ]
  }
}
```

---

## `insert` Command

Inserts text or Markdown content into a Google Doc at a specified location.

### Usage

```shell
docs_cli insert --document_id <DOC_ID> [LOCATION_OPTIONS] [INPUT_FILE]
```

If `INPUT_FILE` is omitted, the command reads the content to be inserted from
standard input.

### Arguments and Options

| Argument/Option           | Description                                                                                               |
| :------------------------ | :-------------------------------------------------------------------------------------------------------- |
| `--document_id <ID>`      | **(Required)** The unique ID of the Google Doc to modify.                                                 |
| `--at_start`              | Insert content at the very beginning of the document body.                                                |
| `--at_end`                | Insert content at the very end of the document body.                                                      |
| `--at_index <INDEX>`      | Insert at a specific character index in the document.                                                     |
| `--section_start`         | Insert at the beginning of the section identified by `--section`.                                         |
| `--section_end`           | Insert at the end of the section identified by `--section`.                                               |
| `--section_replace`       | Replace the existing content of the section identified by `--section` with the new content.               |
| `--section <REGEX>`       | A regular expression to find a section header. Can be used multiple times for nested/hierarchical search. |
| `--heading_id <ID>`       | The Google Docs heading ID of the section to target.                                                      |
| `--instructions <PROMPT>` | Use an LLM to determine where or how to update the document based on the provided instructions.           |
| `--plaintext`             | Treat the input content as plain text rather than Markdown.                                               |
| `--ensure-newline`        | Ensure the insertion occurs on a new line.                                                                |
| `--model <NAME>`          | The LLM model to use (if `--instructions` is used).                                                       |
| `-D <KEY=VALUE>`          | Define a template variable for use in the LLM instructions.                                               |
| `--dry_run`               | Log the modification request to standard error without applying changes.                                  |

### Examples

Insert the content of `notes.md` at the end of a document section named
"Summary".

```bash
docs_cli insert --document_id "1abc123..." --section "Summary" --section_end notes.md
```

Insert the content of `notes.md` to a specific category heading.

```bash
INSTRUCTIONS="Insert at the end of the first level 2 heading regarding `{{category}}`"
CATEGORY="Misc"
docs_cli insert \
   --document_id "1abc123..." \
   -D category="$CATEGORY" \
   --instructions="$INSTRUCTIONS" \
   notes.md
```
