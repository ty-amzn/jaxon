"""Reddit search and browsing tool via public JSON API."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 15_000
REDDIT_USER_AGENT = "assistant-bot/1.0 (personal AI assistant)"


def _fmt_score(score: int | None) -> str:
    if score is None:
        return "0"
    if score >= 1_000_000:
        return f"{score / 1_000_000:.1f}M"
    if score >= 1_000:
        return f"{score / 1_000:.1f}K"
    return str(score)


def _fmt_post(post: dict, index: int) -> str:
    """Format a single Reddit post for search/subreddit listing."""
    d = post.get("data", post)
    title = d.get("title", "No title")
    subreddit = d.get("subreddit_name_prefixed", f"r/{d.get('subreddit', '?')}")
    author = d.get("author", "Unknown")
    score = _fmt_score(d.get("score"))
    num_comments = d.get("num_comments", 0)
    permalink = d.get("permalink", "")
    url = f"https://www.reddit.com{permalink}" if permalink else ""
    selftext = d.get("selftext", "")
    if len(selftext) > 300:
        selftext = selftext[:300] + "..."

    parts = [
        f"## {index}. {title}",
        f"**{subreddit}** | by u/{author} | {score} pts | {num_comments} comments",
    ]
    if url:
        parts.append(f"**URL:** {url}")
    if selftext:
        parts.append(f"{selftext}")
    parts.append("")
    return "\n".join(parts)


def _fmt_comment(comment: dict, depth: int = 0) -> str:
    """Format a single comment with indentation for depth."""
    d = comment.get("data", comment)
    author = d.get("author", "[deleted]")
    score = _fmt_score(d.get("score"))
    body = d.get("body", "")
    if len(body) > 500:
        body = body[:500] + "..."

    indent = "  " * depth
    parts = [f"{indent}**u/{author}** ({score} pts):", f"{indent}{body}"]

    # Recurse into replies (limited depth)
    replies = d.get("replies")
    if isinstance(replies, dict) and depth < 2:
        children = replies.get("data", {}).get("children", [])
        for child in children[:3]:
            if child.get("kind") == "t1":
                parts.append(_fmt_comment(child, depth + 1))

    return "\n".join(parts)


async def _reddit_get(path: str, params: dict | None = None) -> dict:
    """Make a GET request to Reddit's JSON API."""
    url = f"https://www.reddit.com{path}"
    if not url.endswith(".json"):
        url += ".json"

    headers = {"User-Agent": REDDIT_USER_AGENT}
    try:
        async with make_httpx_client(timeout=15.0, headers=headers) as client:
            response = await client.get(url, params=params, follow_redirects=True)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise ValueError("Reddit rate limit reached. Try again in a moment.")
        raise


async def _search_reddit(query: str, sort: str, time_filter: str, num_results: int) -> str:
    """Search Reddit for posts."""
    data = await _reddit_get("/search.json", params={
        "q": query,
        "sort": sort,
        "t": time_filter,
        "limit": num_results,
        "type": "link",
    })

    posts = data.get("data", {}).get("children", [])
    if not posts:
        return f"No Reddit results for: {query}"

    parts = [f"# Reddit Search: {query}\n"]
    for i, post in enumerate(posts, 1):
        parts.append(_fmt_post(post, i))

    return "\n".join(parts)


async def _browse_subreddit(subreddit: str, sort: str, time_filter: str, num_results: int) -> str:
    """Browse a subreddit's posts."""
    # Strip r/ prefix if provided
    subreddit = subreddit.removeprefix("r/").removeprefix("/r/").strip("/")
    if not subreddit:
        raise ValueError("No subreddit name provided")

    params: dict[str, Any] = {"limit": num_results}
    if sort == "top":
        params["t"] = time_filter

    data = await _reddit_get(f"/r/{quote(subreddit)}/{sort}.json", params=params)

    posts = data.get("data", {}).get("children", [])
    if not posts:
        return f"No posts found in r/{subreddit}"

    parts = [f"# r/{subreddit} — {sort}\n"]
    for i, post in enumerate(posts, 1):
        parts.append(_fmt_post(post, i))

    return "\n".join(parts)


