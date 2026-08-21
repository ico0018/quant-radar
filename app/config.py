"""Central configuration for Quant Radar's market-data layer."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BITGET_CONTRACTS_PATH = "/api/v2/mix/market/contracts"
BITGET_CANDLES_PATH = "/api/v2/mix/market/candles"
USDT_FUTURES_PRODUCT_TYPE = "USDT-FUTURES"
SUPPORTED_GRANULARITIES = frozenset({"1m", "5m", "15m", "1H", "4H"})
INDICATOR_WINDOWS = (20, 60, 120)


class Settings(BaseSettings):
    """Settings loaded from environment variables or a local ``.env`` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    bitget_rest_url: str = "https://api.bitget.com"
    bitget_request_timeout_seconds: float = Field(default=10.0, gt=0)
    bitget_usdt_futures_product_type: str = USDT_FUTURES_PRODUCT_TYPE
