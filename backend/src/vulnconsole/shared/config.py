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
    minio_secret_key: str = "change-me-minio"  # noqa: S105 (dev default, overridden in prod)
    minio_secure: bool = False
    minio_bucket_artifacts: str = "scan-artifacts"

    jwt_secret_key: str = "dev-only-secret-change-me"  # noqa: S105 (dev default, overridden in prod)
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 7

    max_upload_bytes: int = 50 * 1024 * 1024
    login_rate_limit_per_minute: int = 10

    # SLA: days to remediate per severity (info has no SLA). Comma-free by design.
    sla_days_critical: int = 3
    sla_days_high: int = 7
    sla_days_medium: int = 30
    sla_days_low: int = 90
    # How often the worker scans for newly breached SLAs.
    sla_scan_interval_seconds: int = 60

    # Notification channels. Any that are configured are used; if none are set,
    # notifications are still recorded to the database and structured log.
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from: str = "vulnconsole@localhost"
    notify_email_to: str = ""
    notifications_base_url: str = "http://localhost:8080"


@lru_cache
def get_settings() -> Settings:
    return Settings()