async def _read_post(post_url: str) -> str:
    """Read a specific Reddit post and its top comments."""
    from urllib.parse import urlparse

    parsed = urlparse(post_url)
    path = parsed.path.rstrip("/")

    # Ensure it looks like a Reddit post path
    if not path.startswith("/r/"):
        # Try treating it as a full URL
        if "reddit.com" not in post_url:
            raise ValueError("Please provide a full Reddit post URL or path starting with /r/")

    data = await _reddit_get(path + ".json")

    if not isinstance(data, list) or len(data) < 1:
        return "Failed to parse Reddit post data"

    # First element: post data
    post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
    title = post_data.get("title", "No title")
    author = post_data.get("author", "Unknown")
    subreddit = post_data.get("subreddit_name_prefixed", "")
    score = _fmt_score(post_data.get("score"))
    selftext = post_data.get("selftext", "")
    post_url_display = post_data.get("url", "")
    num_comments = post_data.get("num_comments", 0)

    parts = [
        f"# {title}\n",
        f"**{subreddit}** | by u/{author} | {score} pts | {num_comments} comments",
    ]
    if post_url_display and post_url_display != f"https://www.reddit.com{post_data.get('permalink', '')}":
        parts.append(f"**Link:** {post_url_display}")
    if selftext:
        if len(selftext) > 5000:
            selftext = selftext[:5000] + "\n\n[... post truncated ...]"
        parts.append(f"\n{selftext}")

    # Second element: comments
    if len(data) >= 2:
        comments = data[1].get("data", {}).get("children", [])
        if comments:
            parts.append("\n---\n## Top Comments\n")
            for comment in comments[:10]:
                if comment.get("kind") != "t1":
                    continue
                parts.append(_fmt_comment(comment))
                parts.append("")

    result = "\n".join(parts)
    if len(result) > MAX_CONTENT_CHARS:
        result = result[:MAX_CONTENT_CHARS] + "\n\n[... truncated at 15k chars ...]"
    return result


async def reddit_search(params: dict[str, Any]) -> str:
    """Search Reddit, browse subreddits, or read specific posts.

    Args:
        params: Dictionary with 'query', 'action', 'sort', 'time_filter', 'num_results'.

    Returns:
        Formatted results as markdown.
    """
    query = params.get("query", "")
    action = params.get("action", "search")
    sort = params.get("sort", "relevance" if action == "search" else "hot")
    time_filter = params.get("time_filter", "week")
    num_results = min(params.get("num_results", 5), 15)

    if not query:
        raise ValueError("No query provided")

    try:
        if action == "search":
            return await _search_reddit(query, sort, time_filter, num_results)
        elif action == "subreddit":
            return await _browse_subreddit(query, sort, time_filter, num_results)
        elif action == "post":
            return await _read_post(query)
        else:
            raise ValueError(f"Unknown action: {action}. Use 'search', 'subreddit', or 'post'.")
    except httpx.HTTPError as e:
        return f"Reddit request failed: {e}"
    except ValueError as e:
        return str(e)


REDDIT_SEARCH_TOOL_DEF = {
    "name": "reddit_search",
    "description": (
        "Search Reddit for posts, browse subreddits, or read specific posts and comments. "
        "Use action 'search' to find posts, 'subreddit' to browse a subreddit, "
        "or 'post' to read a specific post with its top comments."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Search query (for search), subreddit name like 'python' (for subreddit), "
                    "or full Reddit post URL (for post)"
                ),
            },
            "action": {
                "type": "string",
                "enum": ["search", "subreddit", "post"],
                "description": "Action to perform: search, subreddit, or post",
                "default": "search",
            },
            "sort": {
                "type": "string",
                "enum": ["relevance", "hot", "top", "new"],
                "description": "Sort order (default: relevance for search, hot for subreddit)",
            },
            "time_filter": {
                "type": "string",
                "enum": ["day", "week", "month", "year", "all"],
                "description": "Time filter for search or subreddit sort=top (default: week)",
                "default": "week",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (max 15, for search/subreddit)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}
