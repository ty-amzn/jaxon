"""Webhook receiver for Town Square agent reply requests."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

townsquare_webhook_router = APIRouter(tags=["townsquare-webhook"])

# Display names for agents in thread context
AGENT_NAMES = {
    "assistant": "Jax",
    "jax": "Jax",
    "nova": "Nova",
    "sage": "Sage",
    "rex": "Rex",
    "atlas": "Atlas",
    "scroll": "Scroll",
    "pixel": "Pixel",
    "bolt": "Bolt",
    "user": "Ty",
}


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


def _build_thread_transcript(thread: list[dict], current_post_id: int) -> str:
    """Build a readable conversation transcript from thread posts."""
    if not thread:
        return ""
    lines = []
    for post in thread:
        if post["id"] == current_post_id:
            break  # Stop before the message we're replying to
        name = AGENT_NAMES.get(post["author"], post["author"])
        lines.append(f"{name}: {post['content']}")
    return "\n".join(lines)


async def _generate_agent_reply(
    request: Request,
    parent: dict,
    user_reply_text: str,
    thread: list[dict],
    reply_post_id: int,
) -> str:
    """Generate a feed reply using the original agent's persona."""
    chat_interface = request.app.state.chat_interface
    author = parent["author"]

    # Try to load the agent's persona from YAML definitions
    agent_persona = ""
    agent_key = "jax" if author == "assistant" else author
    display_name = AGENT_NAMES.get(author, author)
    orchestrator = getattr(chat_interface, "_orchestrator", None)
    if orchestrator:
        loader = getattr(orchestrator, "_loader", None)
        if loader:
            agent_def = loader.get_agent(agent_key)
            if agent_def and agent_def.system_prompt:
                agent_persona = agent_def.system_prompt

    if agent_persona:
        system = (
            f"You are {display_name}.\n\n{agent_persona}\n\n---\n\n"
            f"You are replying in a Town Square feed thread. "
            f"Reply naturally as yourself. Keep it brief — 1-3 sentences."
        )
    else:
        system = (
            f"You are {display_name}. You are replying in a Town Square feed thread. "
            f"Reply naturally. Keep it brief — 1-3 sentences."
        )

    # Build conversation context from thread
    transcript = _build_thread_transcript(thread, reply_post_id)

    if transcript:
        content = (
            f"Thread so far:\n{transcript}\n\n"
            f"Ty just replied: \"{user_reply_text}\"\n\n"
            f"Write your reply."
        )
    else:
        content = (
            f"Your original post was:\n\"{parent['content']}\"\n\n"
            f"Ty replied: \"{user_reply_text}\"\n\n"
            f"Write your reply."
        )

    from assistant.llm.types import StreamEventType

    llm = chat_interface._llm
    messages = [{"role": "user", "content": content}]
    full_text = ""
    async for event in llm.stream_with_tool_loop(system=system, messages=messages):
        if event.type == StreamEventType.TEXT_DELTA:
            full_text += event.text
    return full_text


@townsquare_webhook_router.post("/hooks/townsquare/reply")
async def handle_reply_webhook(request: Request, body: ReplyWebhookBody):
    """Receive a reply webhook from Town Square, generate agent reply, post it back."""
    parent = body.parent_post
    user_reply = body.user_reply
    townsquare_url = request.app.state.settings.townsquare_url

    try:
        # Fetch full thread for conversation context
        root_post_id = parent.get("reply_to") or parent["id"]
        thread = await _fetch_thread_context(townsquare_url, root_post_id)

        agent_text = await _generate_agent_reply(
            request,
            parent,
            user_reply.get("content", ""),
            thread,
            body.reply_to,
        )

        # Post the agent reply back to Town Square
        payload = {
            "content": agent_text.strip(),
            "author": parent["author"],
            "reply_to": body.reply_to,
        }
        # Inherit feed from parent post
        feed_id = parent.get("feed_id")
        if feed_id:
            payload["feed_id"] = feed_id

        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(f"{townsquare_url}/feed/posts", json=payload)

        return {"ok": True}
    except Exception:
        logger.exception("Failed to generate agent reply for webhook")
        return {"error": "Failed to generate agent reply."}
