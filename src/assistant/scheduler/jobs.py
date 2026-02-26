"""Job callables for APScheduler."""

from __future__ import annotations

import asyncio
import json
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


_REFLECTION_SYSTEM = (
    "You extract long-term facts from daily conversation logs. "
    "Focus on: preferences, habits, interests, personal info, recurring topics, "
    "opinions, and project context."
)

_REFLECTION_PROMPT = """\
Review yesterday's conversations and extract any facts worth remembering long-term \
about the user. Focus on: preferences, habits, interests, personal info, \
recurring topics, opinions, and project context.

Current durable memory (avoid duplicates):
{current_memory}

Today's conversations:
{daily_log}

Respond with ONLY a JSON array of objects: [{{"section": "...", "fact": "..."}}]
If nothing new is worth remembering, respond with an empty array: []"""


async def run_reflection_job(
    memory: MemoryManager,
    reflection_model: str,
) -> None:
    """Review today's conversations and extract long-term facts into MEMORY.md.

    Makes a direct LLM call (no tools, no daily log pollution) and appends
    any new insights to durable memory.
    """
    from datetime import datetime, timedelta, timezone

    from assistant.core.config import get_settings
    from assistant.llm.router import LLMRouter
    from assistant.llm.types import StreamEventType

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    daily_log = memory.daily_log.read_full(date=yesterday)
    if not daily_log.strip():
        logger.info("Reflection: no daily log entries for %s, skipping", yesterday.strftime("%Y-%m-%d"))
        return

    current_memory = memory.durable.read()

    prompt = _REFLECTION_PROMPT.format(
        current_memory=current_memory,
        daily_log=daily_log,
    )

    settings = get_settings()
    router = LLMRouter(settings)
    client = router.get_client_for_model(reflection_model)

    full_response = ""
    try:
        async for event in client.stream_with_tool_loop(
            system=_REFLECTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            tools=None,
            tool_executor=None,
            max_tool_rounds=0,
        ):
            if event.type == StreamEventType.TEXT_DELTA:
                full_response += event.text
            elif event.type == StreamEventType.MESSAGE_COMPLETE:
                full_response = event.text
            elif event.type == StreamEventType.ERROR:
                logger.error("Reflection LLM error: %s", event.error)
                return
    except Exception:
        logger.exception("Reflection: LLM call failed")
        return

    # Parse JSON response
    text = full_response.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()

    try:
        insights = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Reflection: could not parse LLM response as JSON: %s", text[:200])
        return

    if not isinstance(insights, list):
        logger.warning("Reflection: expected JSON array, got %s", type(insights).__name__)
        return

    added = 0
    for item in insights:
        if isinstance(item, dict) and "section" in item and "fact" in item:
            await memory.durable.append(item["section"], item["fact"])
            added += 1

    logger.info("Reflection: extracted %d new facts from daily log", added)


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
