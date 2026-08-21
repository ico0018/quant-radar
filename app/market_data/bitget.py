"""Small async client for Bitget's public futures-market REST endpoints."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from app.config import (
    BITGET_CANDLES_PATH,
    BITGET_CONTRACTS_PATH,
    SUPPORTED_GRANULARITIES,
    Settings,
)
from app.models import Candle, FuturesContract


class BitgetMarketDataError(RuntimeError):
    """Base class for expected Bitget market-data failures."""


class BitgetTimeoutError(BitgetMarketDataError):
    """Raised when Bitget does not respond before the configured timeout."""


class BitgetHttpError(BitgetMarketDataError):
    """Raised for transport or non-successful HTTP responses."""


class BitgetApiError(BitgetMarketDataError):
    """Raised when Bitget returns a non-success response payload."""


class BitgetInvalidResponseError(BitgetMarketDataError):
    """Raised when a response cannot be parsed into our internal models."""


class BitgetEmptyDataError(BitgetMarketDataError):
    """Raised when Bitget successfully returns no usable market data."""


class BitgetRestClient:
    """Client for unauthenticated Bitget USDT-futures market data.

    Pass an ``httpx.AsyncClient`` when testing to provide a mock transport.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=self.settings.bitget_rest_url.rstrip("/"),
            timeout=self.settings.bitget_request_timeout_seconds,
        )

    async def __aenter__(self) -> "BitgetRestClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_usdt_futures_contracts(self) -> list[FuturesContract]:
        """Return every contract exposed for the configured USDT futures product."""
        data = await self._get_data(
            BITGET_CONTRACTS_PATH,
            {"productType": self.settings.bitget_usdt_futures_product_type},
        )
        if not isinstance(data, list):
            raise BitgetInvalidResponseError("contracts response data must be a list")
        if not data:
            raise BitgetEmptyDataError("Bitget returned no USDT futures contracts")

        contracts: list[FuturesContract] = []
        for item in data:
            if not isinstance(item, dict):
                raise BitgetInvalidResponseError("contract item must be an object")
            try:
                contracts.append(
                    FuturesContract(
                        symbol=str(item["symbol"]),
                        base_coin=str(item["baseCoin"]),
                        quote_coin=str(item["quoteCoin"]),
                        # The endpoint is already scoped by productType but does
                        # not repeat that field in individual contract objects.
                        product_type=self.settings.bitget_usdt_futures_product_type,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise BitgetInvalidResponseError("contract item has missing fields") from exc
        return contracts

    async def get_candles(
        self,
        symbol: str,
        granularity: str,
        *,
        limit: int = 200,
    ) -> list[Candle]:
        """Return historical OHLCV candles for one USDT perpetual symbol."""
        if granularity not in SUPPORTED_GRANULARITIES:
            supported = ", ".join(sorted(SUPPORTED_GRANULARITIES))
            raise ValueError(f"unsupported granularity {granularity!r}; choose one of {supported}")
        if not symbol:
            raise ValueError("symbol must not be empty")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")

        data = await self._get_data(
            BITGET_CANDLES_PATH,
            {
                "symbol": symbol.upper(),
                "productType": self.settings.bitget_usdt_futures_product_type,
                "granularity": granularity,
                "limit": limit,
            },
        )
        if not isinstance(data, list):
            raise BitgetInvalidResponseError("candles response data must be a list")
        if not data:
            raise BitgetEmptyDataError(f"Bitget returned no candles for {symbol}")

        candles = [self._parse_candle(row) for row in data]
        return sorted(candles, key=lambda candle: candle.timestamp)

    async def _get_data(self, path: str, params: dict[str, Any]) -> Any:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise BitgetTimeoutError(f"Bitget request timed out: {path}") from exc
        except httpx.HTTPStatusError as exc:
            raise BitgetHttpError(
                f"Bitget returned HTTP {exc.response.status_code}: {path}"
            ) from exc
        except httpx.HTTPError as exc:
            raise BitgetHttpError(f"Bitget request failed: {path}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BitgetInvalidResponseError("Bitget returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise BitgetInvalidResponseError("Bitget response must be a JSON object")
        if payload.get("code") != "00000":
            message = payload.get("msg", "unknown Bitget API error")
            raise BitgetApiError(f"Bitget API error: {message}")
        if "data" not in payload:
            raise BitgetInvalidResponseError("Bitget response has no data field")
        return payload["data"]

    @staticmethod
    def _parse_candle(row: Any) -> Candle:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or len(row) < 6:
            raise BitgetInvalidResponseError("candle row must contain six values")
        try:
            return Candle(
                timestamp=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
        except (TypeError, ValueError, IndexError) as exc:
            raise BitgetInvalidResponseError("candle row contains invalid values") from exc
