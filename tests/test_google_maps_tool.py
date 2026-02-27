"""Tests for the Google Maps tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from assistant.tools.google_maps_tool import google_maps


API_KEY = "test-api-key"


def _mock_response(data: dict, status_code: int = 200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json.return_value = data
    return resp


def _make_client(*responses):
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=list(responses))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


@pytest.mark.asyncio
async def test_directions_success():
    data = {
        "status": "OK",
        "routes": [{
            "summary": "I-495 N",
            "legs": [{
                "start_address": "Times Square, NY",
                "end_address": "JFK Airport, NY",
                "distance": {"text": "20.5 mi"},
                "duration": {"text": "35 mins"},
                "duration_in_traffic": {"text": "50 mins"},
                "steps": [
                    {
                        "html_instructions": "Head <b>south</b> on Broadway",
                        "distance": {"text": "0.5 mi"},
                        "duration": {"text": "2 mins"},
                    },
                    {
                        "html_instructions": "Take the <b>I-495 N</b> ramp",
                        "distance": {"text": "15 mi"},
                        "duration": {"text": "25 mins"},
                    },
                ],
            }],
        }],
    }
    client = _make_client(_mock_response(data))

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps(
            {"action": "directions", "origin": "Times Square", "destination": "JFK", "departure_time": "now"},
            API_KEY,
        )

    assert "Times Square, NY" in result
    assert "JFK Airport, NY" in result
    assert "20.5 mi" in result
    assert "35 mins" in result
    assert "50 mins" in result
    assert "I-495 N" in result
    assert "Head south on Broadway" in result
    assert "Steps" in result


@pytest.mark.asyncio
async def test_directions_no_routes():
    data = {"status": "ZERO_RESULTS", "routes": []}
    client = _make_client(_mock_response(data))

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps(
            {"action": "directions", "origin": "A", "destination": "B"},
            API_KEY,
        )

    assert "error" in result.lower() or "ZERO_RESULTS" in result


@pytest.mark.asyncio
async def test_directions_missing_params():
    client = _make_client()

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps({"action": "directions", "origin": "A"}, API_KEY)

    assert "required" in result.lower()


@pytest.mark.asyncio
async def test_nearby_success():
    geocode_data = {
        "status": "OK",
        "results": [{"geometry": {"location": {"lat": 40.785091, "lng": -73.968285}}}],
    }
    places_data = {
        "status": "OK",
        "results": [
            {
                "name": "Blue Bottle Coffee",
                "vicinity": "123 Park Ave",
                "rating": 4.5,
                "user_ratings_total": 200,
                "opening_hours": {"open_now": True},
            },
            {
                "name": "Starbucks",
                "vicinity": "456 5th Ave",
                "rating": 3.8,
                "user_ratings_total": 500,
            },
        ],
    }
    client = _make_client(_mock_response(geocode_data), _mock_response(places_data))

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps(
            {"action": "nearby", "query": "coffee shops", "location": "Central Park"},
            API_KEY,
        )

    assert "Blue Bottle Coffee" in result
    assert "123 Park Ave" in result
    assert "4.5/5" in result
    assert "Open now:** Yes" in result
    assert "Starbucks" in result


@pytest.mark.asyncio
async def test_nearby_no_results():
    geocode_data = {
        "status": "OK",
        "results": [{"geometry": {"location": {"lat": 0, "lng": 0}}}],
    }
    places_data = {"status": "ZERO_RESULTS", "results": []}
    client = _make_client(_mock_response(geocode_data), _mock_response(places_data))

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps(
            {"action": "nearby", "query": "xyz", "location": "Nowhere"},
            API_KEY,
        )

    assert "No places found" in result


@pytest.mark.asyncio
async def test_geocode_forward():
    data = {
        "status": "OK",
        "results": [{
            "formatted_address": "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
            "geometry": {"location": {"lat": 37.4224764, "lng": -122.0842499}},
            "types": ["street_address"],
        }],
    }
    client = _make_client(_mock_response(data))

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps(
            {"action": "geocode", "query": "1600 Amphitheatre Parkway"},
            API_KEY,
        )

    assert "1600 Amphitheatre Pkwy" in result
    assert "37.4224764" in result
    assert "-122.0842499" in result
    assert "street_address" in result


@pytest.mark.asyncio
async def test_geocode_reverse():
    data = {
        "status": "OK",
        "results": [{
            "formatted_address": "New York, NY 10007, USA",
            "geometry": {"location": {"lat": 40.7128, "lng": -74.006}},
            "types": ["locality"],
        }],
    }
    client = _make_client(_mock_response(data))

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps(
            {"action": "geocode", "query": "40.7128, -74.0060"},
            API_KEY,
        )

    assert "New York, NY" in result
    assert "40.7128" in result


@pytest.mark.asyncio
async def test_geocode_no_results():
    data = {"status": "ZERO_RESULTS", "results": []}
    client = _make_client(_mock_response(data))

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps(
            {"action": "geocode", "query": "xyzzyville nowhere"},
            API_KEY,
        )

    assert "No geocoding results" in result


@pytest.mark.asyncio
async def test_api_error():
    client = _make_client()
    client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps(
            {"action": "directions", "origin": "A", "destination": "B"},
            API_KEY,
        )

    assert "failed" in result.lower()


@pytest.mark.asyncio
async def test_no_api_key():
    result = await google_maps({"action": "directions"}, "")
    assert "not configured" in result.lower()


@pytest.mark.asyncio
async def test_unknown_action():
    client = _make_client()

    with patch("assistant.tools.google_maps_tool.make_httpx_client", return_value=client):
        result = await google_maps({"action": "invalid"}, API_KEY)

    assert "Unknown action" in result


@pytest.mark.asyncio
async def test_config_defaults():
    from assistant.core.config import Settings
    s = Settings()
    assert s.google_maps_enabled is False
    assert s.google_maps_api_key == ""
