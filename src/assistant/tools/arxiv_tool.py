"""arXiv search tool — query arXiv API and parse Atom results."""

from __future__ import annotations

import logging
from typing import Any

import feedparser
import httpx

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"


async def arxiv_search(params: dict[str, Any]) -> str:
    """Search arXiv for papers matching a query.

    Args:
        params: Dictionary containing 'query' and optional 'max_results'.

    Returns:
        Formatted list of matching papers.
    """
    query = params.get("query", "")
    max_results = min(params.get("max_results", 5), 10)

    if not query:
        raise ValueError("No search query provided")

    api_params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        async with make_httpx_client(timeout=30.0) as client:
            response = await client.get(ARXIV_API_URL, params=api_params)
            response.raise_for_status()
            xml_text = response.text
    except httpx.HTTPError as e:
        return f"arXiv search failed: {e}"

    feed = feedparser.parse(xml_text)
    entries = feed.entries

    if not entries:
        return f"No arXiv results for: {query}"

    parts = [f"# arXiv Results for: {query}\n"]

    for i, entry in enumerate(entries, 1):
        title = entry.get("title", "No title").replace("\n", " ").strip()
        authors = ", ".join(a.get("name", "") for a in entry.get("authors", []))
        published = entry.get("published", "Unknown date")[:10]
        abstract = entry.get("summary", "No abstract").replace("\n", " ").strip()
        link = entry.get("link", "")

        # Truncate long abstracts
        if len(abstract) > 500:
            abstract = abstract[:500] + "..."

        parts.append(f"## {i}. {title}")
        parts.append(f"**Authors:** {authors}")
        parts.append(f"**Published:** {published}")
        parts.append(f"**Link:** {link}")
        parts.append(f"{abstract}\n")

    return "\n".join(parts)


ARXIV_SEARCH_TOOL_DEF = {
    "name": "arxiv_search",
    "description": (
        "Search arXiv for academic papers. Returns titles, authors, abstracts, "
        "links, and publication dates for matching papers."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "minLength": 1,
                "description": "Search query for arXiv papers",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (max 10)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}
