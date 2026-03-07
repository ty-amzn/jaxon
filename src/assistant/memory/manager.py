"""MemoryManager facade — assembles context from all memory sources."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from assistant.memory.daily_log import DailyLog
from assistant.memory.durable import DurableMemory
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
        timezone: str = "UTC",
        vector_store: Any = None,
    ) -> None:
        self.identity = IdentityLoader(identity_path)
        self._rules_path = identity_path.parent / "RULES.md"
        self.durable = DurableMemory(memory_path)
        self.daily_log = DailyLog(daily_log_dir)
        self.search = SearchIndex(search_db_path)
        self.skills = SkillLoader(skills_dir) if skills_dir else None

        self._timezone = timezone

        # Qdrant vector store (optional)
        self._vector_store = vector_store

        # Plugin skills (injected at runtime)
        self._plugin_skills: dict[str, str] = {}

    async def get_system_prompt(
        self,
        skill_names: list[str] | None = None,
        include_identity: bool = True,
        agent_catalog: list[tuple[str, str]] | None = None,
        user_message: str = "",
    ) -> str:
        """Assemble system prompt from identity, durable memory, skills, and today's log.

        Args:
            skill_names: If provided, only include these skills in the metadata.
                         Pass ``None`` to include all skills.
            include_identity: If False, skip IDENTITY.md (for sub-agents that
                              have their own persona). Shared RULES.md is always included.
            agent_catalog: List of (name, description) tuples for available agents.
                           When provided, an ``<available_agents>`` section is appended
                           so the main agent knows which agents it can delegate to.
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

        # Add agent catalog (dynamic — built from loaded YAML definitions)
        if agent_catalog:
            lines = ["<available_agents>"]
            for aname, adesc in agent_catalog:
                lines.append(f'<agent name="{aname}">{adesc}</agent>')
            lines.append("</available_agents>")
            parts.append("\n".join(lines))

        # Add plugin skills
        if self._plugin_skills:
            plugin_parts = ["# Plugin Skills\n"]
            for name, content in self._plugin_skills.items():
                plugin_parts.append(f"## Plugin Skill: {name}\n\n{content}\n")
            parts.append("\n".join(plugin_parts))

        recent = self.daily_log.read_recent()
        if recent:
            parts.append(f"# Recent Context\n{recent}")

        # Add semantic context from Qdrant if available
        if user_message and self._vector_store:
            try:
                hits = await self._vector_store.search(
                    "conversations", user_message, limit=5
                )
                if hits:
                    block = "## Relevant Past Context\n\n"
                    for h in hits:
                        payload = h.get("payload", {})
                        created = payload.get("created_at", "")
                        preview = payload.get("preview", "")
                        role = payload.get("role", "")
                        prefix = f"[{created}]" if created else ""
                        if role:
                            prefix += f" ({role})"
                        block += f"- {prefix} {preview}\n"
                    parts.append(block)
            except Exception as e:
                logger.warning("Failed to retrieve semantic context: %s", e)

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
        self.search.index_message("user", user_message, session_id)
        self.search.index_message("assistant", assistant_response, session_id)

    def add_plugin_skill(self, name: str, content: str) -> None:
        """Add a skill contributed by a plugin."""
        self._plugin_skills[name] = content

    def remove_plugin_skill(self, name: str) -> None:
        """Remove a plugin-contributed skill."""
        self._plugin_skills.pop(name, None)
