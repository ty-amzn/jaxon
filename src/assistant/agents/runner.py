"""AgentRunner — run a single agent with scoped tool set and isolated session."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from assistant.agents.types import AgentDef, AgentResult
from assistant.gateway.permissions import PermissionManager
from assistant.llm.base import BaseLLMClient
from assistant.llm.metrics import MetricsContext
from assistant.llm.router import LLMRouter
from assistant.llm.types import StreamEventType, ToolCall, ToolResult
from assistant.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentRunner:
    """Runs an agent in an isolated context with scoped tools."""

    def __init__(
        self,
        llm: LLMRouter,
        tool_registry: ToolRegistry,
    ) -> None:
        self._router = llm
        self._tool_registry = tool_registry

    def _filter_tools(self, agent: AgentDef) -> list[dict[str, Any]]:
        """Filter tool definitions based on agent's allowed/denied tools."""
        all_tools = self._tool_registry.definitions

        if agent.allowed_tools:
            tools = [t for t in all_tools if t["name"] in agent.allowed_tools]
        elif agent.denied_tools:
            tools = [t for t in all_tools if t["name"] not in agent.denied_tools]
        else:
            tools = list(all_tools)

        # Auto-include activate_skill when agent has skills available
        has_skills = agent.allowed_skills is None or len(agent.allowed_skills) > 0
        if has_skills and not any(t["name"] == "activate_skill" for t in tools):
            for t in all_tools:
                if t["name"] == "activate_skill":
                    tools.append(t)
                    break

        # Remove delegation tools unless agent is allowed to delegate
        if not agent.can_delegate:
            tools = [t for t in tools if t["name"] not in ("delegate_to_agent", "delegate_parallel", "list_agents")]
        return tools

    async def run(
        self,
        agent: AgentDef,
        task: str,
        context: str = "",
        base_system_prompt: str = "",
        permission_override: PermissionManager | None = None,
        content: str | list[dict] | None = None,
    ) -> AgentResult:
        """Run an agent on a specific task.

        Args:
            agent: Agent definition
            task: The task/query to give the agent
            context: Additional context to include
            base_system_prompt: Base system prompt (memory/identity)
            permission_override: Optional PermissionManager to use instead of the registry's default
            content: Pre-built multimodal content (text + image blocks). When provided,
                     used as the message content directly instead of building from task/context.
        """
        # Build system prompt
        system_parts = []
        if base_system_prompt:
            system_parts.append(base_system_prompt)
        if agent.system_prompt:
            system_parts.append(f"# Agent Role: {agent.name}\n\n{agent.system_prompt}")
        system_prompt = "\n\n---\n\n".join(system_parts)

        # Build messages
        if content is not None:
            messages = [{"role": "user", "content": content}]
        else:
            user_content = task
            if context:
                user_content = f"Context:\n{context}\n\nTask:\n{task}"
            messages = [{"role": "user", "content": user_content}]

        # Filter tools
        tools = self._filter_tools(agent)

        # Track tool calls
        tool_calls_made: list[dict] = []

        # Generate a session ID for this agent run so inference and tool
        # events can be correlated in Observatory.
        agent_session_id = uuid.uuid4().hex[:12]

        # Create scoped tool executor
        allowed_tool_names = {t["name"] for t in tools}

        async def scoped_executor(tool_call: ToolCall) -> ToolResult:
            if tool_call.name not in allowed_tool_names:
                return ToolResult(
                    tool_use_id=tool_call.id,
                    content=f"Tool '{tool_call.name}' is not available to this agent.",
                    is_error=True,
                )
            result = await self._tool_registry.execute(
                tool_call, permission_override=permission_override,
                session_id=agent_session_id,
            )
            tool_calls_made.append({
                "name": tool_call.name,
                "input": tool_call.input,
                "output": result.content[:500],
            })
            return result

        # Select client: per-agent model or default router
        client: BaseLLMClient = self._router
        metrics: MetricsContext | None = None
        if agent.model:
            client = self._router.get_client_for_model(agent.model)
            logger.info("Agent %s using model %s", agent.name, agent.model)

            # Raw clients bypass the router's metrics — track manually
            metrics = MetricsContext(
                self._router._metrics, session_id=agent_session_id,
                agent_name=agent.name,
            )
            # Parse provider/model from "provider/model" syntax
            if "/" in agent.model:
                prov, model_name = agent.model.split("/", 1)
            else:
                prov, model_name = "unknown", agent.model
            metrics.start()
            metrics.record_routing_info(prov, model_name)
            if tools:
                metrics.record_tools_provided()

        # Run the LLM with tool loop (no streaming to user)
        full_response = ""
        response_parts: list[str] = []
        try:
            # When going through the router, pass agent_name/session_id for its own metrics.
            # Raw clients don't accept these kwargs — metrics are tracked via MetricsContext above.
            kwargs: dict[str, Any] = {
                "system": system_prompt,
                "messages": messages,
                "tools": tools if tools else None,
                "tool_executor": scoped_executor,
                "max_tool_rounds": agent.max_tool_rounds,
            }
            if not agent.model:
                kwargs["session_id"] = agent_session_id
                kwargs["agent_name"] = agent.name

            async for event in client.stream_with_tool_loop(**kwargs):
                if event.type == StreamEventType.TEXT_DELTA:
                    full_response += event.text
                    response_parts.append(event.text)
                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    full_response = event.text
                    if metrics:
                        metrics.record_usage(
                            event.input_tokens, event.output_tokens,
                            event.stop_reason,
                        )
                elif event.type == StreamEventType.TOOL_USE_COMPLETE:
                    if metrics:
                        metrics.record_tool_round()
                elif event.type == StreamEventType.ERROR:
                    if metrics:
                        metrics.record_error(event.error)
                    return AgentResult(
                        agent_name=agent.name,
                        response="",
                        tool_calls_made=tool_calls_made,
                        error=event.error,
                    )
        except Exception as e:
            logger.exception("Agent %s failed", agent.name)
            if metrics:
                metrics.record_error(str(e))
            return AgentResult(
                agent_name=agent.name,
                response="",
                tool_calls_made=tool_calls_made,
                error=str(e),
            )
        finally:
            if metrics:
                metrics.record_prompt(system_prompt, messages)
                metrics.record_response("".join(response_parts))
                await metrics.finish()

        return AgentResult(
            agent_name=agent.name,
            response=full_response,
            tool_calls_made=tool_calls_made,
        )
