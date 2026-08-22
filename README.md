# quant-radar

`quant-radar` is a market-monitoring foundation for Bitget spot data. It currently has **no trading and no order execution**.

## Architecture

```text
Bitget REST ───────┐
                   ↓
                 Ticker
                   ↓
Bitget WS ─────────┤
                   ↓
            MarketDataService
                   ↓
             Redis latest cache
```

## Phase 2 status

Complete: public REST snapshots, normalized market models, a public ticker WebSocket stream, Bitget application heartbeat, exponential reconnect, and an optional Redis latest-ticker cache.

Not implemented: private APIs, API keys/signing, trading/orders, strategies/indicators, PostgreSQL history, notifications, and backtesting.

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

The process fetches initial REST snapshots, then subscribes to public SPOT ticker streams for `MARKET_SYMBOLS`. Bitget's documented application heartbeat sends text `ping` every 30 seconds and requires a text `pong`; a missing pong reconnects. Disconnects retry with 1, 2, 4, 8, 16, then 30-second maximum backoff.

Redis is optional. When `REDIS_URL` is configured, each latest ticker is stored as JSON (Decimal values remain strings) at `quant-radar:ticker:<SYMBOL>` with a TTL. Redis failures are logged and do not stop the market feed.

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
| `BITGET_WS_URL` | `wss://ws.bitget.com/v2/ws/public` | Public ticker WebSocket endpoint |
| `MARKET_SYMBOLS` | `BTCUSDT,ETHUSDT` | Comma-separated public SPOT symbols |
| `MARKET_CACHE_TTL_SECONDS` | `120` | Latest-ticker cache TTL |
| `WS_RECONNECT_MAX_SECONDS` | `30` | Maximum reconnect backoff |
| `DATABASE_URL` | empty | Reserved for a later phase |
| `REDIS_URL` | empty | Optional Redis latest-ticker cache |
| `TELEGRAM_BOT_TOKEN` | empty | Reserved for a later phase |
| `TELEGRAM_CHAT_ID` | empty | Reserved for a later phase |
| `WECOM_WEBHOOK_URL` | empty | Reserved for a later phase |

## Security

Never commit API keys, bot tokens, SSH private keys, passwords, or production `.env` files.
