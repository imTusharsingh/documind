from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables.

    Application settings use the DOCUMIND_ prefix, for example
    DOCUMIND_ENVIRONMENT=development. DATABASE_URL keeps its conventional
    name because local tooling, Alembic, and Docker Compose already use it.
    """

    app_name: str = "DocuMind API"
    version: str = "0.1.0"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+psycopg://documind:documind_dev_password@localhost:5432/documind",
        validation_alias=AliasChoices("DATABASE_URL", "DOCUMIND_DATABASE_URL"),
    )
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_connect_timeout: int = 3

    upload_dir: str = Field(
        default="data/uploads",
        validation_alias=AliasChoices("UPLOAD_DIR", "DOCUMIND_UPLOAD_DIR"),
    )
    max_upload_mb: int = Field(
        default=25,
        validation_alias=AliasChoices("MAX_UPLOAD_MB", "DOCUMIND_MAX_UPLOAD_MB"),
    )

    chunk_tokens: int = 350
    chunk_overlap_tokens: int = 50

    worker_poll_seconds: float = 1.0
    worker_stale_after_seconds: int = 300

    model_config = SettingsConfigDict(
        env_prefix="DOCUMIND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        """Maximum accepted upload size in bytes."""
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return one immutable settings instance per process."""
    return Settings()
