# CLI Caching

To improve performance and reduce API costs, `rxllmproc` provides a caching mechanism for LLM responses and other expensive computations.

## Enabling Caching

Caching is disabled by default. You can enable it by specifying a cache file path.

### Using the `--cache` Flag

You can specify the cache file for any CLI tool using the `--cache` flag:

```bash
llm_cli --cache my_cache.json "What is the capital of France?"
```

If the file does not exist, it will be created. If it exists, the tool will try to load it and use cached responses when the prompt and parameters match.

### Using the `RX_LLM_PROC_CACHE` Environment Variable

Instead of passing the flag every time, you can set the `RX_LLM_PROC_CACHE` environment variable:

```bash
export RX_LLM_PROC_CACHE=~/.rxllmproc/cache.json
llm_cli "What is the capital of France?"
```

## Managing Cache Age

Over time, your cache file might grow large or contain outdated information. You can manage the age of cached entries.

### Using `--max_cache_age`

The `--max_cache_age` flag specifies the maximum age of cache entries in **days** since they were last accessed.

```bash
llm_cli --cache my_cache.json --max_cache_age 7 "Summarize this report."
```

In this example, any cache entry that hasn't been used for more than 7 days will be purged from the cache file when the command runs.

## Cache File Format

The cache is stored as a JSON file (using `jsonpickle` for serialization). While it is human-readable, it is managed automatically by the tools.

### Security Warning

The cache file may contain sensitive user data, including prompts sent to the LLM and the responses received. It is stored in plain text (JSON). You should ensure that the file is stored in a secure location and has appropriate file permissions to prevent unauthorized access.

## Why Use Caching?

1.  **Cost Efficiency**: Avoid paying for the same LLM prompt multiple times.
2.  **Speed**: Cached responses are returned instantly, without waiting for a network call to the LLM provider.
3.  **Reproducibility**: Ensure you get the exact same response for the same input during development or testing.
