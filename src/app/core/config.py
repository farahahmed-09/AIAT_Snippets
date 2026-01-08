from dotenv import load_dotenv
import logging
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartCut AI"
    API_V1_STR: str = "/api/v1"

    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    INPUT_DIR: str = os.path.join(DATA_DIR, "input")
    OUTPUT_DIR: str = os.path.join(DATA_DIR, "output")
    TEMP_DIR: str = os.path.join(DATA_DIR, "temp")

    # Database
    DATABASE_URL: str = "sqlite:///./snippets.db"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_BUCKET: str = "snippets"

    # API Keys
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
load_dotenv()

# Setup logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Ensure directories exist
os.makedirs(settings.INPUT_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)
