"""Application configuration loaded from environment variables and .env."""

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    bitget_rest_url: str = "https://api.bitget.com"
    bitget_ws_url: str = "wss://ws.bitget.com/v2/ws/public"
    market_symbols: Annotated[list[str], NoDecode] = ["BTCUSDT", "ETHUSDT"]
    market_cache_ttl_seconds: int = 120
    ws_reconnect_max_seconds: int = 30
    database_url: str | None = None
    redis_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    wecom_webhook_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("market_symbols", mode="before")
    @classmethod
    def parse_market_symbols(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [symbol.strip() for symbol in value.split(",") if symbol.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
