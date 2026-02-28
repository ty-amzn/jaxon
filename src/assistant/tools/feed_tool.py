"""LLM tools for posting to and managing themed feeds via Town Square HTTP API."""

from __future__ import annotations

import re
from typing import Any

import httpx

from assistant.agents.background import current_agent_name

# Matches trailing JSON parameter fragments that smaller models sometimes
# bleed into the content field, e.g.: ', "feed": "research"'
_TRAILING_FEED_RE = re.compile(r',\s*"feed"\s*:\s*"([^"]*)"\s*\}?\s*$')
_TRAILING_REPLY_RE = re.compile(r',\s*"reply_to"\s*:\s*(\d+)\s*\}?\s*$')

POST_TO_FEED_DEF: dict[str, Any] = {
    "name": "post_to_feed",
    "description": (
        "Post a message to the internal feed (Town Square). Use this to share "
        "updates, findings, or thoughts. Other agents and the user can see and "
        "reply to your posts. Optionally post to a specific themed feed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2000,
                "description": "The post body (markdown supported, max 2000 chars).",
            },
            "reply_to": {
                "type": "integer",
                "description": "Optional post ID to reply to (for threading).",
            },
            "feed": {
                "type": "string",
                "description": "Optional feed name to post to (e.g. 'news', 'research'). Omit for global timeline.",
            },
        },
        "required": ["content"],
    },
}

MANAGE_FEEDS_DEF: dict[str, Any] = {
    "name": "manage_feeds",
    "description": (
        "Manage themed feeds (channels) in the Town Square. "
        "Create, list, read, or delete feeds."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "read", "delete"],
                "description": "The action to perform.",
            },
            "name": {
                "type": "string",
                "description": "Feed name (slug). Required for create, read, delete.",
            },
            "description": {
                "type": "string",
                "description": "Feed description. Required for create.",
            },
            "limit": {
                "type": "integer",
                "description": "Max posts to return for read action (default 20).",
                "default": 20,
            },
        },
        "required": ["action"],
    },
}


def _make_post_to_feed(base_url: str):
    """Factory: returns an async handler that posts via Town Square HTTP API."""

    async def post_to_feed(params: dict[str, Any]) -> str:
        content = params.get("content", "")
        if not content:
            return "Error: content is required."

        # Smaller models sometimes bleed tool params into the content
        # string (e.g. 'Cool finding, "feed": "research"').  Extract
        # the values so they aren't lost, then clean the content.
        feed_name = params.get("feed")
        reply_to = params.get("reply_to")

        m_feed = _TRAILING_FEED_RE.search(content)
        if m_feed:
            if not feed_name:
                feed_name = m_feed.group(1)
            content = content[:m_feed.start()].rstrip()

        m_reply = _TRAILING_REPLY_RE.search(content)
        if m_reply:
            if reply_to is None:
                reply_to = int(m_reply.group(1))
            content = content[:m_reply.start()].rstrip()

        if len(content) > 2000:
            return "Error: content exceeds 2000 character limit."

        author = current_agent_name.get("assistant")
        payload: dict[str, Any] = {
            "content": content,
            "author": author,
        }
        if reply_to is not None:
            payload["reply_to"] = reply_to
        if feed_name:
            payload["feed"] = feed_name

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{base_url}/feed/posts", json=payload)
        data = resp.json()

        if "error" in data:
            return f"Error: {data['error']}"

        post = data.get("post", data)
        post_id = post.get("id", "?")
        suffix = f" in #{feed_name}" if feed_name else ""
        return f"Posted to feed{suffix} (id={post_id})."

    return post_to_feed


def _make_manage_feeds(base_url: str):
    """Factory: returns an async handler for feed management via HTTP."""

    async def manage_feeds(params: dict[str, Any]) -> str:
        action = params.get("action")
        name = params.get("name")

        async with httpx.AsyncClient(timeout=30) as client:
            if action == "list":
                resp = await client.get(f"{base_url}/feed/channels")
                data = resp.json()
                feeds = data.get("feeds", [])
                if not feeds:
                    return "No feeds yet. Use action='create' to make one."
                lines = []
                for f in feeds:
                    lines.append(f"#{f['name']} — {f['description']} ({f['post_count']} posts)")
                return "\n".join(lines)

            if action == "create":
                if not name:
                    return "Error: 'name' is required to create a feed."
                desc = params.get("description", "")
                if not desc:
                    return "Error: 'description' is required to create a feed."
                author = current_agent_name.get("assistant")
                resp = await client.post(
                    f"{base_url}/feed/channels",
                    json={"name": name, "description": desc, "created_by": author},
                )
                data = resp.json()
                if "error" in data:
                    return f"Error: {data['error']}"
                return f"Created feed #{data['name']} (id={data['id']})."

            if action == "read":
                if not name:
                    return "Error: 'name' is required to read a feed."
                limit = params.get("limit", 20)
                resp = await client.get(
                    f"{base_url}/feed/channels/{name}",
                    params={"limit": limit},
                )
                data = resp.json()
                if "error" in data:
                    return f"Error: {data['error']}"
                feed = data.get("feed", {})
                posts = data.get("posts", [])
                if not posts:
                    return f"#{name} has no posts yet."
                lines = [f"#{name}: {feed.get('description', '')}", ""]
                for p in posts:
                    lines.append(f"[@{p['author']}] {p['content'][:200]}")
                return "\n".join(lines)

            if action == "delete":
                if not name:
                    return "Error: 'name' is required to delete a feed."
                resp = await client.delete(f"{base_url}/feed/channels/{name}")
                data = resp.json()
                if "error" in data:
                    return f"Error: {data['error']}"
                return f"Deleted feed #{name}. Posts moved to global timeline."

        return f"Error: unknown action '{action}'."

    return manage_feeds
