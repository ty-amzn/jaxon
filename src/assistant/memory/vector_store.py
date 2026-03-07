"""Qdrant vector store wrapper for semantic search."""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Collection names
CONVERSATIONS = "conversations"
POSTS = "posts"
KNOWLEDGE = "knowledge"

_COLLECTIONS = [CONVERSATIONS, POSTS, KNOWLEDGE]


class VectorStore:
    """Thin wrapper around qdrant-client with automatic collection creation."""

    def __init__(self, config: Any, embedder: Any) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._embedder = embedder
        self._enabled = getattr(config, "qdrant_enabled", False)

        if not self._enabled:
            self._client = None
            self._dimensions = embedder.dimensions
            return

        # Probe actual dimensions if the embedder supports it
        if hasattr(embedder, "probe_dimensions"):
            self._dimensions = embedder.probe_dimensions()
        else:
            self._dimensions = embedder.dimensions

        url = getattr(config, "qdrant_url", "http://localhost:6333")
        self._client = QdrantClient(url=url, timeout=30)
        self._distance = Distance.COSINE
        self._vector_params = VectorParams(
            size=self._dimensions, distance=self._distance
        )
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        """Create collections if they don't exist, or recreate if dimensions changed."""
        if not self._client:
            return
        from qdrant_client.models import VectorParams, Distance

        existing = {c.name for c in self._client.get_collections().collections}
        for name in _COLLECTIONS:
            if name in existing:
                # Check if dimensions match
                info = self._client.get_collection(name)
                current_dim = info.config.params.vectors.size
                if current_dim != self._dimensions:
                    points = info.points_count or 0
                    logger.warning(
                        "Collection %s has dim=%d but embedder needs %d "
                        "(%d points will be lost). Recreating.",
                        name, current_dim, self._dimensions, points,
                    )
                    self._client.delete_collection(name)
                    existing.discard(name)

            if name not in existing:
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=self._dimensions, distance=Distance.COSINE
                    ),
                )
                logger.info("Created Qdrant collection: %s (dim=%d)", name, self._dimensions)

    async def upsert(
        self,
        collection: str,
        id: str | int,
        text: str,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        """Embed text and upsert a single point. Returns True on success."""
        if not self._client:
            return False
        try:
            vectors = await self._embedder.embed([text])
            if not vectors or not vectors[0]:
                return False
            from qdrant_client.models import PointStruct

            self._client.upsert(
                collection_name=collection,
                points=[
                    PointStruct(
                        id=id,
                        vector=vectors[0],
                        payload=payload or {},
                    )
                ],
            )
            return True
        except Exception as e:
            logger.warning("Qdrant upsert failed: %s", e)
            return False

    async def upsert_batch(
        self,
        collection: str,
        items: list[dict[str, Any]],
    ) -> int:
        """Embed and upsert a batch of items. Each item has 'id', 'text', 'payload'.

        Returns count of successfully upserted points.
        """
        if not self._client or not items:
            return 0

        texts = [item["text"] for item in items]
        try:
            vectors = await self._embedder.embed(texts)
        except Exception as e:
            logger.warning("Batch embedding failed: %s", e)
            return 0

        from qdrant_client.models import PointStruct

        points = []
        for item, vec in zip(items, vectors):
            if not vec:
                continue
            points.append(
                PointStruct(
                    id=item["id"],
                    vector=vec,
                    payload=item.get("payload", {}),
                )
            )

        if not points:
            return 0

        try:
            self._client.upsert(collection_name=collection, points=points)
            return len(points)
        except Exception as e:
            logger.warning("Qdrant batch upsert failed: %s", e)
            return 0

    async def search(
        self,
        collection: str,
        query: str,
        filter: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Semantic search. Returns list of {id, score, payload} dicts."""
        if not self._client:
            return []
        try:
            vectors = await self._embedder.embed([query])
            if not vectors or not vectors[0]:
                return []

            qdrant_filter = None
            if filter:
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                conditions = []
                for key, value in filter.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                qdrant_filter = Filter(must=conditions)

            hits = self._client.query_points(
                collection_name=collection,
                query=vectors[0],
                query_filter=qdrant_filter,
                limit=limit,
            )
            return [
                {
                    "id": str(hit.id),
                    "score": hit.score,
                    "payload": hit.payload or {},
                }
                for hit in hits.points
            ]
        except Exception as e:
            logger.warning("Qdrant search failed: %s", e)
            return []

    async def delete(self, collection: str, ids: list[str]) -> bool:
        """Delete points by IDs. Returns True on success."""
        if not self._client or not ids:
            return False
        try:
            from qdrant_client.models import PointIdsList

            self._client.delete(
                collection_name=collection,
                points_selector=PointIdsList(points=ids),
            )
            return True
        except Exception as e:
            logger.warning("Qdrant delete failed: %s", e)
            return False

    def scroll_ids(self, collection: str, limit: int = 100) -> list[str]:
        """Return all point IDs in a collection (for high-water-mark init)."""
        if not self._client:
            return []
        try:
            records, _ = self._client.scroll(
                collection_name=collection,
                limit=limit,
                with_payload=False,
                with_vectors=False,
            )
            return [str(r.id) for r in records]
        except Exception:
            return []

    def close(self) -> None:
        """Close the Qdrant client."""
        if self._client:
            self._client.close()
