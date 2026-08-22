import asyncio
import json
from contextlib import asynccontextmanager

import pytest

from app.exchanges.bitget_ws import BitgetPublicWebSocket, BitgetWebSocketError


def ticker_payload() -> str:
    return json.dumps({"arg": {"instType": "SPOT", "channel": "ticker", "instId": "BTCUSDT"}, "data": [{"instId": "BTCUSDT", "lastPr": "1.25", "bidPr": "1.2", "askPr": "1.3", "high24h": "2", "low24h": "1", "baseVolume": "3", "quoteVolume": "4", "ts": "1"}]})


class FakeConnection:
    def __init__(self, messages: list[object]) -> None:
        self.messages = messages
        self.sent: list[str] = []

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str | bytes:
        if not self.messages:
            raise ConnectionError("connection ended")
        message = self.messages.pop(0)
        if isinstance(message, BaseException):
            raise message
        return message  # type: ignore[return-value]


class FakeConnector:
    def __init__(self, connections: list[FakeConnection]) -> None:
        self.connections = connections
        self.urls: list[str] = []

    @asynccontextmanager
    async def __call__(self, url: str):
        self.urls.append(url)
        yield self.connections.pop(0)


def test_subscription_and_ticker_stream() -> None:
    connection = FakeConnection([json.dumps({"event": "subscribe"}), ticker_payload()])
    connector = FakeConnector([connection])
    websocket = BitgetPublicWebSocket("wss://example.test", ["btc-usdt", "ETH/USDT"], connect=connector)

    async def run():
        stream = websocket.stream_tickers()
        try:
            return await anext(stream)
        finally:
            await stream.aclose()

    ticker = asyncio.run(run())
    subscription = json.loads(connection.sent[0])
    assert ticker.symbol == "BTCUSDT"
    assert subscription == {"op": "subscribe", "args": [{"instType": "SPOT", "channel": "ticker", "instId": "BTCUSDT"}, {"instType": "SPOT", "channel": "ticker", "instId": "ETHUSDT"}]}


def test_reconnects_after_connection_drop() -> None:
    first = FakeConnection([ConnectionError("dropped")])
    second = FakeConnection([ticker_payload()])
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    websocket = BitgetPublicWebSocket("wss://example.test", ["BTCUSDT"], connect=FakeConnector([first, second]), sleep=fake_sleep)

    async def run():
        stream = websocket.stream_tickers()
        try:
            return await anext(stream)
        finally:
            await stream.aclose()

    assert asyncio.run(run()).last_price == 1.25
    assert waits == [1.0]


def test_cancelled_error_is_not_swallowed() -> None:
    websocket = BitgetPublicWebSocket("wss://example.test", ["BTCUSDT"], connect=FakeConnector([FakeConnection([asyncio.CancelledError()])]))

    async def run() -> None:
        with pytest.raises(asyncio.CancelledError):
            await anext(websocket.stream_tickers())

    asyncio.run(run())


def test_application_heartbeat_timeout_fails_connection() -> None:
    connection = FakeConnection([])
    websocket = BitgetPublicWebSocket("wss://example.test", ["BTCUSDT"], heartbeat_interval_seconds=0, heartbeat_timeout_seconds=0)

    async def run() -> None:
        stream = websocket._stream_connection(connection)
        with pytest.raises(BitgetWebSocketError, match="heartbeat timed out"):
            await anext(stream)

    asyncio.run(run())
    assert connection.sent == ["ping"]
