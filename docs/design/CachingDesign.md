# Caching Design

This document describes the design and implementation of the caching mechanism in `rxllmproc`.

## Overview

The caching system is designed to store the results of expensive, deterministic, or near-deterministic computations—primarily Large Language Model (LLM) calls. It aims to reduce latency and API costs while providing a flexible way to manage the lifecycle of cached data.

## Core Components

The caching logic resides in `rxllmproc/core/infra/cache.py`.

### 1. `CachedCall`

Represents an individual execution of a function or method. It stores:
-   **`serialized_args`**: The original arguments in a serialized (dictionary) format for reference and debugging.
-   **`hashed_args`**: An MD5 hash of the serialized arguments, used for fast lookups.
-   **`value`**: The returned result of the computation.
-   **`added`**: Timestamp when the call was first cached.
-   **`accessed`**: Timestamp of the last time this cached result was retrieved.

### 2. `CacheEntry`

A container for multiple `CachedCall` objects associated with a specific logical "key" (e.g., a function name or an LLM model identifier). It manages lookups and additions within its scope.

### 3. `Cache`

The top-level container that holds a registry of `CacheEntry` objects. This is the object that is serialized and stored in a file.

### 4. `CacheManager`

Responsible for the persistence of the `Cache` object. It uses the `Container` abstraction (from `rxllmproc/core/infra/containers.py`) to read from and write to storage (e.g., local files, Google Drive).

## Serialization

We use `jsonpickle` for serialization. This allows us to store complex Python objects in a JSON format while preserving their types and relationships. This is particularly useful for storing LLM responses, which might be complex nested structures.

## Hashing and Matching

To determine if a call matches a cached entry:
1.  The arguments (`*args`, `**kwargs`) are converted into a canonical dictionary format.
2.  This dictionary is serialized to a JSON string (with sorted keys).
3.  An MD5 hash of this string is computed (`hashed_args`).
4.  The system looks for a `CachedCall` with the same hash within the relevant `CacheEntry`.

## Lifecycle Management (Purging)

To prevent the cache from growing indefinitely, the system implements an age-based purging mechanism:

-   **`AgeSpec`**: A configuration dictionary that specifies the maximum allowed age based on `accessed` or `added` timestamps.
-   **`PurgeWalker`**: Traverses the `Cache` structure and removes `CachedCall` and `CacheEntry` objects that exceed the `AgeSpec`.
-   **`TimeSpec`**: Converts an `AgeSpec` into absolute points in time used for comparison during a purge.

The `CacheManager` automatically performs a purge whenever a cache is loaded or stored.

## Usage in CLI

The `CliBase` class handles the initialization of the `CacheManager` and `Cache` instance based on command-line flags (`--cache`, `--max_cache_age`) and environment variables. The `cache_instance` is then injected into the `RxEnvironment` and used by various operators and tools.

## Key Design Principles

-   **Abstraction**: The `CacheInterface` protocol allows for different cache implementations (e.g., `NoCache` for disabling caching).
-   **Thread Safety**: The caching system is **fully thread-safe**. `CacheEntry` uses `threading.Lock` to ensure safe concurrent access. This is critical for **Reactive Application Tools** (e.g., `rx_mail_categorizer`) which utilize `ThreadPoolScheduler` for parallel processing. In contrast, standard **Domain-Specific CLI Tools** (e.g., `gmail_cli`) typically operate in a single thread.
-   **Flexibility**: The `Container` abstraction allows the cache to be stored in various locations without changing the core caching logic.
-   **Observability**: The `CacheManager` provides statistics (hits, ages, counts) which are logged when the cache is loaded or stored.
