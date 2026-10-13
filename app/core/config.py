"""Application settings, loaded from environment variables / a local .env file."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings. Values come from the environment first, then from `.env`.

    There are deliberately no defaults for secrets: the app refuses to start
    without them, so a missing configuration is noticed immediately.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LedgerForge API"
    app_version: str = "0.1.0"
    debug: bool = False

    # e.g. postgresql+psycopg://user:password@db:5432/ledgerforge
    # Inside Docker Compose the host is the service name (`db`), not `localhost`.
    database_url: str = Field(..., description="SQLAlchemy database URL")
    secret_key: str = Field(..., min_length=16, description="Key used to sign tokens")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one parse per process)."""
    return Settings()  # type: ignore[call-arg]
