"""Tests for FastMCP server tools."""

import importlib
from unittest.mock import AsyncMock, patch

import httpx
import pytest

server = importlib.import_module("redhat_status_mcp.server")
get_overall_status = server.get_overall_status
list_service_groups = server.list_service_groups
get_service_group_details = server.get_service_group_details
get_incidents = server.get_incidents
get_maintenances = server.get_maintenances
triage_service_issue = server.triage_service_issue
status_report = server.status_report


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
    _mock_fetch_status: AsyncMock,
) -> None:
    """Each severity indicator maps to the correct icon and label."""
    _mock_fetch_status.return_value = {
        "status": {"indicator": indicator, "description": description}
    }
    result = await get_overall_status()

    assert description in result
    assert icon in result


async def test_get_overall_status_unknown_indicator(
    _mock_fetch_status: AsyncMock,
) -> None:
    """Unknown indicator values fall through gracefully."""
    _mock_fetch_status.return_value = {
        "status": {"indicator": "weird", "description": "Custom Provider Message"}
    }
    result = await get_overall_status()

    assert "Custom Provider Message" in result


async def test_get_overall_status_api_error(
    _mock_fetch_status: AsyncMock,
) -> None:
    """API connection failures are surfaced in the response."""
    request = httpx.Request("GET", "https://status.redhat.com/api/v2/status.json")
    _mock_fetch_status.side_effect = httpx.ConnectError(
        "Connection failed", request=request
    )
    result = await get_overall_status()

    assert "Error fetching status" in result
    assert "Connection failed" in result


