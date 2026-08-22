from decimal import Decimal

from app.models.market import Candle, Ticker


def test_ticker_coerces_string_prices_to_decimal() -> None:
    ticker = Ticker(symbol="BTCUSDT", last_price="65000.12", timestamp_ms=1)
    assert ticker.last_price == Decimal("65000.12")


def test_candle_builds_with_decimal_values() -> None:
    candle = Candle(symbol="BTCUSDT", interval="5m", timestamp_ms=1, open="1", high="2", low="0.5", close="1.5", base_volume="10", quote_volume="15")
    assert candle.close == Decimal("1.5")
    assert candle.quote_volume == Decimal("15")
