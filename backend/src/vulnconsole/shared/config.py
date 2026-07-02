"""Application settings loaded from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "vulnconsole"
    environment: str = "dev"
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+asyncpg://vulnconsole:change-me-postgres@localhost:5432/vulnconsole"
    )
    redis_url: str = "redis://:change-me-redis@localhost:6379/0"
    nats_url: str = "nats://localhost:4222"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "vulnconsole"
    minio_secret_key: str = "change-me-minio"
    minio_secure: bool = False
    minio_bucket_artifacts: str = "scan-artifacts"

    jwt_secret_key: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 7

    max_upload_bytes: int = 50 * 1024 * 1024
    login_rate_limit_per_minute: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
