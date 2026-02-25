"""Skill loader — loads markdown skills from data/skills/ directory."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)


@dataclass
class Skill:
    """Represents a loaded skill."""

    name: str
    content: str
    path: Path
    description: str = ""


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter and body from text.

    Returns (metadata dict, body without frontmatter).
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    body = text[m.end():]
    return meta, body


class SkillLoader:
    """Loads all markdown skills from a directory.

    Supports two layouts:
      - Legacy flat files: ``skills/{name}.md``
      - Directory format:  ``skills/{name}/SKILL.md`` (with YAML frontmatter)
    """

    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}

    def load_all(self) -> dict[str, Skill]:
        """Load skills from the directory (re-scans each call).

        Scans for both ``*.md`` flat files and ``*/SKILL.md`` directory format.
        """
        self._skills.clear()

        if not self._skills_dir.exists():
            logger.debug("Skills directory does not exist: %s", self._skills_dir)
            return self._skills

        # Directory format: skills/{name}/SKILL.md
        for skill_file in self._skills_dir.glob("*/SKILL.md"):
            try:
                raw = skill_file.read_text(encoding="utf-8").strip()
                if not raw:
                    continue
                meta, body = _parse_frontmatter(raw)
                skill_name = meta.get("name", skill_file.parent.name)
                description = meta.get("description", "")
                if not description:
                    # Fall back to first non-heading, non-empty paragraph
                    for line in body.splitlines():
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#"):
                            description = stripped[:120]
                            break
                self._skills[skill_name] = Skill(
                    name=skill_name,
                    content=body.strip(),
                    path=skill_file,
                    description=description,
                )
                logger.debug("Loaded skill (dir): %s", skill_name)
            except Exception as e:
                logger.warning("Failed to load skill %s: %s", skill_file, e)

        # Legacy flat files: skills/{name}.md (skip if already loaded via dir)
        for skill_file in self._skills_dir.glob("*.md"):
            try:
                raw = skill_file.read_text(encoding="utf-8").strip()
                if not raw:
                    continue
                meta, body = _parse_frontmatter(raw)
                skill_name = meta.get("name", skill_file.stem)
                if skill_name in self._skills:
                    continue  # directory format takes precedence
                description = meta.get("description", "")
                if not description:
                    for line in body.splitlines():
                        stripped = line.strip().lstrip("#").strip()
                        if stripped:
                            description = stripped[:120]
                            break
                self._skills[skill_name] = Skill(
                    name=skill_name,
                    content=body.strip(),
                    path=skill_file,
                    description=description,
                )
                logger.debug("Loaded skill (flat): %s", skill_name)
            except Exception as e:
                logger.warning("Failed to load skill %s: %s", skill_file, e)

        logger.debug("Loaded %d skills", len(self._skills))
        return self._skills

    # ------------------------------------------------------------------
    # Prompt generation
    # ------------------------------------------------------------------

    def get_skills_metadata_prompt(
        self, skill_names: list[str] | None = None,
    ) -> str:
        """Generate a compact metadata-only section for the system prompt.

        Returns an ``<available_skills>`` XML block with name + description
        for each skill, plus an instruction to use ``activate_skill`` to load
        the full content when needed.
        """
        skills = self.load_all()
        if not skills:
            return ""

        if skill_names is not None:
            skills = {k: v for k, v in skills.items() if k in skill_names}
        if not skills:
            return ""

        lines = ["<available_skills>"]
        for name, skill in skills.items():
            desc = skill.description or name
            lines.append(f'<skill name="{name}">{desc}</skill>')
        lines.append("</available_skills>")
        lines.append(
            "\nWhen a user's request matches one of the available skills above, "
            "call the `activate_skill` tool with the skill name to load the full "
            "instructions before responding."
        )
        return "\n".join(lines)

    def get_skills_prompt(self) -> str:
        """Generate full skills section for system prompt (legacy/deprecated)."""
        skills = self.load_all()
        if not skills:
            return ""

        parts = [
            "# Available Skills\n\n"
            "These skills define specialized workflows you can follow:\n"
        ]
        for name, skill in skills.items():
            parts.append(f"## Skill: {name}\n\n{skill.content}\n\n---\n")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Skill access
    # ------------------------------------------------------------------

    def get_skill_content(self, name: str) -> str | None:
        """Return the full body of a skill (without frontmatter), or None."""
        skill = self.load_all().get(name)
        return skill.content if skill else None

    def list_skills(self) -> list[Skill]:
        """Return list of all loaded skills."""
        return list(self.load_all().values())

    def get_skill(self, name: str) -> Skill | None:
        """Get a specific skill by name."""
        return self.load_all().get(name)

    def reload(self) -> None:
        """Force reload of skills from disk."""
        self.load_all()
