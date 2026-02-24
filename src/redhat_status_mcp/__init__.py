"""Red Hat Status MCP server."""

import argparse
import logging
import os

from redhat_status_mcp.server import mcp

VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_LOG_LEVEL = "INFO"

logger = logging.getLogger(__name__)


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


def _configure_logging() -> None:
    """Configure logging from the LOG_LEVEL environment variable.

    Defaults to INFO. Accepts any standard Python log level name
    (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    level = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    logging.basicConfig(
        level=level,
        format="%(levelname)s - %(name)s - %(message)s",
    )


def main() -> None:
    """Run the MCP server with configurable transport.

    Transport can be set via CLI args or environment variables:
        --transport / MCP_TRANSPORT: "stdio", "sse", or "streamable-http"
        --host / MCP_HOST: Host to bind to (HTTP transports only)
        --port / MCP_PORT: Port to bind to (HTTP transports only)

    Log level can be set via LOG_LEVEL environment variable (default: INFO).

    CLI arguments take precedence over environment variables.
    """
    _configure_logging()
    args = _parse_args()

    transport = args.transport or os.environ.get("MCP_TRANSPORT", "stdio")
    host = args.host or os.environ.get("MCP_HOST", DEFAULT_HOST)
    port = args.port or int(os.environ.get("MCP_PORT", str(DEFAULT_PORT)))

    logger.info("Starting MCP server with transport=%s", transport)

    if transport == "sse":
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "streamable-http":
        mcp.run(transport="streamable-http", host=host, port=port)
    elif transport == "stdio":
        mcp.run(transport="stdio")
    else:
        raise SystemExit(f"Unknown transport: {transport!r}")
