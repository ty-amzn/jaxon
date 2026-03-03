"""Weather tool — current conditions, forecast, and alerts via Open-Meteo + NWS APIs."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"

# US state abbreviations → full names for matching Open-Meteo's admin1 field
_US_STATES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def _parse_location(raw: str) -> tuple[str, str]:
    """Split 'City, State/Country' into (city_name, qualifier).

    Open-Meteo's geocoding API only searches by city name — qualifiers like
    'MA', 'Massachusetts', or 'France' must be matched against results.
    """
    # Try splitting on comma or slash
    parts = re.split(r"[,/]", raw, maxsplit=1)
    city = parts[0].strip()
    qualifier = parts[1].strip() if len(parts) > 1 else ""
    # Expand US state abbreviations
    if qualifier.upper() in _US_STATES:
        qualifier = _US_STATES[qualifier.upper()]
    return city, qualifier


def _pick_best_result(results: list[dict], qualifier: str) -> dict:
    """Pick the best geocoding result matching the qualifier string."""
    if not qualifier:
        return results[0]
    q = qualifier.lower()
    for r in results:
        admin1 = (r.get("admin1") or "").lower()
        country = (r.get("country") or "").lower()
        # Match against state/region or country
        if q == admin1 or q == country or q in admin1 or q in country:
            return r
    # No match — fall back to first result
    return results[0]

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


async def _fetch_nws_alerts(lat: float, lon: float) -> str:
    """Fetch active NWS weather alerts for a lat/lon point.

    US-only; returns empty string for non-US locations or on any error.
    """
    try:
        async with make_httpx_client(
            timeout=10.0,
            headers={
                "User-Agent": "(jaxon-assistant, contact@example.com)",
                "Accept": "application/geo+json",
            },
        ) as client:
            resp = await client.get(
                NWS_ALERTS_URL,
                params={"point": f"{lat:.4f},{lon:.4f}"},
            )
            resp.raise_for_status()
            data = resp.json()

            features = data.get("features", [])
            if not features:
                return ""

            lines = ["## Active Weather Alerts"]
            for f in features[:5]:
                props = f.get("properties", {})
                event = props.get("event", "Unknown Alert")
                severity = props.get("severity", "Unknown")
                headline = props.get("headline", "")
                description = props.get("description", "")
                expires = props.get("expires", "")

                lines.append(f"### {event} ({severity})")
                if headline:
                    lines.append(f"**{headline}**")
                if description:
                    desc = description[:500]
                    if len(description) > 500:
                        desc += "..."
                    lines.append(desc)
                if expires:
                    lines.append(f"*Expires: {expires}*")
                lines.append("")

            return "\n".join(lines)
    except Exception:
        return ""


async def get_weather(params: dict[str, Any]) -> str:
    """Fetch weather for a location using Open-Meteo, with optional NWS alerts.

    Args:
        params: Dictionary with 'location' (str), optional 'forecast_days' (int),
                optional 'hourly' (bool), and optional 'units' ("metric"|"imperial").

    Returns:
        Formatted weather report as markdown.
    """
    location = params.get("location", "").strip()
    if not location:
        raise ValueError("No location provided")

    forecast_days = min(max(int(params.get("forecast_days", 3)), 1), 7)
    include_hourly = params.get("hourly", False)
    units = params.get("units", "metric")
    imperial = units == "imperial"

    temp_unit = "\u00b0F" if imperial else "\u00b0C"
    wind_unit = "mph" if imperial else "km/h"
    precip_unit = "in" if imperial else "mm"

    city_name, qualifier = _parse_location(location)

    try:
        async with make_httpx_client(timeout=15.0) as client:
            # Step 1: Geocode (search by city name only; qualifier used to pick best match)
            geo_resp = await client.get(
                GEOCODE_URL,
                params={"name": city_name, "count": 10, "language": "en", "format": "json"},
            )
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()

            results = geo_data.get("results")
            if not results:
                return f"Could not find location: {location}"

            place = _pick_best_result(results, qualifier)
            lat = place["latitude"]
            lon = place["longitude"]
            name = place.get("name", location)
            admin1 = place.get("admin1", "")
            country = place.get("country", "")
            display_parts = [name] + [p for p in (admin1, country) if p]
            display_name = ", ".join(display_parts)

            # Step 2: Fetch forecast
            forecast_params: dict[str, Any] = {
                "latitude": lat,
                "longitude": lon,
                "current": (
                    "temperature_2m,apparent_temperature,"
                    "relative_humidity_2m,wind_speed_10m,weather_code"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "apparent_temperature_max,apparent_temperature_min,"
                    "precipitation_sum,snowfall_sum"
                ),
                "forecast_days": forecast_days,
                "timezone": "auto",
            }
            if imperial:
                forecast_params["temperature_unit"] = "fahrenheit"
                forecast_params["wind_speed_unit"] = "mph"
                forecast_params["precipitation_unit"] = "inch"
            if include_hourly:
                forecast_params["hourly"] = (
                    "temperature_2m,apparent_temperature,weather_code,"
                    "precipitation,wind_speed_10m,snowfall,snow_depth"
                )

            weather_resp = await client.get(FORECAST_URL, params=forecast_params)
            weather_resp.raise_for_status()
            weather = weather_resp.json()

    except httpx.HTTPError as e:
        return f"Weather API error: {e}"

    # Fetch NWS alerts (separate call; fails silently for non-US locations)
    alerts_section = await _fetch_nws_alerts(lat, lon)

    # Format current conditions
    current = weather.get("current", {})
    lines = [
        f"# Weather for {display_name}",
        "",
        "## Current Conditions",
        f"- **Condition:** {_weather_description(current.get('weather_code', -1))}",
        f"- **Temperature:** {current.get('temperature_2m', '?')}{temp_unit}",
        f"- **Feels Like:** {current.get('apparent_temperature', '?')}{temp_unit}",
        f"- **Humidity:** {current.get('relative_humidity_2m', '?')}%",
        f"- **Wind Speed:** {current.get('wind_speed_10m', '?')} {wind_unit}",
    ]

    # Alerts section (before forecasts for visibility)
    if alerts_section:
        lines += ["", alerts_section]

    # Format hourly forecast
    hourly = weather.get("hourly", {})
    hourly_times = hourly.get("time", [])
    if hourly_times:
        lines += ["", "## Hourly Forecast"]
        for i, time_str in enumerate(hourly_times):
            code = hourly.get("weather_code", [])[i] if i < len(hourly.get("weather_code", [])) else -1
            temp = hourly.get("temperature_2m", [])[i] if i < len(hourly.get("temperature_2m", [])) else "?"
            feels = hourly.get("apparent_temperature", [])[i] if i < len(hourly.get("apparent_temperature", [])) else None
            precip = hourly.get("precipitation", [])[i] if i < len(hourly.get("precipitation", [])) else 0
            wind = hourly.get("wind_speed_10m", [])[i] if i < len(hourly.get("wind_speed_10m", [])) else "?"
            snow = hourly.get("snowfall", [])[i] if i < len(hourly.get("snowfall", [])) else 0
            snow_depth = hourly.get("snow_depth", [])[i] if i < len(hourly.get("snow_depth", [])) else 0
            desc = _weather_description(code)
            line = f"- **{time_str}:** {desc}, {temp}{temp_unit}"
            if feels is not None:
                line += f" (feels {feels}{temp_unit})"
            line += f", wind {wind} {wind_unit}"
            if precip and precip > 0:
                line += f", {precip} {precip_unit}"
            if snow and snow > 0:
                line += f", snow {snow} cm"
            if snow_depth and snow_depth > 0:
                line += f", snow depth {snow_depth} cm"
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
            fl_max = daily.get("apparent_temperature_max", [])[i] if i < len(daily.get("apparent_temperature_max", [])) else None
            fl_min = daily.get("apparent_temperature_min", [])[i] if i < len(daily.get("apparent_temperature_min", [])) else None
            precip = daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else 0
            snow = daily.get("snowfall_sum", [])[i] if i < len(daily.get("snowfall_sum", [])) else 0
            desc = _weather_description(code)
            line = f"- **{date}:** {desc}, {t_min}{temp_unit} \u2013 {t_max}{temp_unit}"
            if fl_min is not None and fl_max is not None:
                line += f" (feels {fl_min} \u2013 {fl_max}{temp_unit})"
            if precip and precip > 0:
                line += f", {precip} {precip_unit} precip"
            if snow and snow > 0:
                line += f", {snow} cm snow"
            lines.append(line)

    return "\n".join(lines)


WEATHER_TOOL_DEF = {
    "name": "get_weather",
    "description": (
        "Get current weather conditions, feels-like temperature, snow data, "
        "and forecast for a location. Includes active NWS severe weather alerts "
        "for US locations. Uses the free Open-Meteo API. The location parameter "
        "must be a geographic place name (city, town, or region) — not a question "
        "or sentence."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": (
                    "City or place name, optionally followed by state/country qualifier. "
                    "Examples: 'London', 'Tokyo', 'New York', 'Newton, MA', 'Paris, France'. "
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
                "description": "Include hourly forecast breakdown (temperature, feels-like, weather, precipitation, wind, snowfall). Default false.",
                "default": False,
            },
            "units": {
                "type": "string",
                "enum": ["metric", "imperial"],
                "description": "Unit system: 'metric' (default, °C/km/h/mm) or 'imperial' (°F/mph/in).",
                "default": "metric",
            },
        },
        "required": ["location"],
    },
}
