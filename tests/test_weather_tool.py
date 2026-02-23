"""Tests for the weather tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from assistant.tools.weather_tool import get_weather


def _mock_geo_response(results: list | None = None):
    """Create a mock geocoding response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    data = {}
    if results is not None:
        data["results"] = results
    resp.json.return_value = data
    return resp


def _mock_weather_response(include_hourly: bool = False):
    """Create a mock weather forecast response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    data = {
        "current": {
            "temperature_2m": 22.5,
            "relative_humidity_2m": 55,
            "wind_speed_10m": 12.3,
            "weather_code": 1,
        },
        "daily": {
            "time": ["2026-02-22", "2026-02-23"],
            "weather_code": [1, 61],
            "temperature_2m_max": [24.0, 18.0],
            "temperature_2m_min": [15.0, 12.0],
            "precipitation_sum": [0.0, 5.2],
        },
    }
    if include_hourly:
        data["hourly"] = {
            "time": ["2026-02-22T00:00", "2026-02-22T01:00", "2026-02-22T02:00"],
            "temperature_2m": [18.0, 17.5, 17.0],
            "weather_code": [0, 1, 2],
            "precipitation": [0.0, 0.0, 0.3],
            "wind_speed_10m": [5.0, 4.5, 6.0],
        }
    resp.json.return_value = data
    return resp


@pytest.mark.asyncio
async def test_get_weather_success():
    geo = _mock_geo_response([
        {"latitude": 51.5, "longitude": -0.12, "name": "London", "country": "United Kingdom"}
    ])
    weather = _mock_weather_response()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=[geo, weather])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("assistant.tools.weather_tool.httpx.AsyncClient", return_value=mock_client):
        result = await get_weather({"location": "London"})

    assert "London, United Kingdom" in result
    assert "22.5°C" in result
    assert "Mainly clear" in result
    assert "2026-02-23" in result
    assert "Slight rain" in result
    assert "5.2 mm precip" in result


@pytest.mark.asyncio
async def test_get_weather_unknown_location():
    geo = _mock_geo_response(None)

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=geo)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("assistant.tools.weather_tool.httpx.AsyncClient", return_value=mock_client):
        result = await get_weather({"location": "Xyzzyville"})

    assert "Could not find location" in result


@pytest.mark.asyncio
async def test_get_weather_api_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("assistant.tools.weather_tool.httpx.AsyncClient", return_value=mock_client):
        result = await get_weather({"location": "London"})

    assert "Weather API error" in result


@pytest.mark.asyncio
async def test_get_weather_hourly():
    geo = _mock_geo_response([
        {"latitude": 51.5, "longitude": -0.12, "name": "London", "country": "United Kingdom"}
    ])
    weather = _mock_weather_response(include_hourly=True)

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=[geo, weather])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("assistant.tools.weather_tool.httpx.AsyncClient", return_value=mock_client):
        result = await get_weather({"location": "London", "hourly": True})

    assert "Hourly Forecast" in result
    assert "2026-02-22T00:00" in result
    assert "Clear sky" in result
    assert "18.0°C" in result
    assert "0.3 mm" in result


@pytest.mark.asyncio
async def test_get_weather_no_location():
    with pytest.raises(ValueError, match="No location provided"):
        await get_weather({"location": ""})
