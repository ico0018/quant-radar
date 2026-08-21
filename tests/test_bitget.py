import asyncio

import httpx
import pytest

from app.config import Settings
from app.market_data.bitget import (
    BitgetApiError,
    BitgetEmptyDataError,
    BitgetHttpError,
    BitgetInvalidResponseError,
    BitgetRestClient,
    BitgetTimeoutError,
)


def make_client(handler: httpx.MockTransport) -> BitgetRestClient:
    return BitgetRestClient(
        Settings(_env_file=None, bitget_rest_url="https://bitget.test"),
        httpx.AsyncClient(base_url="https://bitget.test", transport=handler),
    )


def test_get_usdt_futures_contracts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/mix/market/contracts"
        assert request.url.params["productType"] == "USDT-FUTURES"
        return httpx.Response(
            200,
            json={
                "code": "00000",
                "data": [
                    {
                        "symbol": "BTCUSDT",
                        "baseCoin": "BTC",
                        "quoteCoin": "USDT",
                    }
                ],
            },
        )

    client = make_client(httpx.MockTransport(handler))
    contracts = asyncio.run(client.get_usdt_futures_contracts())
    assert contracts[0].symbol == "BTCUSDT"
    assert contracts[0].base_coin == "BTC"
    assert contracts[0].product_type == "USDT-FUTURES"


def test_get_candles_normalizes_and_sorts_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["symbol"] == "BTCUSDT"
        assert request.url.params["granularity"] == "1H"
        return httpx.Response(
            200,
            json={
                "code": "00000",
                "data": [
                    ["2000", "101", "103", "100", "102", "12.5"],
                    ["1000", "99", "102", "98", "101", "10"],
                ],
            },
        )

    candles = asyncio.run(make_client(httpx.MockTransport(handler)).get_candles("btcusdt", "1H"))
    assert [candle.timestamp for candle in candles] == [1000, 2000]
    assert candles[0].close == 101.0
    assert candles[1].volume == 12.5


@pytest.mark.parametrize("payload,error", [
    ({"code": "00000", "data": []}, BitgetEmptyDataError),
    ({"code": "00000", "data": [["bad", "1", "2", "0", "1", "4"]]}, BitgetInvalidResponseError),
    ({"code": "40001", "msg": "bad request"}, BitgetApiError),
])
def test_get_candles_rejects_bad_api_payloads(payload: dict, error: type[Exception]) -> None:
    client = make_client(httpx.MockTransport(lambda _: httpx.Response(200, json=payload)))
    with pytest.raises(error):
        asyncio.run(client.get_candles("BTCUSDT", "1m"))


def test_get_candles_maps_http_error() -> None:
    client = make_client(httpx.MockTransport(lambda _: httpx.Response(503, text="unavailable")))
    with pytest.raises(BitgetHttpError):
        asyncio.run(client.get_candles("BTCUSDT", "1m"))


def test_get_candles_maps_timeout() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(BitgetTimeoutError):
        asyncio.run(client.get_candles("BTCUSDT", "1m"))


def test_get_candles_rejects_unsupported_granularity() -> None:
    client = make_client(httpx.MockTransport(lambda _: httpx.Response(200)))
    with pytest.raises(ValueError, match="unsupported granularity"):
        asyncio.run(client.get_candles("BTCUSDT", "1D"))
