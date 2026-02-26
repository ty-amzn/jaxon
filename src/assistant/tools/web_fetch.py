"""Web fetch tool — fetch URL and extract readable content via trafilatura."""

from __future__ import annotations

import logging
from typing import Any

import trafilatura

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 15_000


async def web_fetch(params: dict[str, Any]) -> str:
    """Fetch a URL and extract its main content as markdown.

    Args:
        params: Dictionary containing 'url' and optional 'include_links'.

    Returns:
        Extracted content as markdown text.
    """
    url = params.get("url", "")
    include_links = params.get("include_links", False)

    if not url:
        return "Error: 'url' parameter is required. Usage: web_fetch(url=\"https://example.com\")"

    try:
        async with make_httpx_client(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (403, 406):
            return (
                f"Fetch failed ({status}): site blocked the request (bot protection). "
                "Retry using the browse_web tool instead, which uses a real browser."
            )
        return f"Fetch failed: {e}"

    # Extract main content with trafilatura
    extracted = trafilatura.extract(
        html,
        include_links=include_links,
        output_format="txt",
        favor_precision=False,
        favor_recall=True,
    )

    if extracted:
        content = extracted
    else:
        # Fallback: return truncated raw HTML
        logger.warning("trafilatura extraction failed for %s, using raw HTML", url)
        content = html

    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS] + f"\n\n... (truncated, {len(content)} total chars)"

    return f"# Content from {url}\n\n{content}"


WEB_FETCH_TOOL_DEF = {
    "name": "web_fetch",
    "description": (
        "Fetch a webpage URL and extract its main readable content as text. "
        "Use this to read articles, documentation, and other web pages. "
        "For raw HTTP requests, use http_request instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch and extract content from",
            },
            "include_links": {
                "type": "boolean",
                "description": "Include hyperlinks in the extracted text",
                "default": False,
            },
        },
        "required": ["url"],
    },
}
