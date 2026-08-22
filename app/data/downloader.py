"""Incremental BTCUSDT historical data downloader."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import Settings
from app.data.quality import DataQualityReport, TIMEFRAME_MILLISECONDS, missing_ranges, validate_candles
from app.data.storage import load_candles, parquet_path, write_candles
from app.market_data import BitgetRestClient
from app.models import Candle

logger = logging.getLogger(__name__)
HISTORY_PAGE_LIMIT = 200


@dataclass(frozen=True, slots=True)
class DownloadResult:
    path: Path
    added_candles: int
    report: DataQualityReport


class HistoricalDataDownloader:
    def __init__(self, client: BitgetRestClient, root: Path = Path("data/parquet"), settings: Settings | None = None) -> None:
        self.client = client
        self.root = root
        self.settings = settings or Settings()

    async def download(self, symbol: str, timeframe: str, days: int, now: datetime | None = None) -> DownloadResult:
        if symbol.upper() != "BTCUSDT":
            raise ValueError("Phase 2A currently supports BTCUSDT only")
        if timeframe not in TIMEFRAME_MILLISECONDS or days <= 0:
            raise ValueError("timeframe must be 15m or 1H and days must be positive")
        interval = TIMEFRAME_MILLISECONDS[timeframe]
        current = (now or datetime.now(UTC)).astimezone(UTC)
        end = int(current.timestamp() * 1000) // interval * interval
        start = (int((current - timedelta(days=days)).timestamp() * 1000) // interval) * interval
        path = parquet_path(self.root, symbol, timeframe)
        existing = load_candles(path)
        existing, _ = validate_candles(existing, timeframe) if existing else ([], None)
        fetched: list[Candle] = []
        existing_timestamps = {c.timestamp for c in existing}
        ranges = missing_ranges(existing_timestamps, start, end, timeframe)
        logger.info("historical request range: start=%s end=%s timeframe=%s", start, end, timeframe)
        for index in range(0, len(ranges), self.settings.bitget_history_concurrency):
            batch = ranges[index:index + self.settings.bitget_history_concurrency]
            for range_start, range_end in batch:
                logger.info("requesting missing range: start=%s end=%s", range_start, range_end)
            results = await asyncio.gather(*[
                self._fetch_range(symbol, timeframe, range_start, range_end)
                for range_start, range_end in batch
            ])
            for result in results:
                fetched.extend(result)
            if self.settings.bitget_rate_limit_wait_seconds:
                await asyncio.sleep(self.settings.bitget_rate_limit_wait_seconds)
        combined, report = validate_candles([*existing, *fetched], timeframe)
        if report.missing_period_count:
            logger.warning("historical data gaps detected: %s", report.as_dict())
        write_candles(path, combined)
        return DownloadResult(path=path, added_candles=len({c.timestamp for c in fetched} - {c.timestamp for c in existing}), report=report)

    async def _fetch_range(self, symbol: str, timeframe: str, start: int, end: int) -> list[Candle]:
        interval = TIMEFRAME_MILLISECONDS[timeframe]
        cursor = end
        windows: list[tuple[int, int]] = []
        while cursor > start:
            page_start = max(start, cursor - HISTORY_PAGE_LIMIT * interval)
            windows.append((page_start, cursor))
            cursor = page_start
        if windows:
            logger.info(
                "earliest history window: page_start=%s page_end=%s",
                windows[-1][0],
                windows[-1][1],
            )
        fetched: list[Candle] = []
        for index in range(0, len(windows), self.settings.bitget_history_concurrency):
            batch = windows[index:index + self.settings.bitget_history_concurrency]
            pages = await asyncio.gather(*[
                self.client.get_historical_candles(symbol, timeframe, start_time=page_start, end_time=page_end - 1, limit=HISTORY_PAGE_LIMIT)
                for page_start, page_end in batch
            ])
            for (page_start, page_end), page in zip(batch, pages):
                accepted = [c for c in page if page_start <= c.timestamp < page_end]
                if not accepted:
                    logger.warning("Bitget returned an empty history page for %s %s [%s, %s)", symbol, timeframe, page_start, page_end)
                fetched.extend(accepted)
            if self.settings.bitget_rate_limit_wait_seconds:
                await asyncio.sleep(self.settings.bitget_rate_limit_wait_seconds)
        return fetched
