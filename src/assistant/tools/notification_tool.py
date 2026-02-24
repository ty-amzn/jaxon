"""LLM tool for explicit notification sending (used in silent mode)."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.core.notifications import NotificationDispatcher

SEND_NOTIFICATION_DEF: dict[str, Any] = {
    "name": "send_notification",
    "description": (
        "Send a notification message to the user. Use this tool when running "
        "in silent mode to explicitly push a message only when there is something "
        "worth reporting. Do not call this if there is nothing noteworthy."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The notification message to send to the user.",
            },
            "urgent": {
                "type": "boolean",
                "description": "If true, bypass DND quiet hours.",
                "default": False,
            },
        },
        "required": ["message"],
    },
}


def _make_send_notification(dispatcher: NotificationDispatcher):
    """Factory: returns an async handler bound to the dispatcher."""

    async def send_notification(params: dict[str, Any]) -> str:
        message = params.get("message", "")
        urgent = params.get("urgent", False)
        if not message:
            return "Error: message is required."
        await dispatcher.send(message, urgent=urgent)
        return "Notification sent."

    return send_notification
