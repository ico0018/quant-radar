"""Single-file Parquet cache helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pandas as pd

from app.models import Candle


def parquet_path(root: Path, symbol: str, timeframe: str) -> Path:
    return root / symbol.upper() / timeframe / "candles.parquet"


def load_candles(path: Path) -> list[Candle]:
    if not path.exists():
        return []
    frame = pd.read_parquet(path)
    required = {"timestamp", "open", "high", "low", "close", "base_volume", "quote_volume"}
    if not required <= set(frame.columns):
        raise ValueError(f"Parquet cache has missing columns: {path}")
    return [Candle(**row) for row in frame[list(required)].to_dict("records")]


def write_candles(path: Path, candles: Sequence[Candle]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [{"timestamp": c.timestamp, "open": c.open, "high": c.high, "low": c.low, "close": c.close, "base_volume": c.base_volume, "quote_volume": c.quote_volume} for c in candles]
    )
    temporary = path.with_suffix(".parquet.tmp")
    frame.to_parquet(temporary, engine="pyarrow", index=False)
    temporary.replace(path)
