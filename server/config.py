import os
from dotenv import load_dotenv

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        database_url: str = "postgresql://root@localhost:26257/recall?sslmode=disable"
        aws_region: str = "us-east-1"

        model_config = SettingsConfigDict(
            env_file=".env", env_file_encoding="utf-8", extra="ignore"
        )

    settings = Settings()
    DATABASE_URL = settings.database_url
    AWS_REGION = settings.aws_region
except ImportError:
    load_dotenv()
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://root@localhost:26257/recall?sslmode=disable"
    )
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

