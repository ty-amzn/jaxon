"""Webhook receiver for Town Square agent reply requests.

When a user replies to an agent's post in the Town Square UI, Town Square
fires a webhook here.  Jax receives the context and decides how to handle
it — he may reply directly, delegate to the original agent, or delegate to
a different agent if the topic suits.  Just like a human team lead.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

townsquare_webhook_router = APIRouter(tags=["townsquare-webhook"])


class ReplyWebhookBody(BaseModel):
    parent_post: dict
    user_reply: dict
    reply_to: int


async def _fetch_thread_context(
    townsquare_url: str, root_post_id: int
) -> list[dict]:
    """Fetch the full thread from Town Square for conversation context."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{townsquare_url}/feed/posts/{root_post_id}/thread"
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        logger.debug("Failed to fetch thread context for post %s", root_post_id)
    return []


def _build_thread_transcript(thread: list[dict]) -> str:
    """Build a readable conversation transcript from thread posts."""
    if not thread:
        return ""
    lines = []
    for post in thread:
        lines.append(f"{post['author']}: {post['content']}")
    return "\n".join(lines)


async def _handle_reply(request: Request, body: ReplyWebhookBody) -> None:
    """Give Jax the thread context and let him decide how to respond."""
    parent = body.parent_post
    user_reply = body.user_reply
    townsquare_url = request.app.state.settings.townsquare_url
    chat_interface = request.app.state.chat_interface
    author = parent["author"]

    # Fetch full thread for conversation context
    root_post_id = parent.get("reply_to") or parent["id"]
    thread = await _fetch_thread_context(townsquare_url, root_post_id)
    transcript = _build_thread_transcript(thread)

    user_text = user_reply.get("content", "")

    # Build the task for Jax
    task_parts = [
        f"Ty replied to a Town Square thread (originally posted by {author}).",
        f"The reply_to post ID is {body.reply_to}.",
        "",
        "Decide how to handle this:",
        f"- If you should reply yourself, use `post_to_feed` with reply_to={body.reply_to}",
        f"- If {author} or another agent should handle it, first post a brief handoff reply "
        f"  mentioning them (e.g. \"@nova, over to you\" or \"Let me get @sage on this\") "
        f"  using `post_to_feed` with reply_to={body.reply_to}, then delegate to them",
        "- If it needs research first, do the same — post a handoff, then delegate",
        "",
        "Keep all replies brief and conversational (1-3 sentences).",
        "",
    ]
    if transcript:
        task_parts.append(f"Thread so far:\n{transcript}")
    else:
        task_parts.append(f"Original post by {author}:\n{parent['content']}")
    task_parts.append(f"\nTy's reply:\n{user_text}")

    task = "\n".join(task_parts)

    # Run Jax with his full system prompt, tools, and delegation capabilities
    from assistant.agents.background import _auto_approve
    from assistant.gateway.permissions import PermissionManager
    from assistant.llm.context import build_system_prompt
    from assistant.llm.types import ToolCall, ToolResult

    agent_catalog = None
    orchestrator = getattr(chat_interface, "_orchestrator", None)
    if orchestrator:
        agents = orchestrator._loader.list_agents()
        if agents:
            agent_catalog = [(a.name, a.description) for a in agents]

    system_prompt = build_system_prompt(
        chat_interface._memory, agent_catalog=agent_catalog,
    )

    # Auto-approve permissions for background webhook handling
    auto_perms = PermissionManager(_auto_approve)

    async def tool_executor(tc: ToolCall) -> ToolResult:
        return await chat_interface._tool_registry.execute(
            tc, permission_override=auto_perms,
        )

    messages = [{"role": "user", "content": task}]
    async for event in chat_interface._llm.stream_with_tool_loop(
        system=system_prompt,
        messages=messages,
        tools=chat_interface._tool_registry.definitions,
        tool_executor=tool_executor,
        max_tool_rounds=chat_interface._settings.max_tool_rounds,
    ):
        pass  # Jax handles everything via tools — no text output needed


@townsquare_webhook_router.post("/hooks/townsquare/reply")
async def handle_reply_webhook(request: Request, body: ReplyWebhookBody):
    """Receive a reply webhook from Town Square and let Jax handle it."""
    try:
        asyncio.create_task(_handle_reply(request, body))
        return {"ok": True}
    except Exception:
        logger.exception("Failed to handle Town Square reply webhook")
        return {"error": "Failed to handle reply webhook."}
