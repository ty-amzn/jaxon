"""Slack bot using slack-bolt with Socket Mode (WebSocket, no public URL needed)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface
    from assistant.scheduler.manager import SchedulerManager
    from assistant.slack.permissions import SlackApprovalCallback
    from assistant.watchdog_monitor.monitor import FileMonitor

logger = logging.getLogger(__name__)


class SlackBot:
    """Wraps slack-bolt AsyncApp for assistant integration via Socket Mode."""

    def __init__(
        self,
        bot_token: str,
        app_token: str,
        chat_interface: ChatInterface,
        allowed_user_ids: list[str] | None = None,
        allowed_channel_ids: list[str] | None = None,
        scheduler_manager: Any = None,
        file_monitor: Any = None,
    ) -> None:
        self.chat_interface = chat_interface
        self.allowed_user_ids = set(allowed_user_ids) if allowed_user_ids else set()
        self.allowed_channel_ids = set(allowed_channel_ids) if allowed_channel_ids else set()
        self.scheduler_manager: SchedulerManager | None = scheduler_manager
        self.file_monitor: FileMonitor | None = file_monitor
        self._approval_callbacks: dict[str, SlackApprovalCallback] = {}

        self._app = AsyncApp(token=bot_token)
        self._socket_handler = AsyncSocketModeHandler(self._app, app_token)

        # Register handlers
        from assistant.slack.handlers import register_handlers

        register_handlers(self)

    async def start(self) -> None:
        """Start the bot via Socket Mode."""
        logger.info("Starting Slack bot in Socket Mode")
        await self._socket_handler.start_async()

    async def stop(self) -> None:
        """Stop the bot."""
        await self._socket_handler.close_async()

    async def send_message(self, channel: str, text: str) -> None:
        """Send a message to a channel (used by notifications and delivery callbacks)."""
        try:
            if len(text) > 4000:
                for i in range(0, len(text), 4000):
                    await self._app.client.chat_postMessage(
                        channel=channel, text=text[i : i + 4000]
                    )
            else:
                await self._app.client.chat_postMessage(channel=channel, text=text)
        except Exception:
            logger.exception("Failed to send Slack message to %s", channel)
