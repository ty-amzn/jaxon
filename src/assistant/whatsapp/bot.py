"""WhatsApp bot using neonize async API (linked-device QR code pairing)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from neonize.aioze.client import NewAClient
from neonize.aioze.events import ConnectedEv, MessageEv
from neonize.utils import build_jid

from assistant.whatsapp.handlers import handle_message

if TYPE_CHECKING:
    from assistant.cli.chat import ChatInterface

logger = logging.getLogger(__name__)

CHUNK_SIZE = 4000


class WhatsAppBot:
    """Wraps neonize NewAClient for assistant integration."""

    def __init__(
        self,
        chat_interface: ChatInterface,
        allowed_numbers: list[str] | None = None,
        session_name: str = "assistant",
        auth_dir: Path | None = None,
    ) -> None:
        self.chat_interface = chat_interface
        self.allowed_numbers = set(allowed_numbers) if allowed_numbers else set()

        # neonize stores auth state in a sqlite file
        auth_path = auth_dir or Path(".")
        auth_path.mkdir(parents=True, exist_ok=True)
        db_path = str(auth_path / f"{session_name}.sqlite3")

        self._client = NewAClient(db_path)
        self._idle_task: asyncio.Task | None = None

        # Register event handlers
        @self._client.event(ConnectedEv)
        async def on_connected(_client: NewAClient, _event: ConnectedEv) -> None:
            logger.info("WhatsApp bot connected")

        @self._client.event(MessageEv)
        async def on_message(client: NewAClient, event: MessageEv) -> None:
            await handle_message(self, client, event)

    async def start(self) -> None:
        """Connect the client (displays QR code in terminal for pairing)."""
        logger.info("Starting WhatsApp bot (scan QR code to link device)")
        await self._client.connect()
        self._idle_task = asyncio.create_task(self._client.idle())

    async def stop(self) -> None:
        """Disconnect the client."""
        try:
            await self._client.stop()
        except Exception:
            logger.exception("Error stopping WhatsApp client")
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
            try:
                await self._idle_task
            except asyncio.CancelledError:
                pass
        logger.info("WhatsApp bot stopped")

    async def send_message(self, number: str, text: str) -> None:
        """Send a text message to a phone number (E.164 format, e.g. +15551234567).

        Long messages are split into chunks of ~4000 characters.
        """
        # Strip the leading + for build_jid (expects digits only)
        digits = number.lstrip("+")
        jid = build_jid(digits)
        try:
            if len(text) > CHUNK_SIZE:
                for i in range(0, len(text), CHUNK_SIZE):
                    await self._client.send_message(jid, text[i : i + CHUNK_SIZE])
            else:
                await self._client.send_message(jid, text)
        except Exception:
            logger.exception("Failed to send WhatsApp message to %s", number)
