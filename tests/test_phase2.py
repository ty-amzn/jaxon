"""Tests for Phase 2 features."""

from pathlib import Path

import pytest

from assistant.core.config import Settings
from assistant.memory.skills import SkillLoader, Skill
from assistant.gateway.thread_store import ThreadStore, Thread
from assistant.cli.media import MediaHandler, MediaContent
from assistant.llm.types import Provider, LLMConfig


class TestSkillLoader:
    """Tests for the skill loading system."""

    def test_load_skills_from_empty_dir(self, tmp_path: Path):
        """Test loading from an empty directory."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        loader = SkillLoader(skills_dir)
        skills = loader.load_all()

        assert skills == {}
        assert loader.get_skills_prompt() == ""

    def test_load_skills_from_dir(self, tmp_path: Path):
        """Test loading skills from a directory."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create test skill
        skill_file = skills_dir / "test-skill.md"
        skill_file.write_text("# Test Skill\n\nThis is a test skill.")

        loader = SkillLoader(skills_dir)
        skills = loader.load_all()

        assert len(skills) == 1
        assert "test-skill" in skills
        assert skills["test-skill"].name == "test-skill"
        assert "Test Skill" in skills["test-skill"].content

    def test_get_skills_prompt(self, tmp_path: Path):
        """Test generating skills prompt."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        (skills_dir / "skill1.md").write_text("# Skill 1\nContent 1")

        loader = SkillLoader(skills_dir)
        prompt = loader.get_skills_prompt()

        assert "Available Skills" in prompt
        assert "skill1" in prompt
        assert "Content 1" in prompt

    def test_list_and_get_skills(self, tmp_path: Path):
        """Test listing and getting individual skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        (skills_dir / "alpha.md").write_text("Alpha skill")
        (skills_dir / "beta.md").write_text("Beta skill")

        loader = SkillLoader(skills_dir)
        skills = loader.list_skills()

        assert len(skills) == 2
        assert loader.get_skill("alpha") is not None
        assert loader.get_skill("nonexistent") is None

    def test_reload_skills(self, tmp_path: Path):
        """Test reloading skills from disk."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        loader = SkillLoader(skills_dir)
        assert len(loader.load_all()) == 0

        # Add a new skill after initial load
        (skills_dir / "new.md").write_text("New skill")
        loader.reload()

        assert len(loader.list_skills()) == 1


class TestThreadStore:
    """Tests for the thread persistence system."""

    def test_create_and_save_thread(self, tmp_path: Path):
        """Test creating and saving a thread."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("Test Thread")
        thread.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        store.save(thread)

        # Verify it was saved
        loaded = store.load(thread.id)
        assert loaded is not None
        assert loaded.name == "Test Thread"
        assert len(loaded.messages) == 2

    def test_list_threads(self, tmp_path: Path):
        """Test listing saved threads."""
        store = ThreadStore(tmp_path)

        thread1 = store.create_thread("Thread 1")
        thread2 = store.create_thread("Thread 2")
        store.save(thread1)
        store.save(thread2)

        threads = store.list_threads()
        assert len(threads) == 2

    def test_load_by_name(self, tmp_path: Path):
        """Test loading a thread by name."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("My Conversation")
        store.save(thread)

        loaded = store.load_by_name("My Conversation")
        assert loaded is not None
        assert loaded.name == "My Conversation"

    def test_delete_thread(self, tmp_path: Path):
        """Test deleting a thread."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("To Delete")
        store.save(thread)

        assert store.load(thread.id) is not None
        assert store.delete(thread.id) is True
        assert store.load(thread.id) is None

    def test_export_thread_json(self, tmp_path: Path):
        """Test exporting a thread as JSON."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("Export Test")
        thread.messages = [{"role": "user", "content": "Test"}]
        store.save(thread)

        exported = store.export_thread(thread, format="json")
        assert "Export Test" in exported
        assert "Test" in exported

    def test_export_thread_markdown(self, tmp_path: Path):
        """Test exporting a thread as Markdown."""
        store = ThreadStore(tmp_path)

        thread = store.create_thread("MD Export")
        thread.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "World"},
        ]
        store.save(thread)

        exported = store.export_thread(thread, format="markdown")
        assert "# MD Export" in exported
        assert "**User:**" in exported
        assert "**Assistant:**" in exported


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


class TestPhase2Config:
    """Tests for Phase 2 configuration."""

    def test_ollama_config(self):
        """Test Ollama configuration defaults."""
        s = Settings(anthropic_api_key="test")

        assert s.ollama_enabled is False
        assert s.ollama_base_url == "http://localhost:11434"
        assert s.ollama_model == "llama3.2"

    def test_routing_config(self):
        """Test routing configuration defaults."""
        s = Settings(anthropic_api_key="test")

        assert s.local_model_threshold_tokens == 1000

    def test_web_search_config(self):
        """Test web search configuration defaults."""
        s = Settings(anthropic_api_key="test")

        assert s.web_search_enabled is False
        assert s.searxng_url == "http://localhost:8888"

    def test_vector_search_config(self):
        """Test vector search configuration defaults."""
        s = Settings(anthropic_api_key="test")

        assert s.vector_search_enabled is False
        assert s.embedding_model == "nomic-embed-text"

    def test_media_config(self):
        """Test media configuration defaults."""
        s = Settings(anthropic_api_key="test")

        assert s.max_media_size_mb == 10