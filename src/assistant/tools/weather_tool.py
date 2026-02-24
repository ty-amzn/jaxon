"""Weather tool — current conditions and forecast via Open-Meteo API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather interpretation codes → descriptions
WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _weather_description(code: int) -> str:
    return WMO_CODES.get(code, f"Unknown ({code})")


async def get_weather(params: dict[str, Any]) -> str:
    """Fetch weather for a location using Open-Meteo.

    Args:
        params: Dictionary with 'location' (str), optional 'forecast_days' (int),
                and optional 'hourly' (bool).

    Returns:
        Formatted weather report as markdown.
    """
    location = params.get("location", "").strip()
    if not location:
        raise ValueError("No location provided")

    forecast_days = min(max(int(params.get("forecast_days", 3)), 1), 7)
    include_hourly = params.get("hourly", False)

    try:
        async with make_httpx_client(timeout=15.0) as client:
            # Step 1: Geocode
            geo_resp = await client.get(
                GEOCODE_URL,
                params={"name": location, "count": 1, "language": "en", "format": "json"},
            )
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()

            results = geo_data.get("results")
            if not results:
                return f"Could not find location: {location}"

            place = results[0]
            lat = place["latitude"]
            lon = place["longitude"]
            name = place.get("name", location)
            country = place.get("country", "")
            display_name = f"{name}, {country}" if country else name

            # Step 2: Fetch forecast
            forecast_params: dict[str, Any] = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forecast_days": forecast_days,
                "timezone": "auto",
            }
            if include_hourly:
                forecast_params["hourly"] = "temperature_2m,weather_code,precipitation,wind_speed_10m"

            weather_resp = await client.get(FORECAST_URL, params=forecast_params)
            weather_resp.raise_for_status()
            weather = weather_resp.json()

    except httpx.HTTPError as e:
        return f"Weather API error: {e}"

    # Format current conditions
    current = weather.get("current", {})
    lines = [
        f"# Weather for {display_name}",
        "",
        "## Current Conditions",
        f"- **Condition:** {_weather_description(current.get('weather_code', -1))}",
        f"- **Temperature:** {current.get('temperature_2m', '?')}°C",
        f"- **Humidity:** {current.get('relative_humidity_2m', '?')}%",
        f"- **Wind Speed:** {current.get('wind_speed_10m', '?')} km/h",
    ]

    # Format hourly forecast
    hourly = weather.get("hourly", {})
    hourly_times = hourly.get("time", [])
    if hourly_times:
        lines += ["", "## Hourly Forecast"]
        for i, time_str in enumerate(hourly_times):
            code = hourly.get("weather_code", [])[i] if i < len(hourly.get("weather_code", [])) else -1
            temp = hourly.get("temperature_2m", [])[i] if i < len(hourly.get("temperature_2m", [])) else "?"
            precip = hourly.get("precipitation", [])[i] if i < len(hourly.get("precipitation", [])) else 0
            wind = hourly.get("wind_speed_10m", [])[i] if i < len(hourly.get("wind_speed_10m", [])) else "?"
            desc = _weather_description(code)
            line = f"- **{time_str}:** {desc}, {temp}°C, wind {wind} km/h"
            if precip and precip > 0:
                line += f", {precip} mm"
            lines.append(line)

    # Format daily forecast
    daily = weather.get("daily", {})
    dates = daily.get("time", [])
    if dates:
        lines += ["", "## Daily Forecast"]
        for i, date in enumerate(dates):
            code = daily.get("weather_code", [])[i] if i < len(daily.get("weather_code", [])) else -1
            t_max = daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else "?"
            t_min = daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else "?"
            precip = daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else 0
            desc = _weather_description(code)
            line = f"- **{date}:** {desc}, {t_min}°C – {t_max}°C"
            if precip and precip > 0:
                line += f", {precip} mm precip"
            lines.append(line)

    return "\n".join(lines)


WEATHER_TOOL_DEF = {
    "name": "get_weather",
    "description": (
        "Get current weather conditions and forecast for a location. "
        "Uses the free Open-Meteo API. The location parameter must be a "
        "geographic place name (city, town, or region) — not a question or sentence."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": (
                    "Freeform location search text. Works best with short place names like "
                    "'London', 'Tokyo', 'New York', 'Paris, France', 'San Francisco, CA'. "
                    "Extract just the place name from the user's message — do not pass full "
                    "sentences like 'What is the weather in London'."
                ),
            },
            "forecast_days": {
                "type": "integer",
                "description": "Number of forecast days (1-7, default 3)",
                "default": 3,
            },
            "hourly": {
                "type": "boolean",
                "description": "Include hourly forecast breakdown (temperature, weather, precipitation, wind). Default false.",
                "default": False,
            },
        },
        "required": ["location"],
    },
}
