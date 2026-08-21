import asyncio
import argparse
import logging

from app.indicators import calculate_trend_indicators
from app.market_data import BitgetRestClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quant-radar")


async def main() -> None:
    logger.info("Quant Radar starting...")
    while True:
        await asyncio.sleep(60)


async def market_data_demo() -> None:
    """Fetch BTCUSDT candles and print the latest supported indicators."""
    async with BitgetRestClient() as client:
        candles = await client.get_candles("BTCUSDT", "1H", limit=150)
    indicators = calculate_trend_indicators(candles)
    latest = indicators.iloc[-1]
    logger.info(
        "BTCUSDT: %s 1H candles; latest close=%s MA20=%s EMA20=%s",
        len(candles),
        latest["close"],
        latest["ma_20"],
        latest["ema_20"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quant Radar")
    parser.add_argument(
        "--demo", action="store_true", help="run the BTCUSDT market-data demo and exit"
    )
    args = parser.parse_args()
    asyncio.run(market_data_demo() if args.demo else main())
