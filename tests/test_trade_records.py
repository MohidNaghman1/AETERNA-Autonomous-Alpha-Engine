"""Unit tests for intelligence trade record extraction and idempotent identity."""

from datetime import datetime

from app.modules.intelligence.application.trade_records import (
    is_trade_like_event,
    extract_trade_record_payload,
    build_deterministic_trade_id,
)


def test_is_trade_like_event_for_dex_swap_payload():
    event = {
        "id": "evt-1",
        "source": "ethereum",
        "timestamp": "2026-04-18T10:00:00Z",
        "content": {
            "event_type": "dex_swap",
            "wallet_address": "0xABC",
            "token_in": "USDC",
            "token_out": "ETH",
            "amount_in": "1000",
            "amount_out": "0.32",
            "usd_value": 1000,
        },
    }

    assert is_trade_like_event(event) is True


def test_extract_trade_record_payload_normalizes_wallet_and_amounts():
    event = {
        "id": "evt-2",
        "source": "ethereum",
        "timestamp": "2026-04-18T10:01:00Z",
        "content": {
            "event_type": "dex_swap",
            "wallet_address": "0xABCDEF",
            "transaction_hash": "0xtxhash",
            "dex": "uniswap",
            "token_in": "USDC",
            "token_out": "ETH",
            "amount_in": "2500.5",
            "amount_out": "0.8",
            "usd_value": "2500.5",
        },
    }

    payload = extract_trade_record_payload(event)

    assert payload is not None
    assert payload["wallet_address"] == "0xabcdef"
    assert payload["token_in"] == "USDC"
    assert payload["token_out"] == "ETH"
    assert payload["amount_in"] == 2500.5
    assert payload["amount_out"] == 0.8
    assert payload["exchange_or_dex"] == "uniswap"
    assert isinstance(payload["timestamp"], datetime)


def test_build_deterministic_trade_id_uses_tx_hash_and_log_index_when_available():
    payload = {
        "event_id": "evt-3",
        "transaction_hash": "0xabc",
        "log_index": 7,
        "wallet_address": "0xwallet",
        "token_in": "USDT",
        "token_out": "WBTC",
        "amount_in": 10000.0,
        "amount_out": 0.15,
        "timestamp": datetime(2026, 4, 18, 10, 2, 0),
    }

    trade_id_a = build_deterministic_trade_id(payload)
    trade_id_b = build_deterministic_trade_id(payload)

    assert trade_id_a == trade_id_b
    assert trade_id_a == "0xabc_7_0xwallet"


def test_build_deterministic_trade_id_fallback_hash_when_tx_hash_missing():
    payload = {
        "event_id": "evt-3-fallback",
        "wallet_address": "0xwallet",
        "token_in": "USDT",
        "token_out": "WBTC",
        "amount_in": 10000.0,
        "amount_out": 0.15,
        "timestamp": datetime(2026, 4, 18, 10, 2, 0),
    }

    trade_id = build_deterministic_trade_id(payload)
    assert len(trade_id) == 40


def test_extract_trade_record_payload_returns_none_for_non_trade_event():
    event = {
        "id": "evt-4",
        "source": "ethereum",
        "timestamp": "2026-04-18T10:03:00Z",
        "content": {
            "transaction_type": "transfer",
            "from_address": "0x1",
            "to_address": "0x2",
            "token": "USDC",
            "usd_value": 100000,
        },
    }

    assert extract_trade_record_payload(event) is None


def test_is_trade_like_event_detects_transaction_type_swap():
    event = {
        "id": "evt-5",
        "source": "ethereum",
        "timestamp": "2026-04-18T10:04:00Z",
        "content": {
            "transaction_type": "swap",
            "wallet_address": "0xabc",
            "token_in": "USDC",
            "token_out": "ETH",
            "amount_in": "100",
            "amount_out": "0.03",
            "usd_value": 100,
        },
    }

    assert is_trade_like_event(event) is True


def test_is_trade_like_event_rejects_non_ethereum_source():
    event = {
        "id": "evt-6",
        "source": "rss",
        "timestamp": "2026-04-18T10:05:00Z",
        "content": {
            "event_type": "dex_swap",
            "token_in": "USDC",
            "token_out": "ETH",
            "amount_in": "100",
            "amount_out": "0.03",
            "usd_value": 100,
        },
    }

    assert is_trade_like_event(event) is False
