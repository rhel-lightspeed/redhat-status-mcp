"""Tests for the Red Hat Statuspage API client."""

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

api = importlib.import_module("redhat_status_mcp.api")


def _mock_async_client_with_response(response: MagicMock) -> AsyncMock:
    """Build an AsyncClient mock usable as an async context manager."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=response)
    return mock_client


async def test_fetch_status_returns_parsed_json() -> None:
    """Successful fetch returns the parsed JSON payload."""
    payload = {
        "status": {"indicator": "none", "description": "All Systems Operational"}
    }
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = _mock_async_client_with_response(mock_response)
        mock_client_class.return_value = mock_client

        result = await api.fetch_status()

    assert result == payload


async def test_fetch_components_returns_parsed_json(components_response: dict) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = components_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = _mock_async_client_with_response(mock_response)
        mock_client_class.return_value = mock_client

        result = await api.fetch_components()

    assert result == components_response


async def test_fetch_unresolved_incidents_returns_parsed_json(
    incidents_response: dict,
) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = incidents_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = _mock_async_client_with_response(mock_response)
        mock_client_class.return_value = mock_client

        result = await api.fetch_unresolved_incidents()

    assert result == incidents_response


async def test_fetch_upcoming_maintenances_returns_parsed_json(
    maintenances_upcoming: dict,
) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = maintenances_upcoming
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = _mock_async_client_with_response(mock_response)
        mock_client_class.return_value = mock_client

        result = await api.fetch_upcoming_maintenances()

    assert result == maintenances_upcoming


async def test_fetch_active_maintenances_returns_parsed_json(
    maintenances_active: dict,
) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = maintenances_active
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = _mock_async_client_with_response(mock_response)
        mock_client_class.return_value = mock_client

        result = await api.fetch_active_maintenances()

    assert result == maintenances_active


async def test_fetch_status_http_error() -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    request = httpx.Request("GET", "https://status.redhat.com/api/v2/status.json")
    response = httpx.Response(status_code=503, request=request)
    error = httpx.HTTPStatusError(
        "Service unavailable", request=request, response=response
    )
    mock_client.get = AsyncMock(side_effect=error)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await api.fetch_status()


async def test_fetch_status_connect_error() -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    request = httpx.Request("GET", "https://status.redhat.com/api/v2/status.json")
    error = httpx.ConnectError("Connection failed", request=request)
    mock_client.get = AsyncMock(side_effect=error)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.ConnectError):
            await api.fetch_status()


async def test_fetch_status_uses_expected_endpoint() -> None:
    """fetch_status hits the correct status.json endpoint."""
    payload = {"status": {"indicator": "none"}}
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = _mock_async_client_with_response(mock_response)
        mock_client_class.return_value = mock_client

        await api.fetch_status()

    mock_client.get.assert_awaited_once_with(
        "https://status.redhat.com/api/v2/status.json"
    )
