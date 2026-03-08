# Command-Line Examples

## Introduction

The command-line tools provided by this library are designed to be composable.
They follow the Unix philosophy of doing one thing well and can be chained
together using standard shell pipes (`|`) to create powerful, automated
workflows.

The following examples demonstrate how you can combine these tools to solve
real-world problems.

---

### Example 1: Summarize Recent Emails

**Goal**: Find all unread emails from a specific sender, download them, and use an LLM to summarize their content.

This example uses these steps:

1.  `gmail_cli get_all`: To download unread emails from a sender to a temporary directory.
2.  `llm_cli`: To process the downloaded email files with a summarization prompt.

```bash
#!/bin/bash

# 1. Download all unread emails from 'newsletter@example.com' to the 'emails' directory.
#    We use --to_markdown to make them easier for the LLM to read.
gmail_cli get_all "from:newsletter@example.com is:unread" --output_dir emails --to_markdown

# 2. Use llm_cli to summarize the downloaded emails.
#    We use a glob to provide all downloaded .md files as context.
llm_cli --context_files "emails/*.md" "Summarize these emails, highlighting the key news from each."
```

---

### Example 2: Create To-Dos from a Google Doc

**Goal**: Fetch a document from Google Drive, extract action items using an LLM,
and add them to Google Tasks.

This workflow demonstrates how the tools can pass structured data (JSON) between
each other.

1.  `gdrive_cli get`: To get the text content of a document as Markdown.
2.  `llm_cli`: To parse the text and generate a list of to-dos in the JSON format
    required by `tasks_cli batch`.
3.  `tasks_cli batch`: To read the JSON and create/update the tasks.

```bash
#!/bin/bash

# We need a Task List ID to add tasks to.
# You can find this using `tasks_cli list_tasklists`
TASKLIST_ID="YOUR_TASKLIST_ID"

# The LLM prompt instructions. We use --as_json to ensure we get a valid JSON array.
PROMPT="Review the following content and extract all action items as a JSON array of objects.
Each object must have:
- 'title': The action item text
- 'id_url': A unique URL for identifying the task (e.g., 'https://internal/task/1')
- 'tasklist_id': '$TASKLIST_ID'
If no action items are found, return an empty array []."

echo "Fetching document and extracting action items..."

# 1. Get the document ID (e.g., from the browser URL)
FILE_ID="1abc123..."

# 2. Download document as Markdown
# 3. Pipe it to the LLM with the prompt and the --as_json flag
# 4. Pipe the resulting JSON to the tasks tool
gdrive_cli get --id "$FILE_ID" --as_markdown | \
  llm_cli "$PROMPT" --as_json | \
  tasks_cli batch

echo "Tasks processed successfully."
```

---

### Example 3: Use a Template to Build a Complex Prompt

**Goal**: Use a local template file to construct a complex prompt before sending it to the LLM.

1. Create a `report_prompt.j2` template file.
2. `gdrive_cli get`: To get the dynamic data (e.g., a report).
3. `template_cli`: To render the template, passing the report as a variable.
4. `llm_cli`: To evaluate the final rendered prompt.

**Template file: `report_prompt.j2`**

```jinja
Analyze the following quarterly report:
---
{{ report_content }}
---
Please answer:
1. What were the total sales?
2. What was the biggest challenge?
```

**Shell command:**

```bash
# 1. Get the report content
# 2. Use template_cli to define the 'report_content' variable from the output of gdrive_cli
#    Note: we use -D to define the variable.
REPORT=$(gdrive_cli get --id "FILE_ID" --as_markdown)
template_cli --template report_prompt.j2 -D "report_content=$REPORT" | llm_cli
```
