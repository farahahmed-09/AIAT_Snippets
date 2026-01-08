from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = Field(default="AIAT-SNIPPETS")
    APP_VERSION: str = Field(default="1.0.0")

    # AI Model Settings
    LITELLM_API_KEY: str
    LITELLM_BASE_URL: str

    # Database Settings
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_BUCKET: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()