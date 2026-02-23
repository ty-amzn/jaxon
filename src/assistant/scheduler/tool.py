"""LLM tool definition for schedule_reminder."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.scheduler.manager import SchedulerManager

SCHEDULE_REMINDER_DEF: dict[str, Any] = {
    "name": "schedule_reminder",
    "description": (
        "Manage reminders and scheduled notifications.\n"
        "Actions:\n"
        "- 'create': schedule a new reminder. Requires description, trigger_type, trigger_args, message.\n"
        "- 'cancel': remove a reminder by job_id. Use 'list' first to find the ID.\n"
        "- 'list': show all active reminders with their IDs and schedules.\n\n"
        "Trigger types:\n"
        "- 'date': one-time reminder at a specific time. Use for 'remind me in 10 minutes' — "
        "compute the absolute UTC datetime from the current time and pass as run_date.\n"
        "- 'cron': recurring on a schedule (e.g. every weekday at 9am).\n"
        "- 'interval': repeating at a fixed interval (e.g. every 30 minutes).\n\n"
        "All times must be in UTC."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "cancel", "list"],
                "description": "Action to perform",
            },
            "description": {
                "type": "string",
                "description": "Human-readable description of the reminder (required for create)",
            },
            "trigger_type": {
                "type": "string",
                "enum": ["date", "cron", "interval"],
                "description": "Type of trigger (required for create)",
            },
            "trigger_args": {
                "type": "object",
                "description": (
                    "Trigger arguments (required for create). "
                    "For 'date': {\"run_date\": \"2025-01-15T14:30:00\"} (UTC ISO datetime). "
                    "For 'cron': {\"hour\": 9, \"minute\": 0, \"day_of_week\": \"mon-fri\"}. "
                    "For 'interval': {\"minutes\": 30} (supports seconds, minutes, hours)."
                ),
            },
            "message": {
                "type": "string",
                "description": "The notification message to deliver (required for create)",
            },
            "job_id": {
                "type": "string",
                "description": "Job ID to cancel (required for cancel, use 'list' to find IDs)",
            },
        },
        "required": ["action"],
    },
}


def create_schedule_reminder_handler(scheduler: SchedulerManager):
    """Factory: returns an async handler bound to the scheduler."""

    async def schedule_reminder(params: dict[str, Any]) -> str:
        action = params.get("action", "create")

        if action == "list":
            jobs = scheduler.list_jobs()
            if not jobs:
                return "No scheduled reminders."
            lines = []
            for j in jobs:
                lines.append(f"- **{j['id']}**: {j['description']} ({j['trigger']})")
            return "Scheduled reminders:\n" + "\n".join(lines)

        if action == "cancel":
            job_id = params.get("job_id", "")
            if not job_id:
                return "Error: job_id is required for cancel."
            removed = scheduler.remove_job(job_id)
            if removed:
                return f"Reminder {job_id} cancelled."
            return f"Reminder {job_id} not found."

        # Default: create
        for field in ("description", "trigger_type", "trigger_args", "message"):
            if field not in params:
                return f"Error: {field} is required for create."
        job_id = scheduler.add_reminder(
            description=params["description"],
            trigger_type=params["trigger_type"],
            trigger_args=params["trigger_args"],
            message=params.get("message"),
        )
        return f"Reminder scheduled with ID: {job_id}"

    return schedule_reminder
