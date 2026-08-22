import asyncio
from decimal import Decimal

import httpx
import pytest

from app.exchanges.bitget import BitgetAPIError, BitgetPublicClient, normalize_symbol


def make_client(handler) -> BitgetPublicClient:
    return BitgetPublicClient("https://api.bitget.com", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def test_get_ticker_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/spot/market/tickers"
        assert request.url.params["symbol"] == "BTCUSDT"
        return httpx.Response(200, json={"code": "00000", "msg": "success", "data": [{"lastPr": "65000.12", "bidPr": "65000.11", "askPr": "65000.13", "high24h": "66000", "low24h": "64000", "baseVolume": "10.5", "quoteVolume": "682501", "ts": "1720000000000"}]})

    async def run():
        client = make_client(handler)
        try:
            return await client.get_ticker("btc-usdt")
        finally:
            await client.aclose()

    ticker = asyncio.run(run())
    assert ticker.symbol == "BTCUSDT"
    assert ticker.last_price == Decimal("65000.12")
    assert ticker.timestamp_ms == 1720000000000


def test_get_candles_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["granularity"] == "5min"
        return httpx.Response(200, json={"code": "00000", "msg": "success", "data": [["1720000000000", "1", "2", "0.5", "1.5", "10", "15"]]})

    async def run():
        client = make_client(handler)
        try:
            return await client.get_candles("BTC/USDT", "5m", 1)
        finally:
            await client.aclose()

    candles = asyncio.run(run())
    assert candles[0].close == Decimal("1.5")
    assert candles[0].quote_volume == Decimal("15")


def test_bitget_error_code_raises() -> None:
    async def run() -> None:
        client = make_client(lambda request: httpx.Response(200, json={"code": "40001", "msg": "bad symbol", "data": []}))
        try:
            with pytest.raises(BitgetAPIError, match="40001"):
                await client.get_ticker("BTCUSDT")
        finally:
            await client.aclose()

    asyncio.run(run())


def test_http_failure_raises() -> None:
    async def run() -> BitgetAPIError:
        client = make_client(lambda request: httpx.Response(500, text="upstream unavailable"))
        try:
            with pytest.raises(BitgetAPIError) as error:
                await client.get_ticker("BTCUSDT")
            return error.value
        finally:
            await client.aclose()

    assert asyncio.run(run()).code == "500"


def test_symbol_normalization() -> None:
    assert normalize_symbol("btcusdt") == "BTCUSDT"
    assert normalize_symbol("BTC-USDT") == "BTCUSDT"
    assert normalize_symbol("BTC/USDT") == "BTCUSDT"


def test_unsupported_interval_raises() -> None:
    async def run() -> None:
        client = make_client(lambda request: httpx.Response(200))
        try:
            with pytest.raises(ValueError, match="unsupported interval"):
                await client.get_candles("BTCUSDT", "2h")
        finally:
            await client.aclose()

    asyncio.run(run())


def test_context_manager_does_not_close_injected_http_client() -> None:
    async def run() -> None:
        external_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
        async with BitgetPublicClient("https://api.bitget.com", client=external_client):
            pass
        assert not external_client.is_closed
        await external_client.aclose()

    asyncio.run(run())
