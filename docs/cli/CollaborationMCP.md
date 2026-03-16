# `collaboration-hub`: Collaboration Tool

## Introduction

The `collaboration-hub` tool provides a centralized message bus for inter-agent
communication and coordination. It allows multiple agents to share state,
broadcast progress, and synchronize on tasks using a publish/subscribe model
organized by topics.

- **See Also**: [[CollaborationMCP]]

## Core Concepts

- **Topic**: A named channel for messages (e.g., `tasks`, `status`,
  `knowledge-base`).
- **Agent**: A participant in the collaboration hub, identified by a unique
  `agent_id`.
- **Message**: A string payload published to a topic by an agent.
- **Offset**: A pointer maintained for each agent per topic to track which
  messages have been consumed.

---

## Tools and Commands

As an MCP server, the collaboration hub exposes several tools that can be
invoked by agents.

### `publish`

Publishes a message to a specific topic.

**Arguments:**

- `topic`: The name of the topic to publish to.
- `message`: The message payload (string).
- `agent_id`: The ID of the agent publishing the message.

### `peek`

Returns the latest messages in a topic without advancing the agent's offset.

**Arguments:**

- `topic`: The name of the topic to peek at.
- `limit`: (Optional) Maximum number of messages to return (default: 10).

### `receive`

Blocks until a new message is available on any of the specified topics, then
returns it and advances the agent's offset.

**Arguments:**

- `agent_id`: The ID of the agent receiving the message.
- `topics`: A list of topic names to listen to.
- `timeout`: (Optional) Seconds to wait before timing out (default: 60.0).

### `list_topics`

Lists all active topics on the bus.

### `register_agent`

Registers an agent to signal presence. Returns the registered `agent_id`.

**Arguments:**

- `agent_id`: (Optional) A preferred unique identifier.

### `list_agents`

Lists all currently registered agents.

---

## Resources

The collaboration hub also exposes resources that can be read by agents.

### `collaboration://topics/{topic}`

Returns the full history of messages for the specified topic (up to the server's
retention limit).

---

## Example Usage (Conceptual)

An agent starting a task:

1. `register_agent("agent-007")`
2. `publish("status", "Starting task: documentation update", "agent-007")`

Another agent waiting for task completion:

1. `receive("agent-008", ["status"])`
