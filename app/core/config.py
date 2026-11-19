"""Application settings, loaded from environment variables / a local .env file."""

from functools import lru_cache

from pydantic import Field, field_validator
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

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_postgres_driver(cls, v: str) -> str:
        """Render and Heroku inject postgres:// or postgresql://; SQLAlchemy needs postgresql+psycopg:// for psycopg v3."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return "postgresql+psycopg://" + v[len("postgres://"):]
            if v.startswith("postgresql://"):
                return "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    # Queue broker / Redis configuration (Task 16)
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis broker URL")
    celery_broker_url: str | None = Field(default=None, description="Celery broker URL override")
    celery_result_backend: str | None = Field(default=None, description="Celery result backend URL override")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one parse per process)."""
    return Settings()  # type: ignore[call-arg]
