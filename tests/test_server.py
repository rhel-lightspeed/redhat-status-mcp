"""Tests for FastMCP server tools."""

import asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from cachetools import TTLCache

server = importlib.import_module("redhat_status_mcp.server")
get_overall_status = server.get_overall_status
list_service_groups = server.list_service_groups
get_incidents = server.get_incidents
get_maintenances = server.get_maintenances
triage_service_issue = server.triage_service_issue
status_report = server.status_report


@pytest.fixture
def _mock_ctx():
    """Provide a mock Context with lifespan_context containing cache and lock."""
    cache = TTLCache(maxsize=64, ttl=60)
    cache_lock = asyncio.Lock()
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "cache": cache,
        "cache_lock": cache_lock,
    }
    return ctx


@pytest.fixture
def _mock_fetch_status():
    """Patch api.fetch_status for the duration of a test."""
    with patch(
        "redhat_status_mcp.server.api.fetch_status", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture
def _mock_fetch_components():
    """Patch api.fetch_components for the duration of a test."""
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture
def _mock_fetch_incidents():
    """Patch api.fetch_unresolved_incidents for the duration of a test."""
    with patch(
        "redhat_status_mcp.server.api.fetch_unresolved_incidents",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def _mock_fetch_maintenances():
    """Patch both maintenance endpoints for the duration of a test."""
    with patch(
        "redhat_status_mcp.server.api.fetch_upcoming_maintenances",
        new_callable=AsyncMock,
    ) as mock_upcoming:
        with patch(
            "redhat_status_mcp.server.api.fetch_active_maintenances",
            new_callable=AsyncMock,
        ) as mock_active:
            yield mock_upcoming, mock_active


@pytest.mark.parametrize(
    ("indicator", "description", "icon"),
    [
        ("none", "All Systems Operational", "✅"),
        ("minor", "Minor Service Degradation", "⚠️"),
        ("major", "Major Service Outage", "🔴"),
        ("critical", "Critical Service Outage", "🚨"),
    ],
)
async def test_get_overall_status_indicator_mapping(
    indicator: str,
    description: str,
    icon: str,
    _mock_ctx: MagicMock,
    _mock_fetch_status: AsyncMock,
) -> None:
    """Each severity indicator maps to the correct icon and label."""
    _mock_fetch_status.return_value = {
        "status": {"indicator": indicator, "description": description}
    }
    result = await get_overall_status(_mock_ctx)

    assert description in result
    assert icon in result


async def test_get_overall_status_unknown_indicator(
    _mock_ctx: MagicMock,
    _mock_fetch_status: AsyncMock,
) -> None:
    """Unknown indicator values fall through gracefully."""
    _mock_fetch_status.return_value = {
        "status": {"indicator": "weird", "description": "Custom Provider Message"}
    }
    result = await get_overall_status(_mock_ctx)

    assert "Custom Provider Message" in result


async def test_get_overall_status_api_error(
    _mock_ctx: MagicMock,
    _mock_fetch_status: AsyncMock,
) -> None:
    """API connection failures are surfaced in the response."""
    request = httpx.Request("GET", "https://status.redhat.com/api/v2/status.json")
    _mock_fetch_status.side_effect = httpx.ConnectError(
        "Connection failed", request=request
    )
    result = await get_overall_status(_mock_ctx)

    assert "Error fetching status" in result
    assert "Connection failed" in result


async def test_list_service_groups_returns_groups_sorted_with_counts(
    components_response: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Groups are listed alphabetically with correct child counts."""
    _mock_fetch_components.return_value = components_response
    result = await list_service_groups(_mock_ctx)

    lines = result.splitlines()
    bullet_lines = [line for line in lines if line.startswith("- ")]
    assert len(bullet_lines) == 4
    assert bullet_lines == sorted(bullet_lines, key=str.casefold)
    assert "console.redhat.com" in result
    assert "3 services" in result


async def test_list_service_groups_ignores_non_group_components(
    components_response: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Child components are excluded from the group listing."""
    _mock_fetch_components.return_value = components_response
    result = await list_service_groups(_mock_ctx)

    assert "Ansible Automation Platform - Automation Hub" not in result
    assert "registry.redhat.io" not in result


async def test_list_service_groups_empty_components(
    _mock_ctx: MagicMock,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Empty component list returns a friendly message."""
    _mock_fetch_components.return_value = {"components": []}
    result = await list_service_groups(_mock_ctx)

    assert "No service groups" in result


async def test_list_service_groups_api_error(
    _mock_ctx: MagicMock,
    _mock_fetch_components: AsyncMock,
) -> None:
    """API errors are surfaced in the response."""
    _mock_fetch_components.side_effect = RuntimeError("components endpoint down")
    result = await list_service_groups(_mock_ctx)

    assert "Error fetching service groups" in result
    assert "components endpoint down" in result


@pytest.mark.parametrize(
    "query",
    [
        "console.redhat.com",
        "CONSOLE.REDHAT.COM",
        "console",
    ],
    ids=["exact", "case-insensitive", "partial"],
)
async def test_list_service_groups_successful_group_match(
    query: str,
    components_response: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Exact, case-insensitive, and partial queries all resolve to the correct group."""
    _mock_fetch_components.return_value = components_response
    result = await list_service_groups(_mock_ctx, query)

    assert "Group: console.redhat.com" in result
    assert "Ansible Automation Platform - Automation Hub" in result
    assert "Cost Management" in result


async def test_list_service_groups_no_group_match(
    components_response: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Unmatched query suggests listing available groups."""
    _mock_fetch_components.return_value = components_response
    result = await list_service_groups(_mock_ctx, "satellite")

    assert "No service group found" in result
    assert "without group_name" in result


async def test_list_service_groups_multiple_group_matches(
    components_response: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Ambiguous query returns all matching group names."""
    _mock_fetch_components.return_value = components_response
    result = await list_service_groups(_mock_ctx, "redhat.com")

    assert "Multiple service groups matched" in result
    assert "console.redhat.com" in result
    assert "access.redhat.com" in result
    assert "bugzilla.redhat.com" in result


async def test_list_service_groups_group_details_include_child_statuses(
    components_response: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Child service statuses are formatted and included."""
    _mock_fetch_components.return_value = components_response
    result = await list_service_groups(_mock_ctx, "console")

    assert "Degraded Performance" in result
    assert "Partial Outage" in result


async def test_list_service_groups_group_details_api_error(
    _mock_ctx: MagicMock,
    _mock_fetch_components: AsyncMock,
) -> None:
    """API errors are surfaced in the response."""
    _mock_fetch_components.side_effect = RuntimeError("components timeout")
    result = await list_service_groups(_mock_ctx, "console")

    assert "Error fetching service groups" in result
    assert "components timeout" in result


async def test_get_incidents_empty(
    incidents_empty: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_incidents: AsyncMock,
) -> None:
    """No incidents returns a friendly message."""
    _mock_fetch_incidents.return_value = incidents_empty
    result = await get_incidents(_mock_ctx)

    assert "No unresolved incidents" in result


async def test_get_incidents_active_incident_format(
    incidents_response: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_incidents: AsyncMock,
) -> None:
    """Active incidents include name, impact, status, and affected components."""
    _mock_fetch_incidents.return_value = incidents_response
    result = await get_incidents(_mock_ctx)

    assert "Elevated error rates on console.redhat.com" in result
    assert "Impact: Major" in result
    assert "Status: Investigating" in result
    assert "Affected Components: console.redhat.com" in result


async def test_get_incidents_uses_most_recent_update_only(
    incidents_response: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_incidents: AsyncMock,
) -> None:
    """Only the latest update body is shown, not older ones."""
    _mock_fetch_incidents.return_value = incidents_response
    result = await get_incidents(_mock_ctx)

    assert "continuing to investigate elevated error rates" in result
    assert "We are investigating reports of elevated error rates" not in result


async def test_get_incidents_handles_missing_updates(
    _mock_ctx: MagicMock,
    _mock_fetch_incidents: AsyncMock,
) -> None:
    """Incidents with no updates show a fallback message."""
    _mock_fetch_incidents.return_value = {
        "incidents": [
            {
                "name": "Storage API latency spike",
                "impact": "minor",
                "status": "identified",
                "components": [{"name": "Storage API"}],
                "incident_updates": [],
            }
        ]
    }
    result = await get_incidents(_mock_ctx)

    assert "Storage API latency spike" in result
    assert "Latest Update: No updates posted yet" in result


async def test_get_incidents_api_error(
    _mock_ctx: MagicMock,
    _mock_fetch_incidents: AsyncMock,
) -> None:
    """API errors are surfaced in the response."""
    _mock_fetch_incidents.side_effect = RuntimeError("incident endpoint timeout")
    result = await get_incidents(_mock_ctx)

    assert "Error fetching incidents" in result
    assert "incident endpoint timeout" in result


@pytest.mark.parametrize(
    ("upcoming_key", "active_key", "expected", "not_expected"),
    [
        (
            "empty",
            "empty",
            ["No scheduled maintenances"],
            [],
        ),
        (
            "upcoming",
            "empty",
            ["Upcoming Maintenances", "Scheduled maintenance on registry.redhat.io"],
            [],
        ),
        (
            "empty",
            "active",
            ["Active Maintenances", "Active maintenance on console.redhat.com"],
            [],
        ),
        (
            "upcoming",
            "active",
            [
                "Active Maintenances",
                "Upcoming Maintenances",
                "Active maintenance on console.redhat.com",
                "Scheduled maintenance on registry.redhat.io",
            ],
            [],
        ),
    ],
    ids=["both-empty", "upcoming-only", "active-only", "both-present"],
)
async def test_get_maintenances_scenarios(
    upcoming_key: str,
    active_key: str,
    expected: list[str],
    not_expected: list[str],
    maintenances_upcoming: dict,
    maintenances_active: dict,
    maintenances_empty: dict,
    _mock_ctx: MagicMock,
    _mock_fetch_maintenances: tuple[AsyncMock, AsyncMock],
) -> None:
    """Maintenance output varies correctly for empty, upcoming, active, and both."""
    fixture_map = {
        "empty": maintenances_empty,
        "upcoming": maintenances_upcoming,
        "active": maintenances_active,
    }
    mock_upcoming, mock_active = _mock_fetch_maintenances
    mock_upcoming.return_value = fixture_map[upcoming_key]
    mock_active.return_value = fixture_map[active_key]
    result = await get_maintenances(_mock_ctx)

    for text in expected:
        assert text in result
    for text in not_expected:
        assert text not in result


async def test_get_maintenances_calls_both_endpoints(
    _mock_ctx: MagicMock,
    _mock_fetch_maintenances: tuple[AsyncMock, AsyncMock],
) -> None:
    """Both upcoming and active endpoints are always called."""
    mock_upcoming, mock_active = _mock_fetch_maintenances
    mock_upcoming.return_value = {"scheduled_maintenances": []}
    mock_active.return_value = {"scheduled_maintenances": []}
    await get_maintenances(_mock_ctx)

    mock_upcoming.assert_awaited_once()
    mock_active.assert_awaited_once()


async def test_get_maintenances_api_error(
    _mock_ctx: MagicMock,
    _mock_fetch_maintenances: tuple[AsyncMock, AsyncMock],
) -> None:
    """API errors are surfaced in the response."""
    mock_upcoming, mock_active = _mock_fetch_maintenances
    mock_upcoming.side_effect = RuntimeError("maintenance backend offline")
    mock_active.return_value = {"scheduled_maintenances": []}
    result = await get_maintenances(_mock_ctx)

    assert "Error fetching maintenances" in result
    assert "maintenance backend offline" in result


async def test_cache_hit_returns_cached_response(
    _mock_ctx: MagicMock,
    _mock_fetch_status: AsyncMock,
) -> None:
    """Second call within TTL returns cached result without hitting the API."""
    _mock_fetch_status.return_value = {
        "status": {"indicator": "none", "description": "All Systems Operational"}
    }
    result1 = await get_overall_status(_mock_ctx)
    result2 = await get_overall_status(_mock_ctx)

    assert result1 == result2
    _mock_fetch_status.assert_awaited_once()


async def test_cache_miss_after_ttl(
    _mock_fetch_status: AsyncMock,
) -> None:
    """After TTL expiry, the cache misses and the API is called again."""
    cache = TTLCache(maxsize=64, ttl=0)
    cache_lock = asyncio.Lock()
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"cache": cache, "cache_lock": cache_lock}

    _mock_fetch_status.return_value = {
        "status": {"indicator": "none", "description": "All Systems Operational"}
    }
    await get_overall_status(ctx)
    await get_overall_status(ctx)

    assert _mock_fetch_status.await_count == 2


async def test_cache_not_populated_on_error(
    _mock_ctx: MagicMock,
    _mock_fetch_status: AsyncMock,
) -> None:
    """Errors from the API are not cached; next call retries the API."""
    request = httpx.Request("GET", "https://status.redhat.com/api/v2/status.json")
    _mock_fetch_status.side_effect = [
        httpx.ConnectError("failed", request=request),
        {"status": {"indicator": "none", "description": "All Systems Operational"}},
    ]
    result1 = await get_overall_status(_mock_ctx)
    result2 = await get_overall_status(_mock_ctx)

    assert "Error fetching status" in result1
    assert "All Systems Operational" in result2
    assert _mock_fetch_status.await_count == 2


async def test_components_cache_shared_between_tools(
    _mock_ctx: MagicMock,
    components_response: dict,
    _mock_fetch_components: AsyncMock,
) -> None:
    """list and details modes share the same components cache."""
    _mock_fetch_components.return_value = components_response
    await list_service_groups(_mock_ctx)
    await list_service_groups(_mock_ctx, "console")

    _mock_fetch_components.assert_awaited_once()


def test_triage_service_issue_without_service() -> None:
    """Generic triage prompt includes all investigation steps."""
    result = triage_service_issue()

    assert "get_overall_status" in result
    assert "get_incidents" in result
    assert "get_maintenances" in result
    assert "group_name=" not in result


def test_triage_service_issue_with_service() -> None:
    """Service-specific triage prompt drills into the named group."""
    result = triage_service_issue(service_name="console.redhat.com")

    assert "get_overall_status" in result
    assert "get_incidents" in result
    assert "get_maintenances" in result
    assert "list_service_groups" in result
    assert "group_name=" in result
    assert "console.redhat.com" in result


def test_status_report_prompt() -> None:
    """Status report prompt references all four tools in the recommended order."""
    result = status_report()

    assert "get_overall_status" in result
    assert "list_service_groups" in result
    assert "get_incidents" in result
    assert "get_maintenances" in result
    assert "group_name" in result
