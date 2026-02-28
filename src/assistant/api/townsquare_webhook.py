"""Webhook receiver for Town Square agent reply requests."""

from __future__ import annotations

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


async def _generate_agent_reply(request: Request, parent: dict, user_reply_text: str) -> str:
    """Generate a feed reply using the original agent's persona."""
    chat_interface = request.app.state.chat_interface
    author = parent["author"]

    # Try to load the agent's persona from YAML definitions
    agent_persona = ""
    agent_key = "jax" if author == "assistant" else author
    orchestrator = getattr(chat_interface, "_orchestrator", None)
    if orchestrator:
        loader = getattr(orchestrator, "_loader", None)
        if loader:
            agent_def = loader.get_agent(agent_key)
            if agent_def and agent_def.system_prompt:
                agent_persona = agent_def.system_prompt

    if agent_persona:
        system = (
            f"# Agent Role: {agent_key}\n\n{agent_persona}\n\n---\n\n"
            f"You are replying in a feed thread. Keep replies concise — "
            f"1-2 sentences, tweet-style. Stay in character."
        )
    else:
        system = (
            f"You are {author}. You are replying in a feed thread. "
            f"Keep replies concise — 1-2 sentences, tweet-style."
        )

    from assistant.llm.types import StreamEventType

    llm = chat_interface._llm
    messages = [
        {
            "role": "user",
            "content": (
                f"Your original post was:\n\"{parent['content']}\"\n\n"
                f"Ty replied: \"{user_reply_text}\"\n\n"
                f"Write your reply."
            ),
        }
    ]
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
        agent_text = await _generate_agent_reply(request, parent, user_reply.get("content", ""))

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
