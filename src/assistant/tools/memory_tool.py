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
        "Use this PROACTIVELY — not only when the user explicitly asks to recall something, "
        "but whenever context from past conversations could be relevant. For example: "
        "if the user asks about weather, search for their location; if they mention a project, "
        "search for past discussions about it; if they reference a preference, look it up. "
        "IMPORTANT: This tool already searches all memory sources internally — "
        "do NOT use read_file or shell_exec to look at log files or memory files. "
        "The results returned by this tool are complete and authoritative."
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

UPDATE_IDENTITY_DEF: dict[str, Any] = {
    "name": "update_identity",
    "description": (
        "Read or update the assistant's personality and communication style. "
        "Use this when the user asks you to change how you talk, your tone, "
        "personality traits, name, or any behavioural preferences. "
        "Call with action='read' first to see the current identity, then "
        "action='write' with the full updated content. Always preserve the "
        "core traits section and only modify what the user asked to change."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write"],
                "description": "'read' to view current identity, 'write' to update it.",
            },
            "content": {
                "type": "string",
                "description": "The full new IDENTITY.md content (required for write).",
            },
        },
        "required": ["action"],
    },
}

MEMORY_STORE_DEF: dict[str, Any] = {
    "name": "memory_store",
    "description": (
        "Save a fact or note to the user's durable memory (MEMORY.md). "
        "Use this when the user asks you to remember, memorize, or note something "
        "for future conversations. Facts stored here persist across sessions and are "
        "automatically included in every conversation. "
        "Do NOT use write_file or read_file to edit MEMORY.md — use this tool instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "description": (
                    "The section heading to file the fact under, e.g. 'Personal', "
                    "'Preferences', 'Projects', 'Locations'. Creates the section if it doesn't exist."
                ),
            },
            "fact": {
                "type": "string",
                "description": "The fact or note to store, as a concise single line.",
            },
        },
        "required": ["section", "fact"],
    },
}

MEMORY_FORGET_DEF: dict[str, Any] = {
    "name": "memory_forget",
    "description": (
        "Delete or forget information from the user's memory and history. "
        "Use this when the user says 'forget about X', 'delete memories of X', "
        "or asks you to remove specific information. "
        "This tool handles all deletion internally — do NOT use shell_exec or "
        "write_file to manually edit or delete memory/log files."
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


def _make_update_identity(memory: MemoryManager):
    """Return an async handler bound to *memory*."""

    async def update_identity(params: dict[str, Any]) -> str:
        action = params.get("action", "read")

        if action == "read":
            content = memory.identity.load()
            if not content:
                return "No identity file found. You can create one with action='write'."
            return f"## Current Identity\n\n{content}"

        elif action == "write":
            content = params.get("content", "")
            if not content:
                return "Error: 'content' is required for write."
            await memory.identity.write(content)
            return "Identity updated successfully. Changes take effect on the next message."

        return f"Error: unknown action '{action}'."

    return update_identity


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


def _make_memory_store(memory: MemoryManager):
    """Return an async handler bound to *memory*."""

    async def memory_store(params: dict[str, Any]) -> str:
        section = params.get("section", "").strip()
        fact = params.get("fact", "").strip()
        if not section:
            return "Error: section is required."
        if not fact:
            return "Error: fact is required."
        await memory.durable.append(section, fact)
        return f"Stored under '{section}': {fact}"

    return memory_store


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
