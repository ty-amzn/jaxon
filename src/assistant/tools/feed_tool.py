"""LLM tool for posting to the internal feed."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from assistant.feed.store import FeedStore

POST_TO_FEED_DEF: dict[str, Any] = {
    "name": "post_to_feed",
    "description": (
        "Post a message to the internal feed (Town Square). Use this to share "
        "updates, findings, or thoughts. Other agents and the user can see and "
        "reply to your posts."
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
        },
        "required": ["content"],
    },
}


def _make_post_to_feed(feed_store: FeedStore):
    """Factory: returns an async handler bound to the feed store."""

    async def post_to_feed(params: dict[str, Any]) -> str:
        content = params.get("content", "")
        if not content:
            return "Error: content is required."
        if len(content) > 2000:
            return "Error: content exceeds 2000 character limit."
        reply_to = params.get("reply_to")
        if reply_to is not None:
            parent = feed_store.get_post(reply_to)
            if parent is None:
                return f"Error: post {reply_to} not found."
        post = feed_store.create_post(
            author="assistant",
            content=content,
            reply_to=reply_to,
        )
        return f"Posted to feed (id={post['id']})."

    return post_to_feed
