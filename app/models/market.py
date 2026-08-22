"""Exchange-neutral market data models."""

from decimal import Decimal

from pydantic import BaseModel


class Ticker(BaseModel):
    symbol: str
    last_price: Decimal
    bid_price: Decimal | None = None
    ask_price: Decimal | None = None
    high_24h: Decimal | None = None
    low_24h: Decimal | None = None
    volume_24h: Decimal | None = None
    quote_volume_24h: Decimal | None = None
    timestamp_ms: int


class Candle(BaseModel):
    symbol: str
    interval: str
    timestamp_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    base_volume: Decimal
    quote_volume: Decimal | None = None
