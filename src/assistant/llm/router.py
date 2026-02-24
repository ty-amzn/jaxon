"""LLM Router — routes between multiple LLM providers."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from assistant.core.config import Settings
from assistant.llm.base import BaseLLMClient, ToolExecutor
from assistant.llm.client import ClaudeClient
from assistant.llm.gemini import GeminiClient
from assistant.llm.ollama import OllamaClient
from assistant.llm.openai_client import OpenAIClient
from assistant.llm.types import (
    LLMConfig,
    Provider,
    StreamEvent,
    StreamEventType,
)

logger = logging.getLogger(__name__)


class LLMRouter(BaseLLMClient):
    """Routes requests between multiple LLM providers based on config."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._claude_client: ClaudeClient | None = None
        self._ollama_client: OllamaClient | None = None
        self._openai_client: OpenAIClient | None = None
        self._gemini_client: GeminiClient | None = None
        self._ollama_available: bool | None = None
        self._model_clients: dict[str, BaseLLMClient] = {}

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

    def _get_openai_client(self) -> OpenAIClient:
        """Get or create OpenAI client."""
        if self._openai_client is None:
            config = LLMConfig(
                provider=Provider.OPENAI,
                model=self._settings.openai_model,
                max_tokens=self._settings.max_tokens,
                api_key=self._settings.openai_api_key,
            )
            self._openai_client = OpenAIClient(config)
        return self._openai_client

    def _get_gemini_client(self) -> GeminiClient:
        """Get or create Gemini client."""
        if self._gemini_client is None:
            config = LLMConfig(
                provider=Provider.GEMINI,
                model=self._settings.gemini_model,
                max_tokens=self._settings.max_tokens,
                api_key=self._settings.gemini_api_key,
            )
            self._gemini_client = GeminiClient(config)
        return self._gemini_client

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
        """Determine if Ollama should be used for simple queries.

        Routing rules:
        1. Tool use → skip Ollama
        2. Complex reasoning (long messages) → skip Ollama
        3. Simple query → Ollama
        """
        if tools:
            logger.debug("Skipping Ollama: tool use required")
            return False

        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        approx_tokens = total_chars // 4

        if approx_tokens > self._settings.local_model_threshold_tokens:
            logger.debug(
                "Skipping Ollama: complex reasoning (%d approx tokens)",
                approx_tokens,
            )
            return False

        return True

    def _get_default_client(self) -> tuple[BaseLLMClient, Provider, str]:
        """Get the configured default provider's client.

        Returns (client, provider_enum, model_name).
        """
        default = self._settings.default_provider

        if default == "openai" and self._settings.openai_enabled:
            return (
                self._get_openai_client(),
                Provider.OPENAI,
                self._settings.openai_model,
            )
        if default == "gemini" and self._settings.gemini_enabled:
            return (
                self._get_gemini_client(),
                Provider.GEMINI,
                self._settings.gemini_model,
            )
        if default == "ollama" and self._settings.ollama_enabled:
            return (
                self._get_ollama_client(),
                Provider.OLLAMA,
                self._settings.ollama_model,
            )

        # Default or fallback: Claude
        return (
            self._get_claude_client(),
            Provider.CLAUDE,
            self._settings.model,
        )

    # Known vision-capable model families (substring match)
    _VISION_MODELS = (
        "claude", "gpt-4o", "gpt-4-turbo", "gpt-4-vision",
        "gemini", "llava", "bakllava", "moondream",
        "qwen-vl", "qwen2-vl", "cogvlm", "minicpm-v",
    )

    @staticmethod
    def model_supports_vision(model: str) -> bool:
        """Check if a model name is likely vision-capable."""
        model_lower = model.lower()
        return any(v in model_lower for v in LLMRouter._VISION_MODELS)

    def default_model_supports_vision(self) -> bool:
        """Check if the current default model supports vision.

        Uses ``ASSISTANT_VISION`` setting if set, otherwise auto-detects.
        """
        if self._settings.vision is not None:
            return self._settings.vision
        _, _, model = self._get_default_client()
        return self.model_supports_vision(model)

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
        if self._settings.anthropic_api_key:
            return True
        if self._settings.openai_enabled and self._settings.openai_api_key:
            return True
        if self._settings.gemini_enabled and self._settings.gemini_api_key:
            return True
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

        # Check if Ollama should intercept simple queries
        if self._settings.ollama_enabled and self._settings.default_provider != "ollama":
            use_ollama = self._should_use_ollama(messages, tools)
            if use_ollama and not await self._check_ollama_available():
                logger.info("Ollama not available, using default provider")
                use_ollama = False

        # Select client
        if use_ollama:
            client: BaseLLMClient = self._get_ollama_client()
            provider = Provider.OLLAMA
            model = self._settings.ollama_model
        else:
            client, provider, model = self._get_default_client()

        self._config = LLMConfig(
            provider=provider,
            model=model,
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

    _PROVIDER_MAP: dict[str, Provider] = {
        "claude": Provider.CLAUDE,
        "openai": Provider.OPENAI,
        "gemini": Provider.GEMINI,
        "ollama": Provider.OLLAMA,
    }

    def get_client_for_model(self, model: str) -> BaseLLMClient:
        """Return a client configured for the given model string.

        Uses ``provider/model`` syntax, e.g.:
        - ``openai/gpt-4o``
        - ``claude/claude-sonnet-4-5-20250514``
        - ``gemini/gemini-2.0-flash``
        - ``ollama/llama3``

        If no ``/`` is present, falls back to the default provider.
        """
        if model in self._model_clients:
            return self._model_clients[model]

        if "/" in model:
            provider_key, model_name = model.split("/", 1)
            provider = self._PROVIDER_MAP.get(provider_key)
            if provider is None:
                raise ValueError(
                    f"Unknown provider '{provider_key}' in '{model}'. "
                    f"Valid providers: {', '.join(self._PROVIDER_MAP)}"
                )
        else:
            # No prefix — use default provider
            _, provider, _ = self._get_default_client()
            model_name = model

        if provider == Provider.OPENAI:
            config = LLMConfig(
                provider=Provider.OPENAI,
                model=model_name,
                max_tokens=self._settings.max_tokens,
                api_key=self._settings.openai_api_key,
            )
            client: BaseLLMClient = OpenAIClient(config)
        elif provider == Provider.GEMINI:
            config = LLMConfig(
                provider=Provider.GEMINI,
                model=model_name,
                max_tokens=self._settings.max_tokens,
                api_key=self._settings.gemini_api_key,
            )
            client = GeminiClient(config)
        elif provider == Provider.OLLAMA:
            config = LLMConfig(
                provider=Provider.OLLAMA,
                model=model_name,
                max_tokens=self._settings.max_tokens,
                base_url=self._settings.ollama_base_url,
            )
            client = OllamaClient(config)
        else:
            config = LLMConfig(
                provider=Provider.CLAUDE,
                model=model_name,
                max_tokens=self._settings.max_tokens,
                api_key=self._settings.anthropic_api_key,
            )
            client = ClaudeClient(config)

        self._model_clients[model] = client
        logger.info("Created %s client for model %s", provider.value, model_name)
        return client

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
        if self._openai_client:
            await self._openai_client.close()
        if self._gemini_client:
            await self._gemini_client.close()
        for client in self._model_clients.values():
            await client.close()
        self._model_clients.clear()
