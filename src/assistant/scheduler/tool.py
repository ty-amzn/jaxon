"""LLM tool definition for schedule_reminder."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.scheduler.manager import SchedulerManager

SCHEDULE_REMINDER_DEF: dict[str, Any] = {
    "name": "schedule_reminder",
    "description": (
        "Schedule a reminder or recurring notification. "
        "Use trigger_type 'date' for one-time reminders (provide run_date in ISO format), "
        "'cron' for recurring (provide cron fields like hour, minute, day_of_week), "
        "or 'interval' for periodic (provide seconds, minutes, or hours)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Human-readable description of the reminder",
            },
            "trigger_type": {
                "type": "string",
                "enum": ["date", "cron", "interval"],
                "description": "Type of trigger",
            },
            "trigger_args": {
                "type": "object",
                "description": (
                    "Trigger arguments. For 'date': {run_date: ISO datetime}. "
                    "For 'cron': {hour, minute, day_of_week, etc}. "
                    "For 'interval': {seconds, minutes, or hours}."
                ),
            },
            "message": {
                "type": "string",
                "description": "The reminder message to send",
            },
        },
        "required": ["description", "trigger_type", "trigger_args", "message"],
    },
}


def create_schedule_reminder_handler(scheduler: SchedulerManager):
    """Factory: returns an async handler bound to the scheduler."""

    async def schedule_reminder(params: dict[str, Any]) -> str:
        job_id = scheduler.add_reminder(
            description=params["description"],
            trigger_type=params["trigger_type"],
            trigger_args=params["trigger_args"],
            message=params.get("message"),
        )
        return f"Reminder scheduled with ID: {job_id}"

    return schedule_reminder
