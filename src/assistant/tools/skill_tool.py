"""LLM-callable tool for agentic skill management (create/edit/delete/list)."""

from __future__ import annotations

from typing import Any

from assistant.memory.skills import SkillLoader

# --------------------------------------------------------------------------- #
# Tool definition (Anthropic format)
# --------------------------------------------------------------------------- #

MANAGE_SKILL_DEF: dict[str, Any] = {
    "name": "manage_skill",
    "description": (
        "Create, edit, delete, or list skill files. Skills are markdown documents "
        "in the skills directory that get injected into the system prompt."
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
                "description": "Skill name (becomes the filename, without .md extension).",
            },
            "content": {
                "type": "string",
                "description": "Markdown content for the skill (required for create/edit).",
            },
        },
        "required": ["action"],
    },
}


# --------------------------------------------------------------------------- #
# Handler factory
# --------------------------------------------------------------------------- #


def _make_manage_skill(skills: SkillLoader):
    """Return an async handler bound to *skills*."""

    async def manage_skill(params: dict[str, Any]) -> str:
        action = params.get("action", "list")
        name = params.get("name", "").strip()
        content = params.get("content", "")

        if action == "list":
            all_skills = skills.list_skills()
            if not all_skills:
                return "No skills found."
            lines = []
            for s in all_skills:
                # Use first non-empty line as description preview
                preview = ""
                for line in s.content.splitlines():
                    stripped = line.strip().lstrip("#").strip()
                    if stripped:
                        preview = stripped[:80]
                        break
                lines.append(f"- **{s.name}**: {preview}")
            return "## Skills\n" + "\n".join(lines)

        if not name:
            return "Error: 'name' is required for create/edit/delete."

        # Sanitize name — alphanumeric, hyphens, underscores only
        safe_name = "".join(
            c for c in name if c.isalnum() or c in "-_"
        )
        if not safe_name:
            return f"Error: invalid skill name '{name}'."

        skill_path = skills._skills_dir / f"{safe_name}.md"

        if action == "create":
            if not content:
                return "Error: 'content' is required to create a skill."
            if skill_path.exists():
                return f"Error: skill '{safe_name}' already exists. Use 'edit' to update it."
            skills._skills_dir.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(content, encoding="utf-8")
            skills.reload()
            return f"Created skill '{safe_name}'."

        elif action == "edit":
            if not content:
                return "Error: 'content' is required to edit a skill."
            if not skill_path.exists():
                return f"Error: skill '{safe_name}' does not exist. Use 'create' to make it."
            skill_path.write_text(content, encoding="utf-8")
            skills.reload()
            return f"Updated skill '{safe_name}'."

        elif action == "delete":
            if not skill_path.exists():
                return f"Error: skill '{safe_name}' does not exist."
            skill_path.unlink()
            skills.reload()
            return f"Deleted skill '{safe_name}'."

        else:
            return f"Error: unknown action '{action}'."

    return manage_skill
