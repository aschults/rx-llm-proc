# Collaboration Hub Design

## Overview

The Collaboration Hub is a centralized message bus designed to facilitate
inter-agent communication and state sharing in a multi-agent system. It allows
agents to coordinate their actions, share research findings, and synchronize on
complex tasks through a publish/subscribe model.

## Architecture

The system is implemented as an MCP (Model Context Protocol) server, allowing it
to be easily integrated into any agent-based workflow.

### 1. Data Structures

- **`Entry`**: Represents a single message on the bus. It contains a unique ID,
  topic name, message payload (string), sender (agent ID), and a timestamp.
- **`Agent`**: Maintains information about a registered agent, including its
  `agent_id`, last-seen timestamp, and its current offset for each topic.
- **`Topic`**: Organizes messages into named channels. It maintains a list of
  recent messages (up to a configurable `max_messages` limit) and provides
  methods for peeking and fetching messages.

### 2. Message Flow

The hub uses a combination of push and pull mechanisms:

1. **Publish**: An agent sends a message to a topic. The hub assigns a unique
   ID, stores it in the topic's history, and notifies any active listeners.
2. **Receive (Blocking)**: An agent can request the next message from a list of
   topics. If a new message is already available (based on the agent's offset),
   it is returned immediately. Otherwise, the agent's request is queued as a
   "listener" (implemented using `asyncio.Future`).
3. **Notify**: When a new message is published, the hub checks for any listeners
   on that topic and fulfills their futures.

### 3. State Management

The hub is currently designed for in-memory state. While it maintains a history
of messages, this history is transient and will be lost if the server restarts.

- **Topic Retention**: Each topic has a maximum number of messages it will
  retain (default: 100). When this limit is reached, the oldest messages are
  evicted.
- **Agent Offsets**: The hub tracks which messages each agent has consumed by
  maintaining an offset (the ID of the last message delivered to that agent) for
  each topic.

### 4. Integration via MCP

By exposing its functionality as MCP tools (`publish`, `peek`, `receive`,
`list_topics`, `register_agent`), the hub allows agents to interact with it
naturally within their standard tool-calling loop.

## Performance and Scalability

- **Asynchronous I/O**: The server is built on `asyncio`, allowing it to handle
  many concurrent "receive" requests efficiently.
- **JSON Serialization**: All data is exchanged in JSON format, ensuring
  compatibility with a wide range of agents and tools.
- **Memory Efficiency**: The `max_messages` limit on topics prevents the hub
  from consuming excessive memory in long-running sessions.

## Future Enhancements

- **Persistence**: Adding a database backend (e.g., SQLite) to persist message
  history and agent offsets across server restarts.
- **Structured Payloads**: Allowing messages to be JSON objects instead of
  simple strings, enabling more complex data exchange.
- **Access Control**: Implementing permissions to restrict which agents can
  publish or subscribe to specific topics.
