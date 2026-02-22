"""LLM Router — routes between local (Ollama) and cloud (Claude) models."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from assistant.core.config import Settings
from assistant.llm.base import BaseLLMClient, ToolExecutor
from assistant.llm.client import ClaudeClient
from assistant.llm.ollama import OllamaClient
from assistant.llm.types import (
    LLMConfig,
    Provider,
    StreamEvent,
    StreamEventType,
)

logger = logging.getLogger(__name__)


class LLMRouter(BaseLLMClient):
    """Routes requests between Ollama (local) and Claude (cloud) based on rules."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._claude_client: ClaudeClient | None = None
        self._ollama_client: OllamaClient | None = None
        self._ollama_available: bool | None = None

        # Create config for router (used for metadata)
        self._config = LLMConfig(
            provider=Provider.CLAUDE,  # Default
            model=settings.model,
            max_tokens=settings.max_tokens,
        )

    def _get_claude_client(self) -> ClaudeClient:
        """Get or create Claude client."""
        if self._claude_client is None:
            config = LLMConfig(
                provider=Provider.CLAUDE,
                model=self._settings.model,
                max_tokens=self._settings.max_tokens,
                api_key=self._settings.anthropic_api_key,
            )
            self._claude_client = ClaudeClient(config)
        return self._claude_client

    def _get_ollama_client(self) -> OllamaClient:
        """Get or create Ollama client."""
        if self._ollama_client is None:
            config = LLMConfig(
                provider=Provider.OLLAMA,
                model=self._settings.ollama_model,
                max_tokens=self._settings.max_tokens,
                base_url=self._settings.ollama_base_url,
            )
            self._ollama_client = OllamaClient(config)
        return self._ollama_client

    async def _check_ollama_available(self) -> bool:
        """Check if Ollama is available (cached)."""
        if self._ollama_available is None:
            client = self._get_ollama_client()
            self._ollama_available = await client.is_available()
            if self._ollama_available:
                logger.info("Ollama is available at %s", self._settings.ollama_base_url)
            else:
                logger.debug("Ollama is not available")
        return self._ollama_available

    def _should_use_ollama(
        self,
        messages: list[dict],
        tools: list[dict] | None,
    ) -> bool:
        """Determine if Ollama should be used based on routing rules.

        Routing rules:
        1. Tool use → Claude (Ollama tool support varies)
        2. Complex reasoning (long messages) → Claude
        3. Ollama unavailable → Claude
        4. Simple query → Ollama
        """
        # Rule 1: Tool use always goes to Claude
        if tools:
            logger.debug("Routing to Claude: tool use required")
            return False

        # Rule 2: Check message complexity
        total_chars = sum(
            len(str(m.get("content", "")))
            for m in messages
        )
        # Approximate token count (rough: ~4 chars per token)
        approx_tokens = total_chars // 4

        if approx_tokens > self._settings.local_model_threshold_tokens:
            logger.debug(
                "Routing to Claude: complex reasoning (%d approx tokens)",
                approx_tokens,
            )
            return False

        # Simple query → Ollama (if available)
        return True

    @property
    def provider(self) -> str:
        """Return the last used provider."""
        return self._config.provider.value

    @property
    def model(self) -> str:
        """Return the model name."""
        return self._config.model

    async def is_available(self) -> bool:
        """Check if any LLM provider is available."""
        # Claude is always available if API key is set
        if self._settings.anthropic_api_key:
            return True
        # Fall back to checking Ollama
        return await self._check_ollama_available()

    async def stream_with_tool_loop(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_executor: ToolExecutor | None = None,
        max_tool_rounds: int = 10,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Route to appropriate LLM and stream response."""
        use_ollama = False

        # Check if Ollama is enabled
        if self._settings.ollama_enabled:
            # Check routing rules
            use_ollama = self._should_use_ollama(messages, tools)

            if use_ollama:
                # Verify Ollama is available
                if not await self._check_ollama_available():
                    logger.info("Ollama not available, falling back to Claude")
                    use_ollama = False

        # Select client
        if use_ollama:
            client = self._get_ollama_client()
            self._config = LLMConfig(
                provider=Provider.OLLAMA,
                model=self._settings.ollama_model,
                max_tokens=self._settings.max_tokens,
            )
        else:
            client = self._get_claude_client()
            self._config = LLMConfig(
                provider=Provider.CLAUDE,
                model=self._settings.model,
                max_tokens=self._settings.max_tokens,
            )

        # Yield routing info event
        yield StreamEvent(
            type=StreamEventType.ROUTING_INFO,
            provider=self._config.provider,
            model=self._config.model,
        )

        # Stream from selected client
        async for event in client.stream_with_tool_loop(
            system=system,
            messages=messages,
            tools=tools,
            tool_executor=tool_executor,
            max_tool_rounds=max_tool_rounds,
        ):
            yield event

    async def get_embedding(self, text: str) -> list[float] | None:
        """Get embedding using Ollama if available."""
        if self._settings.ollama_enabled and await self._check_ollama_available():
            client = self._get_ollama_client()
            return await client.get_embedding(text)
        return None

    async def close(self) -> None:
        """Close all clients."""
        if self._ollama_client:
            await self._ollama_client.close()