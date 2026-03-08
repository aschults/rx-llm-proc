# `conversion_cli`: Format Conversion Tool

## Introduction

The `conversion_cli` tool is a versatile command-line utility for converting
between different file formats. It can detect MIME types automatically from file
extensions or accept manual overrides.

- **See Also**: [[CommandLineExamples]]

---

## Usage

```shell
conversion_cli [OPTIONS] [INPUT_FILE]
```

If `INPUT_FILE` is omitted, the tool will read from standard input.

### Options

| Option                    | Description                                             |
| :------------------------ | :------------------------------------------------------ |
| `--from-mime-type <MIME>` | Manually specify the input's MIME type.                 |
| `--to-mime-type <MIME>`   | Manually specify the desired output MIME type.          |
| `--output` / `-o <FILE>`  | Path to a file to write the output.                     |
| `--verbose` / `-v`        | Enable verbose logging.                                 |
| `--dry_run`               | Log the conversion configuration without performing it. |

### Example

Convert a Markdown file to HTML.

```bash
conversion_cli --to-mime-type "text/html" README.md > README.html
```
