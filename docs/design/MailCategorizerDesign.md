# Mail Categorizer Design

## Overview

The `rx_mail_categorizer` (available as a CLI tool and within the `app/mail` package) is a high-level application designed to automate the triage of Gmail messages. It uses LLMs to categorize emails, extract action items, and maintain an persistent index of processed messages to avoid duplication.

## Architecture

The categorizer is built around a set of reactive pipelines that coordinate data flow between Gmail, an LLM, and a local database.

### 1. Data Sources

- **Gmail API**: The primary source of incoming data. The `gmail_operators` are used to query for message IDs and download full message content (including attachments, which are converted to Markdown).
- **Local Database**: Used as both a source and a sink. It stores the IDs of already-processed messages to implement an efficient "unprocessed only" filter.

### 2. Processing Pipeline

The core logic resides in `rxllmproc/app/mail/pipelines.py`. A typical processing run follows these steps:

1. **Trigger**: The pipeline is triggered (either once or periodically).
2. **Fetch IDs**: Query Gmail for messages matching a user-provided criteria (e.g., `is:unread`).
3. **Filter**: Check the queried IDs against the local database (`mail_metadata` table). Only IDs not already present are passed forward.
4. **Download**: Fetch the full message content for the remaining IDs.
5. **Analyze (LLM)**:
   - Construct a prompt using a Jinja2 template (`_CATEGORIZATION_TEMPLATE`).
   - The template receives email metadata (subject, sender, etc.) and the message body.
   - The LLM (e.g., Gemini) is queried to return a structured JSON response matching the `Analysis` schema (defined in `rxllmproc/app/analysis/types.py`).
6. **Store Results**: Save the extracted `MailMetadata` and `Analysis` (including categories and action items) into the database.

### 3. Intermediate Database

The categorizer uses SQLAlchemy (defaulting to SQLite) to maintain state.

- **`mail_metadata`**: Stores the unique ID (URL) of each processed email and basic header information.
- **`analysis`**: Stores the LLM-generated categorization and extracted action items.
- **`action_item`**: Stores individual tasks extracted from emails, which can then be exported to other systems like Google Tasks or Google Docs.

### 4. Sinks

- **Database**: The primary destination for categorization results.
- **Google Docs**: Optionally, extracted action items can be formatted and inserted into a specific Google Doc using the `DocsUpdater` system.

## Performance and Reliability

- **Concurrency**: The pipeline uses a `ThreadPoolScheduler` to process multiple emails in parallel, significantly improving throughput for large inboxes.
- **Error Handling**: Each step in the pipeline is wrapped in error handling logic to ensure that a single malformed email doesn't crash the entire categorization process.
- **Idempotency**: By tracking processed IDs in the database, the categorizer can be safely re-run multiple times without creating duplicate entries.
- **Telemetry**: The `Environment.collect` operator provides real-time visibility into the number of emails queried, downloaded, and analyzed.
