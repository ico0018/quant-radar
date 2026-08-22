"""Application-facing market data service."""

from typing import Protocol

from app.models.market import Candle, Ticker


class MarketDataExchangeClient(Protocol):
    async def get_ticker(self, symbol: str) -> Ticker: ...
    async def get_candles(self, symbol: str, interval: str, limit: int = 100) -> list[Candle]: ...


class MarketDataService:
    def __init__(self, exchange_client: MarketDataExchangeClient) -> None:
        self._exchange_client = exchange_client

    async def get_snapshot(self, symbol: str) -> Ticker:
        return await self._exchange_client.get_ticker(symbol)

    async def get_recent_candles(self, symbol: str, interval: str = "5m", limit: int = 100) -> list[Candle]:
        return await self._exchange_client.get_candles(symbol, interval, limit)
