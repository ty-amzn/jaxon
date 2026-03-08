"""Tests for BedrockClient format converters and error handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from assistant.llm.bedrock import BedrockClient
from assistant.llm.types import LLMConfig, Provider, StreamEventType


def _make_client() -> BedrockClient:
    """Create a BedrockClient with a mocked boto3 client."""
    config = LLMConfig(
        provider=Provider.BEDROCK,
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region="us-east-1",
    )
    with patch("assistant.llm.bedrock.boto3") as mock_boto3:
        mock_boto3.client.return_value = MagicMock()
        client = BedrockClient(config)
    return client


def test_convert_tools():
    """Anthropic tool defs → Bedrock toolSpec format."""
    tools = [
        {
            "name": "get_weather",
            "description": "Get current weather",
            "input_schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        }
    ]
    result = BedrockClient._convert_tools(tools)
    assert len(result) == 1
    spec = result[0]["toolSpec"]
    assert spec["name"] == "get_weather"
    assert spec["description"] == "Get current weather"
    assert spec["inputSchema"]["json"]["type"] == "object"
    assert "city" in spec["inputSchema"]["json"]["properties"]


def test_convert_messages_text_string():
    """String content → Bedrock text block."""
    messages = [{"role": "user", "content": "Hello"}]
    result = BedrockClient._convert_messages(messages)
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"] == [{"text": "Hello"}]


def test_convert_messages_text_list():
    """List content with text blocks → Bedrock text blocks."""
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Hi"}, {"type": "text", "text": "there"}],
        }
    ]
    result = BedrockClient._convert_messages(messages)
    assert result[0]["content"] == [{"text": "Hi"}, {"text": "there"}]


def test_convert_messages_tool_use():
    """Assistant tool_use blocks → Bedrock toolUse format."""
    messages = [
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "tool_123",
                    "name": "get_weather",
                    "input": {"city": "London"},
                }
            ],
        }
    ]
    result = BedrockClient._convert_messages(messages)
    tool_use = result[0]["content"][0]["toolUse"]
    assert tool_use["toolUseId"] == "tool_123"
    assert tool_use["name"] == "get_weather"
    assert tool_use["input"] == {"city": "London"}


def test_convert_messages_tool_result():
    """User tool_result blocks → Bedrock toolResult format."""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "tool_123",
                    "content": "Sunny, 22°C",
                }
            ],
        }
    ]
    result = BedrockClient._convert_messages(messages)
    tool_result = result[0]["content"][0]["toolResult"]
    assert tool_result["toolUseId"] == "tool_123"
    assert tool_result["content"] == [{"text": "Sunny, 22°C"}]
    assert tool_result["status"] == "success"


def test_convert_messages_tool_result_error():
    """Error tool_result → status 'error'."""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "tool_456",
                    "content": "Not found",
                    "is_error": True,
                }
            ],
        }
    ]
    result = BedrockClient._convert_messages(messages)
    tool_result = result[0]["content"][0]["toolResult"]
    assert tool_result["status"] == "error"


@pytest.mark.asyncio
async def test_is_available_no_credentials():
    """Returns False when AWS credentials are missing."""
    client = _make_client()
    with patch("assistant.llm.bedrock.boto3") as mock_boto3:
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = Exception("No credentials")
        mock_boto3.client.return_value = mock_sts
        available = await client.is_available()
    assert available is False


@pytest.mark.asyncio
async def test_stream_error_handling():
    """boto3 ClientError → ERROR StreamEvent."""
    client = _make_client()

    # Make converse_stream raise an error
    client._boto3_client.converse_stream.side_effect = Exception(
        "An error occurred (ValidationException)"
    )

    events = []
    async for event in client.stream_with_tool_loop(
        system="test",
        messages=[{"role": "user", "content": "Hello"}],
    ):
        events.append(event)

    assert any(e.type == StreamEventType.ERROR for e in events)
    error_event = next(e for e in events if e.type == StreamEventType.ERROR)
    assert "ValidationException" in error_event.error
