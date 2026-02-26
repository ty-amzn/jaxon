"""Slack-based permission approval via Block Kit interactive messages."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from assistant.gateway.permissions import PermissionRequest

if TYPE_CHECKING:
    from slack_sdk.web.async_client import AsyncWebClient

logger = logging.getLogger(__name__)

APPROVAL_TIMEOUT = 600  # seconds (10 minutes)
DETAIL_TRUNCATE_LIMIT = 500


def _format_details(request: PermissionRequest) -> tuple[str, str | None]:
    """Format request details into display text and optional full text.

    Returns (display_text, full_text_or_none). If the full text fits within
    the truncation limit, full_text_or_none is None (no expand needed).
    """
    lines: list[str] = []
    for key, value in request.details.items():
        lines.append(f"{key}: {value}")
    full_text = "\n".join(lines) if lines else request.description

    if len(full_text) <= DETAIL_TRUNCATE_LIMIT:
        return full_text, None
    return full_text[:DETAIL_TRUNCATE_LIMIT] + "…", full_text


class SlackApprovalCallback:
    """Sends Block Kit interactive message for tool approval, waits for button press."""

    def __init__(self, client: AsyncWebClient, channel_id: str) -> None:
        self._client = client
        self._channel_id = channel_id
        self._pending: dict[str, asyncio.Future[bool]] = {}
        self._full_details: dict[str, str] = {}

    async def __call__(self, request: PermissionRequest) -> bool:
        request_id = f"perm_{id(request)}"
        future: asyncio.Future[bool] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        display_text, full_text = _format_details(request)

        blocks: list[dict[str, Any]] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔧 {request.tool_name}* [{request.action_category.value}]\n\n{display_text}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "action_id": f"approve:{request_id}",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Deny"},
                        "style": "danger",
                        "action_id": f"deny:{request_id}",
                    },
                ],
            },
        ]

        if full_text is not None:
            self._full_details[request_id] = full_text
            blocks[1]["elements"].append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Show Full"},
                    "action_id": f"show_full:{request_id}",
                }
            )

        await self._client.chat_postMessage(
            channel=self._channel_id,
            text=f"🔧 {request.tool_name} [{request.action_category.value}] — Approve or Deny?",
            blocks=blocks,
        )

        try:
            return await asyncio.wait_for(future, timeout=APPROVAL_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning("Permission request timed out for %s", request.description)
            return False
        finally:
            self._pending.pop(request_id, None)
            self._full_details.pop(request_id, None)

    def resolve(self, request_id: str, approved: bool) -> None:
        """Called by action handler to resolve a pending approval."""
        future = self._pending.get(request_id)
        if future and not future.done():
            future.set_result(approved)

    def get_full_details(self, request_id: str) -> str | None:
        """Return stored full details for a request, if any."""
        return self._full_details.get(request_id)
