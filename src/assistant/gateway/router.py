"""LLM Router — Phase 1: pass-through to Claude."""

from __future__ import annotations

from assistant.llm.client import ClaudeClient


class LLMRouter:
    """Routes LLM requests. Phase 1: direct pass-through to Claude."""

    def __init__(self, client: ClaudeClient) -> None:
        self._client = client

    @property
    def client(self) -> ClaudeClient:
        return self._client
