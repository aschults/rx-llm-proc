# pyright: reportPrivateUsage=false
"""Tests for MCP Base CLI class."""

import unittest
from unittest import mock

from rxllmproc.cli import mcp_base


class TestMcpCliBase(unittest.TestCase):
    """Test the McpCliBase class."""

    @mock.patch("mcp.server.fastmcp.FastMCP")
    def test_default_transports(self, _: mock.Mock):
        """Test default transport arguments."""
        cli = mcp_base.McpCliBase("test-mcp")

        # Test that all arguments are present
        actions = [action.dest for action in cli.arg_parser._actions]
        self.assertIn("transport", actions)
        self.assertIn("port", actions)
        self.assertIn("host", actions)
        self.assertIn("secret", actions)
        self.assertIn("insecure", actions)

    @mock.patch("mcp.server.fastmcp.FastMCP")
    def test_stdio_only_transport(self, _: mock.Mock):
        """Test arguments when only stdio is allowed."""
        cli = mcp_base.McpCliBase("test-mcp", allowed_transports=["stdio"])

        # Test that transport flag and SSE flags are missing
        actions = [action.dest for action in cli.arg_parser._actions]
        self.assertNotIn("transport", actions)
        self.assertNotIn("port", actions)
        self.assertNotIn("host", actions)
        self.assertNotIn("secret", actions)
        self.assertNotIn("insecure", actions)

        self.assertEqual(cli.transport, "stdio")

    @mock.patch("mcp.server.fastmcp.FastMCP")
    def test_sse_only_transport(self, _: mock.Mock):
        """Test arguments when only sse is allowed."""
        cli = mcp_base.McpCliBase("test-mcp", allowed_transports=["sse"])

        # Test that transport flag is missing but SSE flags are present
        actions = [action.dest for action in cli.arg_parser._actions]
        self.assertNotIn("transport", actions)
        self.assertIn("port", actions)
        self.assertIn("host", actions)
        self.assertIn("secret", actions)
        self.assertIn("insecure", actions)

        self.assertEqual(cli.transport, "sse")

    @mock.patch("mcp.server.fastmcp.FastMCP")
    def test_empty_transports(self, _: mock.Mock):
        """Test empty transport list raises ValueError."""
        with self.assertRaises(ValueError):
            mcp_base.McpCliBase("test-mcp", allowed_transports=[])

    @mock.patch("mcp.server.fastmcp.FastMCP")
    def test_apply_args(self, _: mock.Mock):
        """Test applying arguments updates the CLI state."""
        cli = mcp_base.McpCliBase("test-mcp")
        args = cli.arg_parser.parse_args(
            ["--transport", "sse", "--port", "9000"]
        )
        cli._apply_args(args)
        self.assertEqual(cli.transport, "sse")
        self.assertEqual(cli.port, 9000)
