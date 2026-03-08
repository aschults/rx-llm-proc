# Docs Updater Design

## Overview

The `rxllmproc/docs` package provides a robust interface for interacting with and updating Google Docs. It's designed to handle the complexity of the Google Docs REST API, which uses index-based offsets for all operations.

## Architecture

The system is composed of several layers:

### 1. `DocsWrapper` (REST API Wrapper)

The `DocsWrapper` (`rxllmproc/docs/api.py`) provides a direct, low-level wrapper around the Google Docs REST API.

- **Batch Updates**: It provides a `batch_update` method that takes a list of typed requests (e.g., `InsertTextRequest`, `DeleteContentRangeRequest`) and executes them in a single HTTP request.
- **Typed Responses**: It uses the `dacite` library to deserialize the complex JSON responses from the Google Docs API into well-defined Python dataclasses (`rxllmproc/docs/types.py`).

### 2. `Document` Model

The `Document` model (`rxllmproc/docs/docs_model.py`) provides a higher-level, more developer-friendly object model for working with a document's content.

- **Sections and Hierarchies**: It parses the flat list of `structuralElement` objects from the REST API into a hierarchical structure of `Section` objects. This makes it easy to find specific headings, paragraphs, and their relative positions.
- **Index Management**: It provides methods like `get_start()` and `get_end()` to help calculate correct offsets for modification.

### 3. Reactive Operators

The `rxllmproc/docs/operators.py` file provides Rx operators for common document tasks:

- **`read_doc`**: An operator that fetches a document's content and emits a `Document` model.
- **`apply_edits`**: An operator that takes a list of `EditOperation` objects and applies them to a document using `batch_update`.

## Key Concepts

### Index-Based Offsets

Google Docs uses 1-based character offsets for all modifications. Inserting or deleting text changes the offsets of all subsequent content. The `DocsUpdater` system manages this complexity by:

1.  **Read-then-Write**: Fetching the latest document state to determine current offsets.
2.  **Batching**: Grouping multiple edits into a single `batchUpdate` call. The Google Docs API handles the index shifts *within* a single batch update (as long as they are provided in a specific order, which the library manages).

### Structured Sections

The `Section` model represents the document as a tree of headings and paragraphs. Each section has:
- `level`: The heading level (e.g., `HEADING_1`).
- `text`: The raw text content.
- `start`/`end`: The character offsets for this section.
- `subsections`: Any nested headings or paragraphs.

This structured view is critical for the `LlmUpdater`, as it allows the LLM to understand the document's layout and target specific sections for modification.
