"""Skill loader — loads markdown skills from data/skills/ directory."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """Represents a loaded skill."""

    name: str
    content: str
    path: Path


class SkillLoader:
    """Loads all markdown skills from a directory."""

    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}
        self._loaded = False

    def load_all(self) -> dict[str, Skill]:
        """Load all .md files from skills directory."""
        if self._loaded:
            return self._skills

        if not self._skills_dir.exists():
            logger.debug(f"Skills directory does not exist: {self._skills_dir}")
            self._loaded = True
            return self._skills

        for skill_file in self._skills_dir.glob("*.md"):
            try:
                content = skill_file.read_text(encoding="utf-8").strip()
                if content:
                    skill_name = skill_file.stem
                    self._skills[skill_name] = Skill(
                        name=skill_name,
                        content=content,
                        path=skill_file,
                    )
                    logger.debug(f"Loaded skill: {skill_name}")
            except Exception as e:
                logger.warning(f"Failed to load skill {skill_file}: {e}")

        self._loaded = True
        logger.info(f"Loaded {len(self._skills)} skills")
        return self._skills

    def get_skills_prompt(self) -> str:
        """Generate skills section for system prompt."""
        skills = self.load_all()
        if not skills:
            return ""

        parts = ["# Available Skills\n\nThese skills define specialized workflows you can follow:\n"]
        for name, skill in skills.items():
            parts.append(f"## Skill: {name}\n\n{skill.content}\n\n---\n")

        return "\n".join(parts)

    def list_skills(self) -> list[Skill]:
        """Return list of all loaded skills."""
        return list(self.load_all().values())

    def get_skill(self, name: str) -> Skill | None:
        """Get a specific skill by name."""
        return self.load_all().get(name)

    def reload(self) -> None:
        """Force reload of skills from disk."""
        self._skills.clear()
        self._loaded = False
        self.load_all()