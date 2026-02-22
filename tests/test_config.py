"""Tests for configuration."""

from pathlib import Path

from assistant.core.config import Settings


def test_settings_defaults():
    s = Settings(anthropic_api_key="test", _env_file=None)
    assert s.model == "claude-sonnet-4-20250514"
    assert s.max_tokens == 8192
    assert s.host == "127.0.0.1"
    assert s.port == 51430


def test_settings_paths():
    s = Settings(anthropic_api_key="test", _env_file=None)
    assert s.memory_dir == s.data_dir / "memory"
    assert s.daily_log_dir == s.data_dir / "memory" / "daily"
    assert s.identity_path == s.data_dir / "memory" / "IDENTITY.md"
    assert s.memory_path == s.data_dir / "memory" / "MEMORY.md"
    assert s.audit_log_path == s.data_dir / "logs" / "audit.jsonl"
    assert s.search_db_path == s.data_dir / "db" / "search.db"


def test_settings_phase2_paths():
    """Test Phase 2 configuration paths."""
    s = Settings(anthropic_api_key="test", _env_file=None)
    assert s.skills_dir == s.data_dir / "skills"
    assert s.threads_dir == s.data_dir / "threads"
    assert s.embeddings_db_path == s.data_dir / "db" / "embeddings.db"


def test_settings_phase2_defaults():
    """Test Phase 2 default settings."""
    s = Settings(anthropic_api_key="test", _env_file=None)
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
