"""Tests for ServerConfig settings loading and validation."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError
from pydantic_settings import CliApp

from redhat_status_mcp.config import ServerConfig


def test_defaults():
    """All fields have sensible defaults when no env vars or CLI args are set."""
    config = ServerConfig()

    assert config.transport == "stdio"
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.log_level == "INFO"
    assert config.base_url == "https://status.redhat.com/api/v2"
    assert config.request_timeout == 10.0
    assert config.cache_ttl == 60
    assert config.max_connections == 20
    assert config.max_retries == 3


@pytest.mark.parametrize(
    "transport",
    ["stdio", "sse", "streamable-http"],
    ids=["stdio", "sse", "streamable-http"],
)
def test_valid_transports(transport: str):
    """All supported transport values are accepted."""
    config = ServerConfig(transport=transport)

    assert config.transport == transport


def test_invalid_transport_rejected():
    """Transport values outside the Literal choices raise ValidationError."""
    with pytest.raises(ValidationError, match="transport"):
        ServerConfig(transport="websocket")


def test_env_var_loading():
    """Settings are populated from MCP_* environment variables."""
    with patch.dict(
        "os.environ",
        {"MCP_TRANSPORT": "sse", "MCP_HOST": "127.0.0.1", "MCP_PORT": "9090"},
    ):
        config = ServerConfig()

    assert config.transport == "sse"
    assert config.host == "127.0.0.1"
    assert config.port == 9090


def test_env_var_invalid_transport():
    """Invalid transport from env var raises ValidationError."""
    with (
        patch.dict("os.environ", {"MCP_TRANSPORT": "websocket"}),
        pytest.raises(ValidationError, match="transport"),
    ):
        ServerConfig()


def test_cli_args_via_cli_app():
    """CliApp.run parses CLI arguments into ServerConfig."""
    config = CliApp.run(
        ServerConfig,
        cli_args=["--transport", "sse", "--host", "127.0.0.1", "--port", "3000"],
    )

    assert config.transport == "sse"
    assert config.host == "127.0.0.1"
    assert config.port == 3000


def test_cli_overrides_env_var():
    """CLI arguments take precedence over environment variables."""
    with patch.dict("os.environ", {"MCP_TRANSPORT": "streamable-http"}):
        config = CliApp.run(
            ServerConfig,
            cli_args=["--transport", "sse"],
        )

    assert config.transport == "sse"


def test_env_var_overrides_default():
    """Environment variables take precedence over field defaults."""
    with patch.dict("os.environ", {"MCP_PORT": "9999"}):
        config = ServerConfig()

    assert config.port == 9999


def test_port_type_coercion():
    """Port value from env var string is coerced to int."""
    with patch.dict("os.environ", {"MCP_PORT": "4000"}):
        config = ServerConfig()

    assert config.port == 4000
    assert isinstance(config.port, int)


def test_env_var_loading_new_fields():
    """New performance fields are populated from MCP_* environment variables."""
    with patch.dict(
        "os.environ",
        {
            "MCP_CACHE_TTL": "120",
            "MCP_REQUEST_TIMEOUT": "5.0",
            "MCP_MAX_CONNECTIONS": "50",
            "MCP_MAX_RETRIES": "5",
        },
    ):
        config = ServerConfig()

    assert config.cache_ttl == 120
    assert config.request_timeout == 5.0
    assert config.max_connections == 50
    assert config.max_retries == 5


def test_cache_ttl_validation():
    """Negative cache_ttl is rejected."""
    with pytest.raises(ValidationError):
        ServerConfig(cache_ttl=-1)


def test_request_timeout_validation():
    """Zero or negative request_timeout is rejected."""
    with pytest.raises(ValidationError):
        ServerConfig(request_timeout=0)


def test_max_connections_validation():
    """Zero or negative max_connections is rejected."""
    with pytest.raises(ValidationError):
        ServerConfig(max_connections=0)


def test_max_retries_accepts_zero():
    """max_retries=0 is valid (disables retries)."""
    config = ServerConfig(max_retries=0)

    assert config.max_retries == 0
