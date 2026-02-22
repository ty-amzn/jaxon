"""File monitor wrapping watchdog Observer."""

from __future__ import annotations

import asyncio
import logging

from watchdog.observers import Observer

from assistant.core.notifications import NotificationDispatcher
from assistant.watchdog_monitor.handler import DebouncedChangeHandler

logger = logging.getLogger(__name__)


class FileMonitor:
    """Watches filesystem paths for changes and sends notifications."""

    def __init__(
        self,
        dispatcher: NotificationDispatcher,
        debounce_seconds: float = 2.0,
        analyze: bool = False,
    ) -> None:
        self._dispatcher = dispatcher
        self._debounce_seconds = debounce_seconds
        self._analyze = analyze
        self._observer: Observer | None = None
        self._watched_paths: set[str] = set()
        self._watches: dict[str, object] = {}  # path -> watch handle

    @property
    def watched_paths(self) -> list[str]:
        return sorted(self._watched_paths)

    def start(self) -> None:
        """Start the observer thread."""
        if self._observer is not None:
            return
        self._observer = Observer()
        self._observer.start()
        logger.info("File monitor started")

    def stop(self) -> None:
        """Stop the observer thread."""
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=5)
        self._observer = None
        self._watches.clear()
        logger.info("File monitor stopped")

    def add_path(self, path: str) -> bool:
        """Add a path to watch. Returns True if added."""
        if path in self._watched_paths:
            return False
        if self._observer is None:
            self.start()

        loop = asyncio.get_event_loop()
        handler = DebouncedChangeHandler(
            dispatcher=self._dispatcher,
            loop=loop,
            debounce_seconds=self._debounce_seconds,
            analyze=self._analyze,
        )

        try:
            watch = self._observer.schedule(handler, path, recursive=True)
            self._watches[path] = watch
            self._watched_paths.add(path)
            logger.info("Watching path: %s", path)
            return True
        except Exception:
            logger.exception("Failed to watch path: %s", path)
            return False

    def remove_path(self, path: str) -> bool:
        """Remove a watched path. Returns True if removed."""
        if path not in self._watched_paths:
            return False

        watch = self._watches.pop(path, None)
        if watch and self._observer:
            self._observer.unschedule(watch)
        self._watched_paths.discard(path)
        logger.info("Stopped watching path: %s", path)
        return True
