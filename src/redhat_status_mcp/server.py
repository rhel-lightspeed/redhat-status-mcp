"""FastMCP tools and prompts for Red Hat status information."""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

import httpx
from cachetools import TTLCache
from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from redhat_status_mcp import api
from redhat_status_mcp.config import ServerConfig


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Manage shared resources for the lifetime of the MCP server."""
    config = ServerConfig()
    api.set_config(config)
    limits = httpx.Limits(max_connections=config.max_connections)
    timeout = httpx.Timeout(config.request_timeout)
    client = httpx.AsyncClient(limits=limits, timeout=timeout)
    api.set_client(client)
    cache: TTLCache = TTLCache(maxsize=64, ttl=config.cache_ttl)
    cache_lock = asyncio.Lock()
    try:
        yield {"cache": cache, "cache_lock": cache_lock}
    finally:
        await api.close_client()


mcp = FastMCP("Red Hat Status", lifespan=app_lifespan)

logger = logging.getLogger(__name__)


async def _cached_fetch(
    ctx: Context,
    cache_key: str,
    fetcher: Callable[[], Awaitable[dict]],
) -> dict:
    """Fetch data from cache or API, storing successful responses in cache."""
    request_context = ctx.request_context
    assert request_context is not None, "request_context must be set"
    cache: TTLCache = request_context.lifespan_context["cache"]
    cache_lock: asyncio.Lock = request_context.lifespan_context["cache_lock"]

    async with cache_lock:
        if cache_key in cache:
            logger.debug("Cache hit for key: %s", cache_key)
            return cache[cache_key]

    # Cache miss — fetch outside the lock
    logger.debug("Cache miss for key: %s", cache_key)
    result = await fetcher()

    async with cache_lock:
        cache[cache_key] = result

    return result


_INDICATOR_LABELS = {
    "none": "✅ All Systems Operational",
    "minor": "⚠️ Minor Service Degradation",
    "major": "🔴 Major Service Outage",
    "critical": "🚨 Critical Service Outage",
}


def _format_status(value: str) -> str:
    """Convert API status tokens into readable text."""
    return value.replace("_", " ").title() if value else "Unknown"


def _render_service_group_list(groups: list[dict]) -> str:
    """Render all service groups with status and child counts."""
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


def _find_group_matches(groups: list[dict], group_name: str) -> list[dict]:
    """Find service groups by case-insensitive substring match."""
    normalized_query = group_name.casefold()
    return [
        group
        for group in groups
        if normalized_query in str(group.get("name", "")).casefold()
    ]


def _render_group_details(
    components: list[dict], matches: list[dict], group_name: str
) -> str:
    """Render one matched group's child service status details."""
    if not matches:
        return (
            f"No service group found matching '{group_name}'. "
            "Call list_service_groups without group_name to see available groups."
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


_READONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_overall_status(ctx: Context) -> str:
    """Get the overall Red Hat service status.

    Returns a severity indicator (operational, minor, major, or critical) with a
    human-readable description. Call this first to decide whether deeper
    investigation with get_incidents or list_service_groups is needed.
    """
    logger.info("Tool called: get_overall_status")
    try:
        data = await _cached_fetch(ctx, "status", api.fetch_status)
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
async def list_service_groups(
    ctx: Context,
    group_name: Annotated[
        str | None,
        Field(
            description="Optional case-insensitive substring to match group names "
            "(e.g. 'console' matches 'console.redhat.com'). "
            "Leave empty to list all service groups."
        ),
    ] = None,
) -> str:
    """List service groups or drill into one group's child services.

    When ``group_name`` is empty, returns all service groups with statuses and
    child service counts. When provided, returns matching group details and
    child service statuses.
    """
    logger.info("Tool called: list_service_groups (group_name=%r)", group_name)
    try:
        data = await _cached_fetch(ctx, "components", api.fetch_components)
    except Exception as error:  # pragma: no cover - tested via mocked exception path
        logger.exception("Failed to fetch service groups")
        return f"Error fetching service groups: {error}"

    components = data.get("components", [])
    groups = [component for component in components if component.get("group")]
    if not groups:
        return "No service groups found."

    if not group_name:
        logger.info("Found %d service groups", len(groups))
        return _render_service_group_list(groups)

    matches = _find_group_matches(groups, group_name)
    logger.info("Group query '%s' matched %d result(s)", group_name, len(matches))
    return _render_group_details(components, matches, group_name)


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
async def get_incidents(ctx: Context) -> str:
    """Get all currently unresolved Red Hat service incidents.

    Returns each incident's name, severity, status, affected components, and the
    most recent update. Use this when get_overall_status reports degraded service.
    """
    logger.info("Tool called: get_incidents")
    try:
        data = await _cached_fetch(ctx, "incidents", api.fetch_unresolved_incidents)
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
async def get_maintenances(ctx: Context) -> str:
    """Get active and upcoming scheduled maintenances for Red Hat services.

    Returns maintenance windows with their status, time range, and affected
    components. Use this to check whether an outage is due to planned maintenance.
    """
    logger.info("Tool called: get_maintenances")
    try:
        upcoming_data, active_data = await asyncio.gather(
            _cached_fetch(
                ctx, "upcoming_maintenances", api.fetch_upcoming_maintenances
            ),
            _cached_fetch(ctx, "active_maintenances", api.fetch_active_maintenances),
        )
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
            f"4. Call list_service_groups with group_name='{service_name}' to "
            "check that specific service group.\n"
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
        "list_service_groups with group_name set to that group to identify "
        "the affected child services.\n"
        "Present the results as a structured status report with sections for "
        "overall health, incidents, maintenances, and degraded services."
    )
