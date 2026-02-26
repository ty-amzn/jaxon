"""AWS Bedrock client using the Converse API."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from assistant.llm.base import BaseLLMClient, ToolExecutor
from assistant.llm.types import (
    LLMConfig,
    StreamEvent,
    StreamEventType,
    ToolCall,
    ToolResult,
)

import boto3

logger = logging.getLogger(__name__)


class BedrockClient(BaseLLMClient):
    """Streaming Bedrock client using the Converse API with tool-use loop."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._boto3_client = boto3.client(
            "bedrock-runtime",
            region_name=config.region or "us-east-1",
        )

    # ------------------------------------------------------------------
    # Format converters: Anthropic → Bedrock Converse
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_tools(tools: list[dict]) -> list[dict]:
        """Convert Anthropic-format tool definitions to Bedrock toolSpec."""
        specs: list[dict] = []
        for tool in tools:
            spec: dict[str, Any] = {
                "toolSpec": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "inputSchema": {
                        "json": tool.get("input_schema", {}),
                    },
                }
            }
            specs.append(spec)
        return specs

    @staticmethod
    def _convert_messages(messages: list[dict]) -> list[dict]:
        """Convert Anthropic-format messages to Bedrock Converse format."""
        result: list[dict] = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            bedrock_content: list[dict[str, Any]] = []

            if isinstance(content, str):
                bedrock_content.append({"text": content})
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, str):
                        bedrock_content.append({"text": block})
                    elif isinstance(block, dict):
                        btype = block.get("type", "")
                        if btype == "text":
                            bedrock_content.append({"text": block["text"]})
                        elif btype == "tool_use":
                            bedrock_content.append({
                                "toolUse": {
                                    "toolUseId": block["id"],
                                    "name": block["name"],
                                    "input": block.get("input", {}),
                                },
                            })
                        elif btype == "tool_result":
                            result_content: list[dict] = []
                            raw = block.get("content", "")
                            if isinstance(raw, str):
                                result_content.append({"text": raw})
                            elif isinstance(raw, list):
                                for rc in raw:
                                    if isinstance(rc, dict) and rc.get("type") == "text":
                                        result_content.append({"text": rc["text"]})
                                    elif isinstance(rc, str):
                                        result_content.append({"text": rc})
                            status = "error" if block.get("is_error") else "success"
                            bedrock_content.append({
                                "toolResult": {
                                    "toolUseId": block["tool_use_id"],
                                    "content": result_content,
                                    "status": status,
                                },
                            })
                        elif btype == "image":
                            source = block.get("source", {})
                            if source.get("type") == "base64":
                                fmt = source.get("media_type", "image/png").split("/")[-1]
                                # Map MIME subtypes to Bedrock format names
                                fmt_map = {"jpeg": "jpeg", "jpg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
                                bedrock_content.append({
                                    "image": {
                                        "format": fmt_map.get(fmt, "png"),
                                        "source": {
                                            "bytes": base64.b64decode(source["data"]),
                                        },
                                    },
                                })
                        else:
                            # Unknown block type — pass as text
                            bedrock_content.append({"text": str(block)})

            if bedrock_content:
                result.append({"role": role, "content": bedrock_content})

        return result

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def stream_with_tool_loop(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_executor: ToolExecutor | None = None,
        max_tool_rounds: int = 10,
    ) -> AsyncGenerator[StreamEvent, None]:
        current_messages = list(messages)

        for _round in range(max_tool_rounds):
            tool_calls_in_round: list[ToolCall] = []
            text_parts: list[str] = []

            try:
                async for event in self._stream_single(
                    system, current_messages, tools
                ):
                    if event.type == StreamEventType.TEXT_DELTA:
                        text_parts.append(event.text)
                        yield event
                    elif event.type == StreamEventType.TOOL_USE_START:
                        yield event
                    elif event.type == StreamEventType.TOOL_USE_COMPLETE:
                        if event.tool_call:
                            tool_calls_in_round.append(event.tool_call)
                        yield event
                    elif event.type == StreamEventType.ERROR:
                        yield event
                        return
            except Exception as exc:
                logger.error("Bedrock stream error: %s", exc)
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=str(exc),
                )
                return

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

        # Max tool rounds exhausted — summary without tools
        current_messages.append({
            "role": "user",
            "content": (
                "You've used all available tool rounds. Please summarize what you've "
                "accomplished so far and what remains to be done."
            ),
        })

        summary_parts: list[str] = []
        try:
            async for event in self._stream_single(
                system, current_messages, tools=None
            ):
                if event.type == StreamEventType.TEXT_DELTA:
                    summary_parts.append(event.text)
                    yield event
        except Exception as exc:
            logger.error("Bedrock summary stream error: %s", exc)
            yield StreamEvent(type=StreamEventType.ERROR, error=str(exc))
            return

        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            text="".join(summary_parts),
        )

    async def _stream_single(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Run a single Bedrock converse_stream call, bridging sync→async."""
        queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()

        def _run_sync() -> None:
            try:
                kwargs: dict[str, Any] = {
                    "modelId": self._config.model,
                    "system": [{"text": system}],
                    "messages": self._convert_messages(messages),
                    "inferenceConfig": {
                        "maxTokens": self._config.max_tokens,
                    },
                }
                if tools:
                    kwargs["toolConfig"] = {
                        "tools": self._convert_tools(tools),
                    }

                response = self._boto3_client.converse_stream(**kwargs)
                stream = response.get("stream", [])

                current_tool_name = ""
                current_tool_id = ""
                current_tool_json = ""

                for evt in stream:
                    if "contentBlockStart" in evt:
                        start = evt["contentBlockStart"].get("start", {})
                        if "toolUse" in start:
                            current_tool_name = start["toolUse"]["name"]
                            current_tool_id = start["toolUse"]["toolUseId"]
                            current_tool_json = ""
                            queue.put_nowait(StreamEvent(
                                type=StreamEventType.TOOL_USE_START,
                                text=current_tool_name,
                            ))

                    elif "contentBlockDelta" in evt:
                        delta = evt["contentBlockDelta"].get("delta", {})
                        if "text" in delta:
                            queue.put_nowait(StreamEvent(
                                type=StreamEventType.TEXT_DELTA,
                                text=delta["text"],
                            ))
                        elif "toolUse" in delta:
                            current_tool_json += delta["toolUse"].get("input", "")

                    elif "contentBlockStop" in evt:
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
                            queue.put_nowait(StreamEvent(
                                type=StreamEventType.TOOL_USE_COMPLETE,
                                tool_call=tc,
                            ))
                            current_tool_name = ""
                            current_tool_id = ""
                            current_tool_json = ""

                # Signal completion
                queue.put_nowait(None)

            except Exception as exc:
                queue.put_nowait(StreamEvent(
                    type=StreamEventType.ERROR,
                    error=str(exc),
                ))
                queue.put_nowait(None)

        # Run the sync boto3 call in a thread
        task = asyncio.get_event_loop().run_in_executor(None, _run_sync)

        while True:
            event = await queue.get()
            if event is None:
                break
            yield event

        # Ensure the thread has finished
        await task

    async def is_available(self) -> bool:
        """Check if AWS credentials are configured."""
        def _check() -> bool:
            try:
                sts = boto3.client(
                    "sts",
                    region_name=self._config.region or "us-east-1",
                )
                sts.get_caller_identity()
                return True
            except Exception:
                return False

        try:
            return await asyncio.to_thread(_check)
        except Exception:
            return False

    async def close(self) -> None:
        """Nothing to close for boto3."""
        pass