async def test_list_service_groups_returns_groups_sorted_with_counts(
    components_response: dict,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Groups are listed alphabetically with correct child counts."""
    _mock_fetch_components.return_value = components_response
    result = await list_service_groups()

    lines = result.splitlines()
    bullet_lines = [line for line in lines if line.startswith("- ")]
    assert len(bullet_lines) == 4
    assert bullet_lines == sorted(bullet_lines, key=str.casefold)
    assert "console.redhat.com" in result
    assert "3 services" in result


async def test_list_service_groups_ignores_non_group_components(
    components_response: dict,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Child components are excluded from the group listing."""
    _mock_fetch_components.return_value = components_response
    result = await list_service_groups()

    assert "Ansible Automation Platform - Automation Hub" not in result
    assert "registry.redhat.io" not in result


async def test_list_service_groups_empty_components(
    _mock_fetch_components: AsyncMock,
) -> None:
    """Empty component list returns a friendly message."""
    _mock_fetch_components.return_value = {"components": []}
    result = await list_service_groups()

    assert "No service groups" in result


async def test_list_service_groups_api_error(
    _mock_fetch_components: AsyncMock,
) -> None:
    """API errors are surfaced in the response."""
    _mock_fetch_components.side_effect = RuntimeError("components endpoint down")
    result = await list_service_groups()

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
async def test_get_service_group_details_successful_match(
    query: str,
    components_response: dict,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Exact, case-insensitive, and partial queries all resolve to the correct group."""
    _mock_fetch_components.return_value = components_response
    result = await get_service_group_details(query)

    assert "Group: console.redhat.com" in result
    assert "Ansible Automation Platform - Automation Hub" in result
    assert "Cost Management" in result


async def test_get_service_group_details_no_match(
    components_response: dict,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Unmatched query suggests using list_service_groups."""
    _mock_fetch_components.return_value = components_response
    result = await get_service_group_details("satellite")

    assert "No service group found" in result
    assert "list_service_groups" in result


async def test_get_service_group_details_multiple_matches(
    components_response: dict,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Ambiguous query returns all matching group names."""
    _mock_fetch_components.return_value = components_response
    result = await get_service_group_details("redhat.com")

    assert "Multiple service groups matched" in result
    assert "console.redhat.com" in result
    assert "access.redhat.com" in result
    assert "bugzilla.redhat.com" in result


async def test_get_service_group_details_lists_child_statuses(
    components_response: dict,
    _mock_fetch_components: AsyncMock,
) -> None:
    """Child service statuses are formatted and included."""
    _mock_fetch_components.return_value = components_response
    result = await get_service_group_details("console")

    assert "Degraded Performance" in result
    assert "Partial Outage" in result


async def test_get_service_group_details_api_error(
    _mock_fetch_components: AsyncMock,
) -> None:
    """API errors are surfaced in the response."""
    _mock_fetch_components.side_effect = RuntimeError("components timeout")
    result = await get_service_group_details("console")

    assert "Error fetching service group details" in result
    assert "components timeout" in result


async def test_get_incidents_empty(
    incidents_empty: dict,
    _mock_fetch_incidents: AsyncMock,
) -> None:
    """No incidents returns a friendly message."""
    _mock_fetch_incidents.return_value = incidents_empty
    result = await get_incidents()

    assert "No unresolved incidents" in result


async def test_get_incidents_active_incident_format(
    incidents_response: dict,
    _mock_fetch_incidents: AsyncMock,
) -> None:
    """Active incidents include name, impact, status, and affected components."""
    _mock_fetch_incidents.return_value = incidents_response
    result = await get_incidents()

    assert "Elevated error rates on console.redhat.com" in result
    assert "Impact: Major" in result
    assert "Status: Investigating" in result
    assert "Affected Components: console.redhat.com" in result


async def test_get_incidents_uses_most_recent_update_only(
    incidents_response: dict,
    _mock_fetch_incidents: AsyncMock,
) -> None:
    """Only the latest update body is shown, not older ones."""
    _mock_fetch_incidents.return_value = incidents_response
    result = await get_incidents()

    assert "continuing to investigate elevated error rates" in result
    assert "We are investigating reports of elevated error rates" not in result


async def test_get_incidents_handles_missing_updates(
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
    result = await get_incidents()

    assert "Storage API latency spike" in result
    assert "Latest Update: No updates posted yet" in result


async def test_get_incidents_api_error(
    _mock_fetch_incidents: AsyncMock,
) -> None:
    """API errors are surfaced in the response."""
    _mock_fetch_incidents.side_effect = RuntimeError("incident endpoint timeout")
    result = await get_incidents()

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
    result = await get_maintenances()

    for text in expected:
        assert text in result
    for text in not_expected:
        assert text not in result


async def test_get_maintenances_calls_both_endpoints(
    _mock_fetch_maintenances: tuple[AsyncMock, AsyncMock],
) -> None:
    """Both upcoming and active endpoints are always called."""
    mock_upcoming, mock_active = _mock_fetch_maintenances
    mock_upcoming.return_value = {"scheduled_maintenances": []}
    mock_active.return_value = {"scheduled_maintenances": []}
    await get_maintenances()

    mock_upcoming.assert_awaited_once()
    mock_active.assert_awaited_once()


async def test_get_maintenances_api_error(
    _mock_fetch_maintenances: tuple[AsyncMock, AsyncMock],
) -> None:
    """API errors are surfaced in the response."""
    mock_upcoming, mock_active = _mock_fetch_maintenances
    mock_upcoming.side_effect = RuntimeError("maintenance backend offline")
    mock_active.return_value = {"scheduled_maintenances": []}
    result = await get_maintenances()

    assert "Error fetching maintenances" in result
    assert "maintenance backend offline" in result


def test_triage_service_issue_without_service() -> None:
    """Generic triage prompt includes all investigation steps."""
    result = triage_service_issue()

    assert "get_overall_status" in result
    assert "get_incidents" in result
    assert "get_maintenances" in result
    assert "get_service_group_details" not in result


def test_triage_service_issue_with_service() -> None:
    """Service-specific triage prompt drills into the named group."""
    result = triage_service_issue(service_name="console.redhat.com")

    assert "get_overall_status" in result
    assert "get_incidents" in result
    assert "get_maintenances" in result
    assert "get_service_group_details" in result
    assert "console.redhat.com" in result


def test_status_report_prompt() -> None:
    """Status report prompt references all five tools in the recommended order."""
    result = status_report()

    assert "get_overall_status" in result
    assert "list_service_groups" in result
    assert "get_incidents" in result
    assert "get_maintenances" in result
    assert "get_service_group_details" in result
