from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "persona-sim"
    environment: str = Field(default="local", alias="APP_ENV")
    openai_api_key: str = Field(default="CHANGE_ME", alias="OPENAI_API_KEY")
    database_url: str = Field(default="sqlite+aiosqlite:///./personas.db", alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
