"""Slack event and action handlers."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from assistant.gateway.permissions import PermissionManager, parse_approval_required

if TYPE_CHECKING:
    from assistant.slack.bot import SlackBot

logger = logging.getLogger(__name__)


def register_handlers(bot: SlackBot) -> None:
    """Register all handlers on the bot's Slack app."""

    @bot._app.event("message")
    async def handle_message(event: dict, say: object) -> None:
        # Skip bot messages, message_changed, message_deleted, etc.
        subtype = event.get("subtype")
        if subtype is not None:
            return

        user_id = event.get("user", "")
        channel_id = event.get("channel", "")
        text = event.get("text", "").strip()

        if not text or not user_id:
            return

        if not _check_allowed(bot, user_id, channel_id):
            await bot._app.client.chat_postMessage(
                channel=channel_id, text="Not authorized."
            )
            return

        session_key = f"slack_{channel_id}"

        # Get or create approval callback for this channel
        if session_key not in bot._approval_callbacks:
            from assistant.slack.permissions import SlackApprovalCallback

            bot._approval_callbacks[session_key] = SlackApprovalCallback(
                bot._app.client, channel_id
            )
        approval_cb = bot._approval_callbacks[session_key]
        approval_tools = parse_approval_required(
            bot.chat_interface._settings.approval_required_tools
        )
        permission_manager = PermissionManager(
            approval_cb, approval_required_tools=approval_tools
        )

        # Create delivery callback for background tasks
        async def _slack_deliver(msg: str) -> None:
            await bot.send_message(channel_id, msg)

        try:
            response = await bot.chat_interface.get_response(
                session_key,
                text,
                permission_manager=permission_manager,
                delivery_callback=_slack_deliver,
            )
            if response:
                await bot.send_message(channel_id, response)
            else:
                await bot._app.client.chat_postMessage(
                    channel=channel_id,
                    text="Sorry, I got an empty response. Please try again.",
                )
        except Exception:
            logger.exception("Error processing Slack message")
            await bot._app.client.chat_postMessage(
                channel=channel_id, text="Sorry, an error occurred."
            )

    @bot._app.action(re.compile(r"^(approve|deny|show_full):"))
    async def handle_action(ack: object, body: dict) -> None:
        await ack()  # type: ignore[operator]

        action = body.get("actions", [{}])[0]
        action_id = action.get("action_id", "")
        parts = action_id.split(":", 1)
        if len(parts) != 2:
            return

        action_type, request_id = parts
        channel_id = body.get("channel", {}).get("id", "")

        # Find the approval callback for this channel
        session_key = f"slack_{channel_id}"
        approval_cb = bot._approval_callbacks.get(session_key)

        if action_type == "show_full":
            if approval_cb:
                full_text = approval_cb.get_full_details(request_id)
                if full_text and channel_id:
                    await bot.send_message(channel_id, full_text)
            return

        approved = action_type == "approve"

        if approval_cb:
            approval_cb.resolve(request_id, approved)

        # Update the original message to show the decision
        status = "✅ Approved" if approved else "❌ Denied"
        original_text = body.get("message", {}).get("text", "")
        try:
            await bot._app.client.chat_update(
                channel=channel_id,
                ts=body.get("message", {}).get("ts", ""),
                text=f"{original_text}\n\n{status}",
                blocks=[],  # Remove buttons
            )
        except Exception:
            logger.debug("Could not update approval message", exc_info=True)


def _check_allowed(bot: SlackBot, user_id: str, channel_id: str) -> bool:
    """Check both user and channel whitelists. Empty list = allow all."""
    if bot.allowed_user_ids and user_id not in bot.allowed_user_ids:
        return False
    if bot.allowed_channel_ids and channel_id not in bot.allowed_channel_ids:
        return False
    return True
