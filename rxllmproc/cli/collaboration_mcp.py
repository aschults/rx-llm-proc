"""MCP server for inter-agent collaboration."""

import logging
from typing import Any, Dict, List, Optional
import argparse
import datetime
import asyncio
import json
import uuid

from rxllmproc.cli import mcp_base

logger = logging.getLogger(__name__)


class Entry:
    """Represents a message on a topic."""

    def __init__(
        self,
        id: int,
        topic: "Topic",
        message: str,
        sender: "Agent",
        timestamp: str,
    ) -> None:
        """Initialize a new entry."""
        self.id = id
        self.topic = topic
        self.message = message
        self.sender = sender
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert the entry to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "topic": self.topic.name,
            "message": self.message,
            "sender": self.sender.agent_id,
            "timestamp": self.timestamp,
        }


class Agent:
    """Represents an agent connected to the collaboration hub."""

    def __init__(self, agent_id: str) -> None:
        """Initialize a new agent."""
        self.agent_id = agent_id
        self.last_seen: str = datetime.datetime.now().isoformat()
        self.offsets: Dict[str, int] = {}

    def seen(self) -> None:
        """Update the last seen timestamp."""
        self.last_seen = datetime.datetime.now().isoformat()

    def get_offset(self, topic: str) -> int:
        """Get the offset for a given topic."""
        return self.offsets.get(topic, 0)

    def set_offset(self, topic: str, offset: int) -> None:
        """Set the offset for a given topic."""
        self.offsets[topic] = offset


class Topic:
    """Represents a topic on the collaboration hub."""

    def __init__(self, name: str, max_messages: int = 100) -> None:
        """Initialize a new topic."""
        self.name = name
        self.messages: List[Entry] = []
        self.max_messages = max_messages

    def add_message(self, entry: Entry) -> None:
        """Add a message to the topic, respecting the max_messages limit."""
        self.messages.append(entry)
        if self.max_messages > 0:
            if len(self.messages) > self.max_messages:
                self.messages = self.messages[-self.max_messages :]

    def peek(self, limit: int) -> List[Entry]:
        """Return the latest messages in the topic."""
        return self.messages[-limit:]

    def get_next_message(self, offset: int) -> Optional[Entry]:
        """Return the next message after the given offset."""
        for msg in self.messages:
            if msg.id > offset:
                return msg
        return None


