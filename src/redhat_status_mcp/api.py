"""Red Hat Statuspage public API client."""

import logging

import httpx

from redhat_status_mcp.config import ServerConfig

logger = logging.getLogger(__name__)

_config = ServerConfig()


async def _fetch_json(path: str) -> dict:
    """Fetch and return JSON content from a Statuspage API path."""
    url = f"{_config.base_url}/{path}"
    logger.info("Fetching %s", url)
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def fetch_status() -> dict:
    """Fetch the overall Red Hat status page indicator."""
    return await _fetch_json("status.json")


async def fetch_components() -> dict:
    """Fetch all service components and their current statuses."""
    return await _fetch_json("components.json")


async def fetch_unresolved_incidents() -> dict:
    """Fetch all currently unresolved incidents."""
    return await _fetch_json("incidents/unresolved.json")


async def fetch_upcoming_maintenances() -> dict:
    """Fetch all upcoming scheduled maintenances."""
    return await _fetch_json("scheduled-maintenances/upcoming.json")


async def fetch_active_maintenances() -> dict:
    """Fetch all currently active scheduled maintenances."""
    return await _fetch_json("scheduled-maintenances/active.json")
