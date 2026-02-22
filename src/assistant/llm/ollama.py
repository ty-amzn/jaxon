"""Ollama client using OpenAI-compatible API with streaming and tool support."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from assistant.llm.base import BaseLLMClient, ToolExecutor
from assistant.llm.types import (
    LLMConfig,
    Provider,
    StreamEvent,
    StreamEventType,
    ToolCall,
    ToolResult,
)

logger = logging.getLogger(__name__)


class OllamaClient(BaseLLMClient):
    """Streaming Ollama client using OpenAI-compatible API."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._base_url = config.base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=120.0)

    @classmethod
    def from_settings(
        cls,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        max_tokens: int = 8192,
    ) -> "OllamaClient":
        """Create an OllamaClient from individual settings."""
        config = LLMConfig(
            provider=Provider.OLLAMA,
            model=model,
            max_tokens=max_tokens,
            base_url=base_url,
        )
        return cls(config)

    async def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def get_embedding(self, text: str) -> list[float] | None:
        """Get embedding for text using Ollama embeddings API."""
        try:
            response = await self._client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._config.model, "prompt": text},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
        except Exception as e:
            logger.warning(f"Failed to get embedding: {e}")
        return None

    def _convert_tools_to_openai(self, tools: list[dict] | None) -> list[dict] | None:
        """Convert Anthropic tool format to OpenAI format."""
        if not tools:
            return None

        openai_tools = []
        for tool in tools:
            if tool.get("type") == "function" or "function" in tool:
                # Already in OpenAI format or converted
                openai_tools.append(tool)
                continue

            # Convert Anthropic format to OpenAI format
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                }
            }
            openai_tools.append(openai_tool)

        return openai_tools

    def _convert_messages_to_openai(
        self, system: str, messages: list[dict]
    ) -> list[dict]:
        """Convert messages to OpenAI format with system message."""
        openai_messages = [{"role": "system", "content": system}]

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")

            # Handle string content
            if isinstance(content, str):
                openai_messages.append({"role": role, "content": content})
            # Handle list content (multimodal or tool results)
            elif isinstance(content, list):
                # Check if it's tool results
                if role == "user" and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
                    for item in content:
                        if item.get("type") == "tool_result":
                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": item.get("tool_use_id", ""),
                                "content": item.get("content", ""),
                            })
                # Check if it's tool use (assistant with tool_calls)
                elif role == "assistant":
                    text_content = ""
                    tool_calls = []

                    for item in content:
                        if item.get("type") == "text":
                            text_content += item.get("text", "")
                        elif item.get("type") == "tool_use":
                            # Convert to OpenAI tool call format
                            tool_calls.append({
                                "id": item.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": item.get("name", ""),
                                    "arguments": json.dumps(item.get("input", {})),
                                }
                            })

                    msg_dict: dict[str, Any] = {"role": "assistant"}
                    if text_content:
                        msg_dict["content"] = text_content
                    if tool_calls:
                        msg_dict["tool_calls"] = tool_calls
                    openai_messages.append(msg_dict)
                else:
                    # Handle other list content (e.g., multimodal)
                    openai_messages.append({"role": role, "content": content})
            else:
                openai_messages.append({"role": role, "content": str(content)})

        return openai_messages

    async def stream_with_tool_loop(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_executor: ToolExecutor | None = None,
        max_tool_rounds: int = 10,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream a response using OpenAI-compatible API with tool support."""
        current_messages = self._convert_messages_to_openai(system, messages)
        openai_tools = self._convert_tools_to_openai(tools)

        for _round in range(max_tool_rounds):
            tool_calls_in_round: list[ToolCall] = []
            text_parts: list[str] = []

            # Build request
            request_body: dict[str, Any] = {
                "model": self._config.model,
                "max_tokens": self._config.max_tokens,
                "messages": current_messages,
                "stream": True,
            }
            if openai_tools:
                request_body["tools"] = openai_tools

            try:
                async with self._client.stream(
                    "POST",
                    f"{self._base_url}/v1/chat/completions",
                    json=request_body,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield StreamEvent(
                            type=StreamEventType.ERROR,
                            error=f"Ollama API error: {response.status_code} - {error_text.decode()}",
                        )
                        return

                    current_tool_calls: dict[int, dict[str, Any]] = {}

                    async for line in response.aiter_lines():
                        if not line or line == "data: [DONE]":
                            continue

                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                            except json.JSONDecodeError:
                                continue

                            delta = data.get("choices", [{}])[0].get("delta", {})

                            # Handle text content
                            if "content" in delta and delta["content"]:
                                text_parts.append(delta["content"])
                                yield StreamEvent(
                                    type=StreamEventType.TEXT_DELTA,
                                    text=delta["content"],
                                )

                            # Handle tool calls
                            if "tool_calls" in delta:
                                for tc_delta in delta["tool_calls"]:
                                    idx = tc_delta.get("index", 0)

                                    if idx not in current_tool_calls:
                                        current_tool_calls[idx] = {
                                            "id": "",
                                            "name": "",
                                            "arguments": "",
                                        }
                                        yield StreamEvent(
                                            type=StreamEventType.TOOL_USE_START,
                                            text="",  # Name comes in delta
                                        )

                                    if "id" in tc_delta:
                                        current_tool_calls[idx]["id"] = tc_delta["id"]
                                    if "function" in tc_delta:
                                        if "name" in tc_delta["function"]:
                                            current_tool_calls[idx]["name"] = tc_delta["function"]["name"]
                                        if "arguments" in tc_delta["function"]:
                                            current_tool_calls[idx]["arguments"] += tc_delta["function"]["arguments"]

            except Exception as e:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=f"Ollama connection error: {e}",
                )
                return

            # Process completed tool calls
            for idx in sorted(current_tool_calls.keys()):
                tc_data = current_tool_calls[idx]
                try:
                    tool_input = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                except json.JSONDecodeError:
                    tool_input = {}

                tc = ToolCall(
                    id=tc_data["id"] or f"tool_{idx}",
                    name=tc_data["name"],
                    input=tool_input,
                )
                tool_calls_in_round.append(tc)
                yield StreamEvent(
                    type=StreamEventType.TOOL_USE_COMPLETE,
                    tool_call=tc,
                )

            if not tool_calls_in_round:
                yield StreamEvent(
                    type=StreamEventType.MESSAGE_COMPLETE,
                    text="".join(text_parts),
                )
                return

            # Add assistant message with tool calls
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            if text_parts:
                assistant_msg["content"] = "".join(text_parts)
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.input),
                    }
                }
                for tc in tool_calls_in_round
            ]
            current_messages.append(assistant_msg)

            # Execute tools and add results
            for tc in tool_calls_in_round:
                if tool_executor:
                    result = await tool_executor(tc)
                else:
                    result = ToolResult(
                        tool_use_id=tc.id,
                        content="No tool executor configured",
                        is_error=True,
                    )

                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result.content,
                })

        yield StreamEvent(
            type=StreamEventType.ERROR,
            error="Max tool rounds exceeded",
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()