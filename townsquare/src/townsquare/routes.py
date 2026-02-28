"""Town Square API routes."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from townsquare.ui import APP_ICON_SVG, FEED_HTML, MANIFEST_JSON, SERVICE_WORKER_JS

logger = logging.getLogger(__name__)

feed_router = APIRouter(prefix="/feed", tags=["feed"])


class CreatePostBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    reply_to: int | None = None
    feed: str | None = None
    author: str = "user"


class EditPostBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CreateFeedBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    created_by: str = "user"


async def _fire_reply_webhook(webhook_url: str, parent: dict, user_reply: dict) -> None:
    """Fire a non-blocking webhook to Jaxon for agent reply generation."""
    payload = {
        "parent_post": parent,
        "user_reply": user_reply,
        "reply_to": parent["id"],
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(f"{webhook_url}/hooks/townsquare/reply", json=payload)
    except Exception:
        logger.exception("Failed to fire reply webhook to %s", webhook_url)


# -- Static assets -----------------------------------------------------------

@feed_router.get("/ui", response_class=HTMLResponse)
async def feed_ui():
    return HTMLResponse(FEED_HTML)


@feed_router.get("/manifest.json")
async def feed_manifest():
    return Response(MANIFEST_JSON, media_type="application/manifest+json")


@feed_router.get("/sw.js")
async def feed_service_worker():
    return Response(
        SERVICE_WORKER_JS,
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/feed/"},
    )


@feed_router.get("/icon-192.svg")
async def feed_icon_192():
    return Response(APP_ICON_SVG, media_type="image/svg+xml")


@feed_router.get("/icon-512.svg")
async def feed_icon_512():
    return Response(APP_ICON_SVG, media_type="image/svg+xml")


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


# -- Likes ------------------------------------------------------------------

@feed_router.post("/posts/{post_id}/like")
async def like_post(request: Request, post_id: int):
    store = request.app.state.feed_store
    store.like_post(post_id)
    return {"ok": True}


@feed_router.delete("/posts/{post_id}/like")
async def unlike_post(request: Request, post_id: int):
    store = request.app.state.feed_store
    store.unlike_post(post_id)
    return {"ok": True}


# -- Posts -------------------------------------------------------------------

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

    # Attach reply counts, feed name, and liked status
    feeds_cache: dict[int, str] = {}
    liked_ids = store.get_liked_post_ids()
    for p in posts:
        thread = store.get_thread(p["id"])
        p["reply_count"] = len(thread) - 1
        p["liked"] = p["id"] in liked_ids
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
    posts = store.get_thread(post_id)
    liked_ids = store.get_liked_post_ids()
    for p in posts:
        p["liked"] = p["id"] in liked_ids
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
    )

    result = {"post": post}

    # If a user is replying to a non-user post, fire webhook for agent reply
    if body.reply_to is not None and body.author == "user":
        parent = store.get_post(body.reply_to)
        if parent and parent["author"] != "user" and settings.webhook_callback_url:
            import asyncio
            asyncio.create_task(_fire_reply_webhook(settings.webhook_callback_url, parent, post))

    return result
