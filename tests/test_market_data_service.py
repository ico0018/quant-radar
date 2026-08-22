import asyncio
from decimal import Decimal

from app.models.market import Candle, Ticker
from app.services.market_data import MarketDataService


class FakeExchangeClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def get_ticker(self, symbol: str) -> Ticker:
        self.calls.append(("ticker", symbol))
        return Ticker(symbol=symbol, last_price=Decimal("1"), timestamp_ms=1)

    async def get_candles(self, symbol: str, interval: str, limit: int = 100) -> list[Candle]:
        self.calls.append(("candles", symbol, interval, limit))
        return [Candle(symbol=symbol, interval=interval, timestamp_ms=1, open="1", high="1", low="1", close="1", base_volume="1")]


def test_get_snapshot_delegates_to_exchange() -> None:
    exchange = FakeExchangeClient()
    ticker = asyncio.run(MarketDataService(exchange).get_snapshot("BTCUSDT"))
    assert ticker.last_price == Decimal("1")
    assert exchange.calls == [("ticker", "BTCUSDT")]


def test_get_recent_candles_delegates_to_exchange() -> None:
    exchange = FakeExchangeClient()
    candles = asyncio.run(MarketDataService(exchange).get_recent_candles("ETHUSDT", "1h", 20))
    assert len(candles) == 1
    assert exchange.calls == [("candles", "ETHUSDT", "1h", 20)]
