from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.backtest.dataset import DatasetLoader, DatasetRangeError, IncompleteDatasetError
from app.data.storage import parquet_path, write_candles
from app.models import Candle


def candle(timestamp: int, price: float = 100.0) -> Candle:
    return Candle(timestamp, price, price + 1, price - 1, price, 1.0, price)


def write_dataset(root: Path, timeframe: str, candles: list[Candle]) -> None:
    write_candles(parquet_path(root, "BTCUSDT", timeframe), candles)


@pytest.mark.parametrize(("timeframe", "interval"), [("15m", 900_000), ("1H", 3_600_000)])
def test_loader_supports_backtest_timeframes(tmp_path: Path, timeframe: str, interval: int) -> None:
    write_dataset(tmp_path, timeframe, [candle(0), candle(interval), candle(2 * interval)])
    dataset = DatasetLoader(tmp_path).load("btcusdt", timeframe)
    assert dataset.symbol == "BTCUSDT"
    assert dataset.report.is_complete
    assert len(dataset.candles) == 3


def test_loader_rejects_incomplete_dataset(tmp_path: Path) -> None:
    write_dataset(tmp_path, "15m", [candle(0), candle(1_800_000)])
    with pytest.raises(IncompleteDatasetError, match="incomplete"):
        DatasetLoader(tmp_path).load("BTCUSDT", "15m")


def test_loader_filters_utc_range_and_sorts_candles(tmp_path: Path) -> None:
    interval = 900_000
    write_dataset(
        tmp_path,
        "15m",
        [candle(2 * interval), candle(0), candle(3 * interval), candle(interval)],
    )
    dataset = DatasetLoader(tmp_path).load(
        "BTCUSDT",
        "15m",
        start=datetime.fromtimestamp(interval / 1000, tz=UTC),
        end=datetime.fromtimestamp(3 * interval / 1000, tz=UTC),
    )
    assert [item.timestamp for item in dataset.candles] == [interval, 2 * interval]
    assert dataset.report.is_complete


def test_loader_requires_timezone_aware_range(tmp_path: Path) -> None:
    write_dataset(tmp_path, "15m", [candle(0), candle(900_000)])
    with pytest.raises(DatasetRangeError, match="timezone-aware"):
        DatasetLoader(tmp_path).load("BTCUSDT", "15m", start=datetime(1970, 1, 1))
