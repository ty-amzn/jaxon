"""Wikipedia tool — article summaries and search via Wikipedia REST & Action APIs."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

REST_API_URL = "https://en.wikipedia.org/api/rest_v1"
ACTION_API_URL = "https://en.wikipedia.org/w/api.php"
_USER_AGENT = "jaxon-assistant/1.0 (https://github.com/ty-amzn/jaxon)"


def _wiki_client() -> httpx.AsyncClient:
    """Create an httpx client with Wikipedia-friendly User-Agent."""
    return make_httpx_client(
        timeout=15.0,
        headers={"User-Agent": _USER_AGENT},
    )


async def wikipedia(params: dict[str, Any]) -> str:
    """Look up or search Wikipedia articles.

    Args:
        params: Dictionary with 'action' ("summary"|"search"), 'query' (str),
                and optional 'max_results' (int, search only).

    Returns:
        Formatted article summary or search results as markdown.
    """
    action = params.get("action", "summary")
    query = (params.get("query") or "").strip()
    if not query:
        raise ValueError("No query provided")

    if action == "search":
        return await _search(query, min(params.get("max_results", 5), 10))
    return await _summary(query)


async def _summary(title: str) -> str:
    """Fetch a Wikipedia article summary via the REST API."""
    try:
        async with _wiki_client() as client:
            resp = await client.get(
                f"{REST_API_URL}/page/summary/{httpx.URL(title)}",
                headers={"Accept": "application/json"},
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return await _search_and_summarize(title)
        return f"Wikipedia API error: {e}"
    except httpx.HTTPError as e:
        return f"Wikipedia API error: {e}"

    page_title = data.get("title", title)
    extract = data.get("extract", "No summary available.")
    url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
    description = data.get("description", "")

    lines = [f"# {page_title}"]
    if description:
        lines.append(f"*{description}*")
    lines += ["", extract]
    if url:
        lines += ["", f"**Read more:** {url}"]
    return "\n".join(lines)


async def _search_and_summarize(title: str) -> str:
    """If a direct summary lookup 404s, search and summarize the top result."""
    results = await _search(title, 1)
    if results.startswith("No Wikipedia results"):
        return f"No Wikipedia article found for: {title}"
    # _search returns markdown — extract the first result title and fetch summary
    # Parse the first result from the search response
    try:
        async with _wiki_client() as client:
            resp = await client.get(
                ACTION_API_URL,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": title,
                    "srlimit": 1,
                    "format": "json",
                    "formatversion": 2,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("query", {}).get("search", [])
            if hits:
                return await _summary(hits[0]["title"])
    except httpx.HTTPError:
        pass
    return f"No Wikipedia article found for: {title}"


async def _search(query: str, max_results: int) -> str:
    """Search Wikipedia via the Action API."""
    try:
        async with _wiki_client() as client:
            resp = await client.get(
                ACTION_API_URL,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": max_results,
                    "format": "json",
                    "formatversion": 2,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        return f"Wikipedia search failed: {e}"

    hits = data.get("query", {}).get("search", [])
    if not hits:
        return f"No Wikipedia results for: {query}"

    lines = [f"# Wikipedia Results for: {query}\n"]
    for i, hit in enumerate(hits, 1):
        title = hit.get("title", "Untitled")
        snippet = hit.get("snippet", "").replace('<span class="searchmatch">', "**").replace("</span>", "**")
        url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        lines.append(f"## {i}. {title}")
        lines.append(f"{snippet}")
        lines.append(f"**Link:** {url}\n")

    return "\n".join(lines)


WIKIPEDIA_TOOL_DEF = {
    "name": "wikipedia",
    "description": (
        "Look up Wikipedia articles or search for topics. Use 'summary' to get "
        "a concise article summary (faster and cleaner than web_fetch for factual "
        "lookups), or 'search' to find relevant articles. Prefer this over "
        "web_search + web_fetch when the user asks about a specific topic, person, "
        "place, event, or concept that likely has a Wikipedia article."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["summary", "search"],
                "description": "Action: 'summary' to get an article summary by title, 'search' to find articles matching a query.",
                "default": "summary",
            },
            "query": {
                "type": "string",
                "description": (
                    "Article title (for summary) or search query (for search). "
                    "For summary, use the canonical article title when known "
                    "(e.g. 'Python (programming language)', 'Newton, Massachusetts')."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum search results to return (max 10, default 5). Only used with 'search' action.",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}
