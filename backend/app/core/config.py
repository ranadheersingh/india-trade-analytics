from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    postgres_user: str = "trade"
    postgres_password: str = "changeme"
    postgres_db: str = "india_trade"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Auth / JWT
    jwt_secret: str = "dev-secret-change-me-in-production-please-use-a-long-random-string"
    jwt_secret_previous: str = ""
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 60
    refresh_token_ttl_days: int = 7

    # App
    log_level: str = "INFO"
    timezone: str = "Asia/Kolkata"
    enable_scheduler: bool = True
    frontend_origin: str = "http://localhost:3000"
    admin_email: str = "admin@india-trade.com"
    admin_password: str = "admin123"

    # Ingestion API keys (optional)
    exchangerate_api_key: str = ""
    comtrade_api_key: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
