"""Trend indicators required for Phase 1."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from app.config import INDICATOR_WINDOWS
from app.models import Candle


def calculate_trend_indicators(candles: Sequence[Candle]) -> pd.DataFrame:
    """Build an OHLCV frame and add MA/EMA values for the configured windows."""
    if not candles:
        raise ValueError("cannot calculate indicators from empty candles")

    frame = pd.DataFrame(
        [
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in sorted(candles, key=lambda item: item.timestamp)
        ]
    )
    for window in INDICATOR_WINDOWS:
        frame[f"ma_{window}"] = frame["close"].rolling(window, min_periods=window).mean()
        frame[f"ema_{window}"] = frame["close"].ewm(
            span=window, adjust=False, min_periods=window
        ).mean()
    return frame
