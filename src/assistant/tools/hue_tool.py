"""Philips Hue smart lighting tool — local CLIP API v2."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

# Common color names → CIE xy coordinates
NAMED_COLORS: dict[str, tuple[float, float]] = {
    "red": (0.6750, 0.3220),
    "green": (0.4091, 0.5180),
    "blue": (0.1670, 0.0400),
    "yellow": (0.4432, 0.5154),
    "orange": (0.5562, 0.4084),
    "purple": (0.2703, 0.1398),
    "pink": (0.3944, 0.1990),
    "cyan": (0.1500, 0.3000),
    "warm white": (0.4596, 0.4105),
    "cool white": (0.3227, 0.3290),
    "white": (0.3127, 0.3290),
}

# Named color temperature presets → mirek values
COLOR_TEMP_PRESETS: dict[str, int] = {
    "warm": 400,      # ~2500K
    "neutral": 300,   # ~3333K
    "cool": 200,      # ~5000K
}


def _hue_client(bridge_ip: str, api_key: str) -> httpx.AsyncClient:
    """Create an httpx client configured for a Hue Bridge."""
    return make_httpx_client(
        verify=False,
        headers={"hue-application-key": api_key},
        base_url=f"https://{bridge_ip}",
        timeout=10.0,
    )


def _light_summary(light: dict[str, Any]) -> str:
    """Format a single light resource into a readable line."""
    meta = light.get("metadata", {})
    name = meta.get("name", "Unknown")
    rid = light.get("id", "?")
    on = light.get("on", {}).get("on", False)
    dimming = light.get("dimming", {})
    brightness = dimming.get("brightness")

    state = "on" if on else "off"
    parts = [f"- **{name}** (`{rid}`) — {state}"]
    if brightness is not None and on:
        parts.append(f", {brightness:.0f}%")
    return "".join(parts)


def _room_summary(room: dict[str, Any], grouped_lights: dict[str, dict]) -> str:
    """Format a room with its grouped_light state."""
    meta = room.get("metadata", {})
    name = meta.get("name", "Unknown")
    rid = room.get("id", "?")

    # Find the grouped_light service for this room
    gl_id = None
    for svc in room.get("services", []):
        if svc.get("rtype") == "grouped_light":
            gl_id = svc.get("rid")
            break

    parts = [f"- **{name}** (room `{rid}`)"]
    if gl_id:
        gl = grouped_lights.get(gl_id, {})
        on = gl.get("on", {}).get("on", False)
        brightness = gl.get("dimming", {}).get("brightness")
        state = "on" if on else "off"
        parts.append(f"\n  - Grouped light `{gl_id}` — {state}")
        if brightness is not None and on:
            parts.append(f", {brightness:.0f}%")
    return "".join(parts)


def _scene_summary(scene: dict[str, Any]) -> str:
    """Format a scene resource."""
    meta = scene.get("metadata", {})
    name = meta.get("name", "Unknown")
    rid = scene.get("id", "?")
    group = scene.get("group", {})
    group_rid = group.get("rid", "?")
    return f"- **{name}** (`{rid}`) — group `{group_rid}`"


def _build_control_body(params: dict[str, Any]) -> dict[str, Any]:
    """Build the PUT body for light/grouped_light control."""
    body: dict[str, Any] = {}

    if "on" in params:
        body["on"] = {"on": bool(params["on"])}

    if "brightness" in params:
        body["dimming"] = {"brightness": float(params["brightness"])}

    if "color_temp" in params:
        ct = params["color_temp"]
        if isinstance(ct, str) and ct in COLOR_TEMP_PRESETS:
            body["color_temperature"] = {"mirek": COLOR_TEMP_PRESETS[ct]}
        else:
            body["color_temperature"] = {"mirek": int(ct)}

    if "color" in params:
        color = params["color"]
        if isinstance(color, str) and color.startswith("xy:"):
            # Raw xy format: "xy:0.3,0.4"
            parts = color[3:].split(",")
            x, y = float(parts[0]), float(parts[1])
            body["color"] = {"xy": {"x": x, "y": y}}
        elif isinstance(color, str) and color.lower() in NAMED_COLORS:
            x, y = NAMED_COLORS[color.lower()]
            body["color"] = {"xy": {"x": x, "y": y}}
        else:
            return {"error": f"Unknown color: {color}. Use a named color ({', '.join(NAMED_COLORS)}) or 'xy:X,Y'."}

    if "transition" in params:
        # Hue API expects transition time in multiples of 100ms
        body["dynamics"] = {"duration": int(params["transition"])}

    return body


async def _list_lights(client: httpx.AsyncClient) -> str:
    resp = await client.get("/clip/v2/resource/light")
    resp.raise_for_status()
    lights = resp.json().get("data", [])
    if not lights:
        return "No lights found on this Hue Bridge."
    parts = ["# Hue Lights\n"]
    for light in lights:
        parts.append(_light_summary(light))
    return "\n".join(parts)


async def _list_rooms(client: httpx.AsyncClient) -> str:
    # Fetch rooms and grouped_lights in parallel-ish (sequential for simplicity)
    resp_rooms = await client.get("/clip/v2/resource/room")
    resp_rooms.raise_for_status()
    rooms = resp_rooms.json().get("data", [])

    resp_gl = await client.get("/clip/v2/resource/grouped_light")
    resp_gl.raise_for_status()
    grouped_lights = {gl["id"]: gl for gl in resp_gl.json().get("data", [])}

    if not rooms:
        return "No rooms found on this Hue Bridge."
    parts = ["# Hue Rooms\n"]
    for room in rooms:
        parts.append(_room_summary(room, grouped_lights))
    return "\n".join(parts)


async def _list_scenes(client: httpx.AsyncClient) -> str:
    resp = await client.get("/clip/v2/resource/scene")
    resp.raise_for_status()
    scenes = resp.json().get("data", [])
    if not scenes:
        return "No scenes found on this Hue Bridge."

    # Group scenes by their group
    by_group: dict[str, list[dict]] = {}
    for scene in scenes:
        group_rid = scene.get("group", {}).get("rid", "ungrouped")
        by_group.setdefault(group_rid, []).append(scene)

    parts = ["# Hue Scenes\n"]
    for group_rid, group_scenes in by_group.items():
        parts.append(f"## Group `{group_rid}`\n")
        for scene in group_scenes:
            parts.append(_scene_summary(scene))
        parts.append("")
    return "\n".join(parts)


async def _control_light(client: httpx.AsyncClient, params: dict[str, Any]) -> str:
    light_id = params.get("id", "")
    if not light_id:
        return "A light 'id' is required for control_light."
    body = _build_control_body(params)
    if "error" in body:
        return body["error"]
    if not body:
        return "No control parameters provided. Use 'on', 'brightness', 'color_temp', or 'color'."

    resp = await client.put(f"/clip/v2/resource/light/{light_id}", json=body)
    resp.raise_for_status()
    data = resp.json()
    errors = data.get("errors", [])
    if errors:
        return f"Hue error: {errors[0].get('description', errors)}"
    changes = ", ".join(body.keys())
    return f"Light `{light_id}` updated: {changes}"


async def _control_room(client: httpx.AsyncClient, params: dict[str, Any]) -> str:
    gl_id = params.get("id", "")
    if not gl_id:
        return "A grouped_light 'id' is required for control_room."
    body = _build_control_body(params)
    if "error" in body:
        return body["error"]
    if not body:
        return "No control parameters provided. Use 'on', 'brightness', 'color_temp', or 'color'."

    resp = await client.put(f"/clip/v2/resource/grouped_light/{gl_id}", json=body)
    resp.raise_for_status()
    data = resp.json()
    errors = data.get("errors", [])
    if errors:
        return f"Hue error: {errors[0].get('description', errors)}"
    changes = ", ".join(body.keys())
    return f"Room (grouped_light `{gl_id}`) updated: {changes}"


async def _activate_scene(client: httpx.AsyncClient, params: dict[str, Any]) -> str:
    scene_id = params.get("id", "")
    if not scene_id:
        return "A scene 'id' is required for activate_scene."
    body = {"recall": {"action": "active"}}
    if "transition" in params:
        body["recall"]["duration"] = int(params["transition"])

    resp = await client.put(f"/clip/v2/resource/scene/{scene_id}", json=body)
    resp.raise_for_status()
    data = resp.json()
    errors = data.get("errors", [])
    if errors:
        return f"Hue error: {errors[0].get('description', errors)}"
    return f"Scene `{scene_id}` activated."


async def hue(params: dict[str, Any], bridge_ip: str, api_key: str) -> str:
    """Philips Hue tool: control smart lights via local CLIP API v2.

    Args:
        params: Dictionary with 'action' and action-specific fields.
        bridge_ip: IP address of the Hue Bridge.
        api_key: Hue API key (hue-application-key).

    Returns:
        Formatted results as markdown.
    """
    action = params.get("action", "list_lights")

    if not bridge_ip or not api_key:
        return "Hue Bridge IP and API key are not configured."

    try:
        async with _hue_client(bridge_ip, api_key) as client:
            if action == "list_lights":
                return await _list_lights(client)
            elif action == "list_rooms":
                return await _list_rooms(client)
            elif action == "list_scenes":
                return await _list_scenes(client)
            elif action == "control_light":
                return await _control_light(client, params)
            elif action == "control_room":
                return await _control_room(client, params)
            elif action == "activate_scene":
                return await _activate_scene(client, params)
            else:
                return f"Unknown action: {action}. Use 'list_lights', 'list_rooms', 'list_scenes', 'control_light', 'control_room', or 'activate_scene'."

    except httpx.HTTPError as e:
        return f"Hue Bridge request failed: {e}"


HUE_TOOL_DEF = {
    "name": "hue",
    "description": (
        "Control Philips Hue smart lights on the local network. "
        "Use 'list_lights' to see all lights and their states, "
        "'list_rooms' for rooms with grouped light IDs, "
        "'list_scenes' for available scenes. "
        "Use 'control_light' or 'control_room' to turn on/off, set brightness, "
        "color temperature (warm/cool/neutral or mirek 153-500), "
        "or color (named colors like red, blue, warm white, or raw xy coordinates). "
        "Use 'activate_scene' to activate a Hue scene."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list_lights",
                    "list_rooms",
                    "list_scenes",
                    "control_light",
                    "control_room",
                    "activate_scene",
                ],
                "description": "Action to perform",
                "default": "list_lights",
            },
            "id": {
                "type": "string",
                "description": "Resource ID — light ID for control_light, grouped_light ID for control_room, scene ID for activate_scene",
            },
            "on": {
                "type": "boolean",
                "description": "Turn light on (true) or off (false)",
            },
            "brightness": {
                "type": "number",
                "description": "Brightness level 0-100",
            },
            "color_temp": {
                "type": "string",
                "description": "Color temperature: 'warm', 'cool', 'neutral', or mirek value (153-500)",
            },
            "color": {
                "type": "string",
                "description": "Color: named color (red, blue, green, warm white, etc.) or 'xy:X,Y' for raw CIE coordinates",
            },
            "transition": {
                "type": "integer",
                "description": "Transition duration in milliseconds",
            },
        },
        "required": ["action"],
    },
}
