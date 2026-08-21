"""CLI entry point for the Phase 2A historical-data cache."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from app.data.downloader import HistoricalDataDownloader
from app.market_data import BitgetRestClient


async def run(symbol: str, timeframe: str, days: int) -> None:
    async with BitgetRestClient() as client:
        result = await HistoricalDataDownloader(client).download(symbol, timeframe, days)
    print(json.dumps({"path": str(result.path), "added_candles": result.added_candles, **result.report.as_dict()}, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="Download Bitget historical candles to Parquet")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", required=True, choices=("15m", "1H"))
    parser.add_argument("--days", required=True, type=int)
    arguments = parser.parse_args()
    asyncio.run(run(arguments.symbol, arguments.timeframe, arguments.days))
