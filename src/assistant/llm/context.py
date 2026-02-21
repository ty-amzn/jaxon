"""Context assembly from memory for LLM calls."""

from __future__ import annotations

from assistant.llm.types import Message
from assistant.memory.manager import MemoryManager


def build_system_prompt(memory: MemoryManager) -> str:
    """Build the system prompt from all memory sources."""
    return memory.get_system_prompt()


def build_messages(
    conversation_messages: list[Message],
    max_messages: int = 50,
) -> list[dict]:
    """Convert conversation messages to API format, trimmed to max."""
    trimmed = conversation_messages[-max_messages:]
    return [m.to_api() for m in trimmed]
