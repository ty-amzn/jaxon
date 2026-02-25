"""LRU page cache for paginating large tool outputs."""

from __future__ import annotations

import hashlib
import math
import time
from collections import OrderedDict

_SEVEN_DAYS = 7 * 24 * 3600


class PageCache:
    """Stores large text outputs split into pages with LRU eviction and TTL."""

    def __init__(
        self,
        max_entries: int = 20,
        default_page_size: int = 12_000,
        ttl: float = _SEVEN_DAYS,
    ) -> None:
        self._pages: OrderedDict[str, list[str]] = OrderedDict()
        self._timestamps: dict[str, float] = {}
        self._max_entries = max_entries
        self._default_page_size = default_page_size
        self._ttl = ttl

    def _evict_expired(self) -> None:
        """Remove entries older than TTL."""
        now = time.time()
        expired = [
            pid for pid, ts in self._timestamps.items()
            if now - ts > self._ttl
        ]
        for pid in expired:
            self._pages.pop(pid, None)
            self._timestamps.pop(pid, None)

    def store(self, text: str, page_size: int | None = None) -> tuple[str, int]:
        """Split *text* into pages and return ``(page_id, total_pages)``."""
        self._evict_expired()

        ps = page_size or self._default_page_size
        total_pages = max(1, math.ceil(len(text) / ps))
        chunks = [text[i * ps : (i + 1) * ps] for i in range(total_pages)]

        # Short hex id from content hash + timestamp
        raw = hashlib.sha256(f"{text[:256]}{time.monotonic()}".encode()).hexdigest()[:8]
        page_id = raw

        # Evict oldest if at capacity
        while len(self._pages) >= self._max_entries:
            evicted_id, _ = self._pages.popitem(last=False)
            self._timestamps.pop(evicted_id, None)

        self._pages[page_id] = chunks
        self._timestamps[page_id] = time.time()
        return page_id, total_pages

    def get_page(self, page_id: str, page: int) -> tuple[str, int] | None:
        """Return ``(page_text, total_pages)`` or ``None`` if not found."""
        chunks = self._pages.get(page_id)
        if chunks is None:
            return None
        if page < 1 or page > len(chunks):
            return None
        # Refresh LRU position
        self._pages.move_to_end(page_id)
        return chunks[page - 1], len(chunks)

    def clear(self, page_id: str) -> bool:
        """Remove a specific entry. Returns True if it existed."""
        if page_id in self._pages:
            del self._pages[page_id]
            self._timestamps.pop(page_id, None)
            return True
        return False

    def clear_all(self) -> int:
        """Remove all entries. Returns the number cleared."""
        count = len(self._pages)
        self._pages.clear()
        self._timestamps.clear()
        return count


_cache: PageCache | None = None


def get_page_cache() -> PageCache:
    global _cache
    if _cache is None:
        _cache = PageCache()
    return _cache
