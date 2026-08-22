# quant-radar

`quant-radar` is a market-monitoring foundation for Bitget spot data. It currently has **no trading and no order execution**.

## Architecture

```text
Bitget public REST -> BitgetPublicClient -> MarketDataService -> application heartbeat
                         |                      |
                    normalized models      future cache/storage/indicators
```

## Phase 1 status

Complete: configuration, normalized market models, Bitget public REST ticker/candles, a market-data service, and offline unit tests.

Not implemented: private APIs, API keys/signing, trading/orders, strategies/indicators, databases, Redis, notifications, and WebSocket data.

## Development

Requires Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running locally

Copy `.env.example` to `.env` if you want to override defaults, then run `python -m app.main`.

The process logs a BTCUSDT public ticker snapshot every 60 seconds and keeps retrying after temporary API failures.

## Testing

```bash
python -m pytest -q
python -m compileall app
```

All tests use `httpx.MockTransport` or fake clients and do not access the internet.

## Environment variables

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ENV` | `development` | Application environment |
| `LOG_LEVEL` | `INFO` | Python log level |
| `BITGET_REST_URL` | `https://api.bitget.com` | Public REST base URL |
| `BITGET_WS_URL` | `wss://ws.bitget.com/v2/ws/public` | Reserved for a later phase |
| `DATABASE_URL` | empty | Reserved for a later phase |
| `REDIS_URL` | empty | Reserved for a later phase |
| `TELEGRAM_BOT_TOKEN` | empty | Reserved for a later phase |
| `TELEGRAM_CHAT_ID` | empty | Reserved for a later phase |
| `WECOM_WEBHOOK_URL` | empty | Reserved for a later phase |

## Security

Never commit API keys, bot tokens, SSH private keys, passwords, or production `.env` files.
