"""Bitget public spot-market REST client."""

from collections.abc import Mapping
from typing import Any

import httpx

from app.models.market import Candle, Ticker

SPOT_TICKERS_PATH = "/api/v2/spot/market/tickers"
SPOT_CANDLES_PATH = "/api/v2/spot/market/candles"
INTERVAL_GRANULARITIES = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1day"}


class BitgetAPIError(RuntimeError):
    def __init__(self, code: str | int, message: str) -> None:
        self.code = str(code)
        self.message = message
        super().__init__(f"Bitget API error {self.code}: {self.message}")


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.upper().replace("-", "").replace("/", "").strip()
    if not normalized or not normalized.isalnum():
        raise ValueError("symbol must contain a base and quote currency")
    return normalized


class BitgetPublicClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(10.0))
        self._owns_client = client is None
        self._base_url = base_url.rstrip("/")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "BitgetPublicClient":
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.aclose()

    async def get_ticker(self, symbol: str) -> Ticker:
        normalized_symbol = normalize_symbol(symbol)
        payload = await self._get(SPOT_TICKERS_PATH, {"symbol": normalized_symbol})
        data = payload["data"]
        ticker_data = data[0] if isinstance(data, list) and data else data
        if not isinstance(ticker_data, Mapping):
            raise BitgetAPIError("INVALID_RESPONSE", "ticker data has an invalid format")
        return Ticker(symbol=normalized_symbol, last_price=ticker_data["lastPr"], bid_price=ticker_data.get("bidPr"), ask_price=ticker_data.get("askPr"), high_24h=ticker_data.get("high24h"), low_24h=ticker_data.get("low24h"), volume_24h=ticker_data.get("baseVolume"), quote_volume_24h=ticker_data.get("quoteVolume"), timestamp_ms=ticker_data.get("ts", payload.get("requestTime", 0)))

    async def get_candles(self, symbol: str, interval: str, limit: int = 100) -> list[Candle]:
        if interval not in INTERVAL_GRANULARITIES:
            raise ValueError(f"unsupported interval: {interval}")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        normalized_symbol = normalize_symbol(symbol)
        payload = await self._get(SPOT_CANDLES_PATH, {"symbol": normalized_symbol, "granularity": INTERVAL_GRANULARITIES[interval], "limit": str(limit)})
        data = payload["data"]
        if not isinstance(data, list):
            raise BitgetAPIError("INVALID_RESPONSE", "candle data has an invalid format")
        try:
            return [Candle(symbol=normalized_symbol, interval=interval, timestamp_ms=row[0], open=row[1], high=row[2], low=row[3], close=row[4], base_volume=row[5], quote_volume=row[6] if len(row) > 6 else None) for row in data]
        except (IndexError, TypeError, ValueError) as exc:
            raise BitgetAPIError("INVALID_RESPONSE", "candle data has an invalid format") from exc

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        response = await self._client.get(f"{self._base_url}{path}", params=params)
        if response.is_error:
            raise BitgetAPIError(response.status_code, "HTTP request failed")
        try:
            payload = response.json()
        except ValueError as exc:
            raise BitgetAPIError("INVALID_RESPONSE", "response is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise BitgetAPIError("INVALID_RESPONSE", "response has an invalid format")
        if payload.get("code") != "00000":
            raise BitgetAPIError(payload.get("code", "UNKNOWN"), str(payload.get("msg", "unknown error")))
        if "data" not in payload:
            raise BitgetAPIError("INVALID_RESPONSE", "response does not contain data")
        return payload
