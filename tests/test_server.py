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
) -> None:
    payload = {"status": {"indicator": indicator, "description": description}}

    with patch(
        "redhat_status_mcp.server.api.fetch_status", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = payload
        result = await get_overall_status()

    assert description in result
    assert icon in result


async def test_get_overall_status_operational(status_operational: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_status", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = status_operational
        result = await get_overall_status()

    assert "All Systems Operational" in result
    assert "✅" in result


async def test_get_overall_status_minor(status_minor_issues: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_status", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = status_minor_issues
        result = await get_overall_status()

    assert "Minor Service Degradation" in result
    assert "⚠️" in result


async def test_get_overall_status_major(status_major_outage: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_status", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = status_major_outage
        result = await get_overall_status()

    assert "Major Service Outage" in result
    assert "🔴" in result


async def test_get_overall_status_critical() -> None:
    critical_status = {
        "status": {
            "indicator": "critical",
            "description": "Critical Service Outage",
        }
    }

    with patch(
        "redhat_status_mcp.server.api.fetch_status", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = critical_status
        result = await get_overall_status()

    assert "Critical Service Outage" in result
    assert "🚨" in result


async def test_get_overall_status_unknown_indicator() -> None:
    unknown_status = {
        "status": {
            "indicator": "weird",
            "description": "Custom Provider Message",
        }
    }

    with patch(
        "redhat_status_mcp.server.api.fetch_status", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = unknown_status
        result = await get_overall_status()

    assert "Custom Provider Message" in result


async def test_get_overall_status_api_error() -> None:
    request = httpx.Request("GET", "https://status.redhat.com/api/v2/status.json")
    error = httpx.ConnectError("Connection failed", request=request)

    with patch(
        "redhat_status_mcp.server.api.fetch_status", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = error
        result = await get_overall_status()

    assert "Error fetching status" in result
    assert "Connection failed" in result


async def test_list_service_groups_returns_groups_sorted_with_counts(
    components_response: dict,
) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = components_response
        result = await list_service_groups()

    lines = result.splitlines()
    bullet_lines = [line for line in lines if line.startswith("- ")]
    assert len(bullet_lines) == 4
    assert bullet_lines == sorted(bullet_lines, key=str.casefold)
    assert "console.redhat.com" in result
    assert "3 services" in result


async def test_list_service_groups_ignores_non_group_components(
    components_response: dict,
) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = components_response
        result = await list_service_groups()

    assert "Ansible Automation Platform - Automation Hub" not in result
    assert "registry.redhat.io" not in result


async def test_list_service_groups_empty_components() -> None:
    empty_payload = {"components": []}
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = empty_payload
        result = await list_service_groups()

    assert "No service groups" in result


async def test_list_service_groups_api_error() -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = RuntimeError("components endpoint down")
        result = await list_service_groups()

    assert "Error fetching service groups" in result
    assert "components endpoint down" in result


async def test_get_service_group_details_exact_match(components_response: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = components_response
        result = await get_service_group_details("console.redhat.com")

    assert "console.redhat.com" in result
    assert "Ansible Automation Platform - Automation Hub" in result
    assert "Cost Management" in result


async def test_get_service_group_details_case_insensitive_match(
    components_response: dict,
) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = components_response
        result = await get_service_group_details("CONSOLE.REDHAT.COM")

    assert "Group: console.redhat.com" in result


async def test_get_service_group_details_partial_match(
    components_response: dict,
) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = components_response
        result = await get_service_group_details("console")

    assert "Group: console.redhat.com" in result


async def test_get_service_group_details_no_match(components_response: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = components_response
        result = await get_service_group_details("satellite")

    assert "No service group found" in result
    assert "list_service_groups" in result


async def test_get_service_group_details_multiple_matches(
    components_response: dict,
) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = components_response
        result = await get_service_group_details("redhat.com")

    assert "Multiple service groups matched" in result
    assert "console.redhat.com" in result
    assert "access.redhat.com" in result
    assert "bugzilla.redhat.com" in result


async def test_get_service_group_details_lists_child_statuses(
    components_response: dict,
) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = components_response
        result = await get_service_group_details("console")

    assert "Degraded Performance" in result
    assert "Partial Outage" in result


async def test_get_service_group_details_api_error() -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_components", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = RuntimeError("components timeout")
        result = await get_service_group_details("console")

    assert "Error fetching service group details" in result
    assert "components timeout" in result


async def test_get_incidents_empty(incidents_empty: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_unresolved_incidents",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = incidents_empty
        result = await get_incidents()

    assert "No unresolved incidents" in result


async def test_get_incidents_active_incident_format(incidents_response: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_unresolved_incidents",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = incidents_response
        result = await get_incidents()

    assert "Elevated error rates on console.redhat.com" in result
    assert "Impact: Major" in result
    assert "Status: Investigating" in result
    assert "Affected Components: console.redhat.com" in result


async def test_get_incidents_uses_most_recent_update_only(
    incidents_response: dict,
) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_unresolved_incidents",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = incidents_response
        result = await get_incidents()

    assert "continuing to investigate elevated error rates" in result
    assert "We are investigating reports of elevated error rates" not in result


async def test_get_incidents_handles_missing_updates() -> None:
    payload = {
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

    with patch(
        "redhat_status_mcp.server.api.fetch_unresolved_incidents",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = payload
        result = await get_incidents()

    assert "Storage API latency spike" in result
    assert "Latest Update: No updates posted yet" in result


async def test_get_incidents_api_error() -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_unresolved_incidents",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.side_effect = RuntimeError("incident endpoint timeout")
        result = await get_incidents()

    assert "Error fetching incidents" in result
    assert "incident endpoint timeout" in result


async def test_get_maintenances_both_empty(maintenances_empty: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_upcoming_maintenances",
        new_callable=AsyncMock,
    ) as mock_upcoming:
        with patch(
            "redhat_status_mcp.server.api.fetch_active_maintenances",
            new_callable=AsyncMock,
        ) as mock_active:
            mock_upcoming.return_value = maintenances_empty
            mock_active.return_value = maintenances_empty
            result = await get_maintenances()

    assert "No scheduled maintenances" in result


async def test_get_maintenances_upcoming_only(maintenances_upcoming: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_upcoming_maintenances",
        new_callable=AsyncMock,
    ) as mock_upcoming:
        with patch(
            "redhat_status_mcp.server.api.fetch_active_maintenances",
            new_callable=AsyncMock,
        ) as mock_active:
            mock_upcoming.return_value = maintenances_upcoming
            mock_active.return_value = {"scheduled_maintenances": []}
            result = await get_maintenances()

    assert "Upcoming Maintenances" in result
    assert "Scheduled maintenance on registry.redhat.io" in result
    assert "registry.redhat.io" in result


async def test_get_maintenances_active_only(maintenances_active: dict) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_upcoming_maintenances",
        new_callable=AsyncMock,
    ) as mock_upcoming:
        with patch(
            "redhat_status_mcp.server.api.fetch_active_maintenances",
            new_callable=AsyncMock,
        ) as mock_active:
            mock_upcoming.return_value = {"scheduled_maintenances": []}
            mock_active.return_value = maintenances_active
            result = await get_maintenances()

    assert "Active Maintenances" in result
    assert "Active maintenance on console.redhat.com" in result
    assert "console.redhat.com" in result


async def test_get_maintenances_both_present(
    maintenances_upcoming: dict,
    maintenances_active: dict,
) -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_upcoming_maintenances",
        new_callable=AsyncMock,
    ) as mock_upcoming:
        with patch(
            "redhat_status_mcp.server.api.fetch_active_maintenances",
            new_callable=AsyncMock,
        ) as mock_active:
            mock_upcoming.return_value = maintenances_upcoming
            mock_active.return_value = maintenances_active
            result = await get_maintenances()

    assert "Active Maintenances" in result
    assert "Upcoming Maintenances" in result
    assert "Active maintenance on console.redhat.com" in result
    assert "Scheduled maintenance on registry.redhat.io" in result


async def test_get_maintenances_calls_both_endpoints() -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_upcoming_maintenances",
        new_callable=AsyncMock,
    ) as mock_upcoming:
        with patch(
            "redhat_status_mcp.server.api.fetch_active_maintenances",
            new_callable=AsyncMock,
        ) as mock_active:
            mock_upcoming.return_value = {"scheduled_maintenances": []}
            mock_active.return_value = {"scheduled_maintenances": []}
            await get_maintenances()

    mock_upcoming.assert_awaited_once()
    mock_active.assert_awaited_once()


async def test_get_maintenances_api_error() -> None:
    with patch(
        "redhat_status_mcp.server.api.fetch_upcoming_maintenances",
        new_callable=AsyncMock,
    ) as mock_upcoming:
        with patch(
            "redhat_status_mcp.server.api.fetch_active_maintenances",
            new_callable=AsyncMock,
        ) as mock_active:
            mock_upcoming.side_effect = RuntimeError("maintenance backend offline")
            mock_active.return_value = {"scheduled_maintenances": []}
            result = await get_maintenances()

    assert "Error fetching maintenances" in result
    assert "maintenance backend offline" in result
