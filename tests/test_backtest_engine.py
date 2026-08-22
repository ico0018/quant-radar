import pytest

from app.backtest.engine import BacktestEngine, BacktestError, calculate_stats
from app.backtest.models import PositionSide, Signal, Trade
from app.backtest.strategy import Strategy, StrategyContext
from app.models import Candle


def candle(index: int, open_price: float) -> Candle:
    timestamp = index * 900_000
    return Candle(timestamp, open_price, open_price + 1, open_price - 1, open_price, 1.0, open_price)


class IndexedSignalStrategy(Strategy):
    """Test fixture that emits prearranged signals by zero-based candle index."""

    def __init__(self, signals: dict[int, Signal]) -> None:
        self.signals = signals
        self.observed: list[tuple[int, tuple[int, ...]]] = []

    def on_candle(self, current: Candle, context: StrategyContext) -> Signal:
        history = tuple(item.timestamp for item in context.history)
        self.observed.append((current.timestamp, history))
        return self.signals.get(context.index, Signal.NONE)


def run_trade(side: Signal, entry_open: float, exit_open: float, **costs: float):
    candles = [candle(0, 90), candle(1, entry_open), candle(2, exit_open)]
    strategy = IndexedSignalStrategy({0: side, 1: Signal.EXIT})
    return BacktestEngine(**costs).run(candles, strategy).trades[0]


def test_signal_executes_at_next_bar_open_without_future_history() -> None:
    candles = [candle(index, 100 + index * 10) for index in range(5)]
    strategy = IndexedSignalStrategy({1: Signal.LONG, 3: Signal.EXIT})
    result = BacktestEngine().run(candles, strategy)
    trade = result.trades[0]
    assert trade.entry_time == candles[2].timestamp
    assert trade.entry_price == candles[2].open
    assert trade.exit_time == candles[4].timestamp
    assert trade.exit_price == candles[4].open
    for index, (current_timestamp, history) in enumerate(strategy.observed):
        assert current_timestamp == candles[index].timestamp
        assert history == tuple(item.timestamp for item in candles[: index + 1])


def test_engine_processes_candles_in_strict_order() -> None:
    candles = [candle(index, 100) for index in range(3)]
    strategy = IndexedSignalStrategy({})
    BacktestEngine().run(candles, strategy)
    assert [timestamp for timestamp, _ in strategy.observed] == [0, 900_000, 1_800_000]
    with pytest.raises(BacktestError, match="strictly ordered"):
        BacktestEngine().run([candles[1], candles[0]], IndexedSignalStrategy({}))


def test_long_pnl() -> None:
    trade = run_trade(Signal.LONG, 100, 110)
    assert trade.side is PositionSide.LONG
    assert trade.gross_pnl == pytest.approx(10)
    assert trade.net_pnl == pytest.approx(10)


def test_short_pnl() -> None:
    trade = run_trade(Signal.SHORT, 110, 100)
    assert trade.side is PositionSide.SHORT
    assert trade.gross_pnl == pytest.approx(10)
    assert trade.net_pnl == pytest.approx(10)


def test_fee_and_slippage_are_applied_to_both_fills() -> None:
    trade = run_trade(Signal.LONG, 100, 110, fee_rate=0.001, slippage_rate=0.01)
    assert trade.entry_price == pytest.approx(101)
    assert trade.exit_price == pytest.approx(108.9)
    assert trade.gross_pnl == pytest.approx(7.9)
    assert trade.fees == pytest.approx((101 + 108.9) * 0.001)
    assert trade.net_pnl == pytest.approx(7.9 - (101 + 108.9) * 0.001)


def trade_with_net_pnl(net_pnl: float) -> Trade:
    return Trade(0, 1, PositionSide.LONG, 0, 0, net_pnl, 0, net_pnl)


def test_max_drawdown_uses_realized_net_pnl_curve() -> None:
    stats = calculate_stats([trade_with_net_pnl(value) for value in (10, -4, -8, 6)])
    assert stats.total_trades == 4
    assert stats.wins == 2
    assert stats.losses == 2
    assert stats.win_rate == pytest.approx(0.5)
    assert stats.total_net_pnl == pytest.approx(4)
    assert stats.average_pnl == pytest.approx(1)
    assert stats.max_drawdown == pytest.approx(12)
