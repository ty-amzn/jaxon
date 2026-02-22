"""Web search tool via SearXNG."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default SearXNG URL - can be overridden via config
DEFAULT_SEARXNG_URL = "http://localhost:8888"


async def web_search(params: dict[str, Any], searxng_url: str = DEFAULT_SEARXNG_URL) -> str:
    """Search the web using SearXNG.

    Args:
        params: Dictionary containing 'query' and optional 'num_results'
        searxng_url: Base URL of the SearXNG instance

    Returns:
        Formatted search results as markdown
    """
    query = params.get("query", "")
    num_results = min(params.get("num_results", 5), 10)  # Max 10 results

    if not query:
        raise ValueError("No search query provided")

    # Build SearXNG API URL
    search_url = f"{searxng_url.rstrip('/')}/search"

    params_dict = {
        "q": query,
        "format": "json",
        "engines": "google,bing,duckduckgo",  # Can be customized
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(search_url, params=params_dict)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        return f"Search failed: {e}"
    except Exception as e:
        return f"Search error: {e}"

    results = data.get("results", [])

    if not results:
        return f"No results found for: {query}"

    # Format results as markdown
    output_parts = [f"# Search Results for: {query}\n"]
    output_parts.append(f"Found {len(results)} results (showing top {num_results})\n")

    for i, result in enumerate(results[:num_results], 1):
        title = result.get("title", "No title")
        url = result.get("url", result.get("link", ""))
        snippet = result.get("content", result.get("snippet", "No description"))

        output_parts.append(f"## {i}. {title}")
        output_parts.append(f"**URL:** {url}")
        output_parts.append(f"{snippet}\n")

    return "\n".join(output_parts)


WEB_SEARCH_TOOL_DEF = {
    "name": "web_search",
    "description": "Search the web for information using SearXNG. Returns formatted search results with titles, URLs, and snippets.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (max 10)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}