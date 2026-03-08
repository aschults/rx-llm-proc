---
name: document-architect
description: High-fidelity document generation and transformation in Google Docs. Use when the user needs to convert Markdown to GDocs, update document sections using LLMs, or manage structured documentation templates.
---

# Document Architect

Create, update, and manage Google Docs using `docs_cli` and associated transformation tools.

## Core Workflows

### 1. Markdown to Google Doc
Seamlessly convert complex Markdown (with headers and lists) to a formatted Google Doc.
- **Tool**: `docs_cli insert --document_id <ID> --at_end --file <path>`
- **Note**: Markdown is the default. Use `--plaintext` for raw text.

### 2. Intelligent Content Placement
Use LLM instructions to determine where and how to insert or delete content in a document.
- **Tool**: `docs_cli insert --document_id <ID> --instructions "<PROMPT>" --file <path>`
- **Capability**: The LLM analyzes document structure (sections, headings, indices) to perform precise edits.
- **Flag**: `--instructions` allows for natural language guidance on placement (e.g., "Insert this after the 'Next Steps' section but before 'Contact Info'").

### 3. Sectioned Updates
Select specific sections of a Google Doc (by header or index) and rewrite or extend them.
- **Tools**: `docs_cli insert` with `--section`, `--heading_id`, `--section_start`, `--section_end`, or `--section_replace`.

## Best Practices
- Prefer `docs_cli get --document_id <ID> --nested` for reading and structure analysis.
- Use `template_cli` with Jinja2 templates for repetitive document structures before pushing to GDocs.
- For intelligent placement, describe the target location relative to existing headings or content in the `--instructions` prompt.
