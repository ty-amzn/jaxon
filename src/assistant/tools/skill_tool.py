"""LLM-callable tools for skill activation and management."""

from __future__ import annotations

import shutil
from typing import Any

from assistant.memory.skills import SkillLoader

# --------------------------------------------------------------------------- #
# activate_skill — on-demand full skill loading
# --------------------------------------------------------------------------- #

ACTIVATE_SKILL_DEF: dict[str, Any] = {
    "name": "activate_skill",
    "description": (
        "Load the full instructions for a skill by name. "
        "Call this when a user request matches one of the available skills "
        "listed in the system prompt."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The skill name to activate (e.g. 'code-review').",
            },
        },
        "required": ["name"],
    },
}


def _make_activate_skill(skills: SkillLoader):
    """Return an async handler that loads full skill content on demand."""

    async def activate_skill(params: dict[str, Any]) -> str:
        name = params.get("name", "").strip()
        if not name:
            return "Error: 'name' is required."
        content = skills.get_skill_content(name)
        if content is None:
            available = [s.name for s in skills.list_skills()]
            return (
                f"Error: skill '{name}' not found. "
                f"Available skills: {', '.join(available) or 'none'}"
            )
        return content

    return activate_skill


# --------------------------------------------------------------------------- #
# manage_skill — create/edit/delete/list
# --------------------------------------------------------------------------- #

MANAGE_SKILL_DEF: dict[str, Any] = {
    "name": "manage_skill",
    "description": (
        "Create, edit, delete, or list skill files. Skills are markdown documents "
        "that define specialized workflows the assistant can follow. "
        "Only skill names and descriptions appear in the system prompt; "
        "full content is loaded on-demand via activate_skill. "
        "When creating a skill, provide a clear 'description' — this is what "
        "determines when the skill gets activated."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "edit", "delete", "list"],
                "description": "The action to perform.",
            },
            "name": {
                "type": "string",
                "description": "Skill name (used as directory name).",
            },
            "content": {
                "type": "string",
                "description": "Markdown content for the skill (required for create/edit).",
            },
            "description": {
                "type": "string",
                "description": "Short description shown in the system prompt to determine when to activate this skill. Should describe what the skill does and when to use it (e.g. 'Review code for quality and security. Use when asked to review or audit code.').",
            },
        },
        "required": ["action"],
    },
}


def _make_manage_skill(skills: SkillLoader):
    """Return an async handler bound to *skills*."""

    async def manage_skill(params: dict[str, Any]) -> str:
        action = params.get("action", "list")
        name = params.get("name", "").strip()
        content = params.get("content", "")
        description = params.get("description", "")

        if action == "list":
            all_skills = skills.list_skills()
            if not all_skills:
                return "No skills found."
            lines = []
            for s in all_skills:
                desc = s.description or ""
                if not desc:
                    for line in s.content.splitlines():
                        stripped = line.strip().lstrip("#").strip()
                        if stripped:
                            desc = stripped[:80]
                            break
                lines.append(f"- **{s.name}**: {desc}")
            return "## Skills\n" + "\n".join(lines)

        if not name:
            return "Error: 'name' is required for create/edit/delete."

        # Sanitize name — alphanumeric, hyphens, underscores only
        safe_name = "".join(
            c for c in name if c.isalnum() or c in "-_"
        )
        if not safe_name:
            return f"Error: invalid skill name '{name}'."

        skill_dir = skills._skills_dir / safe_name
        skill_path = skill_dir / "SKILL.md"
        # Also check for legacy flat file
        legacy_path = skills._skills_dir / f"{safe_name}.md"

        if action == "create":
            if not content:
                return "Error: 'content' is required to create a skill."
            if skill_path.exists() or legacy_path.exists():
                return f"Error: skill '{safe_name}' already exists. Use 'edit' to update it."
            skill_dir.mkdir(parents=True, exist_ok=True)
            frontmatter = f"---\nname: {safe_name}\ndescription: {description or safe_name}\n---\n"
            skill_path.write_text(frontmatter + content, encoding="utf-8")
            skills.reload()
            return f"Created skill '{safe_name}'."

        elif action == "edit":
            if not content:
                return "Error: 'content' is required to edit a skill."
            # Support editing both formats
            if skill_path.exists():
                # Preserve/update frontmatter
                raw = skill_path.read_text(encoding="utf-8")
                from assistant.memory.skills import _parse_frontmatter
                meta, _ = _parse_frontmatter(raw)
                if description:
                    meta["description"] = description
                meta.setdefault("name", safe_name)
                meta.setdefault("description", safe_name)
                import yaml
                frontmatter = "---\n" + yaml.dump(meta, default_flow_style=False).strip() + "\n---\n"
                skill_path.write_text(frontmatter + content, encoding="utf-8")
            elif legacy_path.exists():
                # Migrate to directory format on edit
                skill_dir.mkdir(parents=True, exist_ok=True)
                desc = description or safe_name
                frontmatter = f"---\nname: {safe_name}\ndescription: {desc}\n---\n"
                skill_path.write_text(frontmatter + content, encoding="utf-8")
                legacy_path.unlink()
            else:
                return f"Error: skill '{safe_name}' does not exist. Use 'create' to make it."
            skills.reload()
            return f"Updated skill '{safe_name}'."

        elif action == "delete":
            if skill_dir.exists() and skill_dir.is_dir():
                shutil.rmtree(skill_dir)
            elif legacy_path.exists():
                legacy_path.unlink()
            else:
                return f"Error: skill '{safe_name}' does not exist."
            skills.reload()
            return f"Deleted skill '{safe_name}'."

        else:
            return f"Error: unknown action '{action}'."

    return manage_skill
