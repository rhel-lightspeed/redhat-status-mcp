# redhat-status-mcp

[![CI/CD](https://github.com/rhel-lightspeed/redhat-status-mcp/actions/workflows/build.yml/badge.svg)](https://github.com/rhel-lightspeed/redhat-status-mcp/actions/workflows/build.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-312/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![GHCR](https://img.shields.io/badge/ghcr.io-container-blue?logo=github)](https://ghcr.io/rhel-lightspeed/redhat-status-mcp)

[MCP](https://modelcontextprotocol.io/) server that exposes [Red Hat's status page](https://status.redhat.com) data to LLMs. Built with [FastMCP](https://github.com/jlowin/fastmcp) and [httpx](https://www.python-httpx.org/).

This is definitely a work in progress.

## Tools

| Tool | Description |
|------|-------------|
| `get_overall_status` | Top-level severity indicator (operational, minor, major, critical) |
| `list_service_groups` | List all groups, or pass `group_name` to drill into one group's child services |
| `get_incidents` | Currently unresolved incidents with impact, status, and latest updates |
| `get_maintenances` | Active and upcoming scheduled maintenance windows |

## Prompts

| Prompt | Description |
|--------|-------------|
| `triage_service_issue` | Walk through status, incidents, and maintenances for a specific service |
| `status_report` | Full status report across all groups, incidents, and maintenances |

## Quickstart

### Run with stdio (default, for MCP clients like Claude Desktop)

```sh
uv sync
uv run redhat-status-mcp
```

### Run with HTTP transport (for llama-stack, lightspeed-stack, etc.)

```sh
uv run redhat-status-mcp --transport streamable-http --port 8000
```

Or use environment variables:

```sh
MCP_TRANSPORT=streamable-http MCP_PORT=8000 uv run redhat-status-mcp
```

SSE transport is also supported:

```sh
uv run redhat-status-mcp --transport sse --port 8000
```

### Run from container

The container defaults to streamable-http on `0.0.0.0:8000`:

```sh
podman run --rm -p 8000:8000 ghcr.io/rhel-lightspeed/redhat-status-mcp:latest
```

Override transport settings with environment variables:

```sh
podman run --rm -p 9090:9090 \
  -e MCP_TRANSPORT=sse \
  -e MCP_PORT=9090 \
  ghcr.io/rhel-lightspeed/redhat-status-mcp:latest
```

## Integration

### llama-stack

Register as a connector in your llama-stack `config.yaml`:

```yaml
connectors:
  - connector_type: mcp
    connector_id: redhat-status
    url: http://localhost:8000/mcp
```

### lightspeed-stack

Add to `mcp_servers` in your `lightspeed-stack.yaml`:

```yaml
mcp_servers:
  - name: "redhat-status"
    url: "http://localhost:8000/mcp"
```

## Development

```sh
uv sync                # install deps
make ci                # lint + typecheck + complexity + tests
make lint              # ruff check
make format            # ruff format
make typecheck         # ty check
make radon             # cyclomatic complexity gate (fail on C+)
make test              # pytest with coverage
```
