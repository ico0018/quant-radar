"""Application-facing market data service."""

import asyncio
import logging
from typing import Protocol

from app.cache.market_cache import MarketCache
from app.models.market import Candle, Ticker


class MarketDataExchangeClient(Protocol):
    async def get_ticker(self, symbol: str) -> Ticker: ...
    async def get_candles(self, symbol: str, interval: str, limit: int = 100) -> list[Candle]: ...


class MarketDataService:
    def __init__(self, exchange_client: MarketDataExchangeClient, market_cache: MarketCache | None = None) -> None:
        self._exchange_client = exchange_client
        self._market_cache = market_cache

    async def get_snapshot(self, symbol: str) -> Ticker:
        return await self._exchange_client.get_ticker(symbol)

    async def get_recent_candles(self, symbol: str, interval: str = "5m", limit: int = 100) -> list[Candle]:
        return await self._exchange_client.get_candles(symbol, interval, limit)

    async def handle_ticker(self, ticker: Ticker) -> None:
        if self._market_cache is None:
            return
        try:
            await self._market_cache.set_ticker(ticker)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logging.getLogger(__name__).error("unable to cache latest ticker %s: %s", ticker.symbol, exc)
