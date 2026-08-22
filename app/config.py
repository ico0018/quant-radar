"""Application configuration loaded from environment variables and .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    bitget_rest_url: str = "https://api.bitget.com"
    bitget_ws_url: str = "wss://ws.bitget.com/v2/ws/public"
    database_url: str | None = None
    redis_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    wecom_webhook_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
