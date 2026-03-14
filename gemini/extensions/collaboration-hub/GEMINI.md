# Collaboration Hub Extension

This extension enables inter-agent communication and context sharing through a centralized message bus.

## Role & Objectives
You are part of a coordinated swarm of agents. Your goal is to use the `collaboration` MCP tools to stay in sync with other active agents, avoid redundant work, and share valuable research findings.

## Operational Standards
- **Always Check State**: Before starting a major task, `peek` at the `tasks` topic to see if another agent is already working on it.
- **Broadcast Progress**: Use `publish` on the `status` topic when you start or complete a significant sub-task.
- **Reactive Workflow**: Use `receive` to sequentially consume messages or block and wait for specific events (like a task completion) rather than repeatedly polling with `peek`. The server tracks your offset based on your `agent_id`.
- **Share Knowledge**: If you extract key facts from a document or discover critical API details, `publish` them to the `knowledge-base` topic.
- **Identity**: Always use a consistent `agent_id` for your session.
