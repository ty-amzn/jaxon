"""LLM metrics client for logging inference events to Observatory."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class InferenceEvent:
    """Represents a single LLM inference call."""

    timestamp: str
    provider: str
    model: str
    duration_ms: int
    success: bool
    error_message: str | None = None
    session_id: str | None = None
    agent_name: str | None = None
    tool_rounds: int = 0
    has_tools: bool = False
    routed_from: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    raw_prompt: str | None = None
    raw_response: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        d: dict[str, Any] = {
            "timestamp": self.timestamp,
            "provider": self.provider,
            "model": self.model,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "tool_rounds": self.tool_rounds,
            "has_tools": self.has_tools,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "stop_reason": self.stop_reason,
        }
        if self.error_message:
            d["error_message"] = self.error_message
        if self.session_id:
            d["session_id"] = self.session_id
        if self.agent_name:
            d["agent_name"] = self.agent_name
        if self.routed_from:
            d["routed_from"] = self.routed_from
        if self.raw_prompt:
            d["raw_prompt"] = self.raw_prompt
        if self.raw_response:
            d["raw_response"] = self.raw_response
        return d


class LLMMetricsClient:
    """Fire-and-forget HTTP client for logging to Observatory."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=5.0)

    async def log_inference(self, event: InferenceEvent) -> None:
        """Log an inference event to Observatory (fire-and-forget)."""
        try:
            await self._client.post(
                f"{self._base_url}/observe/events",
                json=event.to_dict(),
            )
        except Exception:
            # Log failures are not critical — just warn and continue
            logger.debug("Failed to log inference event to Observatory")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


class MetricsContext:
    """Context for capturing metrics during an LLM call."""

    def __init__(
        self,
        metrics_client: LLMMetricsClient | None,
        session_id: str | None = None,
        agent_name: str | None = None,
    ) -> None:
        self._metrics_client = metrics_client
        self._session_id = session_id
        self._agent_name = agent_name
        self._start_time: float | None = None
        self._provider: str | None = None
        self._model: str | None = None
        self._success = True
        self._error_message: str | None = None
        self._tool_rounds = 0
        self._has_tools = False
        self._routed_from: str | None = None
        self._input_tokens = 0
        self._output_tokens = 0
        self._stop_reason = ""
        self._raw_prompt: str | None = None
        self._raw_response: str | None = None

    def start(self) -> None:
        """Mark the start of an inference."""
        self._start_time = time.perf_counter()

    def record_routing_info(self, provider: str, model: str) -> None:
        """Record provider/model info from ROUTING_INFO event."""
        # If this is a fallback, track the original provider
        if self._provider is not None and self._provider != provider:
            self._routed_from = self._provider
        self._provider = provider
        self._model = model

    def record_tool_round(self) -> None:
        """Increment tool round counter."""
        self._tool_rounds += 1

    def record_tools_provided(self) -> None:
        """Mark that tools were provided to this call."""
        self._has_tools = True

    def record_error(self, error: str) -> None:
        """Record an error."""
        self._success = False
        self._error_message = error

    def record_usage(self, input_tokens: int, output_tokens: int, stop_reason: str) -> None:
        """Record token usage from MESSAGE_COMPLETE event."""
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        if stop_reason:
            self._stop_reason = stop_reason

    def record_prompt(self, system: str, messages: list[dict]) -> None:
        """Record the raw prompt sent to the LLM."""
        import json
        try:
            self._raw_prompt = json.dumps({"system": system, "messages": messages}, default=str)
        except Exception:
            pass

    def record_response(self, text: str) -> None:
        """Record the raw response text from the LLM."""
        self._raw_response = text

    async def finish(self) -> None:
        """Calculate duration and log the event."""
        if self._metrics_client is None:
            return
        if self._provider is None or self._model is None:
            return
        if self._start_time is None:
            return

        duration_ms = int((time.perf_counter() - self._start_time) * 1000)

        event = InferenceEvent(
            timestamp="",  # Server will set timestamp
            provider=self._provider,
            model=self._model,
            duration_ms=duration_ms,
            success=self._success,
            error_message=self._error_message,
            session_id=self._session_id,
            agent_name=self._agent_name,
            tool_rounds=self._tool_rounds,
            has_tools=self._has_tools,
            routed_from=self._routed_from,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            stop_reason=self._stop_reason,
            raw_prompt=self._raw_prompt,
            raw_response=self._raw_response,
        )

        await self._metrics_client.log_inference(event)