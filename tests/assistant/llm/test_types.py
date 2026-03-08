"""Tests for LLM types and client utilities."""

from assistant.llm.types import (
    Message,
    Role,
    ToolCall,
    ToolResult,
    StreamEvent,
    StreamEventType,
    Provider,
    LLMConfig,
)
from assistant.llm.context import build_messages


def test_message_to_api():
    msg = Message(role=Role.USER, content="Hello")
    api = msg.to_api()
    assert api == {"role": "user", "content": "Hello"}


def test_tool_result_to_api():
    tr = ToolResult(tool_use_id="123", content="result text")
    api = tr.to_api()
    assert api["tool_use_id"] == "123"
    assert api["content"] == "result text"
    assert "is_error" not in api


def test_tool_result_error():
    tr = ToolResult(tool_use_id="123", content="error", is_error=True)
    api = tr.to_api()
    assert api["is_error"] is True


def test_build_messages_trimming():
    messages = [Message(role=Role.USER, content=f"msg {i}") for i in range(100)]
    result = build_messages(messages, max_messages=5)
    assert len(result) == 5
    assert result[0]["content"] == "msg 95"


def test_stream_event():
    event = StreamEvent(type=StreamEventType.TEXT_DELTA, text="hello")
    assert event.type == StreamEventType.TEXT_DELTA
    assert event.text == "hello"


class TestLLMTypes:
    """Tests for LLM types."""

    def test_provider_enum(self):
        """Test Provider enum values."""
        assert Provider.CLAUDE.value == "claude"
        assert Provider.OLLAMA.value == "ollama"

    def test_llm_config(self):
        """Test LLMConfig creation."""
        config = LLMConfig(
            provider=Provider.CLAUDE,
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            api_key="test-key",
        )

        assert config.provider == Provider.CLAUDE
        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_tokens == 4096
        assert config.api_key == "test-key"
        assert config.base_url == ""
