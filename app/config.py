"""Environment-backed application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the single A0 application process."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://evofit:evofit@localhost:5432/evofit"
    log_level: str = "INFO"
    experiment_mode: bool = False
    otel_exporter_otlp_endpoint: str | None = None
    seed_id: str = "a0-v1"


@lru_cache
def get_settings() -> Settings:
    """Return cached process settings."""
    return Settings()
