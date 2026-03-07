"""knowledge_search tool — semantic search across Qdrant vector store."""

from __future__ import annotations

from typing import Any

from assistant.memory.vector_store import CONVERSATIONS, KNOWLEDGE, POSTS, VectorStore

KNOWLEDGE_SEARCH_DEF: dict[str, Any] = {
    "name": "knowledge_search",
    "description": (
        "Semantic search across past conversations, feed posts, and stored knowledge. "
        "Unlike memory_search (keyword-based), this uses vector embeddings to find "
        "semantically similar content even when exact words don't match. "
        "Use this when you need to recall context about a topic discussed previously, "
        "find related conversations, or search stored knowledge."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query.",
            },
            "scope": {
                "type": "string",
                "enum": ["all", "conversations", "posts", "knowledge"],
                "description": (
                    "Which collection to search: 'all' (default) searches everything, "
                    "'conversations' for past chat history, 'posts' for feed posts, "
                    "'knowledge' for stored facts/notes."
                ),
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default 10).",
            },
        },
        "required": ["query"],
    },
}


def _make_knowledge_search(vector_store: VectorStore):
    """Return an async handler bound to the vector store."""

    async def knowledge_search(params: dict[str, Any]) -> str:
        query = params.get("query", "").strip()
        if not query:
            return "Error: query is required."

        scope = params.get("scope", "all")
        limit = min(params.get("limit", 10), 20)

        collections = []
        if scope == "all":
            collections = [CONVERSATIONS, POSTS, KNOWLEDGE]
        elif scope in (CONVERSATIONS, POSTS, KNOWLEDGE):
            collections = [scope]
        else:
            return f"Error: invalid scope '{scope}'. Use all, conversations, posts, or knowledge."

        all_results: list[dict[str, Any]] = []
        for coll in collections:
            hits = await vector_store.search(coll, query, limit=limit)
            for hit in hits:
                hit["collection"] = coll
            all_results.extend(hits)

        # Sort by score descending and take top `limit`
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        all_results = all_results[:limit]

        if not all_results:
            return f"No semantic matches found for '{query}'."

        parts: list[str] = []
        for r in all_results:
            payload = r.get("payload", {})
            score = r.get("score", 0)
            coll = r.get("collection", "")
            preview = payload.get("preview", "")[:300]
            role = payload.get("role", "")
            created = payload.get("created_at", "")

            header = f"[{coll}]"
            if role:
                header += f" ({role})"
            if created:
                header += f" {created}"
            header += f" score={score:.3f}"

            parts.append(f"- {header}\n  {preview}")

        return f"## Semantic Search Results ({len(all_results)} matches)\n\n" + "\n\n".join(parts)

    return knowledge_search
