"""Notification dispatcher with pluggable sinks and DND support."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, time

logger = logging.getLogger(__name__)

NotificationSink = Callable[[str], Awaitable[None]]


def parse_time(s: str) -> time:
    """Parse HH:MM string to time object."""
    parts = s.strip().split(":")
    return time(int(parts[0]), int(parts[1]))


def in_dnd_window(now: time, start: time, end: time) -> bool:
    """Check if 'now' falls within the DND window.

    Handles windows that cross midnight (e.g. 23:00 -> 07:00).
    """
    if start <= end:
        return start <= now < end
    else:
        # Crosses midnight
        return now >= start or now < end


class NotificationDispatcher:
    """Dispatches messages to registered notification sinks.

    Sinks are async callables that receive a message string.
    Used by scheduler and watchdog to send notifications to CLI, Telegram, etc.
    """

    def __init__(
        self,
        dnd_enabled: bool = False,
        dnd_start: str = "23:00",
        dnd_end: str = "07:00",
        allow_urgent: bool = True,
    ) -> None:
        self._sinks: list[NotificationSink] = []
        self._dnd_enabled = dnd_enabled
        self._dnd_start = parse_time(dnd_start)
        self._dnd_end = parse_time(dnd_end)
        self._allow_urgent = allow_urgent
        self._queued: list[str] = []

    def register(self, sink: NotificationSink) -> None:
        self._sinks.append(sink)

    def unregister(self, sink: NotificationSink) -> None:
        self._sinks = [s for s in self._sinks if s is not sink]

    def _is_dnd(self) -> bool:
        """Check if currently in DND window."""
        if not self._dnd_enabled:
            return False
        now = datetime.now().time()
        return in_dnd_window(now, self._dnd_start, self._dnd_end)

    async def send(self, message: str, urgent: bool = False) -> None:
        """Send a message to all registered sinks.

        If DND is active and message is not urgent, queue it.
        Failures are isolated per-sink.
        """
        if self._is_dnd() and not (urgent and self._allow_urgent):
            self._queued.append(message)
            logger.debug("Message queued (DND active): %s", message[:80])
            return

        # Flush any queued messages first
        messages_to_send = [*self._queued, message]
        self._queued.clear()

        for msg in messages_to_send:
            for sink in self._sinks:
                try:
                    await sink(msg)
                except Exception:
                    logger.exception("Notification sink failed")

    async def flush_queue(self) -> int:
        """Flush queued messages (call when DND ends). Returns count sent."""
        if not self._queued:
            return 0

        count = len(self._queued)
        messages = list(self._queued)
        self._queued.clear()

        for msg in messages:
            for sink in self._sinks:
                try:
                    await sink(msg)
                except Exception:
                    logger.exception("Notification sink failed during flush")

        return count

    @property
    def queued_count(self) -> int:
        return len(self._queued)
