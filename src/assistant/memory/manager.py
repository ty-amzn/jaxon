"""MemoryManager facade — assembles context from all memory sources."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from assistant.memory.daily_log import DailyLog
from assistant.memory.durable import DurableMemory
from assistant.memory.embeddings import EmbeddingService
from assistant.memory.identity import IdentityLoader
from assistant.memory.search import SearchIndex
from assistant.memory.skills import SkillLoader

logger = logging.getLogger(__name__)


class MemoryManager:
    """Facade over all memory subsystems."""

    def __init__(
        self,
        identity_path: Path,
        memory_path: Path,
        daily_log_dir: Path,
        search_db_path: Path,
        skills_dir: Path | None = None,
        embeddings_db_path: Path | None = None,
        ollama_base_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
        vector_search_enabled: bool = False,
        timezone: str = "UTC",
    ) -> None:
        self.identity = IdentityLoader(identity_path)
        self._rules_path = identity_path.parent / "RULES.md"
        self.durable = DurableMemory(memory_path)
        self.daily_log = DailyLog(daily_log_dir)
        self.search = SearchIndex(search_db_path)
        self.skills = SkillLoader(skills_dir) if skills_dir else None

        self._timezone = timezone

        # Plugin skills (injected at runtime)
        self._plugin_skills: dict[str, str] = {}

        # Embedding service (optional)
        self._vector_search_enabled = vector_search_enabled
        self.embeddings: EmbeddingService | None = None
        if vector_search_enabled and embeddings_db_path:
            self.embeddings = EmbeddingService(
                db_path=embeddings_db_path,
                ollama_base_url=ollama_base_url,
                embedding_model=embedding_model,
            )
            logger.info(f"Vector search enabled with model: {embedding_model}")

    def get_system_prompt(
        self,
        skill_names: list[str] | None = None,
        include_identity: bool = True,
    ) -> str:
        """Assemble system prompt from identity, durable memory, skills, and today's log.

        Args:
            skill_names: If provided, only include these skills in the metadata.
                         Pass ``None`` to include all skills.
            include_identity: If False, skip IDENTITY.md (for sub-agents that
                              have their own persona). Shared RULES.md is always included.
        """
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo

        parts: list[str] = []
        tz_name = self._timezone
        try:
            local_tz = ZoneInfo(tz_name)
        except Exception:
            local_tz = timezone.utc
            tz_name = "UTC"
        now = datetime.now(local_tz)
        parts.append(f"Current date/time: {now.strftime('%Y-%m-%d %H:%M:%S')} ({tz_name})")

        if include_identity:
            identity = self.identity.load()
            if identity:
                parts.append(identity)

        # Shared operational rules (feed, delegation) — always included
        if self._rules_path.exists():
            rules = self._rules_path.read_text()
            if rules.strip():
                parts.append(rules)

        memory = self.durable.read()
        if memory:
            parts.append(memory)

        # Add skills metadata (compact — full content loaded on-demand via activate_skill)
        if self.skills:
            skills_prompt = self.skills.get_skills_metadata_prompt(skill_names)
            if skills_prompt:
                parts.append(skills_prompt)

        # Add plugin skills
        if self._plugin_skills:
            plugin_parts = ["# Plugin Skills\n"]
            for name, content in self._plugin_skills.items():
                plugin_parts.append(f"## Plugin Skill: {name}\n\n{content}\n")
            parts.append("\n".join(plugin_parts))

        recent = self.daily_log.read_recent()
        if recent:
            parts.append(f"# Recent Context\n{recent}")

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

        # Index in FTS5
        user_msg_id = self.search.index_message("user", user_message, session_id)
        asst_msg_id = self.search.index_message("assistant", assistant_response, session_id)

        # Store embeddings if enabled
        if self.embeddings:
            try:
                if user_msg_id:
                    await self.embeddings.store_embedding(user_msg_id, user_message)
                if asst_msg_id:
                    await self.embeddings.store_embedding(asst_msg_id, assistant_response)
            except Exception as e:
                logger.warning(f"Failed to store embeddings: {e}")

    async def search_similar(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Semantic search using embeddings."""
        if not self.embeddings:
            return []
        return await self.embeddings.search_similar(query, limit)

    def add_plugin_skill(self, name: str, content: str) -> None:
        """Add a skill contributed by a plugin."""
        self._plugin_skills[name] = content

    def remove_plugin_skill(self, name: str) -> None:
        """Remove a plugin-contributed skill."""
        self._plugin_skills.pop(name, None)

    async def close(self) -> None:
        """Close any open resources."""
        if self.embeddings:
            await self.embeddings.close()