"""Feed API routes — Town Square."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from assistant.feed.ui import FEED_HTML

logger = logging.getLogger(__name__)

feed_router = APIRouter(prefix="/feed", tags=["feed"])


class CreatePostBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    reply_to: int | None = None


@feed_router.get("/ui", response_class=HTMLResponse)
async def feed_ui():
    return HTMLResponse(FEED_HTML)


@feed_router.get("/posts")
async def get_posts(request: Request, limit: int = 50, before_id: int | None = None):
    store = request.app.state.feed_store
    posts = store.get_timeline(limit=limit, before_id=before_id)
    # Attach reply counts
    for p in posts:
        thread = store.get_thread(p["id"])
        p["reply_count"] = len(thread) - 1
    return posts


@feed_router.get("/posts/{post_id}/thread")
async def get_thread(request: Request, post_id: int):
    store = request.app.state.feed_store
    return store.get_thread(post_id)


@feed_router.post("/posts")
async def create_post(request: Request, body: CreatePostBody):
    store = request.app.state.feed_store

    # Create the user's post
    user_post = store.create_post(
        author="user",
        content=body.content,
        reply_to=body.reply_to,
    )

    result = {"post": user_post}

    # If replying to a non-user post, generate an agent response
    if body.reply_to is not None:
        parent = store.get_post(body.reply_to)
        if parent and parent["author"] != "user":
            try:
                chat_interface = request.app.state.chat_interface
                # Build a synthetic prompt with context
                synthetic = (
                    f"You are replying in a feed thread. "
                    f"The original post by @{parent['author']} was:\n"
                    f'"{parent["content"]}"\n\n'
                    f'The user replied: "{body.content}"\n\n'
                    f"Respond concisely in 1-2 sentences, like a tweet-length reply."
                )
                agent_text = await chat_interface.get_response(
                    session_id=f"feed-{body.reply_to}",
                    user_input=synthetic,
                )
                agent_reply = store.create_post(
                    author="assistant",
                    content=agent_text.strip(),
                    reply_to=body.reply_to,
                )
                result["agent_reply"] = agent_reply
            except Exception:
                logger.exception("Failed to generate agent reply for feed post")

    return result
