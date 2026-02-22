"""Telegram-based permission approval via inline keyboard."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from assistant.gateway.permissions import PermissionRequest

if TYPE_CHECKING:
    from telegram import Bot

logger = logging.getLogger(__name__)

APPROVAL_TIMEOUT = 30  # seconds


class TelegramApprovalCallback:
    """Sends inline keyboard for tool approval, waits for button press."""

    def __init__(self, bot: Bot, chat_id: int) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._pending: dict[str, asyncio.Future[bool]] = {}

    async def __call__(self, request: PermissionRequest) -> bool:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        request_id = f"perm_{id(request)}"
        future: asyncio.Future[bool] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Approve", callback_data=f"approve:{request_id}"),
                InlineKeyboardButton("Deny", callback_data=f"deny:{request_id}"),
            ]
        ])

        await self._bot.send_message(
            chat_id=self._chat_id,
            text=f"Permission request [{request.action_category.value}]:\n{request.description}",
            reply_markup=keyboard,
        )

        try:
            return await asyncio.wait_for(future, timeout=APPROVAL_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning("Permission request timed out for %s", request.description)
            return False
        finally:
            self._pending.pop(request_id, None)

    def resolve(self, request_id: str, approved: bool) -> None:
        """Called by callback query handler to resolve a pending approval."""
        future = self._pending.get(request_id)
        if future and not future.done():
            future.set_result(approved)
