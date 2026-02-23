"""Tests for the MCP server entry point and transport configuration."""

import importlib
from unittest.mock import MagicMock, patch

import pytest

init = importlib.import_module("redhat_status_mcp")
main = init.main
_parse_args = init._parse_args


@pytest.fixture
def _mock_mcp_run():
    """Patch mcp.run for the duration of a test."""
    with patch("redhat_status_mcp.mcp") as mock_mcp:
        mock_mcp.run = MagicMock()
        yield mock_mcp


# -- _parse_args tests --


def test_parse_args_defaults():
    """All arguments default to None when no CLI args are provided."""
    with patch("sys.argv", ["redhat-status-mcp"]):
        args = _parse_args()

    assert args.transport is None
    assert args.host is None
    assert args.port is None


@pytest.mark.parametrize(
    "transport",
    ["stdio", "sse", "streamable-http"],
    ids=["stdio", "sse", "streamable-http"],
)
def test_parse_args_transport(transport: str):
    """Valid transport values are accepted from the CLI."""
    with patch("sys.argv", ["redhat-status-mcp", "--transport", transport]):
        args = _parse_args()

    assert args.transport == transport


def test_parse_args_invalid_transport():
    """Invalid transport values cause argparse to exit."""
    with patch("sys.argv", ["redhat-status-mcp", "--transport", "websocket"]):
        with pytest.raises(SystemExit):
            _parse_args()


def test_parse_args_host_and_port():
    """Host and port are parsed from CLI arguments."""
    with patch(
        "sys.argv",
        ["redhat-status-mcp", "--host", "0.0.0.0", "--port", "9090"],
    ):
        args = _parse_args()

    assert args.host == "0.0.0.0"
    assert args.port == 9090


# -- main() transport dispatch tests --


def test_main_defaults_to_stdio(_mock_mcp_run: MagicMock):
    """Default transport is stdio when no args or env vars are set."""
    with patch("sys.argv", ["redhat-status-mcp"]):
        main()

    _mock_mcp_run.run.assert_called_once_with(transport="stdio")


def test_main_sse_transport(_mock_mcp_run: MagicMock):
    """SSE transport passes host and port to mcp.run."""
    with patch("sys.argv", ["redhat-status-mcp", "--transport", "sse"]):
        main()

    _mock_mcp_run.run.assert_called_once_with(
        transport="sse", host="0.0.0.0", port=8000
    )


def test_main_streamable_http_transport(_mock_mcp_run: MagicMock):
    """Streamable-http transport passes host and port to mcp.run."""
    with patch(
        "sys.argv",
        [
            "redhat-status-mcp",
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "3000",
        ],
    ):
        main()

    _mock_mcp_run.run.assert_called_once_with(
        transport="streamable-http", host="0.0.0.0", port=3000
    )


def test_main_env_var_transport(_mock_mcp_run: MagicMock):
    """MCP_TRANSPORT env var selects the transport when no CLI arg is given."""
    with (
        patch("sys.argv", ["redhat-status-mcp"]),
        patch.dict("os.environ", {"MCP_TRANSPORT": "sse"}),
    ):
        main()

    _mock_mcp_run.run.assert_called_once_with(
        transport="sse", host="0.0.0.0", port=8000
    )


def test_main_env_var_host_and_port(_mock_mcp_run: MagicMock):
    """MCP_HOST and MCP_PORT env vars configure the HTTP bind address."""
    with (
        patch("sys.argv", ["redhat-status-mcp"]),
        patch.dict(
            "os.environ",
            {
                "MCP_TRANSPORT": "streamable-http",
                "MCP_HOST": "0.0.0.0",
                "MCP_PORT": "9999",
            },
        ),
    ):
        main()

    _mock_mcp_run.run.assert_called_once_with(
        transport="streamable-http", host="0.0.0.0", port=9999
    )


def test_main_cli_overrides_env_var(_mock_mcp_run: MagicMock):
    """CLI arguments take precedence over environment variables."""
    with (
        patch(
            "sys.argv",
            ["redhat-status-mcp", "--transport", "sse", "--port", "7777"],
        ),
        patch.dict(
            "os.environ",
            {"MCP_TRANSPORT": "streamable-http", "MCP_PORT": "9999"},
        ),
    ):
        main()

    _mock_mcp_run.run.assert_called_once_with(
        transport="sse", host="0.0.0.0", port=7777
    )


def test_main_unknown_transport_from_env():
    """Unknown transport from env var raises SystemExit."""
    with (
        patch("sys.argv", ["redhat-status-mcp"]),
        patch.dict("os.environ", {"MCP_TRANSPORT": "websocket"}),
        pytest.raises(SystemExit, match="Unknown transport"),
    ):
        main()
