from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "SmartCut AI"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Supabase
    supabase_url: str
    supabase_publishable_key: str
    supabase_secret_key: str
    supabase_bucket: str = "snippets"
    supabase_jwt_secret: str

    # Celery / Redis
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
