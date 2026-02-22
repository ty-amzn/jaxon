"""Abstract base class for LLM clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from assistant.llm.types import LLMConfig, StreamEvent, ToolCall, ToolResult

# Type for the tool executor callback
ToolExecutor = Callable[[ToolCall], Awaitable[ToolResult]]


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients with streaming and tool support."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    @property
    def provider(self) -> str:
        """Return the provider name."""
        return self._config.provider.value

    @property
    def model(self) -> str:
        """Return the model name."""
        return self._config.model

    @abstractmethod
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
        When the model requests tool use, executes via tool_executor and
        continues the conversation until a final text response.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM provider is available."""
        ...