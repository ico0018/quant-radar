"""Bitget public ticker WebSocket transport and parser."""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol

import websockets

from app.exchanges.bitget import normalize_symbol
from app.models.market import Ticker

logger = logging.getLogger(__name__)


class BitgetWebSocketError(RuntimeError):
    """A Bitget WebSocket error event or failed connection."""


class BitgetPayloadError(ValueError):
    """A WebSocket message cannot be interpreted as a ticker message."""


class WebSocketConnection(Protocol):
    async def send(self, message: str) -> None: ...
    async def recv(self) -> str | bytes: ...


ConnectionFactory = Callable[[str], AbstractAsyncContextManager[WebSocketConnection]]
SleepFunction = Callable[[float], Awaitable[None]]


def parse_ticker_message(message: Mapping[str, Any]) -> list[Ticker]:
    """Convert one Bitget ticker payload to normalized models without I/O."""
    event = message.get("event")
    if event == "subscribe":
        return []
    if event == "error":
        raise BitgetWebSocketError(
            f"Bitget subscription error {message.get('code', 'UNKNOWN')}: {message.get('msg', 'unknown error')}"
        )

    arg = message.get("arg")
    if not isinstance(arg, Mapping) or arg.get("channel") != "ticker":
        return []
    data = message.get("data")
    if not isinstance(data, list):
        raise BitgetPayloadError("ticker message data must be a list")

    tickers: list[Ticker] = []
    try:
        for item in data:
            if not isinstance(item, Mapping):
                raise BitgetPayloadError("ticker data entry must be an object")
            raw_symbol = item.get("instId") or arg.get("instId")
            if not raw_symbol:
                raise BitgetPayloadError("ticker message is missing instId")
            symbol = normalize_symbol(str(raw_symbol))
            tickers.append(
                Ticker(
                    symbol=symbol,
                    last_price=item["lastPr"],
                    bid_price=item.get("bidPr"),
                    ask_price=item.get("askPr"),
                    high_24h=item.get("high24h"),
                    low_24h=item.get("low24h"),
                    volume_24h=item.get("baseVolume"),
                    quote_volume_24h=item.get("quoteVolume"),
                    timestamp_ms=item["ts"],
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, BitgetPayloadError):
            raise
        raise BitgetPayloadError("invalid ticker payload") from exc
    return tickers


class BitgetPublicWebSocket:
    """Reconnect-capable public SPOT ticker stream using Bitget text ping/pong."""

    def __init__(
        self,
        url: str,
        symbols: list[str],
        *,
        reconnect_max_seconds: float = 30.0,
        heartbeat_interval_seconds: float = 30.0,
        heartbeat_timeout_seconds: float = 10.0,
        connect: ConnectionFactory | None = None,
        sleep: SleepFunction = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = url
        self._symbols = [normalize_symbol(symbol) for symbol in symbols]
        self._reconnect_max_seconds = reconnect_max_seconds
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self._connect: ConnectionFactory = connect or websockets.connect
        self._sleep = sleep
        self._clock = clock

    @property
    def subscription_message(self) -> dict[str, Any]:
        return {
            "op": "subscribe",
            "args": [
                {"instType": "SPOT", "channel": "ticker", "instId": symbol}
                for symbol in self._symbols
            ],
        }

    async def stream_tickers(self) -> AsyncIterator[Ticker]:
        backoff = 1.0
        while True:
            try:
                async with self._connect(self._url) as websocket:
                    logger.info("bitget websocket connected")
                    await websocket.send(json.dumps(self.subscription_message))
                    async for ticker in self._stream_connection(websocket):
                        backoff = 1.0
                        yield ticker
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("bitget websocket disconnected: %s", exc)
                logger.info("bitget websocket reconnecting in %.1fs", backoff)
                await self._sleep(backoff)
                backoff = min(backoff * 2, self._reconnect_max_seconds)

    async def _stream_connection(self, websocket: WebSocketConnection) -> AsyncIterator[Ticker]:
        last_ping_at = self._clock()
        pong_deadline: float | None = None
        while True:
            now = self._clock()
            deadline = pong_deadline if pong_deadline is not None else last_ping_at + self._heartbeat_interval_seconds
            timeout = max(0.0, deadline - now)
            try:
                raw_message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            except TimeoutError:
                if pong_deadline is not None:
                    raise BitgetWebSocketError("Bitget application heartbeat timed out")
                await websocket.send("ping")
                last_ping_at = self._clock()
                pong_deadline = last_ping_at + self._heartbeat_timeout_seconds
                continue

            if isinstance(raw_message, bytes):
                raw_message = raw_message.decode("utf-8")
            if raw_message == "pong":
                pong_deadline = None
                continue
            try:
                parsed = json.loads(raw_message)
                if not isinstance(parsed, Mapping):
                    raise BitgetPayloadError("websocket payload must be an object")
                tickers = parse_ticker_message(parsed)
            except BitgetWebSocketError:
                logger.error("bitget websocket error event received")
                raise
            except (json.JSONDecodeError, BitgetPayloadError) as exc:
                logger.warning("invalid websocket payload: %s", exc)
                continue

            if not tickers and parsed.get("event") not in {"subscribe", None}:
                logger.debug("ignored websocket event: %s", parsed.get("event"))
            elif not tickers:
                arg = parsed.get("arg")
                if isinstance(arg, Mapping) and arg.get("channel") != "ticker":
                    logger.debug("ignored websocket channel: %s", arg.get("channel"))
                elif not isinstance(arg, Mapping):
                    logger.debug("ignored unknown websocket message")
            for ticker in tickers:
                yield ticker
