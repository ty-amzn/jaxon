"""WhatsApp message handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from neonize.aioze.client import NewAClient
from neonize.aioze.events import MessageEv

from assistant.gateway.permissions import PermissionManager, parse_approval_required

if TYPE_CHECKING:
    from assistant.whatsapp.bot import WhatsAppBot

logger = logging.getLogger(__name__)


def _extract_sender_number(event: MessageEv) -> str:
    """Extract the sender's phone number from a message event.

    Returns the raw JID user part (digits only, no '+' prefix).
    """
    sender = event.Info.MessageSource.Sender
    # JID user part is the phone number (digits)
    return sender.User


def _extract_text(event: MessageEv) -> str | None:
    """Extract text content from a message event."""
    msg = event.Message
    # Regular text messages use .conversation, quoted replies use .extendedTextMessage.text
    text = msg.conversation or (msg.extendedTextMessage.text if msg.extendedTextMessage else "")
    return text.strip() if text else None


def _is_from_me(event: MessageEv) -> bool:
    """Check if the message was sent by us (to avoid echo loops)."""
    return event.Info.MessageSource.IsFromMe


def _check_allowed(bot: WhatsAppBot, sender_number: str) -> bool:
    """Check if a sender is in the allowlist. Empty list = allow all."""
    if not bot.allowed_numbers:
        return True
    # Match with or without '+' prefix
    return (
        sender_number in bot.allowed_numbers
        or f"+{sender_number}" in bot.allowed_numbers
    )


async def handle_message(
    bot: WhatsAppBot,
    client: NewAClient,
    event: MessageEv,
) -> None:
    """Process an incoming WhatsApp message."""
    # Skip our own messages
    if _is_from_me(event):
        return

    sender_number = _extract_sender_number(event)
    text = _extract_text(event)

    if not text:
        return

    if not _check_allowed(bot, sender_number):
        logger.warning("Unauthorized WhatsApp message from %s", sender_number)
        return

    # Check if this message is an approval reply to a pending permission prompt
    approval_cb = bot.get_approval_callback(sender_number)
    if approval_cb.try_resolve(text):
        logger.info("WhatsApp approval reply from %s: %s", sender_number, text)
        return

    # Use the sender number as the session key (with + prefix for consistency)
    session_key = f"whatsapp_{sender_number}"

    # Create a PermissionManager with the WhatsApp approval callback for this sender
    approval_tools = parse_approval_required(bot.chat_interface._settings.approval_required_tools)
    wa_permission_manager = PermissionManager(approval_cb, approval_required_tools=approval_tools)

    # Create delivery callback for background tasks
    async def _wa_deliver(msg: str) -> None:
        await bot.send_message(f"+{sender_number}", msg)

    try:
        response = await bot.chat_interface.get_response(
            session_key, text,
            permission_manager=wa_permission_manager,
            delivery_callback=_wa_deliver,
        )
        if response:
            await bot.send_message(f"+{sender_number}", response)
    except Exception:
        logger.exception("Error processing WhatsApp message from %s", sender_number)
        try:
            await bot.send_message(f"+{sender_number}", "Sorry, an error occurred.")
        except Exception:
            logger.exception("Failed to send error reply to %s", sender_number)
