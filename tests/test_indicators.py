import math

import pytest

from app.indicators import calculate_trend_indicators
from app.models import Candle


def candles(count: int) -> list[Candle]:
    return [
        Candle(
            timestamp=index * 60_000,
            open=float(index),
            high=float(index + 1),
            low=float(index - 1),
            close=float(index),
            volume=10.0,
        )
        for index in range(1, count + 1)
    ]


def test_calculate_trend_indicators_adds_all_required_columns() -> None:
    frame = calculate_trend_indicators(candles(120))
    assert {"ma_20", "ma_60", "ma_120", "ema_20", "ema_60", "ema_120"} <= set(frame.columns)
    assert frame.iloc[-1]["ma_20"] == pytest.approx(110.5)
    assert frame.iloc[-1]["ma_60"] == pytest.approx(90.5)
    assert frame.iloc[-1]["ma_120"] == pytest.approx(60.5)
    assert not math.isnan(frame.iloc[-1]["ema_120"])


def test_calculate_trend_indicators_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="empty candles"):
        calculate_trend_indicators([])
