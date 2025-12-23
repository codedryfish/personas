from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    app_name: str = Field(default="persona-sim", alias="APP_NAME")
    environment: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="sqlite+aiosqlite:///./personas.db", alias="DATABASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    model_name: str = Field(default="gpt-4o-mini", alias="MODEL_NAME")
    default_temperature: float = Field(
        default=0.3, ge=0.0, le=1.0, alias="DEFAULT_TEMPERATURE"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="pretty", alias="LOG_FORMAT")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
