"""AgentRunner — run a single agent with scoped tool set and isolated session."""

from __future__ import annotations

import logging
from typing import Any

from assistant.agents.types import AgentDef, AgentResult
from assistant.llm.base import BaseLLMClient
from assistant.llm.types import StreamEventType, ToolCall, ToolResult
from assistant.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentRunner:
    """Runs an agent in an isolated context with scoped tools."""

    def __init__(
        self,
        llm: BaseLLMClient,
        tool_registry: ToolRegistry,
    ) -> None:
        self._llm = llm
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

        # Remove delegation tools to prevent recursive delegation
        tools = [t for t in tools if t["name"] not in ("delegate_to_agent", "delegate_parallel", "list_agents")]
        return tools

    async def run(
        self,
        agent: AgentDef,
        task: str,
        context: str = "",
        base_system_prompt: str = "",
    ) -> AgentResult:
        """Run an agent on a specific task.

        Args:
            agent: Agent definition
            task: The task/query to give the agent
            context: Additional context to include
            base_system_prompt: Base system prompt (memory/identity)
        """
        # Build system prompt
        system_parts = []
        if base_system_prompt:
            system_parts.append(base_system_prompt)
        if agent.system_prompt:
            system_parts.append(f"# Agent Role: {agent.name}\n\n{agent.system_prompt}")
        system_prompt = "\n\n---\n\n".join(system_parts)

        # Build messages
        user_content = task
        if context:
            user_content = f"Context:\n{context}\n\nTask:\n{task}"

        messages = [{"role": "user", "content": user_content}]

        # Filter tools
        tools = self._filter_tools(agent)

        # Track tool calls
        tool_calls_made: list[dict] = []

        # Create scoped tool executor
        allowed_tool_names = {t["name"] for t in tools}

        async def scoped_executor(tool_call: ToolCall) -> ToolResult:
            if tool_call.name not in allowed_tool_names:
                return ToolResult(
                    tool_use_id=tool_call.id,
                    content=f"Tool '{tool_call.name}' is not available to this agent.",
                    is_error=True,
                )
            result = await self._tool_registry.execute(tool_call)
            tool_calls_made.append({
                "name": tool_call.name,
                "input": tool_call.input,
                "output": result.content[:500],
            })
            return result

        # Run the LLM with tool loop (no streaming to user)
        full_response = ""
        try:
            async for event in self._llm.stream_with_tool_loop(
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None,
                tool_executor=scoped_executor,
                max_tool_rounds=agent.max_tool_rounds,
            ):
                if event.type == StreamEventType.TEXT_DELTA:
                    full_response += event.text
                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    full_response = event.text
                elif event.type == StreamEventType.ERROR:
                    return AgentResult(
                        agent_name=agent.name,
                        response="",
                        tool_calls_made=tool_calls_made,
                        error=event.error,
                    )
        except Exception as e:
            logger.exception("Agent %s failed", agent.name)
            return AgentResult(
                agent_name=agent.name,
                response="",
                tool_calls_made=tool_calls_made,
                error=str(e),
            )

        return AgentResult(
            agent_name=agent.name,
            response=full_response,
            tool_calls_made=tool_calls_made,
        )
