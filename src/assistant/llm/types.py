"""Types for LLM interactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Provider(str, Enum):
    CLAUDE = "claude"
    OLLAMA = "ollama"


@dataclass
class Message:
    role: Role
    content: str | list[dict[str, Any]]

    def to_api(self) -> dict[str, Any]:
        return {"role": self.role.value, "content": self.content}


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class ToolResult:
    tool_use_id: str
    content: str
    is_error: bool = False

    def to_api(self) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_use_id,
            "content": self.content,
            **({"is_error": True} if self.is_error else {}),
        }


class StreamEventType(str, Enum):
    TEXT_DELTA = "text_delta"
    TOOL_USE_START = "tool_use_start"
    TOOL_USE_DELTA = "tool_use_delta"
    TOOL_USE_COMPLETE = "tool_use_complete"
    MESSAGE_COMPLETE = "message_complete"
    ROUTING_INFO = "routing_info"  # Phase 2: LLM routing notification
    ERROR = "error"


@dataclass
class StreamEvent:
    type: StreamEventType
    text: str = ""
    tool_call: ToolCall | None = None
    error: str = ""
    provider: Provider | None = None  # For ROUTING_INFO events
    model: str = ""  # For ROUTING_INFO events


@dataclass
class LLMConfig:
    """Configuration for LLM client."""

    provider: Provider
    model: str
    max_tokens: int = 8192
    base_url: str = ""  # For Ollama
    api_key: str = ""  # For Claude
