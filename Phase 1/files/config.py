"""Application configuration.

All settings are loaded from environment variables (or a local .env file in
development). Nothing secret is hard-coded. Access via `get_settings()`.
"""
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------
    app_name: str = "AI Stock Signal Pro"
    environment: str = Field(default="development")  # development | staging | production
    debug: bool = Field(default=False)
    api_v1_prefix: str = "/api/v1"

    # --- Logging -------------------------------------------------------
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)  # True in prod for structured logs

    # --- PostgreSQL ----------------------------------------------------
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="ai_stock_signal")
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_echo: bool = Field(default=False)

    # --- Redis ---------------------------------------------------------
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: str | None = Field(default=None)

    # --- Broker / market-data provider ---------------------------------
    broker_provider: str = Field(default="zerodha")  # selects the adapter
    zerodha_api_key: str | None = Field(default=None)
    zerodha_api_secret: str | None = Field(default=None)
    # Access token is obtained via Kite's daily interactive login; supply it
    # here (or refresh it via a future endpoint). Without it, sync jobs no-op.
    zerodha_access_token: str | None = Field(default=None)

    # --- Ingestion behaviour -------------------------------------------
    job_queue_key: str = Field(default="ingest:jobs")
    default_lookback_days: int = Field(default=30)   # initial backfill window
    intraday_sync_interval_min: int = Field(default=5)
    quote_refresh_sec: int = Field(default=5)
    cache_latest_ttl: int = Field(default=120)       # seconds
    cache_quote_ttl: int = Field(default=30)         # seconds

    # --- Derived URLs --------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton accessor for settings."""
    return Settings()


settings = get_settings()
