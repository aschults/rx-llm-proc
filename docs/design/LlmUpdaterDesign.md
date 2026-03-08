# LLM Updater Design

## Overview

The `LlmUpdater` (`rxllmproc/docs/llm_updater.py`) is an advanced component that uses Large Language Models (LLMs) to intelligently modify Google Docs based on natural language instructions. It bridges the gap between high-level intent (e.g., "Add this todo item after the 'Home Projects' heading") and low-level REST API operations.

## Architecture

The `LlmUpdater` uses a **Tool-Use (Function Calling)** pattern to allow the LLM to interact with the document's structure before generating a set of edit operations.

### 1. The `DocUpdater` Class

The `DocUpdater` is the primary orchestrator. It is initialized with a `Document` model and a set of `edit_instructions`.

- **Prompting**: It constructs a sophisticated prompt that explains how Google Docs indices work and defines the expected JSON response format (`UpdateInstructions`).
- **Function Injection**: It injects several helper functions (tools) that the LLM can call during the generation process.

### 2. Available Tools (LLM Functions)

- **`get_sections`**: Returns a hierarchical view of all headings and paragraph texts in the document, along with their start and end indices. This allows the LLM to "see" the document's layout.
- **`get_doc_bounds`**: Returns the start and end indices of the entire document.

### 3. Generation Process

1. **Initialization**: The LLM receives the prompt and the available tools.
2. **Document Exploration**: The LLM calls `get_sections` (and potentially other tools) to understand the document's current content and where the requested changes should be applied.
3. **Edit Generation**: Based on the exploration, the LLM generates a JSON structure containing:
   - `inserts`: A list of text insertions with specific indices.
   - `deletes`: A list of content range deletions.
4. **Validation and Correction**: The `DocUpdater` receives the JSON response and performs basic validation:
   - Ensuring indices are within the document's bounds.
   - Correcting common LLM mistakes (e.g., trying to delete beyond the end of the document).
5. **Output**: The updater returns a list of `EditOperation` objects that can be passed to the `DocsWrapper` for execution.

## Key Features

### Batch Processing

The `ItemsEditGenerator` class allows for processing multiple items (e.g., multiple action items from different emails) in a single LLM request. This is more efficient and allows the LLM to maintain consistency when inserting multiple related pieces of content.

### Origin ID Tracking

The system supports tracking "origin IDs" throughout the update process. This allows the library to correlate a specific generated `EditOperation` with the original source item (e.g., a specific email ID). This is crucial for:
- Avoiding duplicate insertions in subsequent runs.
- Debugging the provenance of any document modification.

### Reactive Integration

The `generate_edits` function provides a convenient Rx operator that buffers incoming items and processes them in batches using the `LlmUpdater`.

```python
source.pipe(
    ops.buffer_with_count(5),
    generate_edits(document, placement_instructions),
)
```
