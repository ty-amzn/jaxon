"""OpenAI client — subclass of OpenAI-compatible base."""

from __future__ import annotations

import logging

from assistant.llm.openai_compat import OpenAICompatibleClient
from assistant.llm.types import LLMConfig

logger = logging.getLogger(__name__)


class OpenAIClient(OpenAICompatibleClient):
    """Streaming OpenAI client."""

    _CHAT_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)

    def _get_chat_url(self) -> str:
        return self._CHAT_URL

    def _get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._config.api_key}"}

    def _get_provider_label(self) -> str:
        return "OpenAI"

    async def is_available(self) -> bool:
        """Check if OpenAI API is reachable."""
        if not self._config.api_key:
            return False
        try:
            response = await self._client.get(
                "https://api.openai.com/v1/models",
                headers=self._get_headers(),
            )
            return response.status_code == 200
        except Exception:
            return False
