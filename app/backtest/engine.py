"""Single-position, next-bar-open backtest execution engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, overload

from app.backtest.models import (
    BacktestResult,
    BacktestStats,
    PositionSide,
    PositionSnapshot,
    Signal,
    Trade,
)
from app.backtest.strategy import Strategy, StrategyContext
from app.models import Candle


class BacktestError(ValueError):
    """Raised when engine input or strategy output is invalid."""


class _HistoryView(Sequence[Candle]):
    """An immutable-length view that cannot expose candles after the current bar."""

    def __init__(self, candles: list[Candle], end: int) -> None:
        self._candles = candles
        self._end = end

    def __len__(self) -> int:
        return self._end

    @overload
    def __getitem__(self, index: int) -> Candle: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[Candle, ...]: ...

    def __getitem__(self, index: int | slice) -> Candle | tuple[Candle, ...]:
        if isinstance(index, slice):
            start, stop, step = index.indices(self._end)
            return tuple(self._candles[position] for position in range(start, stop, step))
        normalized = index + self._end if index < 0 else index
        if normalized < 0 or normalized >= self._end:
            raise IndexError("candle history index out of range")
        return self._candles[normalized]


@dataclass(slots=True)
class _OpenPosition:
    side: PositionSide
    entry_time: int
    entry_price: float
    entry_fee: float

    def snapshot(self) -> PositionSnapshot:
        return PositionSnapshot(self.side, self.entry_time, self.entry_price)


def calculate_stats(trades: Sequence[Trade]) -> BacktestStats:
    """Calculate statistics from closed trades using realized net PnL."""
    total = len(trades)
    wins = sum(trade.net_pnl > 0 for trade in trades)
    losses = sum(trade.net_pnl < 0 for trade in trades)
    total_net_pnl = sum(trade.net_pnl for trade in trades)
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for trade in trades:
        equity += trade.net_pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return BacktestStats(
        total_trades=total,
        wins=wins,
        losses=losses,
        win_rate=wins / total if total else 0.0,
        total_net_pnl=total_net_pnl,
        average_pnl=total_net_pnl / total if total else 0.0,
        max_drawdown=max_drawdown,
    )


class BacktestEngine:
    """Execute one unit of a single long or short position at a time."""

    def __init__(self, *, fee_rate: float = 0.0, slippage_rate: float = 0.0) -> None:
        if fee_rate < 0:
            raise ValueError("fee_rate must be non-negative")
        if not 0 <= slippage_rate < 1:
            raise ValueError("slippage_rate must be between 0 and 1")
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate

    def run(self, candles: Sequence[Candle], strategy: Strategy) -> BacktestResult:
        ordered = list(candles)
        if not ordered:
            raise BacktestError("at least one candle is required")
        if any(current.timestamp >= following.timestamp for current, following in zip(ordered, ordered[1:])):
            raise BacktestError("candles must be unique and strictly ordered by timestamp")

        visible_history: list[Candle] = []
        trades: list[Trade] = []
        position: _OpenPosition | None = None
        pending_signal = Signal.NONE

        for index, candle in enumerate(ordered):
            position = self._execute(pending_signal, candle, position, trades)
            visible_history.append(candle)
            context = StrategyContext(
                index=index,
                history=_HistoryView(visible_history, len(visible_history)),
                position=position.snapshot() if position else None,
            )
            signal = strategy.on_candle(candle, context)
            if not isinstance(signal, Signal):
                raise BacktestError(f"strategy returned invalid signal at index {index}: {signal!r}")
            pending_signal = signal

        return BacktestResult(
            trades=tuple(trades),
            stats=calculate_stats(trades),
            open_position=position.snapshot() if position else None,
        )

    def _execute(
        self,
        signal: Signal,
        candle: Candle,
        position: _OpenPosition | None,
        trades: list[Trade],
    ) -> _OpenPosition | None:
        if signal is Signal.NONE:
            return position
        if signal is Signal.EXIT:
            if position is not None:
                trades.append(self._close(position, candle))
            return None

        target_side = PositionSide(signal.value)
        if position is not None and position.side is target_side:
            return position
        if position is not None:
            trades.append(self._close(position, candle))
        return self._open(target_side, candle)

    def _open(self, side: PositionSide, candle: Candle) -> _OpenPosition:
        buying = side is PositionSide.LONG
        price = self._execution_price(candle.open, buying=buying)
        return _OpenPosition(side, candle.timestamp, price, price * self.fee_rate)

    def _close(self, position: _OpenPosition, candle: Candle) -> Trade:
        buying = position.side is PositionSide.SHORT
        exit_price = self._execution_price(candle.open, buying=buying)
        gross_pnl = (
            exit_price - position.entry_price
            if position.side is PositionSide.LONG
            else position.entry_price - exit_price
        )
        fees = position.entry_fee + exit_price * self.fee_rate
        return Trade(
            entry_time=position.entry_time,
            exit_time=candle.timestamp,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            gross_pnl=gross_pnl,
            fees=fees,
            net_pnl=gross_pnl - fees,
        )

    def _execution_price(self, open_price: float, *, buying: bool) -> float:
        multiplier = 1 + self.slippage_rate if buying else 1 - self.slippage_rate
        return open_price * multiplier
