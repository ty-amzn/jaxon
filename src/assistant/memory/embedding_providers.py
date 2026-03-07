"""Pluggable embedding providers for vector search."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Interface for text embedding providers."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for each text."""
        ...

    @property
    def dimensions(self) -> int:
        """Dimensionality of the embedding vectors."""
        ...


class OllamaEmbedder:
    """Embedding provider using Ollama's /api/embeddings endpoint."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = make_httpx_client(timeout=60.0)
        self._dimensions = 768  # nomic-embed-text default

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            try:
                resp = await self._client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                )
                if resp.status_code == 200:
                    vec = resp.json().get("embedding", [])
                    if vec:
                        # Update dimensions from actual response
                        self._dimensions = len(vec)
                    results.append(vec)
                else:
                    logger.warning("Ollama embedding failed: %s", resp.status_code)
                    results.append([])
            except Exception as e:
                logger.warning("Ollama embedding error: %s", e)
                results.append([])
        return results

    async def close(self) -> None:
        await self._client.aclose()


class OpenAIEmbedder:
    """Embedding provider using OpenAI's text-embedding API."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
    ) -> None:
        self._model = model
        self._dimensions = 1536  # text-embedding-3-small default
        # Use the openai SDK (already a dependency)
        import openai

        self._client = openai.AsyncOpenAI(api_key=api_key)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            resp = await self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
            results = [[] for _ in texts]
            for item in resp.data:
                results[item.index] = item.embedding
                if item.embedding:
                    self._dimensions = len(item.embedding)
            return results
        except Exception as e:
            logger.warning("OpenAI embedding error: %s", e)
            return [[] for _ in texts]

    async def close(self) -> None:
        await self._client.close()


def create_embedder(config: Any) -> EmbeddingProvider:
    """Factory: create an embedder based on config.embedding_provider."""
    provider = getattr(config, "embedding_provider", "ollama")

    if provider == "openai":
        api_key = getattr(config, "openai_api_key", "")
        if not api_key:
            raise ValueError("OpenAI embedding provider requires OPENAI_API_KEY")
        return OpenAIEmbedder(api_key=api_key)

    # Default: ollama
    base_url = getattr(config, "ollama_base_url", "http://localhost:11434")
    model = getattr(config, "embedding_model", "nomic-embed-text")
    return OllamaEmbedder(base_url=base_url, model=model)
