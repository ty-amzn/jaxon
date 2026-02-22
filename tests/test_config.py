"""Tests for configuration."""

from pathlib import Path

from assistant.core.config import Settings


def test_settings_defaults():
    s = Settings(anthropic_api_key="test")
    assert s.model == "claude-sonnet-4-20250514"
    assert s.max_tokens == 8192
    assert s.host == "127.0.0.1"
    assert s.port == 51430


def test_settings_paths(settings: Settings):
    assert settings.memory_dir == settings.data_dir / "memory"
    assert settings.daily_log_dir == settings.data_dir / "memory" / "daily"
    assert settings.identity_path == settings.data_dir / "memory" / "IDENTITY.md"
    assert settings.memory_path == settings.data_dir / "memory" / "MEMORY.md"
    assert settings.audit_log_path == settings.data_dir / "logs" / "audit.jsonl"
    assert settings.search_db_path == settings.data_dir / "db" / "search.db"


def test_settings_phase2_paths(settings: Settings):
    """Test Phase 2 configuration paths."""
    assert settings.skills_dir == settings.data_dir / "skills"
    assert settings.threads_dir == settings.data_dir / "threads"
    assert settings.embeddings_db_path == settings.data_dir / "db" / "embeddings.db"


def test_settings_phase2_defaults():
    """Test Phase 2 configuration defaults."""
    s = Settings(anthropic_api_key="test")
    # Ollama
    assert s.ollama_enabled is False
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.ollama_model == "llama3.2"

    # Routing
    assert s.local_model_threshold_tokens == 1000

    # Web Search
    assert s.web_search_enabled is False
    assert s.searxng_url == "http://localhost:8888"

    # Vector Search
    assert s.vector_search_enabled is False
    assert s.embedding_model == "nomic-embed-text"

    # Media
    assert s.max_media_size_mb == 10


def test_settings_phase2_paths(settings: Settings):
    """Test Phase 2 config paths."""
    assert settings.skills_dir == settings.data_dir / "skills"
    assert settings.threads_dir == settings.data_dir / "threads"
    assert settings.embeddings_db_path == settings.data_dir / "db" / "embeddings.db"


def test_settings_phase2_defaults():
    """Test Phase 2 default settings."""
    s = Settings(anthropic_api_key="test")
    # Ollama
    assert s.ollama_enabled is False
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.ollama_model == "llama3.2"
    # Routing
    assert s.local_model_threshold_tokens == 1000
    # Web Search
    assert s.web_search_enabled is False
    assert s.searxng_url == "http://localhost:8888"
    # Vector Search
    assert s.vector_search_enabled is False
    assert s.embedding_model == "nomic-embed-text"
    # Media
    assert s.max_media_size_mb == 10
