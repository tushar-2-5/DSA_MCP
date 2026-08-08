import os
from dotenv import load_dotenv

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        database_url: str = "postgresql://root@localhost:26257/recall?sslmode=disable"
        gemini_api_key: str = ""

        model_config = SettingsConfigDict(
            env_file=".env", env_file_encoding="utf-8", extra="ignore"
        )

    settings = Settings()
    DATABASE_URL = settings.database_url
    GEMINI_API_KEY = settings.gemini_api_key
except ImportError:
    load_dotenv()
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://root@localhost:26257/recall?sslmode=disable"
    )
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
