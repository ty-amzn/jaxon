"""LLM tool definition for schedule_reminder."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.scheduler.manager import SchedulerManager

SCHEDULE_REMINDER_DEF: dict[str, Any] = {
    "name": "schedule_reminder",
    "description": (
        "Manage reminders and scheduled tasks.\n"
        "Actions:\n"
        "- 'create': schedule a new reminder or task. Requires description, trigger_type, trigger_args, message.\n"
        "- 'cancel': remove a reminder/task by job_id. Use 'list' first to find the ID.\n"
        "- 'list': show all active reminders and tasks with their IDs and schedules.\n\n"
        "Job types (IMPORTANT: prefer 'assistant' unless the user explicitly asks for a simple reminder):\n"
        "- 'assistant' (preferred): runs the message as a prompt through the AI assistant at the scheduled time, "
        "with full tool access. Use this by default for all scheduled tasks and reminders.\n"
        "- 'notification': sends a pre-written static message. Only use this when the user explicitly "
        "asks for a simple notification with no AI involvement.\n\n"
        "Trigger types:\n"
        "- 'date': one-time at a specific time. Use for 'remind me in 10 minutes' — "
        "compute the absolute datetime from the current time shown in the system prompt and pass as run_date.\n"
        "- 'cron': recurring on a schedule (e.g. every weekday at 9am).\n"
        "- 'interval': repeating at a fixed interval (e.g. every 30 minutes).\n\n"
        "All times must be in the user's local timezone as shown in the system prompt (NOT UTC unless that IS the user's timezone)."
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
            "job_type": {
                "type": "string",
                "enum": ["notification", "assistant"],
                "description": (
                    "Type of job (optional for create, default 'assistant'). "
                    "Use 'assistant' by default — the message will be executed as a prompt with full tool access. "
                    "Use 'notification' only when the user explicitly wants a simple static message with no AI involvement."
                ),
            },
            "silent": {
                "type": "boolean",
                "description": (
                    "If true, the assistant job will NOT auto-deliver its response. "
                    "Instead, the agent must explicitly call send_notification to notify the user. "
                    "Use this for recurring tasks where the user only wants to be notified when "
                    "something noteworthy happens (e.g. 'check news every hour, only notify if interesting')."
                ),
                "default": False,
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

        job_type = params.get("job_type", "assistant")

        if job_type == "assistant":
            silent = params.get("silent", False)
            job_id = scheduler.add_assistant_job(
                description=params["description"],
                trigger_type=params["trigger_type"],
                trigger_args=params["trigger_args"],
                prompt=params["message"],
                silent=silent,
            )
            mode = " (silent mode)" if silent else ""
            return f"Assistant task scheduled with ID: {job_id}{mode}"
        else:
            job_id = scheduler.add_reminder(
                description=params["description"],
                trigger_type=params["trigger_type"],
                trigger_args=params["trigger_args"],
                message=params.get("message"),
            )
            return f"Reminder scheduled with ID: {job_id}"

    return schedule_reminder
