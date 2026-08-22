from decimal import Decimal

import pytest

from app.exchanges.bitget_ws import BitgetPayloadError, BitgetWebSocketError, parse_ticker_message


def ticker_message() -> dict:
    return {"arg": {"instType": "SPOT", "channel": "ticker", "instId": "BTCUSDT"}, "data": [{"instId": "BTCUSDT", "lastPr": "65000.12", "bidPr": "65000.11", "askPr": "65000.13", "high24h": "66000", "low24h": "64000", "baseVolume": "10.5", "quoteVolume": "682501", "ts": "1720000000000"}]}


def test_ticker_message_parses_to_decimal_ticker() -> None:
    ticker = parse_ticker_message(ticker_message())[0]
    assert ticker.symbol == "BTCUSDT"
    assert ticker.last_price == Decimal("65000.12")


def test_subscribe_ack_is_ignored() -> None:
    assert parse_ticker_message({"event": "subscribe", "arg": {"channel": "ticker"}}) == []


def test_error_event_raises() -> None:
    with pytest.raises(BitgetWebSocketError, match="30001"):
        parse_ticker_message({"event": "error", "code": "30001", "msg": "invalid subscription"})


def test_malformed_ticker_payload_raises() -> None:
    message = ticker_message()
    del message["data"][0]["lastPr"]
    with pytest.raises(BitgetPayloadError, match="invalid ticker payload"):
        parse_ticker_message(message)


def test_unknown_channel_is_ignored() -> None:
    assert parse_ticker_message({"arg": {"channel": "books5"}, "data": []}) == []
