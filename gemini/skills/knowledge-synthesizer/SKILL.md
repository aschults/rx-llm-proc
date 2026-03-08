---
name: knowledge-synthesizer
description: Cross-service research and information extraction. Use when the user needs to search across Google Drive, Gmail, and Sheets to synthesize findings or answer complex questions.
---

# Knowledge Synthesizer

Query and extract insights from your Google Workspace ecosystem using the `rxllmproc` toolset.

## Core Workflows

### 1. Research and Summarization
Crawl Drive folders or Gmail threads to extract key information and synthesize it into a report.
- **Tools**: `gmail_cli get_all`, `gdrive_cli list`, `llm_cli`.
- **Technique**: Use `llm_cli` to summarize multiple context blocks into a final response.

### 2. Information Extraction
Scan documents or emails for specific data points (e.g., pricing, names, dates).
- **Tools**: `gdrive_cli get --id <ID> --as_markdown`, `llm_cli --json`.

### 3. Gap Analysis
Compare existing project documents (on Drive) against new requirements (from Gmail) and identify discrepancies.

## Usage Guidelines
- Use `llm_cli` with a structured system prompt to extract data in JSON format for easier downstream processing.
- Prioritize `gdrive_cli list` for file discovery and `gmail_cli get_all` for timeline-based context.
- Always use the specific subcommands for each tool (e.g., `gdrive_cli put` for uploads, `gmail_cli get_all` for searches).
