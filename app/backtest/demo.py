"""CLI smoke test for the local dataset loader and backtest engine."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.backtest.dataset import DatasetLoader
from app.backtest.engine import BacktestEngine
from app.backtest.models import Signal
from app.backtest.strategy import Strategy, StrategyContext
from app.models import Candle


class _DemoStrategy(Strategy):
    """Open on candle five and exit on candle ten; validation use only."""

    def on_candle(self, _candle: Candle, context: StrategyContext) -> Signal:
        if context.index == 4:
            return Signal.LONG
        if context.index == 9:
            return Signal.EXIT
        return Signal.NONE


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the minimal backtest engine on local Parquet data")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", default="15m")
    parser.add_argument("--data-root", type=Path, default=Path("data/parquet"))
    parser.add_argument("--fee-rate", type=float, default=0.0)
    parser.add_argument("--slippage-rate", type=float, default=0.0)
    args = parser.parse_args()

    dataset = DatasetLoader(args.data_root).load(args.symbol, args.timeframe)
    result = BacktestEngine(fee_rate=args.fee_rate, slippage_rate=args.slippage_rate).run(
        dataset.candles,
        _DemoStrategy(),
    )
    output = {
        "symbol": dataset.symbol,
        "timeframe": dataset.timeframe,
        "dataset": dataset.report.as_dict(),
        "stats": asdict(result.stats),
        "trades": [asdict(trade) for trade in result.trades],
        "open_position": asdict(result.open_position) if result.open_position else None,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
