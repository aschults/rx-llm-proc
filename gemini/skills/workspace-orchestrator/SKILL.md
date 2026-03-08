---
name: workspace-orchestrator
description: Automate complex workflows across Google Workspace services. Use when the user needs to chain actions between Gmail, Drive, Sheets, and Tasks (e.g., saving attachments to Drive and logging them in a Sheet).
---

# Workspace Orchestrator

Integrate Gmail, Drive, Sheets, and Tasks into automated pipelines using the `rxllmproc` CLI tools.

## Core Workflows

### 1. Mail to Drive/Sheets
Fetch emails, extract data, and archive metadata.
- **Tools**: `gmail_cli`, `gdrive_cli`, `sheets_cli`.
- **Example**: `gmail_cli get_all "from:accounting" --output_dir ./invoices`
- **Note**: `gmail_cli get_all` requires `--output_dir`.

### 2. Task Synchronization
Convert emails or document action items into Google Tasks.
- **Tools**: `gmail_cli`, `llm_cli`, `tasks_cli`.
- **Example**: `tasks_cli add --tasklist_id <LIST_ID> --title "Follow up" --id_url "https://mail.google.com/..."`
- **Note**: `tasks_cli add` requires `--tasklist_id`, `--title`, and `--id_url`.

### 3. Data Collection
Aggregate information from multiple sources.
- **Tools**: `gmail_cli`, `gdrive_cli`, `sheets_cli`.
- **Example**: Use `sheets_cli get --id <ID> --header_row 1` to read existing data.

## Usage Guidelines
- Pipe JSON output between tools for complex transformations.
- Use `llm_cli` as a "bridge" to parse unstructured email/doc text into structured data for Sheets or Tasks.
- Always check subcommand requirements (e.g., `gmail_cli get_all` vs `gdrive_cli put`).
