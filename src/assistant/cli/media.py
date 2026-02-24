"""Media handling for image uploads and processing."""

from __future__ import annotations

import base64
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MediaContent:
    """Represents a media file (image) for multimodal messages."""

    path: Path
    media_type: str
    data: bytes

    @classmethod
    def from_bytes(cls, data: bytes, media_type: str, filename: str = "upload") -> MediaContent:
        """Construct from raw bytes without a real file path (e.g. Telegram downloads)."""
        return cls(path=Path(filename), media_type=media_type, data=data)

    def to_claude_format(self) -> dict[str, Any]:
        """Convert to Claude API format."""
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": self.media_type,
                "data": base64.b64encode(self.data).decode("utf-8"),
            },
        }

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI-compatible format (for Ollama)."""
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{self.media_type};base64,{base64.b64encode(self.data).decode('utf-8')}"
            },
        }


class MediaHandler:
    """Handles loading and processing of media files for vision models."""

    SUPPORTED_IMAGE_TYPES = {
        "image/jpeg": [".jpg", ".jpeg"],
        "image/png": [".png"],
        "image/gif": [".gif"],
        "image/webp": [".webp"],
    }

    def __init__(self, max_size_mb: int = 10) -> None:
        self._max_size_bytes = max_size_mb * 1024 * 1024

    def _get_media_type(self, path: Path) -> str | None:
        """Determine the media type from file extension."""
        ext = path.suffix.lower()
        for media_type, extensions in self.SUPPORTED_IMAGE_TYPES.items():
            if ext in extensions:
                return media_type
        # Fall back to mimetypes
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type and mime_type.startswith("image/"):
            return mime_type
        return None

    def is_supported(self, path: Path) -> bool:
        """Check if a file is a supported media type."""
        return self._get_media_type(path) is not None

    def load_image(self, path: Path) -> MediaContent | None:
        """Load an image file and return MediaContent."""
        if not path.exists():
            logger.warning(f"Image file not found: {path}")
            return None

        media_type = self._get_media_type(path)
        if not media_type:
            logger.warning(f"Unsupported image type: {path}")
            return None

        # Check file size
        file_size = path.stat().st_size
        if file_size > self._max_size_bytes:
            logger.warning(
                f"Image too large: {path} ({file_size / 1024 / 1024:.1f}MB > {self._max_size_bytes / 1024 / 1024}MB)"
            )
            return None

        try:
            data = path.read_bytes()
            return MediaContent(
                path=path,
                media_type=media_type,
                data=data,
            )
        except Exception as e:
            logger.warning(f"Failed to load image {path}: {e}")
            return None

    def parse_image_reference(self, text: str) -> tuple[str, list[Path]]:
        """Parse @image:/path syntax from text.

        Returns:
            Tuple of (cleaned_text, list_of_image_paths)
        """
        import re

        # Pattern: @image:/path/to/image.png or @image:/path with spaces/image.png
        pattern = r"@image:(\"[^\"]+\"|[^\s]+)"
        matches = re.findall(pattern, text)

        image_paths = []
        for match in matches:
            # Remove quotes if present
            path_str = match.strip('"')
            image_paths.append(Path(path_str))

        # Remove the @image: references from text
        cleaned_text = re.sub(pattern, "", text).strip()
        return cleaned_text, image_paths

    def build_multimodal_message(
        self, text: str, images: list[MediaContent], format: str = "claude"
    ) -> str | list[dict[str, Any]]:
        """Build a multimodal message content.

        Args:
            text: The text content
            images: List of loaded images
            format: "claude" or "openai"

        Returns:
            Either a string (text only) or list of content blocks
        """
        if not images:
            return text

        content: list[dict[str, Any]] = []

        # Add text first
        if text:
            content.append({"type": "text", "text": text})

        # Add images
        for img in images:
            if format == "openai":
                content.append(img.to_openai_format())
            else:
                content.append(img.to_claude_format())

        return content