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

Phase 2A downloads BTCUSDT historical USDT-perpetual candles through Bitget's historical API and caches them in UTC Parquet files. A single Parquet file per timeframe keeps the first version simple and makes incremental updates easy: existing timestamps are read, only newly completed tail candles are requested, then the sorted/deduplicated cache is atomically replaced. Historical gaps are retained in the quality report rather than silently retried on every run.

```bash
python -m app.data.download --symbol BTCUSDT --timeframe 15m --days 730
python -m app.data.download --symbol BTCUSDT --timeframe 1H --days 730
```

Files are stored at `data/parquet/BTCUSDT/<timeframe>/candles.parquet`. Each run prints a UTC data-quality report with candle count, time range, duplicates removed, missing periods, and invalid OHLC count. Re-running the command only requests currently missing or newly completed candle intervals.

The downloader compensates for Bitget's history endpoint boundary semantics: the API returns the candle immediately before the supplied time boundary, so wire request bounds are shifted by one timeframe and then filtered back into the requested UTC range.

## Security

Never commit API keys, bot tokens, SSH private keys, passwords, or production `.env` files.

## Status

Phase 1: Bitget market-data layer and basic trend indicators.
