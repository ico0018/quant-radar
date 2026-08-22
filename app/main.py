"""Application entry point for the market-monitoring heartbeat."""

import asyncio
import logging

import httpx
import redis.asyncio as redis

from app.cache.market_cache import MarketCache
from app.config import get_settings
from app.exchanges.bitget import BitgetAPIError, BitgetPublicClient
from app.exchanges.bitget_ws import BitgetPublicWebSocket
from app.services.market_data import MarketDataService


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger("quant-radar")
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as http_client:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
        market_cache = MarketCache(redis_client, settings.market_cache_ttl_seconds) if redis_client else None
        market_data = MarketDataService(BitgetPublicClient(settings.bitget_rest_url, http_client), market_cache)
        logger.info("quant-radar started")
        for symbol in settings.market_symbols:
            try:
                ticker = await market_data.get_snapshot(symbol)
                await market_data.handle_ticker(ticker)
                logger.info("initial %s last=%s", ticker.symbol, ticker.last_price)
            except (BitgetAPIError, httpx.HTTPError) as exc:
                logger.error("initial market data request failed for %s: %s", symbol, exc)
            except Exception:
                logger.exception("unexpected initial market data error for %s", symbol)

        websocket = BitgetPublicWebSocket(
            settings.bitget_ws_url,
            settings.market_symbols,
            reconnect_max_seconds=settings.ws_reconnect_max_seconds,
        )
        latest_prices: dict[str, str] = {}
        last_summary_at = asyncio.get_running_loop().time()
        try:
            async for ticker in websocket.stream_tickers():
                await market_data.handle_ticker(ticker)
                latest_prices[ticker.symbol] = str(ticker.last_price)
                logger.debug("ticker %s last=%s", ticker.symbol, ticker.last_price)
                now = asyncio.get_running_loop().time()
                if now - last_summary_at >= 60:
                    logger.info("market feed healthy %s", latest_prices)
                    last_summary_at = now
        except asyncio.CancelledError:
            logger.info("quant-radar stopping")
            raise
        finally:
            if redis_client is not None:
                await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger("quant-radar").info("quant-radar stopped")
