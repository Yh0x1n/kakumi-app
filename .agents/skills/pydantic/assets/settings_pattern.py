"""
BaseSettings singleton pattern for kakumi-app.

Usage:
  from kakumi_app.config import get_settings
  settings = get_settings()
  print(settings.database_url)

Environment variables are read from:
  1. OS environment
  2. .env file (root of project)

Install: pip install pydantic-settings
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment / .env file.

    All fields are typed; defaults are safe for local development.
    Override in production via real environment variables — they take
    precedence over .env values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # APP_NAME == app_name
        extra="ignore",  # silently skip unknown env vars
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = Field(default="kakumi-app", description="Application name")
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite:///kakumi.db",
        description="SQLAlchemy-compatible database URL",
    )

    # ── Security ─────────────────────────────────────────────────────────────
    secret_key: SecretStr = Field(
        default=SecretStr("change-me-in-production"),
        description="Used for signing tokens; MUST be overridden in production",
    )

    # ── WKF / Tournament ─────────────────────────────────────────────────────
    default_match_duration_seconds: int = Field(
        default=180,
        ge=60,
        le=600,
        description="Default Kumite match duration (WKF 2026 §6.1 default: 3 min)",
    )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def secret_key_str(self) -> str:
        """Expose the raw secret only when explicitly requested."""
        return self.secret_key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached singleton Settings instance.

    lru_cache ensures the .env file is only read once per process.
    Call `get_settings.cache_clear()` in tests to reload settings.
    """
    return Settings()


# ── Usage example ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    s = get_settings()
    print(f"App       : {s.app_name}")
    print(f"Env       : {s.environment}")
    print(f"Debug     : {s.debug}")
    print(f"DB URL    : {s.database_url}")
    print(f"Prod?     : {s.is_production}")
