# `llm_cli`: LLM Interaction Tool

## Introduction

The `llm_cli` tool provides a command-line interface for interacting with Large Language Models (LLMs). It allows you to send prompts, provide local files as context, and even grant the LLM limited tool-use capabilities like fetching URLs or listing files.

## Authentication

The `llm_cli` tool requires a Gemini API key. You can provide it in two ways:

1.  **Environment Variable (Recommended)**: Set the `GEMINI_API_KEY` environment variable in your shell.
    ```bash
    export GEMINI_API_KEY="your_api_key_here"
    ```
2.  **Command-Line Flag**: Use the `--api_key` flag when running the tool.
    ```bash
    llm_cli --api_key "your_api_key_here" "What is the capital of France?"
    ```

---

## Usage

```shell
llm_cli [OPTIONS] [LLM_TEXT_PROMPT ...]
```

The `LLM_TEXT_PROMPT` is a positional argument where you can provide the text of your prompt. If you provide multiple strings, they will be concatenated together.

### Options

| Option                        | Description                                                                                                   |
| :---------------------------- | :------------------------------------------------------------------------------------------------------------ |
| `--model` / `-M <NAME>`       | Sets the model name to use (default: `gemini`).                                                               |
| `--context_files <GLOB>`      | A glob pattern of filenames to provide as read-only context to the LLM.                                        |
| `--writeable_files <GLOB>`    | A glob pattern of filenames that the LLM is allowed to write to.                                              |
| `--enable_list_files`         | If set, allows the LLM to see a list of all files matching the context glob.                                  |
| `--enable_fetch_url`          | If set, the LLM can fetch the content of URLs.                                                               |
| `--api_key <KEY>`             | Manually provide an API key for authentication.                                                              |
| `--as_json` / `-j`            | Instructs the LLM to return its response as a JSON object.                                                    |
| `--output` / `-o <FILE>`      | Path to a file to write the response to, instead of standard output.                                          |
| `--upload <FILE_PATH>`        | Upload a local file (e.g., an image or large document) to be included in the prompt.                          |
| `-D <KEY=VALUE>` / `--define` | Define a template variable for use in the prompt.                                                             |
| `--cache <PATH>`              | Path to a cache file for LLM responses.                                                                       |
| `--max_cache_age <DAYS>`      | Maximum age of cache entries in days.                                                                         |
| `--verbose` / `-v`            | Enable verbose logging.                                                                                       |
| `--dry_run`                   | Log the prompt and configuration without sending it to the LLM.                                               |

### Examples

#### Basic Prompt
```bash
llm_cli "What is the capital of France?"
```

#### Providing Context Files
```bash
llm_cli --context_files "src/**/*.py" "Summarize the architecture of this project."
```

#### Uploading a File
```bash
llm_cli --upload "chart.png" "Explain the data shown in this image."
```
