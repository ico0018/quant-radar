"""Result and execution models for the minimal backtest engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Signal(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"
    NONE = "NONE"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    side: PositionSide
    entry_time: int
    entry_price: float


@dataclass(frozen=True, slots=True)
class Trade:
    entry_time: int
    exit_time: int
    side: PositionSide
    entry_price: float
    exit_price: float
    gross_pnl: float
    fees: float
    net_pnl: float


@dataclass(frozen=True, slots=True)
class BacktestStats:
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_net_pnl: float
    average_pnl: float
    max_drawdown: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    trades: tuple[Trade, ...]
    stats: BacktestStats
    open_position: PositionSnapshot | None
