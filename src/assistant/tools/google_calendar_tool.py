"""Google Calendar tool — separate tool registered only when google_calendar_enabled=true."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

GOOGLE_CALENDAR_TOOL_DEF: dict[str, Any] = {
    "name": "google_calendar",
    "description": (
        "Read and manage the user's Google Calendar. Actions:\n"
        "- create: add an event (title, start required; end, location, notes optional)\n"
        "- list: list events in a date range (defaults to next 7 days)\n"
        "- today: shortcut to list today's events\n"
        "- update: modify an event by id\n"
        "- delete: remove an event by id\n\n"
        "All datetimes should be ISO 8601 (e.g. 2025-03-15T14:00:00)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "today", "update", "delete"],
                "description": "The Google Calendar action to perform.",
            },
            "title": {
                "type": "string",
                "description": "Event title (for create/update).",
            },
            "start": {
                "type": "string",
                "description": "Start datetime in ISO 8601 (for create/update/list).",
            },
            "end": {
                "type": "string",
                "description": "End datetime in ISO 8601 (for create/update/list).",
            },
            "location": {
                "type": "string",
                "description": "Event location (for create/update).",
            },
            "notes": {
                "type": "string",
                "description": "Event notes (for create/update).",
            },
            "event_id": {
                "type": "string",
                "description": "Event ID (for update/delete).",
            },
        },
        "required": ["action"],
    },
}


# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_gcal_client: Any = None


def _get_google_client() -> Any:
    """Lazily create GoogleCalendarClient."""
    global _gcal_client
    if _gcal_client is None:
        from assistant.core.config import get_settings
        from assistant.tools.google_calendar import GoogleCalendarClient

        settings = get_settings()
        _gcal_client = GoogleCalendarClient(
            credentials_path=settings.google_auth_dir / "credentials.json",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
    return _gcal_client


def set_google_client(client: Any) -> None:
    """Override the Google client (for tests)."""
    global _gcal_client
    _gcal_client = client


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------

async def google_calendar_tool(params: dict[str, Any]) -> str:
    """Handle Google Calendar tool calls."""
    import json

    from assistant.tools.google_calendar import format_event

    client = _get_google_client()
    action = params.get("action", "list")

    if action == "create":
        title = params.get("title")
        start = params.get("start")
        if not title or not start:
            return "Error: 'title' and 'start' are required for create."
        event = await client.create_event(
            summary=title,
            start=start,
            end=params.get("end"),
            location=params.get("location"),
            description=params.get("notes"),
        )
        formatted = format_event(event)
        return f"Event created: {formatted['title']} at {formatted['start']} (id: {formatted['id']})"

    elif action == "today":
        today = datetime.now().strftime("%Y-%m-%dT00:00:00")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        events = await client.list_all_events(today, tomorrow)
        if not events:
            return "No events today."
        return json.dumps([format_event(e) for e in events], indent=2)

    elif action == "list":
        start = params.get("start", datetime.now().strftime("%Y-%m-%dT00:00:00"))
        end = params.get(
            "end",
            (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59"),
        )
        events = await client.list_all_events(start, end)
        if not events:
            return f"No events between {start} and {end}."
        return json.dumps([format_event(e) for e in events], indent=2)

    elif action == "update":
        event_id = params.get("event_id")
        if not event_id:
            return "Error: 'event_id' is required for update."
        result = await client.update_event(
            event_id,
            summary=params.get("title"),
            start=params.get("start"),
            end=params.get("end"),
            location=params.get("location"),
            description=params.get("notes"),
        )
        formatted = format_event(result)
        return f"Event updated: {formatted['title']}"

    elif action == "delete":
        event_id = params.get("event_id")
        if not event_id:
            return "Error: 'event_id' is required for delete."
        if await client.delete_event(event_id):
            return f"Event {event_id} deleted."
        return "Error: failed to delete event."

    else:
        return f"Unknown google_calendar action: {action}"
