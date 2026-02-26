"""Application configuration via environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "ASSISTANT_", "env_file": ".env", "extra": "ignore"}

    # API keys — no prefix, so they match provider conventions
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")

    # Model
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192

    # Paths
    data_dir: Path = Path("./data")

    # Server
    host: str = "127.0.0.1"
    port: int = 51430

    # Logging
    log_level: str = "INFO"

    # Session
    max_context_messages: int = 50
    max_tool_rounds: int = 10

    # Permissions
    auto_approve_reads: bool = True
    # Tools that always require user approval (comma-separated tool:action pairs or tool names)
    # e.g. "calendar:create,calendar:update,calendar:delete,schedule_reminder:create,schedule_reminder:cancel"
    approval_required_tools: str = ""

    # Default provider
    default_provider: str = "claude"

    # OpenAI
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_enabled: bool = False
    openai_model: str = "gpt-4o"

    # Gemini
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_enabled: bool = False
    gemini_model: str = "gemini-2.0-flash"

    # AWS Bedrock (uses boto3 credential chain — AWS_PROFILE, IAM roles, etc.)
    bedrock_enabled: bool = False
    bedrock_region: str = "us-east-1"
    bedrock_model: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"

    # Ollama (Phase 2)
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Routing (Phase 2)
    local_model_threshold_tokens: int = 1000

    # Web Search (Phase 2)
    web_search_enabled: bool = False
    searxng_url: str = "http://localhost:8888"

    # Vector Search (Phase 2)
    vector_search_enabled: bool = False
    embedding_model: str = "nomic-embed-text"

    # Vision — override auto-detection for the main model (True/False/None=auto)
    vision: bool | None = None

    # Media (Phase 2)
    max_media_size_mb: int = 10

    # Telegram (Phase 3)
    telegram_enabled: bool = False
    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_user_ids_raw: str = Field(default="", validation_alias="ASSISTANT_TELEGRAM_ALLOWED_USER_IDS")
    telegram_webhook_url: str = ""

    # Scheduler (Phase 3)
    scheduler_enabled: bool = False
    scheduler_timezone: str = "UTC"

    # Plugins (Phase 4)
    plugins_enabled: bool = False

    # Agents (Phase 4)
    agents_enabled: bool = False

    # Watchdog (Phase 3)
    watchdog_enabled: bool = False
    watchdog_paths_raw: str = Field(default="", validation_alias="ASSISTANT_WATCHDOG_PATHS")
    watchdog_debounce_seconds: float = 2.0
    watchdog_analyze: bool = False

    # Webhooks (Phase 4)
    webhook_enabled: bool = False
    webhook_secret: str = ""

    # WhatsApp
    whatsapp_enabled: bool = False
    whatsapp_allowed_numbers_raw: str = Field(default="", validation_alias="ASSISTANT_WHATSAPP_ALLOWED_NUMBERS")
    whatsapp_session_name: str = "assistant"

    # Google Calendar
    google_calendar_enabled: bool = False
    google_client_id: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")

    # Calendar ICS feeds — auto-synced on startup
    # Comma-separated "name|url" pairs, e.g. Personal|https://...basic.ics,Work|https://...
    calendar_feeds_raw: str = Field(default="", validation_alias="ASSISTANT_CALENDAR_FEEDS")

    # CalDAV (Radicale)
    caldav_enabled: bool = False
    caldav_url: str = ""
    caldav_username: str = Field(default="", validation_alias="CALDAV_USERNAME")
    caldav_password: str = Field(default="", validation_alias="CALDAV_PASSWORD")

    # YouTube
    youtube_enabled: bool = False

    # Reddit
    reddit_enabled: bool = False

    # Tool output pagination
    tool_output_cap: int = 15_000

    # Reflection — nightly extraction of long-term memories from daily logs
    reflection_enabled: bool = False
    reflection_model: str = "ollama/minimax-m2.5:cloud"
    reflection_hour: int = 0  # hour in scheduler_timezone (reviews previous day)

    # DND (Phase 4)
    dnd_enabled: bool = False
    dnd_start: str = "23:00"
    dnd_end: str = "07:00"
    dnd_allow_urgent: bool = True

    @property
    def calendar_feeds(self) -> list[dict[str, str]]:
        """Parse 'name|url,name|url,...' into list of {name, url} dicts."""
        raw = self.calendar_feeds_raw.strip()
        if not raw:
            return []
        feeds = []
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if "|" in entry:
                name, url = entry.split("|", 1)
                feeds.append({"name": name.strip(), "url": url.strip()})
            else:
                # URL only — use URL as name
                feeds.append({"name": entry, "url": entry})
        return feeds

    @property
    def telegram_allowed_user_ids(self) -> list[int]:
        raw = self.telegram_allowed_user_ids_raw.strip()
        if not raw:
            return []
        return [int(x) for x in raw.split(",") if x.strip()]

    @property
    def watchdog_paths(self) -> list[str]:
        raw = self.watchdog_paths_raw.strip()
        if not raw:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]

    @property
    def whatsapp_allowed_numbers(self) -> list[str]:
        raw = self.whatsapp_allowed_numbers_raw.strip()
        if not raw:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]

    @property
    def memory_dir(self) -> Path:
        return self.data_dir / "memory"

    @property
    def daily_log_dir(self) -> Path:
        return self.memory_dir / "daily"

    @property
    def identity_path(self) -> Path:
        return self.memory_dir / "IDENTITY.md"

    @property
    def memory_path(self) -> Path:
        return self.memory_dir / "MEMORY.md"

    @property
    def audit_log_path(self) -> Path:
        return self.data_dir / "logs" / "audit.jsonl"

    @property
    def app_log_path(self) -> Path:
        return self.data_dir / "logs" / "app.log"

    @property
    def search_db_path(self) -> Path:
        return self.data_dir / "db" / "search.db"

    @property
    def skills_dir(self) -> Path:
        return self.data_dir / "skills"

    @property
    def threads_dir(self) -> Path:
        return self.data_dir / "threads"

    @property
    def embeddings_db_path(self) -> Path:
        return self.data_dir / "db" / "embeddings.db"

    @property
    def plugins_dir(self) -> Path:
        return self.data_dir / "plugins"

    @property
    def agents_dir(self) -> Path:
        return self.data_dir / "agents"

    @property
    def scheduler_db_path(self) -> Path:
        return self.data_dir / "db" / "scheduler.db"

    @property
    def workflow_dir(self) -> Path:
        return self.data_dir / "workflows"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def whatsapp_auth_dir(self) -> Path:
        return self.data_dir / "whatsapp_auth"

    @property
    def google_auth_dir(self) -> Path:
        return self.data_dir / "google_auth"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
