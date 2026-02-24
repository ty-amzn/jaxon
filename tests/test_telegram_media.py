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
