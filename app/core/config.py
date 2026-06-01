"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "store-intelligence-api"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = False
    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "store_intel"
    postgres_password: str = "store_intel"
    postgres_db: str = "store_intelligence"

    # Optional override; takes precedence when set.
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        if self.database_url:
            url = self.database_url
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic migrations."""
        url = self.async_database_url
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
