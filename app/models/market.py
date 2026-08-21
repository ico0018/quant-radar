"""Models shared by market-data consumers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Candle:
    """One OHLCV candle, with ``timestamp`` represented as Unix milliseconds."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class FuturesContract:
    """The small, stable subset of a Bitget futures-contract response we need."""

    symbol: str
    base_coin: str
    quote_coin: str
    product_type: str
