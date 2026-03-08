# `template_cli`: Jinja2 Template Tool

## Introduction

The `template_cli` tool provides a command-line interface for rendering
[Jinja2](https://jinja.palletsprojects.com/) templates. It allows you to provide
template files and variables, and output the rendered result.

- **See Also**: [[CommandLineExamples]]

---

## Usage

```shell
template_cli [OPTIONS] [args ...]
```

### Options

| Option                        | Description                                             |
| :---------------------------- | :------------------------------------------------------ |
| `--template <PATH>`           | **(Required)** The path to the Jinja2 template file.    |
| `-D <KEY=VALUE>` / `--define` | Define a template variable. Can be used multiple times. |
| `--output` / `-o <FILE>`      | Path to a file to write the rendered output.            |
| `--verbose` / `-v`            | Enable verbose logging.                                 |
| `--dry_run`                   | Log the configuration without rendering the template.   |

## Standard Input

The content of standard input is available in the template via the `stdin`
variable.

## Available Filters

In addition to the standard Jinja2 filters, the following custom filters are
available:

| Filter         | Description                                                            | Usage                                      |
| :------------- | :--------------------------------------------------------------------- | :----------------------------------------- |
| `req(message)` | Raises an error if the variable is undefined.                          | `{{ my_var \| req("my_var is missing") }}` |
| `as_markdown`  | Converts HTML content to Markdown.                                     | `{{ html_content \| as_markdown }}`        |
| `clean_html`   | Cleans up HTML content (removes scripts, styles, etc.).                | `{{ raw_html \| clean_html }}`             |
| `email_msg`    | Extracts the body content from a Gmail API message object.             | `{{ email_rfc_object \| email_msg }}`      |
| `render`       | Renders a string as a Jinja2 template, inheriting the current context. | `{{ nested_template_string \| render }}`   |

### Examples

#### Render a simple template with variables

```bash
template_cli --template "report.j2" -D "title=Weekly Report" -D "date=2024-01-22"
```

#### Render a template from standard input (if supported, but usually it takes a file)

The current implementation of `template_cli` requires a `--template` path.
