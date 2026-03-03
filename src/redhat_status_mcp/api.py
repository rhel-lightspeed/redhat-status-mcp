"""Red Hat Statuspage public API client."""

import logging

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from redhat_status_mcp.config import ServerConfig

logger = logging.getLogger(__name__)

_config = ServerConfig()

_client: httpx.AsyncClient | None = None


def set_client(client: httpx.AsyncClient) -> None:
    """Set the shared HTTP client for all API requests."""
    global _client
    _client = client


def get_client() -> httpx.AsyncClient:
    """Return the shared HTTP client, raising RuntimeError if not initialized."""
    if _client is None:
        raise RuntimeError("HTTP client not initialized. Call set_client() first.")
    return _client


async def close_client() -> None:
    """Close and reset the shared HTTP client."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _log_before_sleep(retry_state: RetryCallState) -> None:
    """Log a warning before each retry sleep."""
    logger.warning(
        "Retrying after attempt %d due to: %s",
        retry_state.attempt_number,
        retry_state.outcome.exception() if retry_state.outcome else "unknown error",
    )


def _is_retryable(exc: BaseException) -> bool:
    """Return True if the exception warrants a retry attempt."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException))


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(_config.max_retries + 1),
    wait=wait_exponential(multiplier=1, min=0.5, max=10),
    before_sleep=_log_before_sleep,
    reraise=True,
)
async def _fetch_json(path: str) -> dict:
    """Fetch and return JSON content from a Statuspage API path."""
    url = f"{_config.base_url}/{path}"
    logger.info("Fetching %s", url)
    client = get_client()
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
