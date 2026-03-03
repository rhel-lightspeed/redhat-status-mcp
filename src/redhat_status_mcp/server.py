"""FastMCP tools and prompts for Red Hat status information."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from redhat_status_mcp import api
from redhat_status_mcp.config import ServerConfig


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Manage shared resources for the lifetime of the MCP server."""
    config = ServerConfig()
    limits = httpx.Limits(max_connections=config.max_connections)
    timeout = httpx.Timeout(config.request_timeout)
    client = httpx.AsyncClient(limits=limits, timeout=timeout)
    api.set_client(client)
    try:
        yield {}
    finally:
        await api.close_client()


mcp = FastMCP("Red Hat Status", lifespan=app_lifespan)

logger = logging.getLogger(__name__)

_INDICATOR_LABELS = {
    "none": "✅ All Systems Operational",
    "minor": "⚠️ Minor Service Degradation",
    "major": "🔴 Major Service Outage",
    "critical": "🚨 Critical Service Outage",
}


def _format_status(value: str) -> str:
    """Convert API status tokens into readable text."""
    return value.replace("_", " ").title() if value else "Unknown"


_READONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_overall_status() -> str:
    """Get the overall Red Hat service status.

    Returns a severity indicator (operational, minor, major, or critical) with a
    human-readable description. Call this first to decide whether deeper
    investigation with get_incidents or get_service_group_details is needed.
    """
    logger.info("Tool called: get_overall_status")
    try:
        data = await api.fetch_status()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        logger.exception("Failed to fetch overall status")
        return f"Error fetching status: {error}"

    status = data.get("status", {})
    indicator = str(status.get("indicator", "none")).lower()
    logger.info("Overall status indicator: %s", indicator)
    description = status.get("description", "No status description available")
    headline = _INDICATOR_LABELS.get(indicator, f"Status indicator: {indicator}")
    return f"{headline}\nDescription: {description}"


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def list_service_groups() -> str:
    """List all Red Hat service groups with current status and counts.

    Use this to discover valid group names before calling
    get_service_group_details.
    """
    logger.info("Tool called: list_service_groups")
    try:
        data = await api.fetch_components()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        logger.exception("Failed to fetch service groups")
        return f"Error fetching service groups: {error}"

    components = data.get("components", [])
    groups = [component for component in components if component.get("group")]
    if not groups:
        return "No service groups found."

    logger.info("Found %d service groups", len(groups))

    lines = ["Service Groups:"]
    for group in sorted(groups, key=lambda item: str(item.get("name", "")).casefold()):
        child_count = len(group.get("components", []))
        service_label = "service" if child_count == 1 else "services"
        lines.append(
            f"- {group.get('name', 'Unnamed Group')}"
            " ("
            f"{_format_status(group.get('status', 'unknown'))}, "
            f"{child_count} {service_label}"
            ")"
        )
    return "\n".join(lines)


def _find_groups(components: list[dict], query: str) -> list[dict]:
    """Find group components by case-insensitive substring match."""
    normalized_query = query.casefold()
    groups = [component for component in components if component.get("group")]
    return [
        group
        for group in groups
        if normalized_query in str(group.get("name", "")).casefold()
    ]


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_service_group_details(
    group_name: Annotated[
        str,
        Field(
            description="Case-insensitive substring to match against group names "
            "(e.g. 'console' matches 'console.redhat.com'). "
            "Call list_service_groups first to discover valid names."
        ),
    ],
) -> str:
    """Get details for a single service group.

    Includes child services and their statuses. Accepts partial,
    case-insensitive group names. If multiple groups match, the matching
    names are returned so you can refine your query.
    """
    logger.info("Tool called: get_service_group_details (group_name=%r)", group_name)
    try:
        data = await api.fetch_components()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        logger.exception("Failed to fetch service group details")
        return f"Error fetching service group details: {error}"

    components = data.get("components", [])
    matches = _find_groups(components, group_name)
    logger.info("Group query '%s' matched %d result(s)", group_name, len(matches))
    if not matches:
        return (
            f"No service group found matching '{group_name}'. "
            "Use list_service_groups to see available groups."
        )

    if len(matches) > 1:
        names = "\n".join(
            f"- {group.get('name', 'Unnamed Group')}"
            for group in sorted(
                matches, key=lambda item: str(item.get("name", "")).casefold()
            )
        )
        return (
            f"Multiple service groups matched '{group_name}'. "
            f"Please be more specific:\n{names}"
        )

    group = matches[0]
    children = [
        component
        for component in components
        if not component.get("group") and component.get("group_id") == group.get("id")
    ]
    lines = [
        f"Group: {group.get('name', 'Unnamed Group')}",
        f"Status: {_format_status(group.get('status', 'unknown'))}",
        "Services:",
    ]
    if not children:
        lines.append("- No child services listed")
        return "\n".join(lines)

    for child in sorted(
        children, key=lambda item: str(item.get("name", "")).casefold()
    ):
        child_status = _format_status(child.get("status", "unknown"))
        lines.append(f"- {child.get('name', 'Unnamed Service')} ({child_status})")
    return "\n".join(lines)


