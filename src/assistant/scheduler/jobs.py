"""Job callables for APScheduler."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface
    from assistant.core.notifications import NotificationDispatcher
    from assistant.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


async def run_notification_job(
    dispatcher: NotificationDispatcher,
    message: str,
    memory: MemoryManager | None = None,
    job_store: Any | None = None,
    job_id: str | None = None,
) -> None:
    """Send a notification message via dispatcher."""
    notification = f"Reminder: {message}"
    await dispatcher.send(notification)
    if memory:
        await memory.save_exchange(
            f"[Scheduled reminder] {message}",
            notification,
            session_id="scheduler",
        )
    if job_store and job_id:
        job_store.delete(job_id)
        logger.debug("Cleaned up one-time job %s from store", job_id)


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


_SILENT_PROMPT_PREFIX = (
    "You are running in SILENT mode. Do NOT assume the user wants to hear from you. "
    "Only call the `send_notification` tool if there is something genuinely noteworthy "
    "or actionable to report. If there is nothing interesting, simply respond without "
    "calling send_notification and your response will be silently discarded.\n\n"
)


async def run_assistant_job(
    chat_interface: ChatInterface,
    session_id: str,
    prompt: str,
    dispatcher: NotificationDispatcher,
    memory: MemoryManager | None = None,
    silent: bool = False,
    job_store: Any | None = None,
    job_id: str | None = None,
) -> None:
    """Run a prompt through the assistant and send the response as a notification.

    Note: get_response() already persists the exchange to daily log and search
    index via _process_message, so no extra save_exchange call is needed here.

    When silent=True, the prompt is augmented to instruct the agent to use
    send_notification explicitly; auto-delivery of the response is skipped.
    """
    try:
        effective_prompt = _SILENT_PROMPT_PREFIX + prompt if silent else prompt
        response = await chat_interface.get_response(session_id, effective_prompt)
        if not silent:
            await dispatcher.send(f"Scheduled task result:\n{response}")
    except Exception:
        logger.exception("Error running assistant job")
        await dispatcher.send(f"Scheduled task failed for prompt: {prompt}")
    finally:
        if job_store and job_id:
            job_store.delete(job_id)
            logger.debug("Cleaned up one-time job %s from store", job_id)
