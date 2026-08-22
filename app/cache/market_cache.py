"""Redis latest-market snapshot cache."""

import json
from typing import Protocol

from app.models.market import Ticker


class RedisClient(Protocol):
    async def set(self, name: str, value: str, ex: int) -> object: ...


class MarketCache:
    def __init__(self, redis_client: RedisClient, ttl_seconds: int = 120) -> None:
        self._redis_client = redis_client
        self._ttl_seconds = ttl_seconds

    async def set_ticker(self, ticker: Ticker) -> None:
        await self._redis_client.set(
            f"quant-radar:ticker:{ticker.symbol}",
            json.dumps(ticker.model_dump(mode="json"), separators=(",", ":")),
            ex=self._ttl_seconds,
        )
