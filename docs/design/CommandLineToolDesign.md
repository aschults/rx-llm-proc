# Command-Line Tool Design

## Introduction

The command-line tools, located in the `rxllmproc/cli/` directory, are the primary user-facing components of the `Rx LLM Proc` library. They are designed to be thin, consistent, and easily integrable as **skills or extensions within a host environment like the Gemini CLI**.

This document describes the architecture of these tools, which is based on a common base class that handles boilerplate code, allowing each specific tool to focus solely on its unique logic.

## Core Component: `CliBase`

All command-line tools inherit from a common base class, `rxllmproc.cli.cli_base.CliBase`. This class provides a standardized structure and a set of common functionalities for all CLI entry points.

The key responsibilities of `CliBase` are:

1.  **Argument Parsing**: It initializes an `argparse.ArgumentParser` and pre-defines a set of common arguments that are available to all tools, such as `--verbose`, `--output`, and `--help`.
2.  **Environment Setup**: It handles the initialization of the application environment, including setting up logging, instantiating the `CredentialsFactory` for handling credentials, and managing the `CacheManager` for LLM results.
3.  **Standardized Entry Point**: It defines a public `main()` method, which serves as the top-level entry point. This method parses arguments, sets up the environment (including logging and caching), and then calls a `run()` method, which contains the specific logic for the command.
4.  **Plugin Integration**: It includes hooks for the plugin system via `PluginRegistry`, allowing extensions to add their own arguments or modify behavior.
5.  **Argument Post-Processing**: It uses `ArgPostProcessor` to handle advanced argument features like file expansion (`@filename`) and typed arguments (e.g., `(json)@config.json`).

## Concrete Implementation: A Domain CLI Tool

Each tool, such as `gmail_cli.py` or `drive_cli.py`, implements a class that inherits from `CliBase`. This concrete class is responsible for:

1.  Adding its own specific arguments to the argument parser in `_add_args()`.
2.  Implementing the `run()` method, which contains the actual logic for the command. This method orchestrates the work by calling operators and API clients from the appropriate domain packages.

### Implementation Pattern

```python
# In rxllmproc/cli/cli_base.py
import argparse

class CliBase:
    def __init__(self):
        self.arg_parser = argparse.ArgumentParser()
        self._add_args()  # Hook for subclasses

    def _add_args(self):
        """Subclasses override this to add their own arguments."""
        # Base class adds common arguments like --verbose, --cache
        ...

    def main(self):
        """Top-level entry point for the CLI tool."""
        # 1. Parse arguments
        # 2. Setup environment (logging, caching, plugins)
        # 3. Call run()
        self.run()

    def run(self):
        """The core logic of the command goes here."""
        raise NotImplementedError("Subclasses must implement run.")

# In rxllmproc/cli/gmail_cli.py
from rxllmproc.cli.cli_base import CliBase

class GmailCli(CliBase):
    def _add_args(self):
        """Add arguments specific to the Gmail tool."""
        self.arg_parser.add_argument("--query", required=True, help="Gmail query.")

    def run(self):
        """Execute the Gmail listing logic."""
        # Access parsed arguments directly from self (after they are applied by ArgPostProcessor)
        query = self.query
        
        # 1. Instantiate API clients from domain packages
        # 2. Perform the required actions
        ...

# In the executable script for the gmail tool
if __name__ == "__main__":
    GmailCli().main()
```

## Execution Models

The library supports two distinct execution models via its command-line interfaces:

### 1. Domain-Specific CLI Tools (Short-Lived)
Tools like `gmail_cli.py` or `docs_cli.py` are designed for discrete, synchronous operations (e.g., listing messages, reading a specific doc).
- **Threading**: These are typically **single-threaded**.
- **Lifecycle**: They run to completion and exit immediately.
- **Use Case**: Ideal for manual triggers or simple script integration where a single action is required.

### 2. Reactive Application Tools (Long-Running)
Tools prefixed with `rx_`, such as `rx_mail_categorizer.py`, leverage the full power of the RxPy framework.
- **Threading**: These are **multi-threaded**, utilizing `ThreadPoolScheduler` to handle high-concurrency tasks like downloading and analyzing multiple emails in parallel.
- **Lifecycle**: They are designed as **long-running services** that can monitor sources (like a Gmail inbox) periodically via an `--interval` flag.
- **Use Case**: Continuous, automated workflows and complex, multi-stage pipelines.

## Integration with Gemini CLI

This architecture makes integration with a host like the Gemini CLI straightforward. Each tool is a self-contained script that can be run via its `if __name__ == "__main__"` block or by invoking `CliClass().main()`.

A **Gemini CLI extension or skill** would simply be a shim that invokes the `main()` method of the corresponding CLI class (e.g., `GmailCli().main()`). The host environment is responsible for command discovery and mapping a user-facing command to the appropriate entry point in this library.

## Benefits of this Design

*   **Thin Presentation Layer**: The CLI scripts are "thin" and primarily concerned with presentation (parsing arguments, printing output). The core business logic is properly located in the domain packages.
*   **Consistency**: All command-line tools share the same structure, making them predictable and easy to develop and maintain.
*   **Advanced Features by Default**: Every tool automatically inherits powerful features like caching, verbose logging, and flexible argument expansion (`@filename`).
*   **Decoupling & Integration**: The tools are decoupled from any specific host environment but provide a simple, standard entry point (`main()`) that makes integration trivial.
