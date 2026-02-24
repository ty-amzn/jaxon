"""Email notification tool via IFTTT webhook."""

from __future__ import annotations

from typing import Any

import httpx

from assistant.core.http import make_httpx_client


IFTTT_WEBHOOK_URL = (
    "https://maker.ifttt.com/trigger/assistant_notification/json/with/key/bQLotUGi7K2lBB4Z7hA2Yy"
)

SEND_EMAIL_DEF: dict[str, Any] = {
    "name": "send_email",
    "description": (
        "Send an email notification via IFTTT.\n"
        "Use this to deliver information, reports, summaries, or alerts to the user's inbox.\n"
        "The message field must be HTML content — use <p>, <ul>, <ol>, <li>, <b>, <i>, <a>, "
        "<br>, <table>, <tr>, <td>, <th>, <blockquote>, <pre>, <code> tags for formatting.\n"
        "Do NOT use markdown headers (# or ##) — they will not render in email.\n"
        "Use <h3> or <b> tags instead for section headings."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Email subject line. Keep it concise and descriptive.",
            },
            "message": {
                "type": "string",
                "description": (
                    "Email body as HTML content. Use HTML tags for formatting: "
                    "<p>, <b>, <i>, <ul>, <li>, <a href=''>, <br>, <table>, <pre>, <code>. "
                    "No markdown. No # headers."
                ),
            },
        },
        "required": ["title", "message"],
    },
}


async def send_email(params: dict[str, Any]) -> str:
    """Send an email via IFTTT webhook."""
    title = params.get("title", "")
    message = params.get("message", "")

    if not title:
        return "Error: title is required."
    if not message:
        return "Error: message is required."

    payload = {"title": title, "message": message}

    async with make_httpx_client(timeout=15) as client:
        response = await client.post(
            IFTTT_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    if response.status_code == 200:
        return f"Email sent successfully: \"{title}\""
    else:
        return f"Email delivery failed (HTTP {response.status_code}): {response.text}"
