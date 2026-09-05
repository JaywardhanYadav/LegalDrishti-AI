from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    """Application settings loaded from environment variables and root .env files.."""

    model_config = SettingsConfigDict(
        env_file = ENV_FILE,
        env_file_encoding= "utf-8",
        extra="ignore"
    )

    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"
    secret_key: str = Field(default="",repr=False)

    vector_db: str = "weaviate"
    vector_url: str = "http://localhost:8080"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/legaldrishti"
    redis_url: str = "redis://localhost:6379/0"

    tavily_api_key: str = Field(default="", repr=False)
    tavily_base_url: str = "https://api.tavily.com"

    llm_provider: str = "openai"
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = "gpt-5.6-terra"

    embedding_provider: str = "openai"
    openai_embedding_model: str = "text-embedding-3-large"

    jwt_secret: str = Field(default="", repr=False)
    jwt_access_token_expire_minutes: int = 30
    max_upload_size_mb: int = 50

@lru_cache
def get_settings() -> Settings:
    """ Retrun ccached appllication settings without exposing secret values"""
    return Settings()