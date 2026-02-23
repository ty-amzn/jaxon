"""Agent types — definitions and results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentDef:
    """Definition of a specialized agent."""

    name: str
    description: str
    system_prompt: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    model: str = ""  # Empty = use default
    max_tool_rounds: int = 5
    can_delegate: bool = False


@dataclass
class AgentResult:
    """Result from running an agent."""

    agent_name: str
    response: str
    tool_calls_made: list[dict] = field(default_factory=list)
    error: str = ""

    @property
    def success(self) -> bool:
        return not self.error
