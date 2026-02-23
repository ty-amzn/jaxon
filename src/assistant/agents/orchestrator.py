"""Orchestrator — delegate tasks to specialized sub-agents, exposed as tools."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from assistant.agents.background import (
    BackgroundTaskManager,
    TaskStatus,
    _auto_approve,
    current_delivery,
)
from assistant.agents.loader import AgentLoader
from assistant.agents.runner import AgentRunner
from assistant.agents.types import AgentResult
from assistant.gateway.permissions import PermissionManager
from assistant.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrates delegation to sub-agents. Provides tool definitions."""

    def __init__(
        self,
        loader: AgentLoader,
        runner: AgentRunner,
        memory: MemoryManager,
        bg_manager: BackgroundTaskManager | None = None,
    ) -> None:
        self._loader = loader
        self._runner = runner
        self._memory = memory
        self._delegation_depth = 0
        self._bg_manager = bg_manager

    async def delegate(self, agent_name: str, task: str, context: str = "") -> AgentResult:
        """Delegate a task to a named agent."""
        if self._delegation_depth >= 2:
            return AgentResult(
                agent_name=agent_name,
                response="",
                error="Maximum delegation depth (2) exceeded. Cannot delegate further.",
            )

        agent = self._loader.get_agent(agent_name)
        if agent is None:
            return AgentResult(
                agent_name=agent_name,
                response="",
                error=f"Agent '{agent_name}' not found.",
            )

        self._delegation_depth += 1
        try:
            base_prompt = self._memory.get_system_prompt()
            return await self._runner.run(agent, task, context=context, base_system_prompt=base_prompt)
        finally:
            self._delegation_depth -= 1

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

    async def _run_background(
        self,
        bt: Any,  # BackgroundTask
        agent_name: str,
        task: str,
        context: str,
    ) -> None:
        """Run an agent in the background, delivering results when done."""
        bt.status = TaskStatus.RUNNING
        try:
            agent = self._loader.get_agent(agent_name)
            if agent is None:
                bt.status = TaskStatus.ERROR
                bt.error = f"Agent '{agent_name}' not found."
                bt.finished_at = time.time()
                if bt._deliver:
                    await bt._deliver(f"Background task {bt.id} failed: {bt.error}")
                return

            base_prompt = self._memory.get_system_prompt()
            # Use auto-approve permissions for background agents
            auto_perms = PermissionManager(_auto_approve)
            result = await self._runner.run(
                agent, task, context=context,
                base_system_prompt=base_prompt,
                permission_override=auto_perms,
            )

            if result.error:
                bt.status = TaskStatus.ERROR
                bt.error = result.error
                bt.finished_at = time.time()
                if bt._deliver:
                    await bt._deliver(
                        f"Background task {bt.id} ({agent_name}) failed:\n{result.error}"
                    )
            else:
                bt.status = TaskStatus.DONE
                bt.result = result.response
                bt.finished_at = time.time()
                if bt._deliver:
                    await bt._deliver(
                        f"Background task {bt.id} ({agent_name}) completed:\n\n{result.response}"
                    )
        except Exception as e:
            logger.exception("Background task %s failed", bt.id)
            bt.status = TaskStatus.ERROR
            bt.error = str(e)
            bt.finished_at = time.time()
            if bt._deliver:
                try:
                    await bt._deliver(
                        f"Background task {bt.id} ({agent_name}) error:\n{e}"
                    )
                except Exception:
                    logger.exception("Failed to deliver background task error")

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return tool definitions for delegation tools."""
        defs = [
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
                "description": "Delegate a task to a specialized agent. The agent runs autonomously with its own tool set and returns a result. Set background=true for long-running tasks (e.g. deep research) so the user can continue chatting while the agent works.",
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
                        "background": {
                            "type": "boolean",
                            "description": "If true, run the agent in the background and return immediately with a task ID. Use for long-running tasks like deep research so the user can keep chatting. Results are delivered asynchronously.",
                            "default": False,
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

        # Add task_status tool if background manager is available
        if self._bg_manager is not None:
            defs.append({
                "name": "task_status",
                "description": "Check the status or result of a background agent task.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The background task ID to check",
                        },
                    },
                    "required": ["task_id"],
                },
            })

        return defs

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
            background = params.get("background", False)

            if background and self._bg_manager is not None:
                # Background path: fire-and-forget
                deliver = current_delivery.get()
                bt = self._bg_manager.create(
                    agent_name=params["agent_name"],
                    task_description=params["task"],
                    deliver=deliver,
                )
                asyncio.create_task(
                    self._run_background(
                        bt,
                        params["agent_name"],
                        params["task"],
                        params.get("context", ""),
                    )
                )
                return f"Background task started: {bt.id}. Results will be delivered when complete. Use task_status to check progress."

            # Foreground path (unchanged)
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

        async def handle_task_status(params: dict[str, Any]) -> str:
            if self._bg_manager is None:
                return "Background tasks not available."
            task_id = params["task_id"]
            bt = self._bg_manager.get(task_id)
            if bt is None:
                return f"No task found with ID: {task_id}"
            info = f"Task {bt.id} ({bt.agent_name}): {bt.status.value}"
            if bt.status == TaskStatus.DONE:
                info += f"\n\nResult:\n{bt.result}"
            elif bt.status == TaskStatus.ERROR:
                info += f"\n\nError: {bt.error}"
            return info

        handlers = {
            "list_agents": handle_list_agents,
            "delegate_to_agent": handle_delegate,
            "delegate_parallel": handle_delegate_parallel,
        }

        if self._bg_manager is not None:
            handlers["task_status"] = handle_task_status

        return handlers
