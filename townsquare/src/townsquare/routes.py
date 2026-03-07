"""Town Square API routes."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from townsquare.ui import STATIC_DIR, TEMPLATES_DIR

logger = logging.getLogger(__name__)

feed_router = APIRouter(prefix="/feed", tags=["feed"])


class CreatePostBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    reply_to: int | None = None
    feed: str | None = None
    author: str = "user"
    image_url: str | None = Field(None, max_length=2048)
    mentioned_agent: str | None = None


class EditPostBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    image_url: str | None = Field(None, max_length=2048)


class CreateFeedBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    created_by: str = "user"


class ReactBody(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=4)


class AgentEntry(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    tagline: str = ""


class UpsertAgentsBody(BaseModel):
    agents: list[AgentEntry]


async def _fire_reply_webhook(
    webhook_url: str, parent: dict, user_reply: dict, mentioned_agent: str | None = None,
) -> None:
    """Fire a non-blocking webhook to Jaxon for agent reply generation."""
    payload = {
        "parent_post": parent,
        "user_reply": user_reply,
        "reply_to": parent["id"],
    }
    if mentioned_agent:
        payload["mentioned_agent"] = mentioned_agent
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(f"{webhook_url}/hooks/townsquare/reply", json=payload)
    except Exception:
        logger.exception("Failed to fire reply webhook to %s", webhook_url)


# -- Static assets -----------------------------------------------------------

@feed_router.get("/ui", response_class=HTMLResponse)
async def feed_ui():
    return HTMLResponse((TEMPLATES_DIR / "feed.html").read_text())


@feed_router.get("/manifest.json")
async def feed_manifest():
    return Response(
        (STATIC_DIR / "manifest.json").read_text(),
        media_type="application/manifest+json",
    )


@feed_router.get("/sw.js")
async def feed_service_worker():
    return Response(
        (STATIC_DIR / "sw.js").read_text(),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/feed/"},
    )


@feed_router.get("/icon-192.svg")
async def feed_icon_192():
    return Response((STATIC_DIR / "icon.svg").read_text(), media_type="image/svg+xml")


@feed_router.get("/icon-512.svg")
async def feed_icon_512():
    return Response((STATIC_DIR / "icon.svg").read_text(), media_type="image/svg+xml")


# -- Agents ------------------------------------------------------------------

@feed_router.put("/agents")
async def upsert_agents(request: Request, body: UpsertAgentsBody):
    store = request.app.state.feed_store
    store.upsert_agents([a.model_dump() for a in body.agents])
    return {"ok": True, "count": len(body.agents)}


@feed_router.get("/agents")
async def list_agents(request: Request):
    store = request.app.state.feed_store
    return store.list_agents()


# -- Channels ----------------------------------------------------------------

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
        feed = store.create_feed(body.name, body.description, created_by=body.created_by)
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


# -- Reactions ---------------------------------------------------------------

@feed_router.post("/posts/{post_id}/react")
async def react_post(request: Request, post_id: int, body: ReactBody):
    store = request.app.state.feed_store
    try:
        active = store.toggle_reaction(post_id, body.emoji)
    except ValueError as e:
        return {"error": str(e)}
    return {"ok": True, "active": active, "emoji": body.emoji}


@feed_router.get("/posts/{post_id}/reactions")
async def get_post_reactions(request: Request, post_id: int):
    store = request.app.state.feed_store
    return {"reactions": store.get_post_reactions(post_id)}


@feed_router.get("/posts/liked")
async def get_liked_posts(request: Request, limit: int = 50):
    """Return posts with any reaction (backward-compat name)."""
    store = request.app.state.feed_store
    posts = store.get_reacted_posts(limit=limit)
    post_ids = [p["id"] for p in posts]
    bulk = store.get_bulk_reactions(post_ids)
    for p in posts:
        p["reactions"] = bulk.get(p["id"], [])
    return posts


# -- Posts -------------------------------------------------------------------

@feed_router.get("/posts")
async def get_posts(
    request: Request,
    limit: int = 50,
    before_id: int | None = None,
    feed: str | None = None,
    since: str | None = None,
    q: str | None = None,
):
    store = request.app.state.feed_store

    if q:
        posts = store.search_posts(q, limit=limit, before_id=before_id)
    elif feed:
        feed_obj = store.get_feed(feed)
        if feed_obj is None:
            return []
        posts = store.get_feed_posts(feed_obj["id"], limit=limit, before_id=before_id, since=since)
    else:
        posts = store.get_timeline(limit=limit, before_id=before_id, since=since)

    # Attach reply counts, feed name, and reactions
    feeds_cache: dict[int, str] = {}
    post_ids = [p["id"] for p in posts]
    bulk_reactions = store.get_bulk_reactions(post_ids)
    for p in posts:
        thread = store.get_thread(p["id"])
        p["reply_count"] = len(thread) - 1
        p["reactions"] = bulk_reactions.get(p["id"], [])
        fid = p.get("feed_id")
        if fid and fid not in feeds_cache:
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
    updated = store.edit_post(post_id, body.content, image_url=body.image_url)
    return updated


@feed_router.delete("/posts/{post_id}")
async def delete_post(request: Request, post_id: int):
    store = request.app.state.feed_store
    deleted = store.delete_post(post_id)
    if not deleted:
        return {"error": "Post not found."}
    return {"ok": True}


@feed_router.post("/posts/{post_id}/read")
async def mark_post_read(request: Request, post_id: int):
    """Mark a thread as read (by root post ID)."""
    store = request.app.state.feed_store
    store.mark_read(post_id)
    return {"ok": True}


@feed_router.get("/posts/engaged")
async def get_engaged_threads(request: Request, author: str = "user", since: str | None = None):
    """Return full threads where the given author participated, with unread counts."""
    store = request.app.state.feed_store
    threads = store.get_threads_with_author(author, since=since)
    read_state = store.get_read_state()
    for thread in threads:
        if thread:
            root = thread[0]
            root_id = root["id"]
            last_read = read_state.get(root_id)
            root["unread_replies"] = store.count_unread_replies(root_id, last_read)
    return threads


@feed_router.get("/posts/{post_id}/thread")
async def get_thread(request: Request, post_id: int):
    store = request.app.state.feed_store
    posts = store.get_thread(post_id)
    post_ids = [p["id"] for p in posts]
    bulk_reactions = store.get_bulk_reactions(post_ids)
    for p in posts:
        p["reactions"] = bulk_reactions.get(p["id"], [])
    return posts


@feed_router.post("/posts")
async def create_post(request: Request, body: CreatePostBody):
    store = request.app.state.feed_store
    settings = request.app.state.settings

    # Validate reply_to exists
    if body.reply_to is not None:
        parent = store.get_post(body.reply_to)
        if parent is None:
            return {"error": f"Post {body.reply_to} not found."}

    # Resolve feed
    feed_id = None
    if body.feed:
        feed_obj = store.get_feed(body.feed)
        if feed_obj is None:
            return {"error": f"Feed '{body.feed}' not found."}
        feed_id = feed_obj["id"]

    # Create the post
    post = store.create_post(
        author=body.author,
        content=body.content,
        reply_to=body.reply_to,
        feed_id=feed_id,
        image_url=body.image_url,
    )

    result = {"post": post}

    # If a user is replying to a non-user post, fire webhook for agent reply
    if body.reply_to is not None and body.author == "user":
        parent = store.get_post(body.reply_to)
        if parent and parent["author"] != "user" and settings.webhook_callback_url:
            import asyncio
            asyncio.create_task(_fire_reply_webhook(
                settings.webhook_callback_url, parent, post,
                mentioned_agent=body.mentioned_agent,
            ))

    return result
