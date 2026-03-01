"""Hacker News browsing and search tool via Firebase API + Algolia."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 15_000
HN_BASE = "https://hacker-news.firebaseio.com/v0"
ALGOLIA_BASE = "https://hn.algolia.com/api/v1"
MAX_CONCURRENT = 15

FEED_ENDPOINTS = {
    "top": "topstories",
    "best": "beststories",
    "new": "newstories",
    "ask": "askstories",
    "show": "showstories",
}


def _relative_time(unix_ts: int | None) -> str:
    """Convert a Unix timestamp to a relative time string like '2h ago'."""
    if not unix_ts:
        return ""
    delta = int(time.time()) - unix_ts
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    days = delta // 86400
    if days == 1:
        return "1d ago"
    if days < 30:
        return f"{days}d ago"
    return f"{days // 30}mo ago"


def _fmt_score(score: int | None) -> str:
    if score is None:
        return "0"
    if score >= 1_000:
        return f"{score / 1_000:.1f}K"
    return str(score)


async def _hn_get(url: str) -> Any:
    """Make a GET request to the HN Firebase API."""
    async with make_httpx_client(timeout=15.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.json()


async def _fetch_item(item_id: int) -> dict | None:
    """Fetch a single HN item by ID."""
    try:
        data = await _hn_get(f"{HN_BASE}/item/{item_id}.json")
        return data if isinstance(data, dict) else None
    except Exception:
        return None


async def _fetch_items_batch(item_ids: list[int]) -> list[dict]:
    """Fetch multiple items concurrently, capped at MAX_CONCURRENT."""
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def fetch_with_sem(item_id: int) -> dict | None:
        async with sem:
            return await _fetch_item(item_id)

    results = await asyncio.gather(*[fetch_with_sem(i) for i in item_ids])
    return [r for r in results if r is not None]


def _fmt_story(story: dict, index: int) -> str:
    """Format a single HN story for listing."""
    title = story.get("title", "No title")
    url = story.get("url", "")
    author = story.get("by", "unknown")
    score = _fmt_score(story.get("score"))
    comments = story.get("descendants", 0)
    ago = _relative_time(story.get("time"))
    hn_url = f"https://news.ycombinator.com/item?id={story.get('id', '')}"

    parts = [
        f"## {index}. {title}",
        f"**{score} pts** | by {author} | {comments} comments | {ago}",
    ]
    if url:
        parts.append(f"**Link:** {url}")
    parts.append(f"**HN:** {hn_url}")

    # Include text for Ask HN / Show HN
    text = story.get("text", "")
    if text:
        if len(text) > 300:
            text = text[:300] + "..."
        parts.append(f"{text}")
    parts.append("")
    return "\n".join(parts)


async def _fetch_stories(feed: str, num_results: int) -> str:
    """Fetch top N stories from a feed."""
    endpoint = FEED_ENDPOINTS.get(feed, "topstories")
    item_ids = await _hn_get(f"{HN_BASE}/{endpoint}.json")

    if not isinstance(item_ids, list) or not item_ids:
        return f"No stories found for feed: {feed}"

    item_ids = item_ids[:num_results]
    stories = await _fetch_items_batch(item_ids)

    if not stories:
        return f"Failed to fetch stories from {feed} feed"

    # Preserve original order from the feed
    id_order = {sid: i for i, sid in enumerate(item_ids)}
    stories.sort(key=lambda s: id_order.get(s.get("id", 0), 999))

    parts = [f"# Hacker News — {feed} stories\n"]
    for i, story in enumerate(stories, 1):
        parts.append(_fmt_story(story, i))

    result = "\n".join(parts)
    if len(result) > MAX_CONTENT_CHARS:
        result = result[:MAX_CONTENT_CHARS] + "\n\n[... truncated at 15k chars ...]"
    return result


async def _search_hn(query: str, sort: str, num_results: int) -> str:
    """Search HN via Algolia API."""
    endpoint = "search" if sort == "relevance" else "search_by_date"
    url = f"{ALGOLIA_BASE}/{endpoint}"
    params = {"query": query, "tags": "story", "hitsPerPage": num_results}

    async with make_httpx_client(timeout=15.0) as client:
        response = await client.get(url, params=params, follow_redirects=True)
        response.raise_for_status()
        data = response.json()

    hits = data.get("hits", [])
    if not hits:
        return f"No Hacker News results for: {query}"

    parts = [f"# Hacker News Search: {query}\n"]
    for i, hit in enumerate(hits, 1):
        title = hit.get("title", "No title")
        url = hit.get("url", "")
        author = hit.get("author", "unknown")
        points = _fmt_score(hit.get("points"))
        comments = hit.get("num_comments", 0)
        ago = _relative_time(hit.get("created_at_i"))
        object_id = hit.get("objectID", "")
        hn_url = f"https://news.ycombinator.com/item?id={object_id}"

        parts.append(f"## {i}. {title}")
        parts.append(f"**{points} pts** | by {author} | {comments} comments | {ago}")
        if url:
            parts.append(f"**Link:** {url}")
        parts.append(f"**HN:** {hn_url}")
        parts.append("")

    result = "\n".join(parts)
    if len(result) > MAX_CONTENT_CHARS:
        result = result[:MAX_CONTENT_CHARS] + "\n\n[... truncated at 15k chars ...]"
    return result


def _fmt_comment(comment: dict, depth: int = 0) -> str:
    """Format a single HN comment with indentation for depth."""
    author = comment.get("by", "[deleted]")
    text = comment.get("text", "")
    ago = _relative_time(comment.get("time"))
    if not text:
        return ""

    if len(text) > 500:
        text = text[:500] + "..."

    indent = "  " * depth
    return f"{indent}**{author}** ({ago}):\n{indent}{text}"


async def _fetch_comment_tree(comment_ids: list[int], depth: int = 0, max_depth: int = 2, max_per_level: int = 5) -> list[str]:
    """Recursively fetch and format comments up to max_depth."""
    if depth > max_depth or not comment_ids:
        return []

    comments = await _fetch_items_batch(comment_ids[:max_per_level])
    parts: list[str] = []

    for comment in comments:
        if not comment or comment.get("deleted") or comment.get("dead"):
            continue
        formatted = _fmt_comment(comment, depth)
        if formatted:
            parts.append(formatted)

        # Recurse into child comments
        kids = comment.get("kids", [])
        if kids and depth < max_depth:
            child_parts = await _fetch_comment_tree(kids, depth + 1, max_depth, max_per_level=3)
            parts.extend(child_parts)

    return parts


async def _read_story(item_id: int) -> str:
    """Fetch a story and its top comments."""
    story = await _fetch_item(item_id)
    if not story:
        return f"Could not find HN item with ID {item_id}"

    item_type = story.get("type", "story")
    title = story.get("title", "No title")
    url = story.get("url", "")
    author = story.get("by", "unknown")
    score = _fmt_score(story.get("score"))
    comments_count = story.get("descendants", 0)
    ago = _relative_time(story.get("time"))
    hn_url = f"https://news.ycombinator.com/item?id={item_id}"

    parts = [
        f"# {title}\n",
        f"**{score} pts** | by {author} | {comments_count} comments | {ago}",
        f"**Type:** {item_type}",
    ]
    if url:
        parts.append(f"**Link:** {url}")
    parts.append(f"**HN:** {hn_url}")

    text = story.get("text", "")
    if text:
        if len(text) > 5000:
            text = text[:5000] + "\n\n[... text truncated ...]"
        parts.append(f"\n{text}")

    # Fetch top comments
    kids = story.get("kids", [])
    if kids:
        parts.append("\n---\n## Top Comments\n")
        comment_parts = await _fetch_comment_tree(kids, depth=0, max_depth=2, max_per_level=5)
        parts.extend(comment_parts)

    result = "\n".join(parts)
    if len(result) > MAX_CONTENT_CHARS:
        result = result[:MAX_CONTENT_CHARS] + "\n\n[... truncated at 15k chars ...]"
    return result


async def hackernews(params: dict[str, Any]) -> str:
    """Browse and search Hacker News.

    Args:
        params: Dictionary with 'action', 'feed', 'query', 'id', 'sort', 'num_results'.

    Returns:
        Formatted results as markdown.
    """
    action = params.get("action", "top")
    num_results = min(params.get("num_results", 10), 15)

    try:
        if action == "top":
            feed = params.get("feed", "top")
            return await _fetch_stories(feed, num_results)
        elif action == "search":
            query = params.get("query", "")
            if not query:
                return "No search query provided. Use the 'query' parameter."
            sort = params.get("sort", "relevance")
            return await _search_hn(query, sort, num_results)
        elif action == "story":
            item_id = params.get("id")
            if not item_id:
                return "No item ID provided. Use the 'id' parameter."
            return await _read_story(int(item_id))
        else:
            return f"Unknown action: {action}. Use 'top', 'search', or 'story'."
    except httpx.HTTPError as e:
        return f"Hacker News request failed: {e}"
    except ValueError as e:
        return str(e)


HACKERNEWS_TOOL_DEF = {
    "name": "hackernews",
    "description": (
        "Search and browse Hacker News. Use action 'top' to see trending stories "
        "from a feed (top/best/new/ask/show), 'search' to find stories by keyword, "
        "or 'story' to read a specific story with its top comments."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["top", "search", "story"],
                "description": "Action: 'top' for feed browsing, 'search' for keyword search, 'story' for reading a specific item",
                "default": "top",
            },
            "query": {
                "type": "string",
                "description": "Search query (required for 'search' action)",
            },
            "id": {
                "type": "integer",
                "description": "HN item ID (required for 'story' action)",
            },
            "feed": {
                "type": "string",
                "enum": ["top", "best", "new", "ask", "show"],
                "description": "Which feed to browse (for 'top' action, default: top)",
                "default": "top",
            },
            "sort": {
                "type": "string",
                "enum": ["relevance", "date"],
                "description": "Sort order for search (default: relevance)",
                "default": "relevance",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of stories to return (max 15, default 10)",
                "default": 10,
            },
        },
        "required": ["action"],
    },
}
