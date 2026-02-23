"""Red Hat Status MCP server."""

from redhat_status_mcp.server import mcp


def main() -> None:
    """Run the MCP server."""
    mcp.run()