def _component_names(components: list[dict]) -> str:
    """Join component names for compact readable output."""
    names = [
        str(component.get("name", "Unknown component")) for component in components
    ]
    return ", ".join(names) if names else "None listed"


def _format_timestamp(value: str | None) -> str:
    """Convert ISO timestamp into readable UTC text."""
    if not value:
        return "Unknown"

    normalized = value.replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        return "Unknown"
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_incidents() -> str:
    """Get all currently unresolved Red Hat service incidents.

    Returns each incident's name, severity, status, affected components, and the
    most recent update. Use this when get_overall_status reports degraded service.
    """
    logger.info("Tool called: get_incidents")
    try:
        data = await api.fetch_unresolved_incidents()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        logger.exception("Failed to fetch incidents")
        return f"Error fetching incidents: {error}"

    incidents = data.get("incidents", [])
    if not incidents:
        return "No unresolved incidents at this time."

    logger.info("Found %d unresolved incident(s)", len(incidents))

    lines = ["Unresolved Incidents:"]
    for incident in incidents:
        updates = incident.get("incident_updates", [])
        latest_update = updates[0] if updates else {}
        latest_body = latest_update.get("body", "No updates posted yet")
        affected_components = _component_names(incident.get("components", []))
        lines.extend(
            [
                f"- {incident.get('name', 'Unnamed Incident')}",
                f"  Impact: {_format_status(incident.get('impact', 'unknown'))}",
                f"  Status: {_format_status(incident.get('status', 'unknown'))}",
                f"  Affected Components: {affected_components}",
                f"  Latest Update: {latest_body}",
            ]
        )
    return "\n".join(lines)


def _format_maintenances(maintenances: list[dict]) -> list[str]:
    """Format maintenance entries as readable bullet lines."""
    if not maintenances:
        return ["- None"]

    lines: list[str] = []
    for maintenance in maintenances:
        scheduled_start = _format_timestamp(maintenance.get("scheduled_for"))
        scheduled_end = _format_timestamp(maintenance.get("scheduled_until"))
        affected_components = _component_names(maintenance.get("components", []))
        lines.extend(
            [
                f"- {maintenance.get('name', 'Unnamed Maintenance')}",
                f"  Status: {_format_status(maintenance.get('status', 'unknown'))}",
                f"  Scheduled Start: {scheduled_start}",
                f"  Scheduled End: {scheduled_end}",
                f"  Affected Components: {affected_components}",
            ]
        )
    return lines


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_maintenances() -> str:
    """Get active and upcoming scheduled maintenances for Red Hat services.

    Returns maintenance windows with their status, time range, and affected
    components. Use this to check whether an outage is due to planned maintenance.
    """
    logger.info("Tool called: get_maintenances")
    try:
        upcoming_data = await api.fetch_upcoming_maintenances()
        active_data = await api.fetch_active_maintenances()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        logger.exception("Failed to fetch maintenances")
        return f"Error fetching maintenances: {error}"

    upcoming = upcoming_data.get("scheduled_maintenances", [])
    active = active_data.get("scheduled_maintenances", [])
    logger.info(
        "Found %d active and %d upcoming maintenance(s)",
        len(active),
        len(upcoming),
    )
    if not active and not upcoming:
        return "No scheduled maintenances at this time."

    lines = ["Active Maintenances:"]
    lines.extend(_format_maintenances(active))
    lines.append("Upcoming Maintenances:")
    lines.extend(_format_maintenances(upcoming))
    return "\n".join(lines)


@mcp.prompt
def triage_service_issue(
    service_name: Annotated[
        str,
        Field(description="The Red Hat service experiencing issues"),
    ] = "",
) -> str:
    """Triage a service issue via status, incidents, and maintenances."""
    logger.info("Prompt called: triage_service_issue (service_name=%r)", service_name)
    base = (
        "Check the current Red Hat service health:\n"
        "1. Call get_overall_status to see the overall severity.\n"
        "2. Call get_incidents to find any active incidents.\n"
        "3. Call get_maintenances to check for planned maintenance windows.\n"
    )
    if service_name:
        return (
            f"{base}"
            f"4. Call get_service_group_details with '{service_name}' to check "
            "that specific service group.\n"
            "Summarize whether the issue is a known incident, planned "
            "maintenance, or potentially unreported."
        )
    return (
        f"{base}"
        "Summarize the overall health and flag any services that are not fully "
        "operational."
    )


@mcp.prompt
def status_report() -> str:
    """Generate a comprehensive Red Hat service status report."""
    logger.info("Prompt called: status_report")
    return (
        "Generate a Red Hat service status report:\n"
        "1. Call get_overall_status for the top-level health indicator.\n"
        "2. Call list_service_groups to get all groups and their statuses.\n"
        "3. Call get_incidents for any unresolved incidents.\n"
        "4. Call get_maintenances for active and upcoming maintenance windows.\n"
        "5. For any service group not showing 'Operational', call "
        "get_service_group_details to identify the affected child services.\n"
        "Present the results as a structured status report with sections for "
        "overall health, incidents, maintenances, and degraded services."
    )
