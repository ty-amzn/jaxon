"""Tests for Telegram media support and OpenAI image block conversion."""

from __future__ import annotations

import base64

import pytest

from assistant.cli.media import MediaContent, MediaHandler
from assistant.llm.openai_compat import OpenAICompatibleClient


class TestMediaContentFromBytes:
    """Test MediaContent.from_bytes classmethod."""

    def test_from_bytes_basic(self):
        data = b"\x89PNG\r\n\x1a\n"  # PNG magic bytes
        media = MediaContent.from_bytes(data, "image/png", "photo.png")
        assert media.data == data
        assert media.media_type == "image/png"
        assert media.path.name == "photo.png"

    def test_from_bytes_default_filename(self):
        media = MediaContent.from_bytes(b"data", "image/jpeg")
        assert media.path.name == "upload"

    def test_from_bytes_to_claude_format(self):
        data = b"test-image-data"
        media = MediaContent.from_bytes(data, "image/jpeg", "photo.jpg")
        result = media.to_claude_format()
        assert result["type"] == "image"
        assert result["source"]["type"] == "base64"
        assert result["source"]["media_type"] == "image/jpeg"
        assert result["source"]["data"] == base64.b64encode(data).decode("utf-8")

    def test_from_bytes_to_openai_format(self):
        data = b"test-image-data"
        media = MediaContent.from_bytes(data, "image/png", "photo.png")
        result = media.to_openai_format()
        assert result["type"] == "image_url"
        expected_b64 = base64.b64encode(data).decode("utf-8")
        assert result["image_url"]["url"] == f"data:image/png;base64,{expected_b64}"


class TestBuildMultimodalMessage:
    """Test building multimodal messages from MediaContent."""

    def test_build_with_caption_and_image(self):
        handler = MediaHandler()
        media = MediaContent.from_bytes(b"img", "image/jpeg", "photo.jpg")
        result = handler.build_multimodal_message("What's this?", [media])
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"type": "text", "text": "What's this?"}
        assert result[1]["type"] == "image"

    def test_build_no_text(self):
        handler = MediaHandler()
        media = MediaContent.from_bytes(b"img", "image/jpeg", "photo.jpg")
        result = handler.build_multimodal_message("", [media])
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["type"] == "image"

    def test_build_no_images(self):
        handler = MediaHandler()
        result = handler.build_multimodal_message("hello", [])
        assert result == "hello"


class TestOpenAIImageConversion:
    """Test _convert_messages_to_openai handles image blocks."""

    def _make_client(self):
        """Create a concrete subclass for testing conversion."""
        from assistant.llm.types import LLMConfig, Provider

        class _TestClient(OpenAICompatibleClient):
            def is_available(self) -> bool:
                return True

        config = LLMConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            api_key="test",
        )
        return _TestClient(config)

    def test_converts_claude_image_to_openai(self):
        client = self._make_client()
        b64_data = base64.b64encode(b"fake-png").decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64_data,
                        },
                    },
                ],
            }
        ]

        result = client._convert_messages_to_openai("system prompt", messages)
        # First message is system
        assert result[0]["role"] == "system"
        # Second message is the converted user message
        user_msg = result[1]
        assert user_msg["role"] == "user"
        content = user_msg["content"]
        assert isinstance(content, list)
        assert len(content) == 2
        assert content[0] == {"type": "text", "text": "What's in this image?"}
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"] == f"data:image/png;base64,{b64_data}"

    def test_preserves_text_only_messages(self):
        client = self._make_client()
        messages = [{"role": "user", "content": "hello"}]
        result = client._convert_messages_to_openai("sys", messages)
        assert result[1] == {"role": "user", "content": "hello"}

    def test_preserves_text_blocks_without_images(self):
        client = self._make_client()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "just text"},
                ],
            }
        ]
        result = client._convert_messages_to_openai("sys", messages)
        user_msg = result[1]
        assert user_msg["content"] == [{"type": "text", "text": "just text"}]


class TestAgentDelegationMultimodal:
    """Test multimodal content passthrough in agent delegation."""

    def test_runner_uses_content_param(self):
        """AgentRunner.run() should use content when provided."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from assistant.agents.runner import AgentRunner
        from assistant.agents.types import AgentDef
        from assistant.llm.types import StreamEvent, StreamEventType

        runner = AgentRunner(llm=MagicMock(), tool_registry=MagicMock())

        agent = AgentDef(name="test", description="test agent")
        multimodal_content = [
            {"type": "text", "text": "Describe this image"},
            {"type": "image", "source": {"type": "base64", "data": "abc123", "media_type": "image/png"}},
        ]

        captured_messages = []

        async def fake_stream(*args, **kwargs):
            captured_messages.extend(kwargs.get("messages", args[2] if len(args) > 2 else []))
            yield StreamEvent(type=StreamEventType.MESSAGE_COMPLETE, text="done")

        runner._router.stream_with_tool_loop = fake_stream
        runner._tool_registry.definitions = []

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            runner.run(agent, task="Describe this image", content=multimodal_content)
        )

        assert result.response == "done"
        assert len(captured_messages) == 1
        assert captured_messages[0]["content"] == multimodal_content

    def test_runner_falls_back_to_task_without_content(self):
        """AgentRunner.run() should build from task/context when content is None."""
        from unittest.mock import MagicMock

        from assistant.agents.runner import AgentRunner
        from assistant.agents.types import AgentDef
        from assistant.llm.types import StreamEvent, StreamEventType

        runner = AgentRunner(llm=MagicMock(), tool_registry=MagicMock())
        agent = AgentDef(name="test", description="test agent")

        captured_messages = []

        async def fake_stream(*args, **kwargs):
            captured_messages.extend(kwargs.get("messages", args[2] if len(args) > 2 else []))
            yield StreamEvent(type=StreamEventType.MESSAGE_COMPLETE, text="done")

        runner._router.stream_with_tool_loop = fake_stream
        runner._tool_registry.definitions = []

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            runner.run(agent, task="hello", context="ctx")
        )

        assert captured_messages[0]["content"] == "Context:\nctx\n\nTask:\nhello"

    def test_orchestrator_build_content_with_images(self):
        """Orchestrator._build_content builds multimodal blocks from images."""
        from assistant.agents.orchestrator import Orchestrator

        images = [
            {"data": "base64data1", "media_type": "image/jpeg"},
            {"data": "base64data2", "media_type": "image/png"},
        ]
        result = Orchestrator._build_content("Analyze these", images)

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == {"type": "text", "text": "Analyze these"}
        assert result[1] == {
            "type": "image",
            "source": {"type": "base64", "data": "base64data1", "media_type": "image/jpeg"},
        }
        assert result[2] == {
            "type": "image",
            "source": {"type": "base64", "data": "base64data2", "media_type": "image/png"},
        }

    def test_orchestrator_build_content_without_images(self):
        """Orchestrator._build_content returns None when no images."""
        from assistant.agents.orchestrator import Orchestrator

        assert Orchestrator._build_content("hello", None) is None
        assert Orchestrator._build_content("hello", []) is None
