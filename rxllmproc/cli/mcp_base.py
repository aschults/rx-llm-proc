"""Base for MCP servers."""

import argparse
import logging
import secrets
import sys
from typing import Optional, List, Any

from mcp.server import fastmcp
from starlette import responses
import uvicorn

from rxllmproc.cli import cli_base

logger = logging.getLogger(__name__)


class McpCliBase(cli_base.CliBase):
    """Base class for MCP server CLIs using FastMCP."""

    def __init__(
        self,
        name: str,
        creds: Any = None,
        config_objects: List[Any] | None = None,
        allowed_transports: List[str] | None = None,
    ) -> None:
        """Initialize the MCP CLI."""
        self.name = name
        self.allowed_transports = (
            allowed_transports
            if allowed_transports is not None
            else ["stdio", "sse"]
        )
        if not self.allowed_transports:
            raise ValueError("allowed_transports cannot be empty")
        self.transport: str = (
            "stdio"
            if "stdio" in self.allowed_transports
            else self.allowed_transports[0]
        )
        self.port: int = 8080
        self.host: str = "localhost"
        self.secret: Optional[str] = None
        self.insecure: bool = False
        super().__init__(creds=creds, config_objects=config_objects)
        self.server = fastmcp.FastMCP(name)

    def _add_args(self) -> None:
        super()._add_args()
        if len(self.allowed_transports) > 1:
            self.arg_parser.add_argument(
                "--transport",
                choices=self.allowed_transports,
                default=self.transport,
                help='Transport to use for MCP. "sse" uses HTTP SSE.',
            )

        if "sse" in self.allowed_transports:
            self.arg_parser.add_argument(
                "--port",
                type=int,
                default=8080,
                help="Port for SSE transport.",
            )
            self.arg_parser.add_argument(
                "--host",
                default="localhost",
                help="Host for SSE transport.",
            )
            self.arg_parser.add_argument(
                "--secret",
                help="Secret for SSE transport. If not provided, a random one will be generated.",
            )
            self.arg_parser.add_argument(
                "--insecure",
                action="store_true",
                help="Disable authentication for SSE transport.",
            )

    def _apply_args(self, options: argparse.Namespace) -> None:
        super()._apply_args(options)
        self.transport = getattr(options, "transport", self.transport)
        if "sse" in self.allowed_transports:
            self.port = getattr(options, "port", 8080)
            self.host = getattr(options, "host", "localhost")
            self.secret = getattr(options, "secret", None)
            self.insecure = getattr(options, "insecure", False)

        if self.transport == "sse" and not self.insecure and not self.secret:
            self.secret = secrets.token_urlsafe(32)
            print(
                f"Generated random secret for MCP: {self.secret}",
                file=sys.stderr,
            )

    def run(self) -> None:
        """Run the MCP server."""
        if self.transport == "stdio":
            logging.info("Starting MCP server stdio")
            self.server.run(transport="stdio")
        else:
            # For SSE with authentication, we need to wrap the FastMCP Starlette app
            app = self.server.sse_app()

            async def auth_middleware(
                scope: dict[str, Any], receive: Any, send: Any
            ) -> None:
                if scope["type"] in ("http", "websocket") and not self.insecure:
                    # Check headers for our secret
                    headers = dict(scope.get("headers", []))
                    auth_header = headers.get(b"x-mcp-secret", b"").decode()
                    if auth_header != self.secret:
                        logger.warning("Unauthorized access attempt to MCP SSE")
                        response = responses.Response(
                            "Unauthorized", status_code=401
                        )
                        await response(scope, receive, send)
                        return

                await app(scope, receive, send)

            logging.info(
                "Starting MCP SSE server on %s:%s", self.host, self.port
            )
            uvicorn.run(
                auth_middleware,
                host=self.host,
                port=self.port,
                log_level="info",
            )
