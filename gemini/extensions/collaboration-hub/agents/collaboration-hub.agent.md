---
name: collaboration-hub
description: MCP server for inter-agent communication. Use this to allow multiple Gemini CLI instances to share context, broadcast status, and coordinate tasks via a shared message bus.
---

# Collaboration Hub MCP

The Collaboration Hub enables "swarm" behavior between independent Gemini CLI instances. It provides a shared message bus with topics for publishing and peeking at messages.

## Installation

Assuming `collaboration_mcp` is on your PATH:

### 1. Stdio (Local)
Add to your Gemini CLI configuration:
```json
{
  "mcpServers": {
    "collaboration": {
      "command": "collaboration_mcp",
      "args": ["--transport", "stdio"]
    }
  }
}
```

### 2. SSE (Network/Distributed)
Start the server:
```bash
collaboration_mcp --transport sse --port 8080 --secret MY_SECRET
```
Connect from an agent:
```json
{
  "mcpServers": {
    "collaboration": {
      "url": "http://localhost:8080/sse",
      "headers": {
        "X-MCP-Secret": "MY_SECRET"
      }
    }
  }
}
```

## Tools

### `publish`
Send a JSON message to a topic.
- **Arguments**:
  - `topic` (string): The channel name (e.g., "status", "research", "tasks").
  - `message` (object): Any JSON-serializable data.
  - `agent_id` (string): Unique identifier for the sender.

### `peek`
Retrieve recent messages from a topic without consuming them.
- **Arguments**:
  - `topic` (string): The channel name.
  - `limit` (int, default 10): Max messages to return.

### `list_topics`
List all active topics on the bus.

### `register_agent` / `list_agents`
Signal presence and discover other active agents.

## Resources
- `collaboration://topics/{topic}`: Read the full history of a topic as a JSON resource.

## Examples

### 1. Broadcasting Status
When starting a long-running task, an agent should broadcast its status:
```json
// Tool Call: publish
{
  "topic": "status",
  "agent_id": "researcher-1",
  "message": {
    "action": "searching_docs",
    "query": "MCP protocol specification",
    "progress": "started"
  }
}
```

### 2. Coordinating Research
If one agent finds something useful, it shares it:
```json
// Tool Call: publish
{
  "topic": "knowledge-base",
  "agent_id": "analyzer-agent",
  "message": {
    "type": "fact",
    "content": "The Gmail API quota is 1,000,000 units per day per project.",
    "source": "Google API Docs"
  }
}
```
Another agent can then check this:
```json
// Tool Call: peek
{
  "topic": "knowledge-base"
}
```

### 3. Avoiding Redundant Work
Before starting a task, an agent can check if another agent is already doing it:
```json
// Tool Call: peek
{
  "topic": "tasks"
}
// If "agent-2" is already "processing_invoices", "agent-1" can skip it.
```
