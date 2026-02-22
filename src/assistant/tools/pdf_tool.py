"""PDF read tool — fetch PDF from URL and extract text via pymupdf."""

from __future__ import annotations

import logging
from typing import Any

import httpx
import pymupdf

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 15_000


def _parse_page_range(pages: str, total: int) -> list[int]:
    """Parse a page range string like '1-5' or '3' into 0-based page indices."""
    result: list[int] = []
    for part in pages.split(","):
        part = part.strip()
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = max(int(start_s) - 1, 0)
            end = min(int(end_s), total)
            result.extend(range(start, end))
        else:
            idx = int(part) - 1
            if 0 <= idx < total:
                result.append(idx)
    return sorted(set(result))


async def pdf_read(params: dict[str, Any]) -> str:
    """Fetch a PDF from a URL and extract its text.

    Args:
        params: Dictionary containing 'url' and optional 'pages'.

    Returns:
        Extracted text from the PDF.
    """
    url = params.get("url", "")
    pages_param = params.get("pages")

    if not url:
        raise ValueError("No URL provided")

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            pdf_bytes = response.content
    except httpx.HTTPError as e:
        return f"PDF fetch failed: {e}"

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        return f"PDF parse failed: {e}"

    total_pages = len(doc)

    if pages_param:
        page_indices = _parse_page_range(pages_param, total_pages)
    else:
        page_indices = list(range(total_pages))

    text_parts: list[str] = []
    for i in page_indices:
        page = doc[i]
        text = page.get_text()
        if text.strip():
            text_parts.append(f"--- Page {i + 1} ---\n{text}")

    doc.close()

    if not text_parts:
        return f"No text extracted from PDF ({total_pages} pages)."

    content = "\n\n".join(text_parts)
    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS] + f"\n\n... (truncated, {len(content)} total chars)"

    return f"# PDF: {url} ({total_pages} pages)\n\n{content}"


PDF_READ_TOOL_DEF = {
    "name": "pdf_read",
    "description": (
        "Fetch a PDF from a URL and extract its text content. "
        "Supports optional page range selection (e.g. '1-5' or '3,7,10')."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL of the PDF to fetch and read",
            },
            "pages": {
                "type": "string",
                "description": "Page range to extract, e.g. '1-5' or '3,7,10'. Omit for all pages.",
            },
        },
        "required": ["url"],
    },
}
