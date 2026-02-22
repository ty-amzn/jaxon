"""Job callables for APScheduler."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface
    from assistant.core.notifications import NotificationDispatcher

logger = logging.getLogger(__name__)


async def run_notification_job(
    dispatcher: NotificationDispatcher,
    message: str,
) -> None:
    """Send a notification message via dispatcher."""
    await dispatcher.send(f"Reminder: {message}")


async def run_workflow_job(
    workflow_manager: Any,
    workflow_runner: Any,
    workflow_name: str,
    dispatcher: NotificationDispatcher,
    context: dict | None = None,
) -> None:
    """Run a named workflow and send results as notification."""
    try:
        definition = workflow_manager.get(workflow_name)
        if not definition:
            await dispatcher.send(f"Workflow not found: {workflow_name}")
            return
        results = await workflow_runner.run(definition, context)
        summary = "\n".join(
            f"  {r['step']}: {r['status']}" for r in results
        )
        await dispatcher.send(f"Workflow '{workflow_name}' completed:\n{summary}")
    except Exception:
        logger.exception("Error running workflow job: %s", workflow_name)
        await dispatcher.send(f"Workflow '{workflow_name}' failed")


async def run_assistant_job(
    chat_interface: ChatInterface,
    session_id: str,
    prompt: str,
    dispatcher: NotificationDispatcher,
) -> None:
    """Run a prompt through the assistant and send the response as a notification."""
    try:
        response = await chat_interface.get_response(session_id, prompt)
        await dispatcher.send(f"Scheduled task result:\n{response}")
    except Exception:
        logger.exception("Error running assistant job")
        await dispatcher.send(f"Scheduled task failed for prompt: {prompt}")
