"""Server configuration via MCP_* environment variables and CLI arguments."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    """MCP server settings from CLI arguments and MCP_* environment variables.

    Precedence (highest to lowest): CLI args > env vars > defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        cli_prog_name="redhat-status-mcp",
        cli_hide_none_type=True,
    )

    transport: Literal["stdio", "sse", "streamable-http"] = Field(
        default="stdio",
        description="Transport protocol",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind to for HTTP transports",
    )
    port: int = Field(
        default=8000,
        description="Port to bind to for HTTP transports",
    )
    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    base_url: str = Field(
        default="https://status.redhat.com/api/v2",
        description="Statuspage API base URL",
    )
