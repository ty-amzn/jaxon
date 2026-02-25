"""LLM-callable tool for agentic agent management (create/edit/delete/list/reload)."""

from __future__ import annotations

from typing import Any

import yaml

from assistant.agents.loader import AgentLoader

# --------------------------------------------------------------------------- #
# Tool definition (Anthropic format)
# --------------------------------------------------------------------------- #

MANAGE_AGENT_DEF: dict[str, Any] = {
    "name": "manage_agent",
    "description": (
        "Create, edit, delete, list, or reload agent definitions. "
        "Agents are YAML files in the agents directory that define specialized "
        "sub-assistants with scoped tools and custom system prompts. "
        "After any change, agents are automatically reloaded."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "edit", "delete", "list", "reload"],
                "description": "The action to perform.",
            },
            "name": {
                "type": "string",
                "description": "Agent name (becomes the filename, without .yaml extension).",
            },
            "definition": {
                "type": "object",
                "description": (
                    "Agent definition object for create/edit. Fields: "
                    "description (string), system_prompt (string), "
                    "allowed_tools (list of tool names), denied_tools (list of tool names), "
                    "allowed_skills (list of skill names — limits which skills appear in the agent's system prompt), "
                    "model (string, optional), max_tool_rounds (int, default 5)."
                ),
            },
        },
        "required": ["action"],
    },
}


# --------------------------------------------------------------------------- #
# Handler factory
# --------------------------------------------------------------------------- #


def _make_manage_agent(loader: AgentLoader):
    """Return an async handler bound to *loader*."""

    async def manage_agent(params: dict[str, Any]) -> str:
        action = params.get("action", "list")
        name = params.get("name", "").strip()
        definition = params.get("definition", {})

        if action == "list":
            agents = loader.list_agents()
            if not agents:
                return "No agents defined."
            lines = []
            for a in agents:
                tools_info = ""
                if a.allowed_tools:
                    tools_info = f" | tools: {', '.join(a.allowed_tools)}"
                lines.append(
                    f"- **{a.name}**: {a.description} "
                    f"(max_tool_rounds={a.max_tool_rounds}{tools_info})"
                )
            return "## Agents\n" + "\n".join(lines)

        if action == "reload":
            loader.reload()
            count = len(loader.list_agents())
            return f"Reloaded {count} agent(s)."

        if not name:
            return "Error: 'name' is required for create/edit/delete."

        # Sanitize name
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
        if not safe_name:
            return f"Error: invalid agent name '{name}'."

        agent_path = loader._agents_dir / f"{safe_name}.yaml"

        if action == "create":
            if not definition:
                return "Error: 'definition' is required to create an agent."
            if agent_path.exists():
                return f"Error: agent '{safe_name}' already exists. Use 'edit' to update it."

            yaml_data = {"name": safe_name, **definition}
            loader._agents_dir.mkdir(parents=True, exist_ok=True)
            agent_path.write_text(
                yaml.dump(yaml_data, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
            loader.reload()
            return f"Created agent '{safe_name}'."

        elif action == "edit":
            if not definition:
                return "Error: 'definition' is required to edit an agent."
            if not agent_path.exists():
                return f"Error: agent '{safe_name}' does not exist. Use 'create' to make it."

            # Merge: load existing, update with new fields
            existing = yaml.safe_load(agent_path.read_text(encoding="utf-8")) or {}
            existing.update(definition)
            existing["name"] = safe_name
            agent_path.write_text(
                yaml.dump(existing, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
            loader.reload()
            return f"Updated agent '{safe_name}'."

        elif action == "delete":
            if not agent_path.exists():
                return f"Error: agent '{safe_name}' does not exist."
            agent_path.unlink()
            loader.reload()
            return f"Deleted agent '{safe_name}'."

        else:
            return f"Error: unknown action '{action}'."

    return manage_agent
