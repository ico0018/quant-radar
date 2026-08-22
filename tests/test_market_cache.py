import asyncio
import json
from decimal import Decimal

from app.cache.market_cache import MarketCache
from app.models.market import Ticker


class FakeRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    async def set(self, name: str, value: str, ex: int) -> None:
        self.calls.append((name, value, ex))


def test_cache_uses_ticker_key_ttl_and_decimal_strings() -> None:
    redis = FakeRedis()
    ticker = Ticker(symbol="BTCUSDT", last_price=Decimal("1.25"), bid_price=Decimal("1.2"), timestamp_ms=1)
    asyncio.run(MarketCache(redis, ttl_seconds=120).set_ticker(ticker))
    key, value, ttl = redis.calls[0]
    assert key == "quant-radar:ticker:BTCUSDT"
    assert ttl == 120
    assert json.loads(value)["last_price"] == "1.25"
