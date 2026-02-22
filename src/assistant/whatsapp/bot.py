"""WhatsApp bot using neonize async API (linked-device QR code pairing)."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Patch neonize's internal event loop to use the caller's running loop.
# neonize creates its own loop (asyncio.new_event_loop()) at import time and
# schedules all Go→Python callbacks on it.  Inside uvicorn this loop is never
# run, so events never fire.  We patch it lazily in start().
#
# IMPORTANT: both modules must be patched because client.py does
# `from .events import event_global_loop` which creates a separate binding.
import neonize.aioze.client as _neonize_client
import neonize.aioze.events as _neonize_events

from neonize.aioze.client import NewAClient
from neonize.aioze.events import ConnectedEv, MessageEv
from neonize.utils import build_jid

from assistant.whatsapp.handlers import handle_message
from assistant.whatsapp.permissions import WhatsAppApprovalCallback

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

        # Per-number approval callbacks for permission prompts
        self._approval_callbacks: dict[str, WhatsAppApprovalCallback] = {}

        # neonize stores auth state in a sqlite file
        auth_path = auth_dir or Path(".")
        auth_path.mkdir(parents=True, exist_ok=True)
        self._db_path = str(auth_path / f"{session_name}.sqlite3")

        # Client is created lazily in start() after patching the event loop
        self._client: NewAClient | None = None
        self._idle_task: asyncio.Task | None = None

    def _setup_client(self) -> None:
        """Create the neonize client and register event handlers.

        Must be called after patching the event loop in start().
        """
        self._client = NewAClient(self._db_path)

        # Register QR code handler — force output to stdout for Docker logs
        @self._client.event.qr
        async def on_qr(_client: NewAClient, data: bytes) -> None:
            try:
                import segno
                print("\n=== WhatsApp QR Code — scan with WhatsApp > Linked Devices ===", flush=True)
                segno.make_qr(data).terminal(compact=True, out=sys.stdout)
                sys.stdout.flush()
            except Exception:
                logger.info("WhatsApp QR data (paste into a QR generator): %s", data.decode(errors="replace"))

        @self._client.event(ConnectedEv)
        async def on_connected(_client: NewAClient, _event: ConnectedEv) -> None:
            logger.info("WhatsApp bot connected")

        @self._client.event(MessageEv)
        async def on_message(client: NewAClient, event: MessageEv) -> None:
            await handle_message(self, client, event)

    async def start(self) -> None:
        """Connect the client (displays QR code in terminal for pairing)."""
        # Patch neonize's internal event loop to the currently running one.
        # Both neonize.aioze.events AND neonize.aioze.client hold their own
        # binding of event_global_loop (due to `from .events import ...`).
        running_loop = asyncio.get_running_loop()
        _neonize_events.event_global_loop = running_loop
        _neonize_client.event_global_loop = running_loop

        self._setup_client()
        assert self._client is not None
        self._client.loop = running_loop

        logger.info("Starting WhatsApp bot (scan QR code to link device)")
        await self._client.connect()
        self._idle_task = asyncio.create_task(self._client.idle())

    async def stop(self) -> None:
        """Disconnect the client."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                logger.exception("Error stopping WhatsApp client")
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
            try:
                await self._idle_task
            except asyncio.CancelledError:
                pass
        logger.info("WhatsApp bot stopped")

    def get_approval_callback(self, sender_number: str) -> WhatsAppApprovalCallback:
        """Get or create an approval callback for a sender."""
        if sender_number not in self._approval_callbacks:
            self._approval_callbacks[sender_number] = WhatsAppApprovalCallback(self, sender_number)
        return self._approval_callbacks[sender_number]

    async def send_message(self, number: str, text: str) -> None:
        """Send a text message to a phone number (E.164 format, e.g. +15551234567).

        Long messages are split into chunks of ~4000 characters.
        """
        if not self._client:
            logger.error("WhatsApp client not started")
            return
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
