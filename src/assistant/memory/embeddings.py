"""Embedding service using Ollama for vector embeddings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
import sqlite_utils

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages text embeddings using Ollama and stores them in SQLite."""

    def __init__(
        self,
        db_path: Path,
        ollama_base_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
    ) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_utils.Database(str(db_path))
        self._ollama_url = ollama_base_url.rstrip("/")
        self._model = embedding_model
        self._client = httpx.AsyncClient(timeout=30.0)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Create tables for embeddings if they don't exist."""
        if "embeddings" not in self._db.table_names():
            self._db["embeddings"].create(
                {
                    "id": int,
                    "message_id": int,  # Links to messages table
                    "content_hash": str,  # SHA256 hash of content
                    "embedding": bytes,  # Binary blob of embedding vector
                    "created_at": str,
                },
                pk="id",
            )
            # Index for quick message_id lookups
            self._db["embeddings"].create_index(["message_id"])
            self._db["embeddings"].create_index(["content_hash"])

    async def get_embedding(self, text: str) -> list[float] | None:
        """Get embedding for text from Ollama."""
        try:
            response = await self._client.post(
                f"{self._ollama_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
            else:
                logger.warning(f"Embedding failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to get embedding: {e}")
        return None

    def _hash_content(self, content: str) -> str:
        """Generate a hash for content deduplication."""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()

    def _embedding_to_bytes(self, embedding: list[float]) -> bytes:
        """Convert embedding list to binary blob."""
        import struct
        return struct.pack(f"{len(embedding)}f", *embedding)

    def _bytes_to_embedding(self, data: bytes) -> list[float]:
        """Convert binary blob back to embedding list."""
        import struct
        count = len(data) // 4
        return list(struct.unpack(f"{count}f", data))

    async def store_embedding(
        self, message_id: int, content: str
    ) -> int | None:
        """Store embedding for a message. Returns embedding ID or None on failure."""
        embedding = await self.get_embedding(content)
        if not embedding:
            return None

        content_hash = self._hash_content(content)
        embedding_bytes = self._embedding_to_bytes(embedding)

        from datetime import datetime, timezone
        result = self._db["embeddings"].insert(
            {
                "message_id": message_id,
                "content_hash": content_hash,
                "embedding": embedding_bytes,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return result.last_pk

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)

    async def search_similar(
        self, query: str, limit: int = 10, threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """Find messages similar to the query using embeddings."""
        query_embedding = await self.get_embedding(query)
        if not query_embedding:
            return []

        results = []
        for row in self._db["embeddings"].rows:
            stored_embedding = self._bytes_to_embedding(row["embedding"])
            similarity = self.cosine_similarity(query_embedding, stored_embedding)

            if similarity >= threshold:
                results.append({
                    "message_id": row["message_id"],
                    "similarity": similarity,
                })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def delete_by_message_ids(self, ids: list[int]) -> None:
        """Delete embeddings for given message IDs."""
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        self._db.execute(
            f"DELETE FROM embeddings WHERE message_id IN ({placeholders})", ids
        )

    def clear_all(self) -> None:
        """Remove all rows from the embeddings table."""
        self._db.execute("DELETE FROM embeddings")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()