"""Google Maps tool — directions, nearby places, and geocoding."""

from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any

import httpx

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

BASE_URL = "https://maps.googleapis.com/maps/api"


async def _geocode_location(
    client: httpx.AsyncClient, api_key: str, location: str
) -> tuple[float, float]:
    """Convert a place name or address to lat,lng coordinates."""
    resp = await client.get(
        f"{BASE_URL}/geocode/json",
        params={"address": location, "key": api_key},
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        raise ValueError(f"Could not geocode location: {location}")
    loc = results[0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    return unescape(re.sub(r"<[^>]+>", "", text))


async def _directions(
    client: httpx.AsyncClient,
    api_key: str,
    origin: str,
    destination: str,
    mode: str,
    departure_time: str | None,
) -> str:
    """Get directions between two locations."""
    params: dict[str, str] = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": api_key,
    }
    if departure_time:
        params["departure_time"] = departure_time

    resp = await client.get(f"{BASE_URL}/directions/json", params=params)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        return f"Directions error: {data.get('status', 'UNKNOWN')} — {data.get('error_message', 'no details')}"

    routes = data.get("routes", [])
    if not routes:
        return "No routes found."

    route = routes[0]
    leg = route["legs"][0]

    parts = [
        f"# Directions: {leg['start_address']} → {leg['end_address']}\n",
        f"**Mode:** {mode}",
        f"**Distance:** {leg['distance']['text']}",
        f"**Duration:** {leg['duration']['text']}",
    ]

    # Traffic-aware duration (driving only)
    if "duration_in_traffic" in leg:
        parts.append(f"**Duration in traffic:** {leg['duration_in_traffic']['text']}")

    summary = route.get("summary", "")
    if summary:
        parts.append(f"**Via:** {summary}")

    # Step-by-step directions
    steps = leg.get("steps", [])
    if steps:
        parts.append("\n## Steps\n")
        for i, step in enumerate(steps, 1):
            instruction = _strip_html(step.get("html_instructions", ""))
            dist = step.get("distance", {}).get("text", "")
            dur = step.get("duration", {}).get("text", "")
            parts.append(f"{i}. {instruction} — {dist} ({dur})")

    return "\n".join(parts)


async def _nearby_search(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
    location: str,
    radius: int,
) -> str:
    """Find nearby places matching a query."""
    lat, lng = await _geocode_location(client, api_key, location)

    resp = await client.get(
        f"{BASE_URL}/place/nearbysearch/json",
        params={
            "location": f"{lat},{lng}",
            "radius": str(radius),
            "keyword": query,
            "key": api_key,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        return f"Places error: {data.get('status', 'UNKNOWN')} — {data.get('error_message', 'no details')}"

    results = data.get("results", [])
    if not results:
        return f"No places found for \"{query}\" near {location}."

    parts = [f"# Nearby: \"{query}\" near {location}\n"]
    for i, place in enumerate(results[:10], 1):
        name = place.get("name", "Unknown")
        address = place.get("vicinity", "No address")
        rating = place.get("rating")
        total_ratings = place.get("user_ratings_total", 0)
        open_now = place.get("opening_hours", {}).get("open_now")

        line = f"## {i}. {name}"
        parts.append(line)
        parts.append(f"**Address:** {address}")
        if rating is not None:
            parts.append(f"**Rating:** {rating}/5 ({total_ratings} reviews)")
        if open_now is not None:
            parts.append(f"**Open now:** {'Yes' if open_now else 'No'}")
        parts.append("")

    return "\n".join(parts)


async def _geocode(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
) -> str:
    """Geocode an address to lat/lng, or reverse-geocode lat,lng to address."""
    # Auto-detect reverse geocoding: query looks like "lat,lng"
    is_reverse = bool(re.match(r"^-?\d+\.?\d*\s*,\s*-?\d+\.?\d*$", query.strip()))

    if is_reverse:
        params = {"latlng": query.strip(), "key": api_key}
    else:
        params = {"address": query.strip(), "key": api_key}

    resp = await client.get(f"{BASE_URL}/geocode/json", params=params)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        return f"Geocoding error: {data.get('status', 'UNKNOWN')} — {data.get('error_message', 'no details')}"

    results = data.get("results", [])
    if not results:
        return f"No geocoding results for: {query}"

    parts = [f"# Geocode: {query}\n"]
    for i, result in enumerate(results[:5], 1):
        address = result.get("formatted_address", "Unknown")
        loc = result["geometry"]["location"]
        parts.append(f"## {i}. {address}")
        parts.append(f"**Coordinates:** {loc['lat']}, {loc['lng']}")
        types = result.get("types", [])
        if types:
            parts.append(f"**Type:** {', '.join(types)}")
        parts.append("")

    return "\n".join(parts)


async def google_maps(params: dict[str, Any], api_key: str) -> str:
    """Google Maps tool: directions, nearby places, and geocoding.

    Args:
        params: Dictionary with 'action', and action-specific fields.
        api_key: Google Maps API key.

    Returns:
        Formatted results as markdown.
    """
    action = params.get("action", "directions")

    if not api_key:
        return "Google Maps API key is not configured."

    try:
        async with make_httpx_client(timeout=15.0) as client:
            if action == "directions":
                origin = params.get("origin", "")
                destination = params.get("destination", "")
                if not origin or not destination:
                    return "Both 'origin' and 'destination' are required for directions."
                mode = params.get("mode", "driving")
                departure_time = params.get("departure_time")
                return await _directions(client, api_key, origin, destination, mode, departure_time)

            elif action == "nearby":
                query = params.get("query", "")
                location = params.get("location", "")
                if not query or not location:
                    return "Both 'query' and 'location' are required for nearby search."
                radius = params.get("radius", 5000)
                return await _nearby_search(client, api_key, query, location, radius)

            elif action == "geocode":
                query = params.get("query", "")
                if not query:
                    return "A 'query' is required for geocoding."
                return await _geocode(client, api_key, query)

            else:
                return f"Unknown action: {action}. Use 'directions', 'nearby', or 'geocode'."

    except httpx.HTTPError as e:
        return f"Google Maps request failed: {e}"
    except ValueError as e:
        return str(e)


GOOGLE_MAPS_TOOL_DEF = {
    "name": "google_maps",
    "description": (
        "Get driving/walking/transit/bicycling directions with real-time traffic, "
        "find nearby places (restaurants, gas stations, etc.), or geocode addresses. "
        "Use action 'directions' for routes, 'nearby' to find places, or 'geocode' for address lookup."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["directions", "nearby", "geocode"],
                "description": "Action to perform: directions, nearby, or geocode",
                "default": "directions",
            },
            "origin": {
                "type": "string",
                "description": "Starting point for directions (address or place name)",
            },
            "destination": {
                "type": "string",
                "description": "Ending point for directions (address or place name)",
            },
            "mode": {
                "type": "string",
                "enum": ["driving", "walking", "transit", "bicycling"],
                "description": "Travel mode for directions (default: driving)",
                "default": "driving",
            },
            "departure_time": {
                "type": "string",
                "description": "Departure time for traffic info — use 'now' for current traffic (driving only)",
            },
            "query": {
                "type": "string",
                "description": "Search query for nearby places (e.g. 'gas stations'), or address/coordinates for geocode",
            },
            "location": {
                "type": "string",
                "description": "Center location for nearby search (place name or address)",
            },
            "radius": {
                "type": "integer",
                "description": "Search radius in meters for nearby (default: 5000)",
                "default": 5000,
            },
        },
        "required": ["action"],
    },
}
