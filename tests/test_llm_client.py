"""Tests for LLM types and client utilities."""

from assistant.llm.types import Message, Role, ToolCall, ToolResult, StreamEvent, StreamEventType
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
