# Command-Line Tool Reference

## Introduction

This section provides a reference for the individual command-line tools
available in the `Rx LLM Proc` library. These tools are the building blocks for
creating automated workflows. They are designed to be composed together, often
by "piping" the output of one command into the input of another.

While each tool can be used individually, their real power is realized when they
are chained together to solve a larger problem. For practical demonstrations of
how to combine them, please see the **[[CommandLineExamples]]** page.

## Available Tools

The following tools are available. Each link provides detailed information on
the tool's specific commands and arguments.

| Tool Name              | Description                                                               | Documentation Link     |
| :--------------------- | :------------------------------------------------------------------------ | :--------------------- |
| `gmail_cli`            | Fetches email messages and their content from a Gmail account.            | [[GmailCLI]]           |
| `gdrive_cli`           | Downloads and uploads files to and from Google Drive.                     | [[GdriveCLI]]          |
| `docs_cli`             | Accesses and modifies Google Docs.                                        | [[DocsCLI]]            |
| `tasks_cli`            | Manages tasks and task lists in Google Tasks.                             | [[TasksCLI]]           |
| `sheets_cli`           | Fetches data from specified ranges within a Google Sheet.                 | [[SheetsCLI]]          |
| `llm_cli`              | Sends a prompt (and optional context) to an LLM and returns the response. | [[LlmCLI]]             |
| `template_cli`         | Renders [Jinja2](https://jinja.palletsprojects.com/) templates.           | [[TemplateCLI]]        |
| `conversion_cli`       | A versatile tool to convert between different file formats.               | [[ConversionCLI]]      |
| `mail_categorizer_cli` | Categorizes emails from an index file using the Gemini API.              | [[MailCategorizerCLI]] |

## Common Concepts

While each tool has its own specific functionality, most of them share a set of
common concepts and arguments.

### Authentication

Tools that interact with Google Workspace require authentication. The first time
you use one of these tools, it will guide you through a one-time authorization
process in your browser.

> For a full explanation of this process, please read
> **[[CommandLineCredentialsManagement]]**.

### Piping Data

Most tools follow the Unix philosophy of reading from standard input (`stdin`)
and writing to standard output (`stdout`). This is what allows them to be
chained together with the `|` (pipe) operator. For example, you can pipe the
output of `gdrive_cli` directly into `llm_cli`.

## Argument Handling

Many tools in `rxllmproc` provide advanced ways to pass data through command-line arguments, beyond simple strings.

### File Expansion (`@`)

Whenever an argument value starts with the `@` symbol, the tool treats the following text as a filename and replaces the argument with the **entire content** of that file.

For example, instead of passing a long prompt directly:
```bash
llm_cli "Summarize this: $(cat very_long_text.txt)"
```
You can use:
```bash
llm_cli @very_long_text.txt
```

### Typed Arguments and JSON Parsing

You can explicitly specify how an argument should be parsed by prefixing it with a type in parentheses. This is particularly useful for passing structured data like JSON.

The syntax is `(type)value` or `(type)@filename`.

-   **JSON Parsing**: Use `(json)` to parse the value as a JSON object.
    ```bash
    # Passing a JSON string directly to a parameter
    mail_categorizer_cli categorize ... -P "config=(json){\"priority\": \"high\"}"

    # Loading JSON from a file for a template variable
    llm_cli -D "data=(json)@data.json" "Process this data."
    ```

-   **Automatic Type Inference**: If you use `()@filename`, the tool will attempt to infer the type from the file extension.
    ```bash
    # Equivalent to (json)@config.json
    llm_cli -D "config=()@config.json"
    ```

### Named Arguments (Key=Value)

Tools like `llm_cli` (using `-D` / `--define`) and `mail_categorizer_cli` (using `-P` / `--parameter`) accept key-value pairs. These values support the same expansion and typing logic described above.

```bash
mail_categorizer_cli categorize ... -P "threshold=0.5" -P "template=@my_prompt.j2" -P "metadata=(json)@meta.json"
```

## Common Arguments


Many tools support a set of standard command-line flags:

- **`--output <FILENAME>`**: By default, results are printed to standard output.
  This flag allows you to redirect the output directly to a file.
- **`--verbose` / `-v`**: Enables more detailed logging, which is useful for
  debugging.
- **`--help` / `-h`**: Shows a help message listing all available arguments for
  the command.
- **`--cache <PATH>`**: Path to a cache file for storing responses. See **[[Caching]]**.
- **`--max_cache_age <DAYS>`**: Maximum age of cache entries in days since last accessed.
