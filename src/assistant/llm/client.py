"""Claude API client with streaming and tool use loop."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Callable, Awaitable
from typing import Any

import anthropic

from assistant.llm.types import (
    Message,
    Role,
    StreamEvent,
    StreamEventType,
    ToolCall,
    ToolResult,
)

logger = logging.getLogger(__name__)

# Type for the tool executor callback
ToolExecutor = Callable[[ToolCall], Awaitable[ToolResult]]


class ClaudeClient:
    """Streaming Claude client with tool-use loop."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def stream_with_tool_loop(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_executor: ToolExecutor | None = None,
        max_tool_rounds: int = 10,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream a response, automatically handling tool use loops.

        Yields StreamEvents for the caller to render.
        When Claude requests tool use, executes via tool_executor and
        continues the conversation until a final text response.
        """
        current_messages = list(messages)

        for _round in range(max_tool_rounds):
            tool_calls_in_round: list[ToolCall] = []
            text_parts: list[str] = []
            current_tool_json = ""
            current_tool_name = ""
            current_tool_id = ""

            kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "system": system,
                "messages": current_messages,
            }
            if tools:
                kwargs["tools"] = tools

            async with self._client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if block.type == "tool_use":
                            current_tool_name = block.name
                            current_tool_id = block.id
                            current_tool_json = ""
                            yield StreamEvent(
                                type=StreamEventType.TOOL_USE_START,
                                text=current_tool_name,
                            )
                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            text_parts.append(delta.text)
                            yield StreamEvent(
                                type=StreamEventType.TEXT_DELTA,
                                text=delta.text,
                            )
                        elif delta.type == "input_json_delta":
                            current_tool_json += delta.partial_json
                    elif event.type == "content_block_stop":
                        if current_tool_name:
                            try:
                                tool_input = json.loads(current_tool_json) if current_tool_json else {}
                            except json.JSONDecodeError:
                                tool_input = {}
                            tc = ToolCall(
                                id=current_tool_id,
                                name=current_tool_name,
                                input=tool_input,
                            )
                            tool_calls_in_round.append(tc)
                            yield StreamEvent(
                                type=StreamEventType.TOOL_USE_COMPLETE,
                                tool_call=tc,
                            )
                            current_tool_name = ""
                            current_tool_id = ""
                            current_tool_json = ""

            if not tool_calls_in_round:
                yield StreamEvent(
                    type=StreamEventType.MESSAGE_COMPLETE,
                    text="".join(text_parts),
                )
                return

            # Build assistant message with both text and tool_use blocks
            assistant_content: list[dict[str, Any]] = []
            if text_parts:
                assistant_content.append({"type": "text", "text": "".join(text_parts)})
            for tc in tool_calls_in_round:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.input,
                })

            current_messages.append({"role": "assistant", "content": assistant_content})

            # Execute tools and collect results
            tool_results: list[dict[str, Any]] = []
            for tc in tool_calls_in_round:
                if tool_executor:
                    result = await tool_executor(tc)
                else:
                    result = ToolResult(
                        tool_use_id=tc.id,
                        content="No tool executor configured",
                        is_error=True,
                    )
                tool_results.append(result.to_api())

            current_messages.append({"role": "user", "content": tool_results})

        yield StreamEvent(
            type=StreamEventType.ERROR,
            error="Max tool rounds exceeded",
        )
