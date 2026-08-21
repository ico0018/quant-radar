# quant-radar

A rule-driven crypto market radar for Bitget, focused on intraday signal scanning, human confirmation, and real-time notifications.

## Initial goals

- Bitget market data ingestion
- MA/EMA 20/60/120 indicators
- Small-cap short radar
- BTC / major-coin trend-following long radar
- Market regime filter
- Telegram and WeCom notifications
- Backtesting and signal journaling
- Docker-based deployment

## Architecture

```text
Bitget REST/WebSocket
        |
        v
Market Data -> Indicators -> Strategy Engine -> Signal State -> Notifications
                    |                |
                    v                v
                 Storage          Backtest
```

## Development workflow

```text
Local Codex CLI -> GitHub -> GitHub Actions -> Cloud VPS / Docker Compose
```

## Security

Never commit API keys, bot tokens, SSH private keys, passwords, or production `.env` files.

## Status

Phase 0/1: strategy rules and data layer.
