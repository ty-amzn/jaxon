"""Town Square configuration via environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "TOWNSQUARE_", "env_file": ".env", "extra": "ignore"}

    host: str = "127.0.0.1"
    port: int = 51431
    db_path: Path = Path("./townsquare.db")
    webhook_callback_url: str = Field(
        default="",
        description="Jaxon base URL for webhook callbacks (e.g. http://localhost:51430)",
    )
