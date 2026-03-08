# Goals and Motivation

This document outlines the core motivation behind the `Rx LLM Proc` library and
the kinds of problems it is designed to solve.

## The Core Goal: A Modular Framework for Workspace Intelligence

The primary goal of this library is to provide a flexible, modular framework for
scaling LLM-based evaluations across personal and professional data. While the
current implementation is centered around **Google Workspace** (Gmail, Drive,
Sheets, Tasks), the architecture is designed to be ecosystem-agnostic, with
future work intended to introduce integrations for other platforms and data
sources.

It is built to support three primary use cases:

1. **Supercharging the Gemini CLI**: Act as a powerful extension set for the
   Gemini CLI, providing it with the "skills" needed to interact directly with
   Gmail, Drive, Sheets, and Tasks.
2. **Long-Running Reactive Pipelines**: Provide a Python SDK for building
   robust, event-driven pipelines that can continuously monitor and react to
   incoming data (e.g., automatically processing every new email as it arrives).
3. **Modular Scripting & Automation**: Provide a suite of composable
   command-line tools that can be easily integrated into traditional scripts,
   workflows, and dependency-based build systems like **GNU Make**.

This is achieved by providing:

- **Direct integration** with relevant data sources and sinks like Gmail, Google
  Drive, and Google Tasks.
- **A suite of composable command-line tools**, each performing a clear
  function, that can be chained together inside the Gemini CLI or standard shell
  scripts.
- Robust support for preparing prompts (e.g., via templating) and processing
  both text and structured **JSON output** from LLMs.
- An **advanced Python SDK** for developers who need to build event-driven,
  reactive pipelines using **RxPy**.
- A "hybrid" approach that combines traditional, deterministic code for tasks
  like filtering with LLM-based processing for tasks like summarization.

## Example Use Cases

The following examples illustrate the types of workflows this library is built
to enable across its different modes of operation.

### Making the Most of the Email Flood (Reactive Pipeline)

This was the original idea that motivated the project. A long-running process
monitors an inbox to create a curated view of the most relevant messages.

- **Goal**:
  - Continuously fetch new emails as they arrive.
  - Use an LLM to categorize them (e.g., "Family," "Work Project," "Finance").
  - Generate a summary for each important email.
  - Extract action items and automatically add them to Google Tasks, checking
    for duplicates against existing tasks.
  - Send a periodic digest email containing all the summaries.

### Scaling Up Information Extraction (Scripted Workflow)

This is a work-relevant use case for processing large volumes of documents,
often orchestrated using a tool like **GNU Make** to manage dependencies and
avoid redundant processing.

- **Goal**:
  - Iterate through all documents in a specific Google Drive folder.
  - For each document, use an LLM to find and extract specific information
    (e.g., project names, risk assessments, key dates).
  - Store this extracted information in a structured format, like a Google Sheet
    or a local database.
  - Generate a final summary report from the structured data, pointing out key
    trends or critical items.

### Automated Email Writing Coach (Gemini CLI Skill)

A user-facing application where the tools are used as skills within the Gemini
CLI to provide on-demand analysis.

- **Goal**:
  - On a weekly basis, the user triggers an analysis of all emails they've sent.
  - An LLM analyzes the emails based on a set of attributes (e.g., tone,
    conciseness, clarity).
  - The tool generates a short, private feedback report with findings and
    suggestions.
  - The user reviews the feedback directly in the CLI or has it emailed to them.

## Guiding Principles

Our design philosophy is based on a few key principles:

- **Pipelining over Monolithic Prompts**: We believe complex tasks are best
  solved by breaking them into a series of smaller, simpler steps. A
  step-by-step pipeline approach (e.g.,
  `fetch -> clean -> summarize -> categorize`) yields better, cheaper, and
  faster results.

- **Use the Right Tool for the Job**: Some work should **not** be left to LLMs.
  This library uses traditional, deterministic code for reliable tasks like
  filtering data, while leveraging LLMs for fuzzy tasks like natural language
  understanding and summarization.

- **User in Control**: The library favors an explicit, pipeline-driven approach
  where the user defines the workflow. This gives the user full and predictable
  control, as opposed to a fully autonomous "agent" paradigm where behavior
  might be less predictable.

- **Best of Both Worlds**: One motivation was to get the best from two worlds:
  Taking full advantage of the power of LLM language and context processing,
  while keeping the deterministic stability of scripted/programmed
  orchestration. As a side effect this potentially reduces LLM window sizes and
  thus LLM consumption.
