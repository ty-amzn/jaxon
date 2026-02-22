"""Ollama client — subclass of OpenAI-compatible base with embedding support."""

from __future__ import annotations

import logging

from assistant.llm.openai_compat import OpenAICompatibleClient
from assistant.llm.types import LLMConfig, Provider

logger = logging.getLogger(__name__)


class OllamaClient(OpenAICompatibleClient):
    """Streaming Ollama client using OpenAI-compatible API."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)

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

    def _get_chat_url(self) -> str:
        return f"{self._get_base_url()}/v1/chat/completions"

    def _get_provider_label(self) -> str:
        return "Ollama"

    async def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = await self._client.get(
                f"{self._get_base_url()}/api/tags"
            )
            return response.status_code == 200
        except Exception:
            return False

    async def get_embedding(self, text: str) -> list[float] | None:
        """Get embedding for text using Ollama embeddings API."""
        try:
            response = await self._client.post(
                f"{self._get_base_url()}/api/embeddings",
                json={"model": self._config.model, "prompt": text},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
        except Exception as e:
            logger.warning(f"Failed to get embedding: {e}")
        return None
