"""HTTP request tool via httpx."""

from __future__ import annotations

from typing import Any

import httpx

from assistant.core.http import make_httpx_client


async def http_request(params: dict[str, Any]) -> str:
    """Make an HTTP request."""
    method = params.get("method", "GET").upper()
    url = params.get("url", "")
    headers = params.get("headers", {})
    body = params.get("body")
    timeout = min(params.get("timeout", 30), 60)

    if not url:
        raise ValueError("No URL provided")

    async with make_httpx_client(timeout=timeout) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            content=body if isinstance(body, str) else None,
            json=body if isinstance(body, dict) else None,
        )

    result_parts = [
        f"status: {response.status_code}",
        f"headers: {dict(response.headers)}",
    ]

    text = response.text
    if len(text) > 10_000:
        text = text[:10_000] + f"... (truncated, {len(response.text)} total)"
    result_parts.append(f"body:\n{text}")

    return "\n".join(result_parts)


HTTP_TOOL_DEF = {
    "name": "http_request",
    "description": "Make an HTTP request to a URL.",
    "input_schema": {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "description": "HTTP method",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "default": "GET",
            },
            "url": {"type": "string", "minLength": 1, "description": "URL to request"},
            "headers": {
                "type": "object",
                "description": "Request headers",
                "default": {},
            },
            "body": {
                "description": "Request body (string or JSON object)",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (max 60)",
                "default": 30,
            },
        },
        "required": ["url"],
    },
}
