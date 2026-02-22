"""Telegram bot using python-telegram-bot v21 async API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from telegram.ext import Application

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface
    from assistant.scheduler.manager import SchedulerManager
    from assistant.telegram.permissions import TelegramApprovalCallback
    from assistant.watchdog_monitor.monitor import FileMonitor

logger = logging.getLogger(__name__)


class TelegramBot:
    """Wraps python-telegram-bot Application for assistant integration."""

    def __init__(
        self,
        token: str,
        chat_interface: ChatInterface,
        allowed_user_ids: list[int] | None = None,
        webhook_url: str = "",
        scheduler_manager: Any = None,
        file_monitor: Any = None,
    ) -> None:
        self.chat_interface = chat_interface
        self.allowed_user_ids = set(allowed_user_ids) if allowed_user_ids else set()
        self.scheduler_manager: SchedulerManager | None = scheduler_manager
        self.file_monitor: FileMonitor | None = file_monitor
        self._webhook_url = webhook_url
        self._approval_callbacks: dict[str, TelegramApprovalCallback] = {}

        self.application: Application = (
            Application.builder().token(token).concurrent_updates(True).build()
        )

        # Register handlers
        from assistant.telegram.handlers import register_handlers
        register_handlers(self)

    async def start(self) -> None:
        """Start the bot (polling or webhook)."""
        await self.application.initialize()
        await self.application.start()

        if self._webhook_url:
            logger.info("Starting Telegram bot in webhook mode: %s", self._webhook_url)
            await self.application.bot.set_webhook(self._webhook_url)
        else:
            logger.info("Starting Telegram bot in polling mode")
            await self.application.updater.start_polling()

    async def stop(self) -> None:
        """Stop the bot."""
        if self.application.updater and self.application.updater.running:
            await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    async def send_message(self, chat_id: int | str, text: str) -> None:
        """Send a proactive message to a chat (used by scheduler/watchdog notifications)."""
        try:
            if len(text) > 4000:
                for i in range(0, len(text), 4000):
                    await self.application.bot.send_message(
                        chat_id=chat_id, text=text[i:i + 4000]
                    )
            else:
                await self.application.bot.send_message(chat_id=chat_id, text=text)
        except Exception:
            logger.exception("Failed to send Telegram message to %s", chat_id)
