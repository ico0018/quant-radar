"""Deterministic candle validation and quality reporting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Sequence

from app.models import Candle

TIMEFRAME_MILLISECONDS = {"15m": 15 * 60_000, "1H": 60 * 60_000}


@dataclass(frozen=True, slots=True)
class DataQualityReport:
    total_candles: int
    first_timestamp: int | None
    last_timestamp: int | None
    duplicate_count: int
    missing_period_count: int
    invalid_ohlc_count: int

    def as_dict(self) -> dict[str, int | str | None]:
        data: dict[str, int | str | None] = asdict(self)
        for key in ("first_timestamp", "last_timestamp"):
            timestamp = data[key]
            data[key] = (
                datetime.fromtimestamp(int(timestamp) / 1000, tz=UTC).isoformat()
                if timestamp is not None
                else None
            )
        return data


class DataQualityError(ValueError):
    """Raised before persistence if OHLC values or timestamps are invalid."""


def validate_candles(candles: Sequence[Candle], timeframe: str) -> tuple[list[Candle], DataQualityReport]:
    """Sort and deduplicate candles, then validate boundaries, OHLC, and gaps."""
    if timeframe not in TIMEFRAME_MILLISECONDS:
        raise ValueError(f"unsupported historical timeframe: {timeframe}")
    interval = TIMEFRAME_MILLISECONDS[timeframe]
    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    unique: list[Candle] = []
    seen: set[int] = set()
    duplicate_count = 0
    invalid_count = 0
    for candle in ordered:
        if candle.timestamp in seen:
            duplicate_count += 1
            continue
        seen.add(candle.timestamp)
        valid_ohlc = candle.low <= min(candle.open, candle.close) <= max(candle.open, candle.close) <= candle.high
        valid_values = candle.low >= 0 and candle.high >= 0 and candle.base_volume >= 0 and candle.quote_volume >= 0
        if candle.timestamp % interval != 0 or not valid_ohlc or not valid_values:
            invalid_count += 1
            continue
        unique.append(candle)
    missing_count = sum(
        max(0, (current.timestamp - previous.timestamp) // interval - 1)
        for previous, current in zip(unique, unique[1:])
    )
    report = DataQualityReport(
        total_candles=len(unique),
        first_timestamp=unique[0].timestamp if unique else None,
        last_timestamp=unique[-1].timestamp if unique else None,
        duplicate_count=duplicate_count,
        missing_period_count=missing_count,
        invalid_ohlc_count=invalid_count,
    )
    if invalid_count:
        raise DataQualityError(f"refusing to persist {invalid_count} invalid candles: {report.as_dict()}")
    return unique, report


def missing_ranges(existing_timestamps: set[int], start: int, end: int, timeframe: str) -> list[tuple[int, int]]:
    """Return contiguous [start, end) UTC-ms ranges missing from a local cache."""
    interval = TIMEFRAME_MILLISECONDS[timeframe]
    ranges: list[tuple[int, int]] = []
    range_start: int | None = None
    timestamp = start
    while timestamp < end:
        if timestamp not in existing_timestamps:
            range_start = timestamp if range_start is None else range_start
        elif range_start is not None:
            ranges.append((range_start, timestamp))
            range_start = None
        timestamp += interval
    if range_start is not None:
        ranges.append((range_start, end))
    return ranges
