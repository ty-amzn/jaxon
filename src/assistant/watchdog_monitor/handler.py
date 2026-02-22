"""Debounced filesystem event handler bridging watchdog threads to asyncio."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler

if TYPE_CHECKING:
    from assistant.core.notifications import NotificationDispatcher

logger = logging.getLogger(__name__)


class DebouncedChangeHandler(FileSystemEventHandler):
    """Debounces filesystem events and dispatches notifications via asyncio."""

    def __init__(
        self,
        dispatcher: NotificationDispatcher,
        loop: asyncio.AbstractEventLoop,
        debounce_seconds: float = 2.0,
        analyze: bool = False,
    ) -> None:
        super().__init__()
        self._dispatcher = dispatcher
        self._loop = loop
        self._debounce_seconds = debounce_seconds
        self._analyze = analyze
        self._last_event_time: dict[str, float] = {}
        self._pending: dict[str, asyncio.TimerHandle] = {}

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        src_path = str(event.src_path)
        now = time.monotonic()
        last = self._last_event_time.get(src_path, 0)

        if now - last < self._debounce_seconds:
            # Cancel pending notification and reschedule
            handle = self._pending.pop(src_path, None)
            if handle:
                handle.cancel()

        self._last_event_time[src_path] = now

        # Schedule notification after debounce period
        handle = self._loop.call_later(
            self._debounce_seconds,
            self._schedule_notification,
            src_path,
            event.event_type,
        )
        self._pending[src_path] = handle

    def _schedule_notification(self, path: str, event_type: str) -> None:
        self._pending.pop(path, None)
        message = f"File {event_type}: {path}"

        if self._analyze:
            try:
                with open(path) as f:
                    content = f.read(2000)
                message += f"\n\nContent preview:\n```\n{content}\n```"
            except Exception:
                pass  # File may be deleted or unreadable

        asyncio.ensure_future(self._dispatcher.send(message), loop=self._loop)
