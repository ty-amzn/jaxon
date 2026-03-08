"""Tests for the media handling system."""

from pathlib import Path

from assistant.cli.media import MediaHandler, MediaContent


class TestMediaHandler:
    """Tests for the media handling system."""

    def test_parse_image_reference(self, tmp_path: Path):
        """Test parsing @image: references from text."""
        handler = MediaHandler()

        text = "Look at this: @image:/path/to/image.png"
        clean_text, paths = handler.parse_image_reference(text)

        assert clean_text == "Look at this:"
        assert len(paths) == 1
        assert paths[0] == Path("/path/to/image.png")

    def test_parse_multiple_images(self, tmp_path: Path):
        """Test parsing multiple @image: references."""
        handler = MediaHandler()

        text = "First @image:/a.png then @image:/b.jpg end"
        clean_text, paths = handler.parse_image_reference(text)

        assert len(paths) == 2
        assert "First" in clean_text
        assert "then" in clean_text
        assert "end" in clean_text

    def test_is_supported(self, tmp_path: Path):
        """Test checking supported image types."""
        handler = MediaHandler()

        assert handler.is_supported(Path("test.png")) is True
        assert handler.is_supported(Path("test.jpg")) is True
        assert handler.is_supported(Path("test.gif")) is True
        assert handler.is_supported(Path("test.txt")) is False

    def test_load_image(self, tmp_path: Path):
        """Test loading an image file."""
        handler = MediaHandler(max_size_mb=1)

        # Create a minimal valid PNG
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
        test_file = tmp_path / "test.png"
        test_file.write_bytes(png_header)

        media = handler.load_image(test_file)
        assert media is not None
        assert media.media_type == "image/png"

    def test_build_multimodal_message(self, tmp_path: Path):
        """Test building multimodal message content."""
        handler = MediaHandler()

        # Create a minimal image
        png_header = b'\x89PNG\r\n\x1a\n'
        media = MediaContent(
            path=tmp_path / "test.png",
            media_type="image/png",
            data=png_header,
        )

        content = handler.build_multimodal_message("Hello", [media])

        assert isinstance(content, list)
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image"
