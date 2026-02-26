"""AgentLoader — load YAML agent definitions from data/agents/."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from assistant.agents.types import AgentDef

logger = logging.getLogger(__name__)


class AgentLoader:
    """Loads agent definitions from YAML files."""

    def __init__(self, agents_dir: Path) -> None:
        self._agents_dir = agents_dir
        self._agents: dict[str, AgentDef] = {}

    def load_all(self) -> dict[str, AgentDef]:
        """Load all .yaml/.yml files from agents directory."""
        self._agents.clear()

        if not self._agents_dir.exists():
            self._agents_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Created agents directory: %s", self._agents_dir)
            return self._agents

        for pattern in ("*.yaml", "*.yml"):
            for path in sorted(self._agents_dir.glob(pattern)):
                try:
                    self._load_file(path)
                except Exception:
                    logger.exception("Failed to load agent definition: %s", path)

        logger.info("Loaded %d agent definitions", len(self._agents))
        return self._agents

    def _load_file(self, path: Path) -> None:
        """Load a single agent YAML file."""
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning("Invalid agent file (not a mapping): %s", path)
            return

        name = data.get("name", path.stem)
        agent = AgentDef(
            name=name,
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            allowed_tools=data.get("allowed_tools", []),
            denied_tools=data.get("denied_tools", []),
            allowed_skills=data.get("allowed_skills"),
            model=data.get("model", ""),
            max_tool_rounds=data.get("max_tool_rounds", 5),
            can_delegate=data.get("can_delegate", False),
            vision=data.get("vision"),
        )
        self._agents[name] = agent
        logger.debug("Loaded agent: %s", name)

    def get_agent(self, name: str) -> AgentDef | None:
        """Get an agent definition by name (hot-reloads from disk)."""
        if not self._agents:
            self.load_all()

        # Hot-reload: re-read the YAML file so edits are picked up without restart
        path = self._agents_dir / f"{name}.yaml"
        if not path.exists():
            path = self._agents_dir / f"{name}.yml"
        if path.exists():
            try:
                self._load_file(path)
            except Exception:
                logger.warning("Failed to hot-reload agent %s", name)

        return self._agents.get(name)

    def list_agents(self) -> list[AgentDef]:
        """List all loaded agent definitions."""
        if not self._agents:
            self.load_all()
        return list(self._agents.values())

    def reload(self) -> None:
        """Force reload all agent definitions."""
        self.load_all()
