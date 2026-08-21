# quant-radar

A rule-driven crypto market radar for Bitget. Phase 1 provides a reliable, public REST market-data foundation; it does not place trades or send notifications.

## Phase 1

- Public Bitget REST client for USDT perpetual contracts and historical candles
- Supported candle intervals: `1m`, `5m`, `15m`, `1H`, `4H`
- Internal OHLCV candle model: timestamp, open, high, low, close, volume
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

## Security

Never commit API keys, bot tokens, SSH private keys, passwords, or production `.env` files.

## Status

Phase 1: Bitget market-data layer and basic trend indicators.
