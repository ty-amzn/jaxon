"""Reminders tool — VTODO management via CalDAV (syncs to iOS Reminders)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

REMINDERS_TOOL_DEF: dict[str, Any] = {
    "name": "reminders",
    "description": (
        "Manage the user's reminders (synced to iOS Reminders via CalDAV VTODO). Actions:\n"
        "- create: add a reminder (title required; due, priority, notes optional)\n"
        "- list: list pending reminders (set include_completed=true to include done items)\n"
        "- complete: mark a reminder as done by reminder_id\n"
        "- update: modify a reminder by reminder_id (title, due, priority, notes)\n"
        "- delete: remove a reminder by reminder_id\n\n"
        "Priority levels: high, medium, low.\n"
        "Due dates should be ISO 8601 (e.g. 2025-03-15T18:00:00)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "complete", "update", "delete"],
                "description": "The reminders action to perform.",
            },
            "title": {
                "type": "string",
                "description": "Reminder title (for create/update).",
            },
            "due": {
                "type": "string",
                "description": "Due datetime in ISO 8601 (for create/update).",
            },
            "priority": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Priority level (for create/update).",
            },
            "notes": {
                "type": "string",
                "description": "Reminder notes (for create/update).",
            },
            "reminder_id": {
                "type": "string",
                "description": "Reminder ID (for complete/update/delete).",
            },
            "include_completed": {
                "type": "boolean",
                "description": "Include completed reminders in list (default false).",
            },
        },
        "required": ["action"],
    },
}


# ---------------------------------------------------------------------------
# Singleton CalDAV client (reuses calendar_tool's pattern)
# ---------------------------------------------------------------------------

_caldav_client: Any = None


def _get_caldav_client() -> Any:
    """Lazily create CalDAVClient for reminders."""
    global _caldav_client
    if _caldav_client is None:
        from assistant.core.config import get_settings
        from assistant.tools.caldav_client import CalDAVClient

        settings = get_settings()
        _caldav_client = CalDAVClient(
            url=settings.caldav_url,
            username=settings.caldav_username,
            password=settings.caldav_password,
        )
    return _caldav_client


def set_reminders_client(client: Any) -> None:
    """Override the CalDAV client (for tests)."""
    global _caldav_client
    _caldav_client = client


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------

async def reminders_tool(params: dict[str, Any]) -> str:
    """Handle reminders tool calls via CalDAV VTODO."""
    import json

    client = _get_caldav_client()
    action = params.get("action", "list")

    if action == "create":
        title = params.get("title")
        if not title:
            return "Error: 'title' is required for create."
        todo = client.create_todo(
            title=title,
            due=params.get("due"),
            priority=params.get("priority"),
            notes=params.get("notes"),
        )
        due_str = f" due {todo['due']}" if todo["due"] else ""
        return f"Reminder created: {todo['title']}{due_str} (id: {todo['id']})"

    elif action == "list":
        include_completed = params.get("include_completed", False)
        todos = client.list_todos(include_completed=include_completed)
        if not todos:
            label = "reminders" if include_completed else "pending reminders"
            return f"No {label}."
        return json.dumps(todos, indent=2)

    elif action == "complete":
        reminder_id = params.get("reminder_id")
        if not reminder_id:
            return "Error: 'reminder_id' is required for complete."
        result = client.complete_todo(reminder_id)
        if result is None:
            return "Error: reminder not found."
        return f"Reminder completed: {result['title']}"

    elif action == "update":
        reminder_id = params.get("reminder_id")
        if not reminder_id:
            return "Error: 'reminder_id' is required for update."
        result = client.update_todo(
            reminder_id,
            title=params.get("title"),
            due=params.get("due"),
            priority=params.get("priority"),
            notes=params.get("notes"),
        )
        if result is None:
            return "Error: reminder not found."
        return f"Reminder updated: {result['title']}"

    elif action == "delete":
        reminder_id = params.get("reminder_id")
        if not reminder_id:
            return "Error: 'reminder_id' is required for delete."
        if client.delete_todo(reminder_id):
            return f"Reminder {reminder_id} deleted."
        return "Error: reminder not found."

    else:
        return f"Unknown reminders action: {action}"
