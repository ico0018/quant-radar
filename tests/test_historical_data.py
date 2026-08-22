import asyncio
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.data.downloader import HistoricalDataDownloader
from app.data.quality import DataQualityError, missing_ranges, validate_candles
from app.data.storage import load_candles, parquet_path, write_candles
from app.models import Candle


def candle(timestamp: int, close: float = 100.0) -> Candle:
    return Candle(timestamp, close, close + 2, close - 2, close + 1, 4.0, 400.0)


def test_validation_deduplicates_and_reports_gaps() -> None:
    candles, report = validate_candles([candle(0), candle(900_000), candle(900_000), candle(2_700_000)], "15m")
    assert [item.timestamp for item in candles] == [0, 900_000, 2_700_000]
    assert report.duplicate_count == 1
    assert report.missing_period_count == 1
    assert report.invalid_ohlc_count == 0
    assert not report.is_complete


def test_missing_ranges_groups_contiguous_missing_candles() -> None:
    assert missing_ranges({0, 1_800_000}, 0, 3_600_000, "15m") == [(900_000, 1_800_000), (2_700_000, 3_600_000)]


def test_validation_rejects_invalid_ohlc_before_persistence() -> None:
    invalid = Candle(0, 100, 101, 99, 102, 1, 100)
    try:
        validate_candles([invalid], "15m")
    except DataQualityError as error:
        assert "invalid candles" in str(error)
    else:
        raise AssertionError("invalid OHLC must fail validation")


class FakeHistoryClient:
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles
        self.calls: list[tuple[int, int]] = []

    async def get_historical_candles(self, _symbol: str, _timeframe: str, *, start_time: int, end_time: int, limit: int) -> list[Candle]:
        self.calls.append((start_time, end_time))
        return [item for item in self.candles if start_time <= item.timestamp <= end_time][:limit]


def test_downloader_paginates_writes_parquet_and_updates_incrementally(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1, 1, tzinfo=UTC)
    timestamps = list(range(int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() * 1000), int(now.timestamp() * 1000), 900_000))
    client = FakeHistoryClient([candle(timestamp) for timestamp in timestamps])
    settings = Settings(_env_file=None, bitget_rate_limit_wait_seconds=0)
    downloader = HistoricalDataDownloader(client, tmp_path, settings)
    first = asyncio.run(downloader.download("BTCUSDT", "15m", 1 / 24, now))
    path = parquet_path(tmp_path, "BTCUSDT", "15m")
    assert first.added_candles == 4
    assert path.exists()
    assert len(load_candles(path)) == 4
    calls_after_first = len(client.calls)
    second = asyncio.run(downloader.download("BTCUSDT", "15m", 1 / 24, now))
    assert second.added_candles == 0
    assert len(client.calls) == calls_after_first


def test_incremental_run_backfills_only_middle_missing_range(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1, 1, tzinfo=UTC)
    timestamps = list(range(int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() * 1000), int(now.timestamp() * 1000), 900_000))
    client = FakeHistoryClient([candle(timestamp) for timestamp in timestamps])
    path = parquet_path(tmp_path, "BTCUSDT", "15m")
    missing = {timestamps[1], timestamps[2], timestamps[3]}
    write_candles(path, [item for item in client.candles if item.timestamp not in missing])
    downloader = HistoricalDataDownloader(client, tmp_path, Settings(_env_file=None, bitget_rate_limit_wait_seconds=0))
    result = asyncio.run(downloader.download("BTCUSDT", "15m", 1 / 24, now))
    assert result.added_candles == 3
    assert result.report.missing_period_count == 0
    assert result.report.is_complete
    assert len(client.calls) == 1
    assert client.calls[0][0] == timestamps[1]
    assert client.calls[0][1] == timestamps[-1] + 900_000 - 1


def test_fetch_range_pages_history_requests(tmp_path: Path) -> None:
    client = FakeHistoryClient([candle(index * 900_000) for index in range(201)])
    downloader = HistoricalDataDownloader(client, tmp_path, Settings(_env_file=None, bitget_rate_limit_wait_seconds=0))
    fetched = asyncio.run(downloader._fetch_range("BTCUSDT", "15m", 0, 201 * 900_000))
    assert len(fetched) == 201
    assert len(client.calls) == 2
