"""Orchestrator — delegate tasks to specialized sub-agents, exposed as tools."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from assistant.agents.loader import AgentLoader
from assistant.agents.runner import AgentRunner
from assistant.agents.types import AgentResult
from assistant.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrates delegation to sub-agents. Provides tool definitions."""

    def __init__(
        self,
        loader: AgentLoader,
        runner: AgentRunner,
        memory: MemoryManager,
    ) -> None:
        self._loader = loader
        self._runner = runner
        self._memory = memory

    async def delegate(self, agent_name: str, task: str, context: str = "") -> AgentResult:
        """Delegate a task to a named agent."""
        agent = self._loader.get_agent(agent_name)
        if agent is None:
            return AgentResult(
                agent_name=agent_name,
                response="",
                error=f"Agent '{agent_name}' not found.",
            )

        base_prompt = self._memory.get_system_prompt()
        return await self._runner.run(agent, task, context=context, base_system_prompt=base_prompt)

    async def delegate_parallel(
        self, delegations: list[dict[str, str]]
    ) -> list[AgentResult]:
        """Run multiple agent delegations in parallel.

        Each delegation is a dict with keys: agent_name, task, context (optional).
        """
        tasks = [
            self.delegate(
                d["agent_name"],
                d["task"],
                d.get("context", ""),
            )
            for d in delegations
        ]
        return await asyncio.gather(*tasks)

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return tool definitions for delegation tools."""
        return [
            {
                "name": "list_agents",
                "description": "List all available specialized agents that can be delegated to.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "delegate_to_agent",
                "description": "Delegate a task to a specialized agent. The agent runs autonomously with its own tool set and returns a result.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Name of the agent to delegate to",
                        },
                        "task": {
                            "type": "string",
                            "description": "The task or query for the agent",
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context to pass to the agent",
                            "default": "",
                        },
                    },
                    "required": ["agent_name", "task"],
                },
            },
            {
                "name": "delegate_parallel",
                "description": "Delegate tasks to multiple agents in parallel. Each delegation specifies an agent_name and task.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "delegations": {
                            "type": "array",
                            "description": "List of delegations, each with agent_name, task, and optional context",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "agent_name": {"type": "string"},
                                    "task": {"type": "string"},
                                    "context": {"type": "string", "default": ""},
                                },
                                "required": ["agent_name", "task"],
                            },
                        }
                    },
                    "required": ["delegations"],
                },
            },
        ]

    def get_tool_handlers(self) -> dict[str, Any]:
        """Return handler functions for delegation tools."""

        async def handle_list_agents(params: dict[str, Any]) -> str:
            agents = self._loader.list_agents()
            if not agents:
                return "No agents available."
            lines = []
            for a in agents:
                tools_info = ""
                if a.allowed_tools:
                    tools_info = f" (tools: {', '.join(a.allowed_tools)})"
                lines.append(f"- {a.name}: {a.description}{tools_info}")
            return "\n".join(lines)

        async def handle_delegate(params: dict[str, Any]) -> str:
            result = await self.delegate(
                params["agent_name"],
                params["task"],
                params.get("context", ""),
            )
            if result.error:
                return f"Agent error: {result.error}"
            return result.response

        async def handle_delegate_parallel(params: dict[str, Any]) -> str:
            results = await self.delegate_parallel(params["delegations"])
            output = []
            for r in results:
                if r.error:
                    output.append(f"[{r.agent_name}] Error: {r.error}")
                else:
                    output.append(f"[{r.agent_name}] {r.response}")
            return "\n\n---\n\n".join(output)

        return {
            "list_agents": handle_list_agents,
            "delegate_to_agent": handle_delegate,
            "delegate_parallel": handle_delegate_parallel,
        }
