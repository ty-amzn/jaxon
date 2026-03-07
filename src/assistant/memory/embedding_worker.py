"""Background worker that incrementally embeds new messages into Qdrant."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from typing import Any

from assistant.memory.search import SearchIndex
from assistant.memory.vector_store import CONVERSATIONS, KNOWLEDGE, POSTS, VectorStore

logger = logging.getLogger(__name__)


class EmbeddingWorker:
    """Polls SearchIndex for new messages and upserts them into Qdrant."""

    def __init__(
        self,
        vector_store: VectorStore,
        search_index: SearchIndex,
        interval: int = 30,
        townsquare_url: str | None = None,
        durable_memory: Any = None,
    ) -> None:
        self._store = vector_store
        self._search = search_index
        self._interval = interval
        self._last_conv_id = 0
        self._last_post_id = 0
        self._townsquare_url = townsquare_url.rstrip("/") if townsquare_url else None
        self._durable = durable_memory
        self._last_knowledge_hash = ""

    async def run(self) -> None:
        """Main loop: poll new conversations, posts, and knowledge."""
        self._last_conv_id = self._get_high_water_mark(CONVERSATIONS)
        self._last_post_id = self._get_high_water_mark(POSTS)
        self._last_knowledge_hash = self._get_knowledge_hash()
        logger.info(
            "Embedding worker started (conv=%d, post=%d, interval=%ds)",
            self._last_conv_id,
            self._last_post_id,
            self._interval,
        )
        while True:
            try:
                await self._sync_conversations()
            except Exception:
                logger.warning("Conversation sync failed", exc_info=True)
            try:
                await self._sync_posts()
            except Exception:
                logger.warning("Post sync failed", exc_info=True)
            try:
                await self._sync_knowledge()
            except Exception:
                logger.warning("Knowledge sync failed", exc_info=True)
            await asyncio.sleep(self._interval)

    def _get_high_water_mark(self, collection: str) -> int:
        """Get the highest integer point ID in a Qdrant collection."""
        all_ids = self._store.scroll_ids(collection, limit=10000)
        if not all_ids:
            return 0
        max_id = 0
        for point_id in all_ids:
            try:
                max_id = max(max_id, int(point_id))
            except (ValueError, TypeError):
                pass
        return max_id

    def _get_knowledge_hash(self) -> str:
        """Hash current MEMORY.md content for change detection."""
        if not self._durable:
            return ""
        content = self._durable.read()
        return hashlib.sha256(content.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------

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
            embed_text = content[:2000]
            preview = content[:300]
            items.append(
                {
                    "id": msg["id"],
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

    # ------------------------------------------------------------------
    # Town Square Posts
    # ------------------------------------------------------------------

    async def _sync_posts(self) -> None:
        """Fetch new Town Square posts via HTTP and embed them."""
        if not self._townsquare_url:
            return

        import httpx

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self._townsquare_url}/feed/posts",
                    params={
                        "after_id": self._last_post_id,
                        "limit": 200,
                    },
                )
                if resp.status_code != 200:
                    logger.warning("Town Square posts fetch failed: %s", resp.status_code)
                    return
                posts = resp.json()
        except Exception as e:
            logger.warning("Town Square connection failed: %s", e)
            return

        if not posts:
            return

        items = []
        for post in posts:
            content = post.get("content", "")
            if not content or len(content.strip()) < 10:
                continue
            author = post.get("author", "")
            embed_text = f"{author}: {content}" if author else content
            embed_text = embed_text[:2000]
            preview = content[:300]
            items.append(
                {
                    "id": post["id"],
                    "text": embed_text,
                    "payload": {
                        "source_id": post["id"],
                        "author": author,
                        "preview": preview,
                        "created_at": post.get("created_at", ""),
                        "feed_name": post.get("feed_name", ""),
                        "type": "post",
                    },
                }
            )

        if items:
            count = await self._store.upsert_batch(POSTS, items)
            logger.info("Embedded %d/%d new posts", count, len(items))

        self._last_post_id = posts[-1]["id"]

    # ------------------------------------------------------------------
    # Knowledge (MEMORY.md)
    # ------------------------------------------------------------------

    def _parse_memory_facts(self, content: str) -> list[tuple[str, str]]:
        """Parse MEMORY.md into (section, fact) tuples."""
        facts: list[tuple[str, str]] = []
        current_section = "General"
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                current_section = stripped[3:].strip()
            elif stripped.startswith("- ") and len(stripped) > 4:
                fact = stripped[2:].strip()
                if fact and fact != "(none yet)":
                    facts.append((current_section, fact))
        return facts

    def _fact_uuid(self, section: str, fact: str) -> str:
        """Derive a stable UUID from section:fact content."""
        fact_hash = hashlib.sha256(f"{section}:{fact}".encode()).digest()
        return str(uuid.UUID(bytes=fact_hash[:16]))

    async def _sync_knowledge(self) -> None:
        """Re-embed MEMORY.md facts when content changes."""
        if not self._durable:
            return

        content = self._durable.read()
        if not content.strip():
            return

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if content_hash == self._last_knowledge_hash:
            return  # No changes

        facts = self._parse_memory_facts(content)
        if not facts:
            self._last_knowledge_hash = content_hash
            return

        items = []
        for section, fact in facts:
            items.append(
                {
                    "id": self._fact_uuid(section, fact),
                    "text": fact,
                    "payload": {
                        "section": section,
                        "preview": fact[:300],
                        "type": "durable_memory",
                    },
                }
            )

        if items:
            count = await self._store.upsert_batch(KNOWLEDGE, items)
            logger.info("Embedded %d/%d knowledge facts", count, len(items))

        self._last_knowledge_hash = content_hash

    # ------------------------------------------------------------------
    # Backfill
    # ------------------------------------------------------------------

    async def backfill(self) -> None:
        """One-time import of all existing conversations, posts, and knowledge."""
        await self._backfill_conversations()
        await self._backfill_posts()
        await self._backfill_knowledge()

    async def _backfill_conversations(self) -> None:
        """Backfill all conversation messages."""
        logger.info("Starting conversation backfill...")
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
                        "id": msg["id"],
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
            await asyncio.sleep(0.1)
        logger.info("Conversation backfill complete: %d messages embedded", total)

    async def _backfill_posts(self) -> None:
        """Backfill all Town Square posts via HTTP."""
        if not self._townsquare_url:
            logger.info("Skipping post backfill (no townsquare_url)")
            return

        import httpx

        logger.info("Starting post backfill...")
        last_id = 0
        total = 0
        async with httpx.AsyncClient(timeout=60) as client:
            while True:
                try:
                    resp = await client.get(
                        f"{self._townsquare_url}/feed/posts",
                        params={"after_id": last_id, "limit": 200},
                    )
                    if resp.status_code != 200:
                        logger.warning("Post backfill fetch failed: %s", resp.status_code)
                        break
                    posts = resp.json()
                except Exception as e:
                    logger.warning("Post backfill connection failed: %s", e)
                    break

                if not posts:
                    break

                items = []
                for post in posts:
                    content = post.get("content", "")
                    if not content or len(content.strip()) < 10:
                        continue
                    author = post.get("author", "")
                    embed_text = f"{author}: {content}" if author else content
                    embed_text = embed_text[:2000]
                    preview = content[:300]
                    items.append(
                        {
                            "id": post["id"],
                            "text": embed_text,
                            "payload": {
                                "source_id": post["id"],
                                "author": author,
                                "preview": preview,
                                "created_at": post.get("created_at", ""),
                                "feed_name": post.get("feed_name", ""),
                                "type": "post",
                            },
                        }
                    )

                if items:
                    count = await self._store.upsert_batch(POSTS, items)
                    total += count

                last_id = posts[-1]["id"]
                await asyncio.sleep(0.1)
        logger.info("Post backfill complete: %d posts embedded", total)

    async def _backfill_knowledge(self) -> None:
        """Backfill all MEMORY.md facts."""
        if not self._durable:
            logger.info("Skipping knowledge backfill (no durable memory)")
            return

        content = self._durable.read()
        if not content.strip():
            logger.info("Skipping knowledge backfill (MEMORY.md empty)")
            return

        facts = self._parse_memory_facts(content)
        if not facts:
            logger.info("Skipping knowledge backfill (no facts parsed)")
            return

        logger.info("Starting knowledge backfill (%d facts)...", len(facts))
        items = []
        for section, fact in facts:
            items.append(
                {
                    "id": self._fact_uuid(section, fact),
                    "text": fact,
                    "payload": {
                        "section": section,
                        "preview": fact[:300],
                        "type": "durable_memory",
                    },
                }
            )

        total = 0
        # Batch in groups of 50 to avoid huge embedding requests
        for i in range(0, len(items), 50):
            batch = items[i : i + 50]
            count = await self._store.upsert_batch(KNOWLEDGE, batch)
            total += count
            await asyncio.sleep(0.1)

        self._last_knowledge_hash = hashlib.sha256(content.encode()).hexdigest()
        logger.info("Knowledge backfill complete: %d facts embedded", total)
