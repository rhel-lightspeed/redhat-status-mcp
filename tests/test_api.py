"""Tests for the Red Hat Statuspage API client."""

import importlib
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

api = importlib.import_module("redhat_status_mcp.api")


@pytest.fixture(autouse=True)
def _reset_client():
    """Reset shared client before and after each test."""
    api._client = None
    yield
    api._client = None


async def test_fetch_status_returns_parsed_json() -> None:
    """Successful fetch returns the parsed JSON payload."""
    payload = {
        "status": {"indicator": "none", "description": "All Systems Operational"}
    }
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    api.set_client(mock_client)

    result = await api.fetch_status()
    assert result == payload


async def test_fetch_components_returns_parsed_json(components_response: dict) -> None:
    """Successful fetch returns the parsed components payload."""
    mock_response = MagicMock()
    mock_response.json.return_value = components_response
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    api.set_client(mock_client)

    result = await api.fetch_components()
    assert result == components_response


async def test_fetch_unresolved_incidents_returns_parsed_json(
    incidents_response: dict,
) -> None:
    """Successful fetch returns the parsed incidents payload."""
    mock_response = MagicMock()
    mock_response.json.return_value = incidents_response
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    api.set_client(mock_client)

    result = await api.fetch_unresolved_incidents()
    assert result == incidents_response


async def test_fetch_upcoming_maintenances_returns_parsed_json(
    maintenances_upcoming: dict,
) -> None:
    """Successful fetch returns the parsed upcoming maintenances payload."""
    mock_response = MagicMock()
    mock_response.json.return_value = maintenances_upcoming
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    api.set_client(mock_client)

    result = await api.fetch_upcoming_maintenances()
    assert result == maintenances_upcoming


async def test_fetch_active_maintenances_returns_parsed_json(
    maintenances_active: dict,
) -> None:
    """Successful fetch returns the parsed active maintenances payload."""
    mock_response = MagicMock()
    mock_response.json.return_value = maintenances_active
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    api.set_client(mock_client)

    result = await api.fetch_active_maintenances()
    assert result == maintenances_active


async def test_fetch_status_http_error() -> None:
    """HTTPStatusError from the API propagates to the caller."""
    request = httpx.Request("GET", "https://status.redhat.com/api/v2/status.json")
    response = httpx.Response(status_code=503, request=request)
    error = httpx.HTTPStatusError(
        "Service unavailable", request=request, response=response
    )

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=error)
    api.set_client(mock_client)

    with pytest.raises(httpx.HTTPStatusError):
        await api.fetch_status()


async def test_fetch_status_connect_error() -> None:
    """ConnectError from the API propagates to the caller."""
    request = httpx.Request("GET", "https://status.redhat.com/api/v2/status.json")
    error = httpx.ConnectError("Connection failed", request=request)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=error)
    api.set_client(mock_client)

    with pytest.raises(httpx.ConnectError):
        await api.fetch_status()


async def test_fetch_status_uses_expected_endpoint() -> None:
    """fetch_status hits the correct status.json endpoint."""
    payload = {"status": {"indicator": "none"}}
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    api.set_client(mock_client)

    await api.fetch_status()

    mock_client.get.assert_awaited_once_with(
        "https://status.redhat.com/api/v2/status.json"
    )


async def test_get_client_raises_without_initialization() -> None:
    """get_client raises RuntimeError when no client has been set."""
    with pytest.raises(RuntimeError, match="HTTP client not initialized"):
        api.get_client()


async def test_close_client_resets_to_none() -> None:
    """close_client closes the client and resets the module-level reference."""
    mock_client = AsyncMock()
    api.set_client(mock_client)

    await api.close_client()

    assert api._client is None
    mock_client.aclose.assert_awaited_once()


async def test_close_client_noop_when_none() -> None:
    """close_client is a no-op when no client is set."""
    await api.close_client()
    assert api._client is None
