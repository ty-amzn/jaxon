"""LLM tools for posting to and managing themed feeds."""

from __future__ import annotations

import re
from typing import Any, TYPE_CHECKING

from assistant.agents.background import current_agent_name

if TYPE_CHECKING:
    from assistant.feed.store import FeedStore

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


def _make_post_to_feed(feed_store: FeedStore):
    """Factory: returns an async handler bound to the feed store."""

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
        if reply_to is not None:
            parent = feed_store.get_post(reply_to)
            if parent is None:
                return f"Error: post {reply_to} not found."

        # Resolve feed
        feed_id = None
        if feed_name:
            feed = feed_store.get_feed(feed_name)
            if feed is None:
                return f"Error: feed '{feed_name}' not found. Use manage_feeds to create it first."
            feed_id = feed["id"]

        author = current_agent_name.get("assistant")
        post = feed_store.create_post(
            author=author,
            content=content,
            reply_to=reply_to,
            feed_id=feed_id,
        )
        suffix = f" in #{feed_name}" if feed_name else ""
        return f"Posted to feed{suffix} (id={post['id']})."

    return post_to_feed


def _make_manage_feeds(feed_store: FeedStore):
    """Factory: returns an async handler for feed management."""

    async def manage_feeds(params: dict[str, Any]) -> str:
        action = params.get("action")
        name = params.get("name")

        if action == "list":
            feeds = feed_store.list_feeds()
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
            try:
                feed = feed_store.create_feed(name, desc, created_by=author)
            except ValueError as e:
                return f"Error: {e}"
            return f"Created feed #{feed['name']} (id={feed['id']})."

        if action == "read":
            if not name:
                return "Error: 'name' is required to read a feed."
            feed = feed_store.get_feed(name)
            if feed is None:
                return f"Error: feed '{name}' not found."
            limit = params.get("limit", 20)
            posts = feed_store.get_feed_posts(feed["id"], limit=limit)
            if not posts:
                return f"#{name} has no posts yet."
            lines = [f"#{name}: {feed['description']}", ""]
            for p in posts:
                lines.append(f"[@{p['author']}] {p['content'][:200]}")
            return "\n".join(lines)

        if action == "delete":
            if not name:
                return "Error: 'name' is required to delete a feed."
            deleted = feed_store.delete_feed(name)
            if not deleted:
                return f"Error: feed '{name}' not found."
            return f"Deleted feed #{name}. Posts moved to global timeline."

        return f"Error: unknown action '{action}'."

    return manage_feeds