class CollaborationMcp(mcp_base.McpCliBase):
    """MCP server that acts as a message bus for multiple agents."""

    def __init__(
        self,
        creds: Any = None,
        config_objects: List[Any] | None = None,
    ) -> None:
        """Initialize the Collaboration MCP server."""
        super().__init__(
            "collaboration-hub", creds=creds, config_objects=config_objects
        )
        # topic_name -> Topic
        self.topics: Dict[str, Topic] = {}
        # Registered agents
        self.agents: Dict[str, Agent] = {}
        # Topic listeners for receive: topic -> list of futures
        self.listeners: Dict[str, List[asyncio.Future[None]]] = {}
        self.next_msg_id = 1
        self.max_messages = 100
        self._setup_handlers()

    def _get_or_create_topic(self, topic_name: str) -> Topic:
        if topic_name not in self.topics:
            self.topics[topic_name] = Topic(topic_name, self.max_messages)
        return self.topics[topic_name]

    def _get_or_create_agent(self, agent_id: str) -> Agent:
        if agent_id not in self.agents:
            self.agents[agent_id] = Agent(agent_id)
        return self.agents[agent_id]

    def _add_args(self) -> None:
        super()._add_args()
        self.arg_parser.add_argument(
            "--max_messages",
            type=int,
            default=100,
            help="Maximum number of messages to retain per topic.",
        )

    def _apply_args(self, options: argparse.Namespace) -> None:
        super()._apply_args(options)
        self.max_messages = options.max_messages

    def _setup_handlers(self):
        """Set up MCP tool and resource handlers using FastMCP decorators."""
        self.server.tool()(self.publish)
        self.server.tool()(self.peek)
        self.server.tool()(self.list_topics)
        self.server.tool()(self.register_agent)
        self.server.tool()(self.list_agents)
        self.server.tool()(self.receive)
        self.server.resource("collaboration://topics/{topic}")(
            self.get_topic_resource
        )
        logger.info('MCP set up done')

    async def publish(self, topic: str, message: str, agent_id: str) -> str:
        """Publish a message to a specific topic on the shared bus.

        Args:
            topic: The name of the topic to publish to.
            message: The message payload as a string.
            agent_id: The ID of the agent publishing the message.

        Returns:
            A confirmation string.
        """
        topic_obj = self._get_or_create_topic(topic)
        agent = self._get_or_create_agent(agent_id)
        agent.seen()

        entry = Entry(
            id=self.next_msg_id,
            topic=topic_obj,
            message=message,
            sender=agent,
            timestamp=datetime.datetime.now().isoformat(),
        )
        self.next_msg_id += 1
        topic_obj.add_message(entry)

        # Notify listeners
        if topic in self.listeners:
            for future in self.listeners[topic]:
                if not future.done():
                    future.set_result(None)

        return f"Published to {topic}"

    def peek(self, topic: str, limit: int = 10) -> str:
        """Peek at the latest messages in a topic without consuming them.

        Args:
            topic: The name of the topic to peek at.
            limit: The maximum number of recent messages to return.

        Returns:
            A JSON string containing the list of messages.
        """
        if topic not in self.topics:
            return "[]"

        messages = self.topics[topic].peek(limit)
        return json.dumps([m.to_dict() for m in messages], indent=2)

    def _get_next_message(
        self, agent: Agent, topics: List[str]
    ) -> Optional[Entry]:
        best_msg = None
        for topic in topics:
            offset = agent.get_offset(topic)
            if topic in self.topics:
                msg = self.topics[topic].get_next_message(offset)
                if msg:
                    if best_msg is None or msg.id < best_msg.id:
                        best_msg = msg
        return best_msg

    async def receive(
        self, agent_id: str, topics: List[str], timeout: float = 60.0
    ) -> str:
        """Receive the next message for the agent on the given topics.

        Blocks if none available. Keeps track of the last message delivered per client.

        Args:
            agent_id: The ID of the agent receiving the message.
            topics: List of topics to listen to.
            timeout: Seconds to wait before timing out.

        Returns:
            A JSON string containing the message or timeout status.
        """
        agent = self._get_or_create_agent(agent_id)
        agent.seen()

        while True:
            msg = self._get_next_message(agent, topics)
            if msg:
                agent.set_offset(msg.topic.name, msg.id)
                return json.dumps(msg.to_dict(), indent=2)

            loop = asyncio.get_running_loop()
            future = loop.create_future()

            for topic in topics:
                if topic not in self.listeners:
                    self.listeners[topic] = []
                self.listeners[topic].append(future)

            try:
                await asyncio.wait_for(future, timeout=timeout)
            except asyncio.TimeoutError:
                return json.dumps({"status": "timeout"}, indent=2)
            finally:
                for topic in topics:
                    if (
                        topic in self.listeners
                        and future in self.listeners[topic]
                    ):
                        self.listeners[topic].remove(future)

    def list_topics(self) -> str:
        """List all active topics on the bus.

        Returns:
            A JSON string containing the list of topic names.
        """
        return json.dumps(list(self.topics.keys()))

    def register_agent(self, agent_id: Optional[str] = None) -> str:
        """Register an agent on the bus to signal presence.

        Args:
            agent_id: Optional unique identifier for the agent. If not provided,
                one will be generated.

        Returns:
            A confirmation string containing the registered agent ID.
        """
        if not agent_id:
            agent_id = str(uuid.uuid4())
        agent = self._get_or_create_agent(agent_id)
        agent.seen()
        return f"Agent {agent_id} registered."

    def list_agents(self) -> str:
        """List all currently registered agents.

        Returns:
            A JSON string containing the list of agent IDs.
        """
        return json.dumps(list(self.agents.keys()))

    def get_topic_resource(self, topic: str) -> str:
        """Get the latest messages for a topic."""
        if topic not in self.topics:
            return "[]"
        return json.dumps(
            [m.to_dict() for m in self.topics[topic].messages], indent=2
        )


def main():
    """Run the MCP server."""
    CollaborationMcp().main()


if __name__ == "__main__":
    main()
