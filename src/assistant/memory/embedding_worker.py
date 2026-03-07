"""Background worker that incrementally embeds new messages into Qdrant."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from assistant.memory.search import SearchIndex
from assistant.memory.vector_store import CONVERSATIONS, VectorStore

logger = logging.getLogger(__name__)


class EmbeddingWorker:
    """Polls SearchIndex for new messages and upserts them into Qdrant."""

    def __init__(
        self,
        vector_store: VectorStore,
        search_index: SearchIndex,
        interval: int = 30,
    ) -> None:
        self._store = vector_store
        self._search = search_index
        self._interval = interval
        self._last_conv_id = 0

    async def run(self) -> None:
        """Main loop: poll new conversations, embed, upsert."""
        self._last_conv_id = self._get_high_water_mark()
        logger.info(
            "Embedding worker started (high-water mark: %d, interval: %ds)",
            self._last_conv_id,
            self._interval,
        )
        while True:
            try:
                await self._sync_conversations()
            except Exception:
                logger.warning("Embedding sync cycle failed", exc_info=True)
            await asyncio.sleep(self._interval)

    def _get_high_water_mark(self) -> int:
        """Get the highest message ID already in Qdrant."""
        ids = self._store.scroll_ids(CONVERSATIONS, limit=1)
        if not ids:
            return 0
        # IDs are stored as "msg_{id}" strings
        max_id = 0
        all_ids = self._store.scroll_ids(CONVERSATIONS, limit=10000)
        for point_id in all_ids:
            if isinstance(point_id, str) and point_id.startswith("msg_"):
                try:
                    num = int(point_id.split("_", 1)[1])
                    max_id = max(max_id, num)
                except (ValueError, IndexError):
                    pass
        return max_id

    async def _sync_conversations(self) -> None:
        """Fetch new messages from SearchIndex and upsert into Qdrant."""
        new_messages = self._search.get_messages_after(self._last_conv_id)
        if not new_messages:
            return

        items = []
        for msg in new_messages:
            content = msg.get("content", "")
            if not content or len(content.strip()) < 10:
                continue
            # Truncate very long messages for embedding
            embed_text = content[:2000]
            preview = content[:300]
            items.append(
                {
                    "id": f"msg_{msg['id']}",
                    "text": embed_text,
                    "payload": {
                        "source_id": msg["id"],
                        "role": msg.get("role", ""),
                        "preview": preview,
                        "created_at": msg.get("timestamp", ""),
                        "session_id": msg.get("session_id", ""),
                    },
                }
            )

        if items:
            count = await self._store.upsert_batch(CONVERSATIONS, items)
            logger.info("Embedded %d/%d new messages", count, len(items))

        self._last_conv_id = new_messages[-1]["id"]

    async def backfill(self) -> None:
        """One-time import of all existing messages."""
        logger.info("Starting embedding backfill...")
        last_id = 0
        total = 0
        while True:
            batch = self._search.get_messages_after(last_id, limit=200)
            if not batch:
                break
            items = []
            for msg in batch:
                content = msg.get("content", "")
                if not content or len(content.strip()) < 10:
                    continue
                embed_text = content[:2000]
                preview = content[:300]
                items.append(
                    {
                        "id": f"msg_{msg['id']}",
                        "text": embed_text,
                        "payload": {
                            "source_id": msg["id"],
                            "role": msg.get("role", ""),
                            "preview": preview,
                            "created_at": msg.get("timestamp", ""),
                            "session_id": msg.get("session_id", ""),
                        },
                    }
                )
            if items:
                count = await self._store.upsert_batch(CONVERSATIONS, items)
                total += count
            last_id = batch[-1]["id"]
            # Yield to event loop between batches
            await asyncio.sleep(0.1)
        logger.info("Backfill complete: %d messages embedded", total)
