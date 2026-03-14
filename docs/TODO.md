# TODOs / Ideas
## Integrations
[] MQTT integration -- Easier interaction with IoT devices (Rx based)
[] Sheets row by row incremental reader / writer (e.g. for logs)
[] Chat integration
[] Local / private LLM support (e.g. Hugging face, Ollama,...)
[x] Calendar integration.
[] Drive updates, to track changes in docs/sheets,...

## Functionality
[] MCP Proxy, to bridge sandboxing setups
[] Gemini CLI wrapper for continued, Rx based CLI interactions
[] Support using MCPs from LlmBase

## Structure
[] Move to Pydantic AI
[x] MCP server CLI base -- Base class to facilitate Rx Based MCP servers
[] Refactor utilities / Infrastructure into separate repo for reuse.


## Defects / glitches
[] Some inserts in docs don't get correct heading/text level

## MCP Server Ideas
[] **Google Workspace Context Server**: Expose Gmail, Calendar, Tasks, Drive, Docs, and Sheets   
   APIs as MCP tools. Allows an LLM to search, read, and update Google Workspace data 
   (leveraging `rxllmproc/gmail/`, `calendar/`, `tasks/`, etc.).
[] **"Living Document" Updater Server**: Leverage `llm_updater.py` and `markdown_to_gdocs.py` 
   to allow an LLM to "self-edit" or "self-document" technical specs or logs directly into 
   Google Docs in real-time.
[] **Reactive Pipeline Orchestrator**: Use `rx` (ReactiveX) operators and `rxllmproc/app/
   analysis/pipelines.py` to trigger complex, long-running workflows (e.g., "Analyze the last 10 
   emails from 'Project X' and summarize them into a new GDoc").
[] **Mail Categorization & Intelligence Server**: Use `rx_mail_categorizer.py` and    
   `text_processing` modules for semantic inbox analysis, auto-categorization, and high-priority 
   summaries.
[] **Personal Knowledge Graph (via Database Module)**: Use the `rxllmproc/database/` module to 
   provide a persistent "long-term memory" tool for the LLM, storing and retrieving context 
   across sessions.
[] **Template & Content Generator**: Use `jinja_processing.py` and `text_processing/` to 
   generate consistent, formatted reports or emails based on predefined templates.
[] **Prolog Reasoning Engine**: Integrate a Prolog-based reasoning server to provide a "ground 
   truth" for logic. The LLM can offload complex constraint satisfaction (like scheduling), 
   formal verification of business rules, or relationship mapping (knowledge graphs) to a 
   deterministic engine.
[x] **Inter-Agent Message Bus (Collaboration Server)**: A lightweight broker allowing multiple  
    independent Gemini CLI instances to exchange messages, share context, and coordinate tasks. 
    Enables "swarm" behavior where agents can delegate sub-tasks, broadcast high-priority 
    alerts, or avoid redundant API calls through shared knowledge.