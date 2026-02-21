"""MemoryManager facade — assembles context from all memory sources."""

from __future__ import annotations

from pathlib import Path

from assistant.memory.daily_log import DailyLog
from assistant.memory.durable import DurableMemory
from assistant.memory.identity import IdentityLoader
from assistant.memory.search import SearchIndex


class MemoryManager:
    """Facade over all memory subsystems."""

    def __init__(
        self,
        identity_path: Path,
        memory_path: Path,
        daily_log_dir: Path,
        search_db_path: Path,
    ) -> None:
        self.identity = IdentityLoader(identity_path)
        self.durable = DurableMemory(memory_path)
        self.daily_log = DailyLog(daily_log_dir)
        self.search = SearchIndex(search_db_path)

    def get_system_prompt(self) -> str:
        """Assemble system prompt from identity, durable memory, and today's log."""
        parts: list[str] = []

        identity = self.identity.load()
        if identity:
            parts.append(identity)

        memory = self.durable.read()
        if memory:
            parts.append(memory)

        today = self.daily_log.read_today()
        if today:
            parts.append(f"# Today's Context\n{today}")

        return "\n\n---\n\n".join(parts)

    async def save_exchange(
        self,
        user_message: str,
        assistant_response: str,
        session_id: str = "",
        tool_calls: list[dict] | None = None,
    ) -> None:
        """Persist an exchange to daily log and search index."""
        await self.daily_log.append_exchange(
            user_message, assistant_response, tool_calls
        )
        self.search.index_message("user", user_message, session_id)
        self.search.index_message("assistant", assistant_response, session_id)
