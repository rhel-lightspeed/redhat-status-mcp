"""Red Hat Status MCP server."""

import argparse
import os

from redhat_status_mcp.server import mcp

VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for transport configuration."""
    parser = argparse.ArgumentParser(description="Red Hat Status MCP Server")
    parser.add_argument(
        "--transport",
        choices=VALID_TRANSPORTS,
        default=None,
        help="Transport protocol (default: stdio, env: MCP_TRANSPORT)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help=(
            "Host to bind to for HTTP transports"
            f" (default: {DEFAULT_HOST}, env: MCP_HOST)"
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "Port to bind to for HTTP transports"
            f" (default: {DEFAULT_PORT}, env: MCP_PORT)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Run the MCP server with configurable transport.

    Transport can be set via CLI args or environment variables:
        --transport / MCP_TRANSPORT: "stdio", "sse", or "streamable-http"
        --host / MCP_HOST: Host to bind to (HTTP transports only)
        --port / MCP_PORT: Port to bind to (HTTP transports only)

    CLI arguments take precedence over environment variables.
    """
    args = _parse_args()

    transport = args.transport or os.environ.get("MCP_TRANSPORT", "stdio")
    host = args.host or os.environ.get("MCP_HOST", DEFAULT_HOST)
    port = args.port or int(os.environ.get("MCP_PORT", str(DEFAULT_PORT)))

    if transport == "sse":
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "streamable-http":
        mcp.run(transport="streamable-http", host=host, port=port)
    elif transport == "stdio":
        mcp.run(transport="stdio")
    else:
        raise SystemExit(f"Unknown transport: {transport!r}")
