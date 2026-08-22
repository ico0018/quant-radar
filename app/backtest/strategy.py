"""Strategy contract without any production trading strategy."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from app.backtest.models import PositionSnapshot, Signal
from app.models import Candle


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Read-only state visible while evaluating the current candle."""

    index: int
    history: Sequence[Candle]
    position: PositionSnapshot | None


class Strategy(ABC):
    """A strategy emits a signal after observing the current completed candle."""

    @abstractmethod
    def on_candle(self, candle: Candle, context: StrategyContext) -> Signal:
        """Return the action to execute at the next candle's open."""
