"""Orchestrator — delegate tasks to specialized sub-agents, exposed as tools."""

from __future__ import annotations

import asyncio
import base64
import contextvars
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

from assistant.agents.background import (
    BackgroundTaskManager,
    TaskStatus,
    _auto_approve,
    current_delivery,
    current_images,
)
from assistant.agents.loader import AgentLoader
from assistant.agents.runner import AgentRunner
from assistant.agents.types import AgentResult
from assistant.gateway.permissions import PermissionManager
from assistant.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

# Per-async-context delegation depth so background tasks get independent counters.
_delegation_depth_var: contextvars.ContextVar[int] = contextvars.ContextVar(
    "_delegation_depth", default=0,
)

MAX_DELEGATION_DEPTH = 3


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
        self._bg_manager = bg_manager

    async def delegate(
        self, agent_name: str, task: str, context: str = "",
        content: str | list[dict] | None = None,
    ) -> AgentResult:
        """Delegate a task to a named agent."""
        depth = _delegation_depth_var.get()
        if depth >= MAX_DELEGATION_DEPTH:
            return AgentResult(
                agent_name=agent_name,
                response="",
                error=f"Maximum delegation depth ({MAX_DELEGATION_DEPTH}) exceeded. Cannot delegate further.",
            )

        agent = self._loader.get_agent(agent_name)
        if agent is None:
            return AgentResult(
                agent_name=agent_name,
                response="",
                error=f"Agent '{agent_name}' not found.",
            )

        _delegation_depth_var.set(depth + 1)
        try:
            base_prompt = self._memory.get_system_prompt()
            return await self._runner.run(
                agent, task, context=context,
                base_system_prompt=base_prompt, content=content,
            )
        finally:
            _delegation_depth_var.set(depth)

    async def delegate_parallel(
        self, delegations: list[dict[str, Any]]
    ) -> list[AgentResult]:
        """Run multiple agent delegations in parallel.

        Each delegation is a dict with keys: agent_name, task, context (optional),
        images (optional list of {data, media_type}).
        """
        tasks = []
        for d in delegations:
            images = d.get("images")
            agent = self._loader.get_agent(d["agent_name"])
            if agent is not None and images:
                task_text, content = self._build_content_for_agent(
                    agent, d["task"], images,
                )
            else:
                task_text = d["task"]
                content = self._build_content(task_text, images)
            tasks.append(
                self.delegate(
                    d["agent_name"],
                    task_text,
                    d.get("context", ""),
                    content=content,
                )
            )
        return await asyncio.gather(*tasks)

    @staticmethod
    def _model_supports_vision(agent: "AgentDef") -> bool:
        """Check whether an agent's model supports vision.

        Uses explicit ``vision`` flag if set, otherwise heuristic based on
        model name.
        """
        from assistant.llm.router import LLMRouter

        if agent.vision is not None:
            return agent.vision
        # No model specified → will use default (likely Claude) which supports vision
        if not agent.model:
            return True
        return LLMRouter.model_supports_vision(agent.model)

    @staticmethod
    def _save_images_to_temp(
        images: list[dict[str, str]],
    ) -> list[Path]:
        """Save base64 images to temp files, return their paths."""
        paths: list[Path] = []
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        for img in images:
            media_type = img.get("media_type", "image/png")
            ext = ext_map.get(media_type, ".png")
            data = base64.b64decode(img["data"])
            tmp = tempfile.NamedTemporaryFile(
                suffix=ext, prefix="agent_img_", delete=False,
            )
            tmp.write(data)
            tmp.close()
            paths.append(Path(tmp.name))
        return paths

    def _build_content_for_agent(
        self,
        agent: "AgentDef",
        task: str,
        images: list[dict[str, str]] | None,
    ) -> tuple[str, list[dict] | None]:
        """Build content for an agent, handling vision vs text-only models.

        Returns (possibly-augmented task text, multimodal content or None).
        For vision models, returns image content blocks.
        For text-only models, saves images to temp files and appends paths to task.
        """
        if not images:
            return task, None

        if self._model_supports_vision(agent):
            # Vision model — pass images inline
            content: list[dict] = [{"type": "text", "text": task}]
            for img in images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "data": img["data"],
                        "media_type": img["media_type"],
                    },
                })
            return task, content

        # Text-only model — save images to temp files
        paths = self._save_images_to_temp(images)
        path_list = "\n".join(f"  - {p}" for p in paths)
        augmented_task = (
            f"{task}\n\n"
            f"[Note: {len(paths)} image(s) were provided but your model does not "
            f"support vision. The images have been saved to temporary files:\n"
            f"{path_list}\n"
            f"You can use tools (e.g. browse_web, delegate_to_agent with a vision "
            f"model) to analyze them if needed.]"
        )
        return augmented_task, None

    @staticmethod
    def _build_content(
        task: str, images: list[dict[str, str]] | None,
    ) -> list[dict] | None:
        """Build multimodal content blocks from task text and optional images."""
        if not images:
            return None
        content: list[dict] = [{"type": "text", "text": task}]
        for img in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "data": img["data"],
                    "media_type": img["media_type"],
                },
            })
        return content

    async def _run_background(
        self,
        bt: Any,  # BackgroundTask
        agent_name: str,
        task: str,
        context: str,
        content: str | list[dict] | None = None,
    ) -> None:
        """Run an agent in the background, delivering results when done."""
        # Reset delegation depth so background agents get a fresh counter
        # independent of any foreground delegation in progress.
        _delegation_depth_var.set(0)
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
                content=content,
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
                if bt._deliver and not bt.silent:
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
        # Build agent catalog for tool descriptions
        agents = self._loader.list_agents()
        agent_names = [a.name for a in agents]
        agent_catalog = "; ".join(
            f"{a.name}: {a.description}" for a in agents
        ) if agents else "No agents loaded"

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
                "description": f"Delegate a task to a specialized agent. The agent runs autonomously with its own tool set and returns a result. Set background=true for long-running tasks (e.g. deep research) so the user can continue chatting while the agent works.\n\nAvailable agents: {agent_catalog}",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Name of the agent to delegate to",
                            **({"enum": agent_names} if agent_names else {}),
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
                        "silent": {
                            "type": "boolean",
                            "description": "If true (requires background=true), skip auto-delivery of results. The agent must use send_notification to explicitly notify the user. Use for tasks where the agent should only notify when something noteworthy is found.",
                            "default": False,
                        },
                        "images": {
                            "type": "array",
                            "description": "Base64-encoded images to include. Each item has 'data' (base64 string) and 'media_type' (e.g. image/jpeg).",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "data": {"type": "string"},
                                    "media_type": {"type": "string"},
                                },
                                "required": ["data", "media_type"],
                            },
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
                                    "images": {
                                        "type": "array",
                                        "description": "Base64-encoded images to include.",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "data": {"type": "string"},
                                                "media_type": {"type": "string"},
                                            },
                                            "required": ["data", "media_type"],
                                        },
                                    },
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
            # Use explicit images if provided, otherwise auto-forward from current turn
            images = params.get("images") or current_images.get()

            # Resolve agent to check vision capability
            agent = self._loader.get_agent(params["agent_name"])
            if agent is not None and images:
                task, content = self._build_content_for_agent(
                    agent, params["task"], images,
                )
            else:
                task = params["task"]
                content = self._build_content(task, images)

            if background and self._bg_manager is not None:
                # Background path: fire-and-forget
                silent = params.get("silent", False)
                deliver = current_delivery.get()
                bt = self._bg_manager.create(
                    agent_name=params["agent_name"],
                    task_description=params["task"],
                    deliver=deliver,
                    silent=silent,
                )
                asyncio.create_task(
                    self._run_background(
                        bt,
                        params["agent_name"],
                        task,
                        params.get("context", ""),
                        content=content,
                    )
                )
                return f"Background task started: {bt.id}. Results will be delivered when complete. Use task_status to check progress."

            # Foreground path
            result = await self.delegate(
                params["agent_name"],
                task,
                params.get("context", ""),
                content=content,
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
