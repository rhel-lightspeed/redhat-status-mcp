"""Server configuration via MCP_* environment variables and CLI arguments."""

from typing import Literal

from pydantic import Field, field_validator
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
    request_timeout: float = Field(
        default=10.0,
        description="HTTP request timeout in seconds",
    )
    cache_ttl: int = Field(
        default=60,
        description="Cache time-to-live in seconds",
    )
    max_connections: int = Field(
        default=20,
        description="Maximum concurrent HTTP connections",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
    )

    @field_validator("request_timeout")
    @classmethod
    def validate_request_timeout(cls, v: float) -> float:
        """Validate request_timeout is positive."""
        if v <= 0:
            raise ValueError("request_timeout must be greater than 0")
        return v

    @field_validator("cache_ttl")
    @classmethod
    def validate_cache_ttl(cls, v: int) -> int:
        """Validate cache_ttl is non-negative."""
        if v < 0:
            raise ValueError("cache_ttl must be >= 0")
        return v

    @field_validator("max_connections")
    @classmethod
    def validate_max_connections(cls, v: int) -> int:
        """Validate max_connections is positive."""
        if v <= 0:
            raise ValueError("max_connections must be greater than 0")
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        """Validate max_retries is non-negative."""
        if v < 0:
            raise ValueError("max_retries must be >= 0")
        return v
