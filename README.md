# quant-radar

A rule-driven crypto market radar for Bitget. Phase 1 provides a reliable, public REST market-data foundation; it does not place trades or send notifications.

## Phase 1

- Public Bitget REST client for USDT perpetual contracts and historical candles
- Supported candle intervals: `1m`, `5m`, `15m`, `1H`, `4H`
- Internal OHLCV candle model: timestamp, open, high, low, close, base_volume, quote_volume
- MA and EMA trend indicators for 20, 60, and 120 periods
- Explicit timeout, HTTP, API-payload, invalid-response, and empty-data errors

## Architecture

```text
Bitget public REST
        |
        v
Market Data -> Internal Candle Models -> Indicators
```

## Development workflow

```text
Local Codex CLI -> GitHub -> GitHub Actions -> Cloud VPS / Docker Compose
```

## Run the market-data demo

The demo makes one public Bitget request for 150 BTCUSDT 1-hour candles and prints the latest close, MA20, and EMA20.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main --demo
```

Configuration defaults are in `app/config.py`; environment overrides are documented in `.env.example`. No Bitget API key is required for Phase 1.

## Tests

```bash
pytest -q
```

## Historical Data

Phase 2A downloads BTCUSDT historical USDT-perpetual candles through Bitget's historical API and caches them in UTC Parquet files. A single Parquet file per timeframe keeps the first version simple and makes incremental updates easy: existing timestamps are read, all missing start, middle, and tail ranges are requested, then the sorted/deduplicated cache is atomically replaced.

```bash
python -m app.data.download --symbol BTCUSDT --timeframe 15m --days 730
python -m app.data.download --symbol BTCUSDT --timeframe 1H --days 730
```

Files are stored at `data/parquet/BTCUSDT/<timeframe>/candles.parquet`. Each run prints a UTC data-quality report with candle count, time range, duplicates removed, missing periods, and invalid OHLC count. Re-running the command only requests currently missing or newly completed candle intervals.

The downloader compensates for Bitget's history endpoint boundary semantics: the API returns the candle immediately before the supplied time boundary, so wire request bounds are shifted by one timeframe and then filtered back into the requested UTC range.

## Backtest Engine

Phase 2B adds a minimal local-data backtest foundation without a production strategy. `DatasetLoader` reads `data/parquet/<symbol>/<timeframe>/candles.parquet`, converts rows to the shared `Candle` model, sorts and revalidates the data, and rejects incomplete datasets by default. Optional timezone-aware `start` and `end` values filter a UTC `[start, end)` range.

The engine processes one candle at a time in strict timestamp order. A strategy receives only the current and previous candles through `StrategyContext`; a signal emitted on candle N is queued and filled at candle N+1's open. It supports one long or short position, `EXIT`, fee rate, and slippage rate. Leverage, multiple positions, funding, liquidation, optimization, and real trading strategies are intentionally outside this phase.

Run the validation-only demo strategy, which signals long on candle five and exit on candle ten:

```bash
python -m app.backtest.demo --symbol BTCUSDT --timeframe 15m
```

The demo requires a complete local Parquet dataset created by the historical-data commands above. Its fixed-index strategy lives only in the demo and is not a production strategy.

## Security

Never commit API keys, bot tokens, SSH private keys, passwords, or production `.env` files.

## Status

Phase 2B: quality-gated local dataset loader and minimal next-bar-open backtest engine.
