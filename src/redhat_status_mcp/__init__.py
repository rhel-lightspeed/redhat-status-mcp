"""Red Hat Status MCP server."""

import logging

from pydantic_settings import CliApp

from redhat_status_mcp.config import ServerConfig
from redhat_status_mcp.server import mcp

logger = logging.getLogger(__name__)


def _configure_logging(log_level: str) -> None:
    """Configure logging at the given level.

    Accepts any standard Python log level name
    (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    logging.basicConfig(
        level=log_level.upper(),
        format="%(levelname)s - %(name)s - %(message)s",
    )


def main() -> None:
    """Run the MCP server with configurable transport.

    Settings are loaded from CLI arguments and MCP_* environment variables.
    CLI arguments take precedence over environment variables.
    Run ``redhat-status-mcp --help`` for available options.
    """
    config = CliApp.run(ServerConfig)
    _configure_logging(config.log_level)

    logger.info("Starting MCP server with transport=%s", config.transport)

    if config.transport in ("sse", "streamable-http"):
        mcp.run(transport=config.transport, host=config.host, port=config.port)
    else:
        mcp.run(transport="stdio")
