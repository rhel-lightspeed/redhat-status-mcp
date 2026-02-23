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
| `list_service_groups` | All service groups with status and child service counts |
| `get_service_group_details` | Drill into a specific group's child services (fuzzy name match) |
| `get_incidents` | Currently unresolved incidents with impact, status, and latest updates |
| `get_maintenances` | Active and upcoming scheduled maintenance windows |

## Prompts

| Prompt | Description |
|--------|-------------|
| `triage_service_issue` | Walk through status, incidents, and maintenances for a specific service |
| `status_report` | Full status report across all groups, incidents, and maintenances |

## Quickstart

### Run from container

```sh
podman run --rm ghcr.io/rhel-lightspeed/redhat-status-mcp:latest
```

### Run from source

```sh
uv sync
uv run redhat-status-mcp
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
