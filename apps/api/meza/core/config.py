"""Centralised configuration. Everything comes from the environment / .env file.

No model names, credentials or paths are hard-coded anywhere else in the codebase.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "MEZA"
    log_level: str = "INFO"

    secret_key: str = "dev-only-insecure-secret-change-me"
    access_token_minutes: int = 720
    cookie_secure: bool = False

    database_url: str = "sqlite+aiosqlite:///./storage/meza.db"
    redis_url: str = ""

    llm_provider: str = "ollama"  # ollama | none
    llm_model: str = ""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = ""
    embedding_model: str = "nomic-embed-text"
    llm_timeout_seconds: int = 120

    upload_dir: str = "./storage/uploads"
    inbox_dir: str = "./storage/inbox"
    backup_dir: str = "./storage/backups"
    max_upload_mb: int = 50

    max_agent_steps: int = 8
    max_agent_tool_calls: int = 40
    max_agent_handoffs: int = 6
    agent_timeout_seconds: int = 90

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 240

    admin_email: str = "admin@atonplus.internal-demo.kz"
    admin_password: str = "change-me"

    demo_data: bool = Field(default=False, description="Set automatically when demo seed was loaded")

    @field_validator("log_level")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    # ---- derived helpers -------------------------------------------------
    @property
    def effective_model(self) -> str:
        return self.llm_model or self.ollama_model

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def resolve_path(self, p: str) -> Path:
        path = Path(p)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path

    @property
    def upload_path(self) -> Path:
        return self.resolve_path(self.upload_dir)

    @property
    def inbox_path(self) -> Path:
        return self.resolve_path(self.inbox_dir)

    @property
    def backup_path(self) -> Path:
        return self.resolve_path(self.backup_dir)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
