# AGENTS.md — redhat-status-mcp

MCP server exposing Red Hat's status page (`status.redhat.com`) to LLMs.
Built with FastMCP + httpx, targeting Python 3.12.

## Build & Run

```sh
uv sync                # install all deps (including dev)
uv run redhat-status-mcp   # start MCP server
```

## CI Pipeline (`make ci`)

Runs lint → typecheck → complexity gate → tests. All four must pass.

```sh
make ci          # full pipeline (what CI runs)
make lint        # ruff check src/ tests/
make format      # ruff format src/ tests/
make typecheck   # ty check src/
make radon       # cyclomatic complexity gate (fail on C+)
make test        # pytest with coverage
```

### Running Individual Tests

```sh
uv run pytest tests/test_server.py -v                    # one test file
uv run pytest tests/test_server.py::test_get_overall_status_indicator_mapping -v  # one test
uv run pytest -k "maintenances" -v                       # keyword match
uv run pytest tests/test_api.py::test_fetch_status_http_error -v  # specific test
```

### Coverage

Coverage threshold is **85%** (`fail_under = 85` in pyproject.toml).
Source is `redhat_status_mcp`. Report shows missing lines.

```sh
uv run pytest --cov=redhat_status_mcp --cov-report=term-missing
```

## Project Layout

```
src/redhat_status_mcp/
  __init__.py    # entry point: imports mcp, defines main()
  api.py         # httpx client for Statuspage v2 API
  server.py      # FastMCP tools, prompts, and formatting helpers
tests/
  conftest.py    # shared fixtures (API response payloads)
  test_api.py    # tests for api.py (httpx mocking)
  test_server.py # tests for server.py (tool logic)
Containerfile    # multi-stage UBI 10 container build
Makefile         # lint, format, typecheck, radon, test, ci
```

## Code Style

### Formatting & Linting

- **Formatter**: ruff format (default settings)
- **Linter**: ruff with rules `E` (pycodestyle), `F` (pyflakes), `I` (isort)
- **Target**: Python 3.12 (`target-version = "py312"`)
- **Sources**: `src = ["src", "tests"]` for correct first-party import detection

### Imports

Ruff's `I` rule enforces isort ordering. Follow this order with blank lines between groups:

```python
"""Module docstring."""          # 1. docstring (always present)

import stdlib_module             # 2. stdlib
                                 # blank line
from third_party import thing    # 3. third-party
                                 # blank line
from redhat_status_mcp import x  # 4. local
```

### Type Hints

- All functions have full type annotations (params + return type).
- Use `list[dict]`, `str | None` (PEP 604 unions), not `List`, `Optional`.
- MCP tool parameters use `Annotated[str, Field(description="...")]`.
- Never suppress types with `# type: ignore`, `cast()`, or `Any`.

### Naming

- **Modules**: `snake_case.py`
- **Functions/variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE` (module-level only)
- **Private helpers**: `_leading_underscore` (e.g., `_format_status`, `_find_groups`)
- **Test functions**: `test_<unit>_<scenario>` (e.g., `test_get_incidents_empty`)
- **Test fixtures**: `snake_case`, prefixed with `_mock_` for patch fixtures

### Docstrings

PEP 257 on every module, function, and fixture — including test functions and private helpers. One-liner for simple cases, multi-line for complex ones.

```python
def _format_status(value: str) -> str:
    """Convert API status tokens into readable text."""
```

```python
async def get_overall_status() -> str:
    """Get the overall Red Hat service status.

    Returns a severity indicator (operational, minor, major, critical) with a
    human-readable description. Call this first to decide whether deeper
    investigation with get_incidents or get_service_group_details is needed.
    """
```

### Error Handling

Two patterns in this codebase — follow both:

1. **API layer** (`api.py`): Let exceptions propagate. `httpx` raises `HTTPStatusError`, `ConnectError`, etc. Don't catch them here.

2. **Server/tool layer** (`server.py`): Catch broad `Exception` in each tool, return a user-friendly error string. MCP tools must never raise — they return strings.

```python
# api.py — exceptions propagate
async def fetch_status() -> dict:
    """Fetch the overall Red Hat status page indicator."""
    return await _fetch_json("status.json")

# server.py — tools catch and return error strings
try:
    data = await api.fetch_status()
except Exception as error:
    return f"Error fetching status: {error}"
```

### Async

- All I/O functions are `async`. Use `async def` + `await`.
- pytest-asyncio with `asyncio_mode = "auto"` — async tests need no decorator.
- `httpx.AsyncClient` used as async context manager for HTTP calls.

### Complexity

Cyclomatic complexity gate via radon. **Functions rated C or higher are rejected.** Keep all functions at A or B. Break up complex logic into small private helpers.

```sh
make radon   # fails if any function is C+
```

## Testing Patterns

### Framework

pytest + pytest-asyncio + pytest-cov + pytest-randomly.

### Async Tests

Just write `async def test_...` — no `@pytest.mark.asyncio` needed (`asyncio_mode = "auto"`).

### Mocking

- API responses mocked via `unittest.mock.patch` + `AsyncMock`.
- Fixtures in `conftest.py` provide realistic API response payloads.
- Patch targets use full dotted path: `"redhat_status_mcp.server.api.fetch_status"`.
- Test files import via `importlib.import_module` (follow this pattern).

```python
server = importlib.import_module("redhat_status_mcp.server")
get_overall_status = server.get_overall_status
```

### Fixtures

- Response payload fixtures live in `conftest.py`, not duplicated in test files.
- Patch fixtures are local to each test file, prefixed with `_mock_`.
- Fixtures that are patch-only (used via `_mock_fetch_status: AsyncMock` param) use `_` prefix.

### Parameterization

Use `@pytest.mark.parametrize` with `ids=` for readability:

```python
@pytest.mark.parametrize(
    "query",
    ["console.redhat.com", "CONSOLE.REDHAT.COM", "console"],
    ids=["exact", "case-insensitive", "partial"],
)
```

### Coverage

New code must maintain **85% minimum coverage**. Use `# pragma: no cover` sparingly and only for genuinely untestable paths (like exception paths already tested via mocked routes).

## Container

Multi-stage build using UBI 10. Build with podman:

```sh
podman build -f Containerfile -t redhat-status-mcp .
podman run --rm redhat-status-mcp
```

## Git & CI

- GitHub Actions CI runs `make ci` on every PR and push to `main`.
- Conventional Commits for commit messages.
- Container images pushed to `ghcr.io/rhel-lightspeed/redhat-status-mcp` on push to `main` or version tags.
