"""Feed API routes — Town Square."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from assistant.feed.ui import FEED_HTML

logger = logging.getLogger(__name__)

feed_router = APIRouter(prefix="/feed", tags=["feed"])


async def _generate_agent_reply(request: Request, parent: dict, user_reply: str) -> str:
    """Generate a feed reply using the original agent's persona."""
    chat_interface = request.app.state.chat_interface
    author = parent["author"]

    # Try to load the agent's persona from YAML definitions
    agent_persona = ""
    # Map "assistant" back to "jax" for agent lookup
    agent_key = "jax" if author == "assistant" else author
    orchestrator = getattr(chat_interface, "_orchestrator", None)
    if orchestrator:
        loader = getattr(orchestrator, "_loader", None)
        if loader:
            agent_def = loader.get_agent(agent_key)
            if agent_def and agent_def.system_prompt:
                agent_persona = agent_def.system_prompt

    # Build system prompt with the agent's own voice
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

    # Direct LLM call — lightweight, no tools needed
    from assistant.llm.types import StreamEventType

    llm = chat_interface._llm
    messages = [
        {
            "role": "user",
            "content": (
                f"Your original post was:\n\"{parent['content']}\"\n\n"
                f"Ty replied: \"{user_reply}\"\n\n"
                f"Write your reply."
            ),
        }
    ]
    full_text = ""
    async for event in llm.stream_with_tool_loop(system=system, messages=messages):
        if event.type == StreamEventType.TEXT_DELTA:
            full_text += event.text
    return full_text


class CreatePostBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    reply_to: int | None = None
    feed: str | None = None


class EditPostBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CreateFeedBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)


@feed_router.get("/ui", response_class=HTMLResponse)
async def feed_ui():
    return HTMLResponse(FEED_HTML)


@feed_router.get("/channels")
async def list_channels(request: Request):
    store = request.app.state.feed_store
    return {"feeds": store.list_feeds(), "total_posts": store.total_root_post_count()}


@feed_router.get("/channels/{name}")
async def get_channel(request: Request, name: str, limit: int = 50, before_id: int | None = None):
    store = request.app.state.feed_store
    feed = store.get_feed(name)
    if feed is None:
        return {"error": f"Feed '{name}' not found."}
    posts = store.get_feed_posts(feed["id"], limit=limit, before_id=before_id)
    for p in posts:
        thread = store.get_thread(p["id"])
        p["reply_count"] = len(thread) - 1
    return {"feed": feed, "posts": posts}


@feed_router.post("/channels")
async def create_channel(request: Request, body: CreateFeedBody):
    store = request.app.state.feed_store
    try:
        feed = store.create_feed(body.name, body.description, created_by="user")
    except ValueError as e:
        return {"error": str(e)}
    return feed


@feed_router.delete("/channels/{name}")
async def delete_channel(request: Request, name: str):
    store = request.app.state.feed_store
    deleted = store.delete_feed(name)
    if not deleted:
        return {"error": f"Feed '{name}' not found."}
    return {"ok": True}


@feed_router.get("/posts")
async def get_posts(request: Request, limit: int = 50, before_id: int | None = None, feed: str | None = None):
    store = request.app.state.feed_store

    if feed:
        feed_obj = store.get_feed(feed)
        if feed_obj is None:
            return []
        posts = store.get_feed_posts(feed_obj["id"], limit=limit, before_id=before_id)
    else:
        posts = store.get_timeline(limit=limit, before_id=before_id)

    # Attach reply counts and feed name
    feeds_cache: dict[int, str] = {}
    for p in posts:
        thread = store.get_thread(p["id"])
        p["reply_count"] = len(thread) - 1
        fid = p.get("feed_id")
        if fid and fid not in feeds_cache:
            # Look up feed name by id
            for f in store.list_feeds():
                feeds_cache[f["id"]] = f["name"]
        p["feed_name"] = feeds_cache.get(fid) if fid else None
    return posts


@feed_router.patch("/posts/{post_id}")
async def edit_post(request: Request, post_id: int, body: EditPostBody):
    store = request.app.state.feed_store
    post = store.get_post(post_id)
    if post is None:
        return {"error": "Post not found."}
    updated = store.edit_post(post_id, body.content)
    return updated


@feed_router.delete("/posts/{post_id}")
async def delete_post(request: Request, post_id: int):
    store = request.app.state.feed_store
    deleted = store.delete_post(post_id)
    if not deleted:
        return {"error": "Post not found."}
    return {"ok": True}


@feed_router.get("/posts/{post_id}/thread")
async def get_thread(request: Request, post_id: int):
    store = request.app.state.feed_store
    return store.get_thread(post_id)


@feed_router.post("/posts")
async def create_post(request: Request, body: CreatePostBody):
    store = request.app.state.feed_store

    # Resolve feed
    feed_id = None
    if body.feed:
        feed_obj = store.get_feed(body.feed)
        if feed_obj is None:
            return {"error": f"Feed '{body.feed}' not found."}
        feed_id = feed_obj["id"]

    # Create the user's post
    user_post = store.create_post(
        author="user",
        content=body.content,
        reply_to=body.reply_to,
        feed_id=feed_id,
    )

    result = {"post": user_post}

    # If replying to a non-user post, generate a response from that agent
    if body.reply_to is not None:
        parent = store.get_post(body.reply_to)
        if parent and parent["author"] != "user":
            try:
                agent_text = await _generate_agent_reply(request, parent, body.content)
                agent_reply = store.create_post(
                    author=parent["author"],
                    content=agent_text.strip(),
                    reply_to=body.reply_to,
                    feed_id=feed_id,
                )
                result["agent_reply"] = agent_reply
            except Exception:
                logger.exception("Failed to generate agent reply for feed post")

    return result
