"""Minimal, local-data backtesting primitives."""

from app.backtest.dataset import DatasetLoader, IncompleteDatasetError, LoadedDataset
from app.backtest.engine import BacktestEngine, BacktestError, calculate_stats
from app.backtest.models import BacktestResult, BacktestStats, PositionSide, Signal, Trade
from app.backtest.strategy import Strategy, StrategyContext

__all__ = [
    "BacktestEngine",
    "BacktestError",
    "BacktestResult",
    "BacktestStats",
    "DatasetLoader",
    "IncompleteDatasetError",
    "LoadedDataset",
    "PositionSide",
    "Signal",
    "Strategy",
    "StrategyContext",
    "Trade",
    "calculate_stats",
]
