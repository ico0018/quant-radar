"""Application entry point for the market-monitoring heartbeat."""

import asyncio
import logging

import httpx

from app.config import get_settings
from app.exchanges.bitget import BitgetAPIError, BitgetPublicClient
from app.services.market_data import MarketDataService


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger("quant-radar")
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as http_client:
        market_data = MarketDataService(BitgetPublicClient(settings.bitget_rest_url, http_client))
        logger.info("quant-radar started")
        while True:
            try:
                ticker = await market_data.get_snapshot("BTCUSDT")
                logger.info("BTCUSDT last=%s bid=%s ask=%s", ticker.last_price, ticker.bid_price, ticker.ask_price)
            except asyncio.CancelledError:
                logger.info("quant-radar stopping")
                raise
            except (BitgetAPIError, httpx.HTTPError) as exc:
                logger.error("market data request failed: %s", exc)
            except Exception:
                logger.exception("unexpected market data error")
            await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger("quant-radar").info("quant-radar stopped")
