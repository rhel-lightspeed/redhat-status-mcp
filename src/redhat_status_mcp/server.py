"""FastMCP tools for Red Hat status information."""

from datetime import datetime

from fastmcp import FastMCP

from redhat_status_mcp import api

mcp = FastMCP("Red Hat Status")

_INDICATOR_LABELS = {
    "none": "✅ All Systems Operational",
    "minor": "⚠️ Minor Service Degradation",
    "major": "🔴 Major Service Outage",
    "critical": "🚨 Critical Service Outage",
}


def _format_status(value: str) -> str:
    """Convert API status tokens into readable text."""
    return value.replace("_", " ").title() if value else "Unknown"


@mcp.tool
async def get_overall_status() -> str:
    """Get the overall Red Hat service status."""
    try:
        data = await api.fetch_status()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        return f"Error fetching status: {error}"

    status = data.get("status", {})
    indicator = str(status.get("indicator", "none")).lower()
    description = status.get("description", "No status description available")
    headline = _INDICATOR_LABELS.get(indicator, f"Status indicator: {indicator}")
    return f"{headline}\nDescription: {description}"


@mcp.tool
async def list_service_groups() -> str:
    """List service groups and their child service counts."""
    try:
        data = await api.fetch_components()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        return f"Error fetching service groups: {error}"

    components = data.get("components", [])
    groups = [component for component in components if component.get("group")]
    if not groups:
        return "No service groups found."

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


@mcp.tool
async def get_service_group_details(group_name: str) -> str:
    """Get details for a single service group and its child services."""
    try:
        data = await api.fetch_components()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        return f"Error fetching service group details: {error}"

    components = data.get("components", [])
    matches = _find_groups(components, group_name)
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


@mcp.tool
async def get_incidents() -> str:
    """Get unresolved incidents with latest update details."""
    try:
        data = await api.fetch_unresolved_incidents()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        return f"Error fetching incidents: {error}"

    incidents = data.get("incidents", [])
    if not incidents:
        return "No unresolved incidents at this time."

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


@mcp.tool
async def get_maintenances() -> str:
    """Get active and upcoming scheduled maintenances."""
    try:
        upcoming_data = await api.fetch_upcoming_maintenances()
        active_data = await api.fetch_active_maintenances()
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        return f"Error fetching maintenances: {error}"

    upcoming = upcoming_data.get("scheduled_maintenances", [])
    active = active_data.get("scheduled_maintenances", [])
    if not active and not upcoming:
        return "No scheduled maintenances at this time."

    lines = ["Active Maintenances:"]
    lines.extend(_format_maintenances(active))
    lines.append("Upcoming Maintenances:")
    lines.extend(_format_maintenances(upcoming))
    return "\n".join(lines)
