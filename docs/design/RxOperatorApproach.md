# Rx Operator Approach and Environment

## Overview

The `rxllmproc` library heavily utilizes [RxPy](https://github.com/ReactiveX/RxPY) (Reactive Extensions for Python) to build asynchronous, event-driven data processing pipelines. This approach allows for high concurrency, clear separation of concerns, and easy composition of complex workflows.

The `Environment` class plays a central role in this architecture, acting as a shared context for all operators in a pipeline.

## The Environment

The `Environment` (found in `rxllmproc/core/environment.py`) is a container for shared resources and configuration. It is designed to be used as a context manager, allowing different parts of a pipeline to share or override settings.

### Key Responsibilities

- **Credential Management**: Provides access to `Credentials` and `CredentialsFactory`.
- **LLM Integration**: Holds the `LlmModelFactory` and configuration for creating LLM instances (model name, functions, arguments).
- **Service Wrappers**: Lazily creates and provides access to wrappers for Google APIs (`gmail_wrapper`, `tasks_wrapper`, `docs_wrapper`).
- **Caching**: Provides a shared `CacheInterface`.
- **Telemetry**: Offers a `collect` Rx operator for gathering statistics and samples during pipeline execution.
- **Error Handling**: Defines a shared `error_handler` for reporting issues.

### Hierarchical Configuration

The `Environment` supports hierarchical updates. You can create a new environment that inherits from an existing one but overrides specific settings using the `update()` or `add()` methods.

```python
with Environment(model_name="gemini-pro") as env:
    # Operators here use gemini-pro
    with env.update(model_name="gemini-lite") as sub_env:
        # Operators here use gemini-lite
```

## Rx Operators

In `rxllmproc`, business logic is typically implemented as custom Rx operators or functions that return operators. These operators are designed to be composable and often rely on the `Environment` for their dependencies.

### Design Patterns

1. **Lazy Dependency Resolution**: Operators should not hold hard references to service clients. Instead, they should access them via the `Environment` when an item is being processed.
2. **Side Effects via `do_action`**: Logging, telemetry (via `env.collect`), and status updates are typically handled using `do_action` or `ops.do`.
3. **Error Isolation**: Use `ops.catch` to prevent a single item's failure from terminating the entire pipeline.
4. **Contextual Information**: The `Environment` ensures that configuration (like which LLM model to use) is consistent across all stages of a pipeline without having to pass it explicitly to every function.

### Example: Telemetry with `collect`

The `env.collect(key)` operator is a specialized `ops.do` that passes data to a `Collector`. This allows for real-time monitoring of pipeline throughput and content samples.

```python
source.pipe(
    gmail_operators.fetch_ids(query),
    env.collect('mail_loading / queried ids'),
    gmail_operators.download_message(),
    env.collect('mail_loading / downloaded messages'),
)
```
