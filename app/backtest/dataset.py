"""Quality-gated loading of local Parquet candle datasets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.data.quality import DataQualityError, DataQualityReport, validate_candles
from app.data.storage import load_candles, parquet_path
from app.models import Candle


class DatasetError(ValueError):
    """Base class for datasets that cannot safely enter a backtest."""


class DatasetNotFoundError(DatasetError):
    """Raised when the requested Parquet cache does not exist."""


class DatasetRangeError(DatasetError):
    """Raised when a UTC range is invalid or contains no candles."""


class IncompleteDatasetError(DatasetError):
    """Raised when data quality checks find gaps or invalid candles."""


@dataclass(frozen=True, slots=True)
class LoadedDataset:
    symbol: str
    timeframe: str
    candles: tuple[Candle, ...]
    report: DataQualityReport
    path: Path


def _utc_milliseconds(value: datetime | None, name: str) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise DatasetRangeError(f"{name} must be timezone-aware; UTC is used internally")
    return int(value.astimezone(UTC).timestamp() * 1000)


class DatasetLoader:
    """Load, filter, and validate a local candle dataset before backtesting."""

    def __init__(self, root: Path | str = Path("data/parquet")) -> None:
        self.root = Path(root)

    def load(
        self,
        symbol: str,
        timeframe: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        require_complete: bool = True,
    ) -> LoadedDataset:
        path = parquet_path(self.root, symbol, timeframe)
        if not path.exists():
            raise DatasetNotFoundError(f"dataset not found: {path}")

        raw = load_candles(path)
        if not raw:
            raise DatasetRangeError(f"dataset is empty: {path}")
        complete_candles, complete_report = self._validate(raw, timeframe, path)
        if require_complete and not complete_report.is_complete:
            raise IncompleteDatasetError(
                f"dataset is incomplete and cannot enter backtest: {complete_report.as_dict()}"
            )

        start_ms = _utc_milliseconds(start, "start")
        end_ms = _utc_milliseconds(end, "end")
        if start_ms is not None and end_ms is not None and start_ms >= end_ms:
            raise DatasetRangeError("start must be earlier than end")
        selected = [
            candle
            for candle in complete_candles
            if (start_ms is None or candle.timestamp >= start_ms)
            and (end_ms is None or candle.timestamp < end_ms)
        ]
        if not selected:
            raise DatasetRangeError(f"no candles in requested UTC range: {path}")

        selected_candles, selected_report = self._validate(selected, timeframe, path)
        if require_complete and not selected_report.is_complete:
            raise IncompleteDatasetError(
                f"selected dataset range is incomplete and cannot enter backtest: {selected_report.as_dict()}"
            )
        return LoadedDataset(
            symbol=symbol.upper(),
            timeframe=timeframe,
            candles=tuple(selected_candles),
            report=selected_report,
            path=path,
        )

    @staticmethod
    def _validate(candles: list[Candle], timeframe: str, path: Path) -> tuple[list[Candle], DataQualityReport]:
        try:
            return validate_candles(candles, timeframe)
        except DataQualityError as error:
            raise IncompleteDatasetError(f"dataset contains invalid candles: {path}: {error}") from error
