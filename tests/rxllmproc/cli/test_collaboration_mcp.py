"""Tests for Collaboration MCP."""

import unittest
from unittest import mock
import asyncio
import json

from rxllmproc.cli import collaboration_mcp
import test_support

fail_none = test_support.fail_none


class TestCollaborationMcp(unittest.TestCase):
    """Test the Collaboration MCP server."""

    def setUp(self):
        # Patch PluginRegistry to avoid loading plugins during test
        self.plugin_patcher = mock.patch(
            'rxllmproc.plugins.loader.PluginRegistry'
        )
        self.mock_registry = self.plugin_patcher.start()

        # Patch FastMCP to avoid server initialization side effects
        self.fastmcp_patcher = mock.patch('mcp.server.fastmcp.FastMCP')
        self.mock_fastmcp = self.fastmcp_patcher.start()

        # Initialize the MCP instance
        self.mcp = collaboration_mcp.CollaborationMcp()

    def tearDown(self):
        self.plugin_patcher.stop()
        self.fastmcp_patcher.stop()

    def test_publish_and_peek(self):
        """Test publishing a message and retrieving it via peek."""
        asyncio.run(self.mcp.publish("test-topic", "payload", "agent-007"))

        # Test peek
        peek_result = json.loads(self.mcp.peek("test-topic"))
        self.assertEqual(len(peek_result), 1)

        entry = peek_result[0]
        self.assertEqual(entry["topic"], "test-topic")
        self.assertEqual(entry["message"], "payload")
        self.assertEqual(entry["sender"], "agent-007")
        self.assertTrue("timestamp" in entry)
        self.assertTrue("id" in entry)

    def test_publish_limit(self):
        """Test that the topic history is limited to 100 messages."""

        async def run():
            for i in range(110):
                await self.mcp.publish("load-topic", f"seq-{i}", "agent-tester")

        asyncio.run(run())

        peek_result = json.loads(self.mcp.peek("load-topic", limit=200))
        self.assertEqual(len(peek_result), 100)
        self.assertEqual(peek_result[0]["message"], "seq-10")
        self.assertEqual(peek_result[-1]["message"], "seq-109")

    def test_publish_custom_limit(self):
        """Test that the topic history respects a custom max_messages limit."""
        self.mcp.max_messages = 5

        async def run():
            for i in range(10):
                await self.mcp.publish(
                    "custom-limit-topic", f"seq-{i}", "agent-tester"
                )

        asyncio.run(run())

        peek_result = json.loads(self.mcp.peek("custom-limit-topic", limit=200))
        self.assertEqual(len(peek_result), 5)
        self.assertEqual(peek_result[0]["message"], "seq-5")
        self.assertEqual(peek_result[-1]["message"], "seq-9")

    def test_receive_message(self):
        """Test receive blocks until message is received."""

        async def async_test():
            # Start waiting in background
            wait_task = asyncio.create_task(
                self.mcp.receive("agent-b", ["async-topic"])
            )

            # Give it a moment to register listener
            await asyncio.sleep(0.01)

            # Publish message
            await self.mcp.publish("async-topic", "go", "agent-a")

            # Await result
            result_json = await wait_task
            result = json.loads(result_json)

            self.assertEqual(result["topic"], "async-topic")
            self.assertEqual(result["message"], "go")
            self.assertEqual(result["sender"], "agent-a")
            self.assertTrue("id" in result)

        asyncio.run(async_test())

    def test_receive_timeout(self):
        """Test receive returns timeout status when time expires."""

        async def async_test():
            result_json = await self.mcp.receive(
                "agent-c", ["silent-topic"], timeout=0.1
            )
            result = json.loads(result_json)
            self.assertEqual(result, {"status": "timeout"})

        asyncio.run(async_test())

    def test_receive_multiple_topics(self):
        """Test receive works with multiple topics."""

        async def async_test():
            wait_task = asyncio.create_task(
                self.mcp.receive("agent-d", ["topic-a", "topic-b"])
            )

            await asyncio.sleep(0.01)
            await self.mcp.publish("topic-b", "triggered", "agent-b")

            result_json = await wait_task
            result = json.loads(result_json)

            self.assertEqual(result["topic"], "topic-b")

        asyncio.run(async_test())

    def test_receive_history_and_offset(self):
        """Test receive tracks offsets and returns next message."""

        async def async_test():
            await self.mcp.publish("topic-1", "msg1", "agent-a")
            await self.mcp.publish("topic-1", "msg2", "agent-a")

            # Agent B should receive msg 1 then msg 2 without blocking
            res1 = json.loads(await self.mcp.receive("agent-b", ["topic-1"]))
            self.assertEqual(res1["message"], "msg1")

            res2 = json.loads(await self.mcp.receive("agent-b", ["topic-1"]))
            self.assertEqual(res2["message"], "msg2")

            # Agent C should receive msg 1
            res3 = json.loads(await self.mcp.receive("agent-c", ["topic-1"]))
            self.assertEqual(res3["message"], "msg1")

        asyncio.run(async_test())

    def test_agent_class(self):
        """Test the Agent class."""
        agent = collaboration_mcp.Agent("agent-1")
        self.assertEqual(agent.agent_id, "agent-1")
        self.assertEqual(agent.get_offset("topic-a"), 0)
        self.assertTrue(agent.last_seen)

        agent.set_offset("topic-a", 5)
        self.assertEqual(agent.get_offset("topic-a"), 5)
        self.assertEqual(agent.get_offset("topic-b"), 0)

    def test_topic_class(self):
        """Test the Topic class."""
        topic = collaboration_mcp.Topic("test-topic", max_messages=2)
        self.assertEqual(topic.name, "test-topic")

        agent = collaboration_mcp.Agent("agent-1")

        e1 = collaboration_mcp.Entry(1, topic, "msg1", agent, "time")
        e2 = collaboration_mcp.Entry(2, topic, "msg2", agent, "time")
        e3 = collaboration_mcp.Entry(3, topic, "msg3", agent, "time")

        topic.add_message(e1)
        topic.add_message(e2)

        self.assertEqual(len(topic.messages), 2)
        self.assertEqual(topic.messages[0].id, 1)

        topic.add_message(e3)
        self.assertEqual(len(topic.messages), 2)
        self.assertEqual(topic.messages[0].id, 2)
        self.assertEqual(topic.messages[1].id, 3)

        self.assertEqual(len(topic.peek(1)), 1)
        self.assertEqual(topic.peek(1)[0].id, 3)

        self.assertEqual(fail_none(topic.get_next_message(1)).id, 2)
        self.assertEqual(fail_none(topic.get_next_message(2)).id, 3)
        self.assertIsNone(topic.get_next_message(3))

    def test_entry_class(self):
        """Test the Entry class."""
        topic = collaboration_mcp.Topic("topic-x")
        agent = collaboration_mcp.Agent("agent-x")
        entry = collaboration_mcp.Entry(
            42, topic, "payload", agent, "2024-01-01T00:00:00"
        )

        d = entry.to_dict()
        self.assertEqual(d["id"], 42)
        self.assertEqual(d["topic"], "topic-x")
        self.assertEqual(d["message"], "payload")
        self.assertEqual(d["sender"], "agent-x")
        self.assertEqual(d["timestamp"], "2024-01-01T00:00:00")

    def test_register_and_list_agents(self):
        """Test registering and listing agents."""
        self.mcp.register_agent("agent-1")
        self.mcp.register_agent("agent-2")
        agents = json.loads(self.mcp.list_agents())
        self.assertIn("agent-1", agents)
        self.assertIn("agent-2", agents)

    def test_list_topics(self):
        """Test listing topics."""
        asyncio.run(self.mcp.publish("topic-1", "msg", "agent-1"))
        asyncio.run(self.mcp.publish("topic-2", "msg", "agent-1"))
        topics = json.loads(self.mcp.list_topics())
        self.assertIn("topic-1", topics)
        self.assertIn("topic-2", topics)

    def test_get_topic_resource(self):
        """Test getting topic resource."""
        asyncio.run(self.mcp.publish("topic-resource", "msg1", "agent-1"))
        resource = json.loads(self.mcp.get_topic_resource("topic-resource"))
        self.assertEqual(len(resource), 1)
        self.assertEqual(resource[0]["message"], "msg1")
