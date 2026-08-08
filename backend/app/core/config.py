from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MEZA AI"
    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    api_secret_key: str = Field(default="change-me-to-a-long-random-string")
    fernet_key: str = ""

    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    jwt_algorithm: str = "HS256"

    database_url: str = (
        "postgresql+asyncpg://meza:meza_dev_change_me@localhost:5432/meza_ai"
    )
    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "meza"
    minio_secret_key: str = "meza_minio_change_me"
    minio_bucket_media: str = "meza-media"
    minio_bucket_docs: str = "meza-docs"
    minio_secure: bool = False

    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:14b-instruct-q4_K_M"
    llm_mock: bool = False
    gpu_enabled: bool = False
    system_prompt: str = (
        "Ты MEZA AI — локальный ассистент склада и производства. "
        "Отвечай кратко и по делу на русском. Если данных нет — скажи об этом."
    )

    langfuse_enabled: bool = False
    langfuse_host: str = "http://langfuse:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
