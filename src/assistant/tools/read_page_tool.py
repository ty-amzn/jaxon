"""Tool for reading paginated tool output pages."""

from __future__ import annotations

from typing import Any

from assistant.tools.page_cache import get_page_cache

READ_OUTPUT_PAGE_DEF: dict[str, Any] = {
    "name": "read_output_page",
    "description": (
        "Read, clear, or clear all paginated tool outputs. "
        "When a tool result is too large it is automatically split into pages "
        "and you receive page 1 with a page_id. Use this tool to read subsequent pages. "
        "After you are done reading, use action='clear' to free the memory."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "clear", "clear_all"],
                "description": "Action to perform. 'read' (default) reads a page, 'clear' removes one entry by page_id, 'clear_all' removes all cached pages.",
            },
            "page_id": {
                "type": "string",
                "description": "The page_id returned in the paginated output header. Required for 'read' and 'clear'.",
            },
            "page": {
                "type": "integer",
                "description": "Page number to read (1-based). Only used with action='read'.",
            },
        },
        "required": [],
    },
}


async def read_output_page(params: dict[str, Any]) -> str:
    """Handler for the read_output_page tool."""
    action = params.get("action", "read")
    page_id = params.get("page_id", "")
    cache = get_page_cache()

    if action == "clear_all":
        count = cache.clear_all()
        return f"Cleared {count} cached page(s)."

    if action == "clear":
        if not page_id:
            return "Error: page_id is required for 'clear'."
        if cache.clear(page_id):
            return f"Cleared page_id={page_id!r}."
        return f"page_id={page_id!r} not found (already cleared or expired)."

    # Default: read
    page = params.get("page", 1)
    if not page_id:
        return "Error: page_id is required."

    result = cache.get_page(page_id, page)
    if result is None:
        return f"Error: page not found (page_id={page_id!r}, page={page}). It may have expired or the page number is out of range."

    page_text, total_pages = result
    header = f"[Page {page}/{total_pages}]"
    if page < total_pages:
        header += f" — use read_output_page(page_id={page_id!r}, page={page + 1}) for next page"
    else:
        header += f" — last page. Use read_output_page(action='clear', page_id={page_id!r}) to free memory"
    return f"{header}\n{page_text}"
