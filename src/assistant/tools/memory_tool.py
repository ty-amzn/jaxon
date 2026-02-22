"""LLM-callable tools for agentic memory management (search & forget)."""

from __future__ import annotations

from typing import Any

from assistant.memory.manager import MemoryManager

# --------------------------------------------------------------------------- #
# Tool definitions (Anthropic format)
# --------------------------------------------------------------------------- #

MEMORY_SEARCH_DEF: dict[str, Any] = {
    "name": "memory_search",
    "description": (
        "Search the user's conversation history and durable memory. "
        "Use this when the user asks you to recall, find, or look up past "
        "conversations, facts, or notes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query (keywords or natural language).",
            },
            "source": {
                "type": "string",
                "enum": ["all", "memory", "history", "daily_log"],
                "description": (
                    "Where to search: 'all' (default), 'memory' (MEMORY.md), "
                    "'history' (FTS5 index), or 'daily_log' (today's log)."
                ),
            },
        },
        "required": ["query"],
    },
}

MEMORY_FORGET_DEF: dict[str, Any] = {
    "name": "memory_forget",
    "description": (
        "Delete or forget information from the user's memory and history. "
        "Use this when the user says 'forget about X', 'delete memories of X', "
        "or asks you to remove specific information."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to forget — keywords or topic description.",
            },
            "scope": {
                "type": "string",
                "enum": ["topic", "all"],
                "description": (
                    "'topic' deletes only matching entries, "
                    "'all' wipes everything (use with extreme caution)."
                ),
            },
            "confirm": {
                "type": "boolean",
                "description": "Must be true to proceed with deletion.",
            },
        },
        "required": ["query", "scope", "confirm"],
    },
}


# --------------------------------------------------------------------------- #
# Handlers
# --------------------------------------------------------------------------- #


def _make_memory_search(memory: MemoryManager):
    """Return an async handler bound to *memory*."""

    async def memory_search(params: dict[str, Any]) -> str:
        query = params.get("query", "")
        source = params.get("source", "all")
        if not query:
            return "Error: query is required."

        results: list[str] = []

        # Search durable MEMORY.md
        if source in ("all", "memory"):
            content = memory.durable.read()
            matching_lines = [
                line for line in content.splitlines()
                if query.lower() in line.lower()
            ]
            if matching_lines:
                results.append("## Durable Memory matches\n" + "\n".join(matching_lines))

        # Search FTS5 index
        if source in ("all", "history"):
            rows = memory.search.search(query, limit=20)
            if rows:
                parts = []
                for r in rows:
                    parts.append(
                        f"- [{r.get('role', '?')}] {r.get('content', '')[:200]}"
                    )
                results.append("## History matches\n" + "\n".join(parts))

        # Search today's log
        if source in ("all", "daily_log"):
            today = memory.daily_log.read_today(max_chars=8000)
            matching = [
                line for line in today.splitlines()
                if query.lower() in line.lower()
            ]
            if matching:
                results.append("## Today's log matches\n" + "\n".join(matching[:20]))

        if not results:
            return f"No results found for '{query}'."

        return "\n\n".join(results)

    return memory_search


def _make_memory_forget(memory: MemoryManager):
    """Return an async handler bound to *memory*."""

    async def memory_forget(params: dict[str, Any]) -> str:
        query = params.get("query", "")
        scope = params.get("scope", "topic")
        confirm = params.get("confirm", False)

        if not confirm:
            return "Deletion cancelled — confirm must be true."
        if not query:
            return "Error: query is required."

        deleted_parts: list[str] = []

        if scope == "all":
            # Wipe everything
            await memory.durable.write("")
            deleted_parts.append("Cleared durable memory (MEMORY.md)")

            memory.search.clear_all()
            deleted_parts.append("Cleared FTS5 search index")

            if memory.embeddings:
                memory.embeddings.clear_all()
                deleted_parts.append("Cleared embeddings")

            memory.daily_log.clear_all()
            deleted_parts.append("Cleared all daily logs")

        elif scope == "topic":
            # Remove matching lines from MEMORY.md
            content = memory.durable.read()
            original_lines = content.splitlines()
            kept = [l for l in original_lines if query.lower() not in l.lower()]
            removed_count = len(original_lines) - len(kept)
            if removed_count > 0:
                await memory.durable.write("\n".join(kept) + "\n" if kept else "")
                deleted_parts.append(
                    f"Removed {removed_count} line(s) from MEMORY.md"
                )

            # Delete matching FTS5 rows
            fts_deleted = memory.search.delete_matching(query)
            if fts_deleted:
                deleted_parts.append(
                    f"Deleted {fts_deleted} row(s) from search index"
                )

                # Also delete related embeddings
                if memory.embeddings:
                    # Re-search to get IDs of deleted messages (already gone)
                    # The IDs were returned during delete_matching
                    pass  # embeddings tied to message IDs already deleted

        if not deleted_parts:
            return f"Nothing found to delete for '{query}'."

        return "Deleted:\n" + "\n".join(f"- {p}" for p in deleted_parts)

    return memory_forget
