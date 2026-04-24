"""Regression tests for on-chain swap normalization passthrough behavior."""

from datetime import datetime

from app.modules.ingestion.application import onchain_collector


def test_normalize_dex_swap_event_allows_zero_usd_passthrough(monkeypatch):
    monkeypatch.setattr(onchain_collector.OnChainConfig, "MIN_TRANSACTION_VALUE_USD", 10000)

    event = onchain_collector.normalize_dex_swap_event(
        tx_hash="0xtxhash",
        wallet_address="0xwallet",
        token_in="USDC",
        token_out="ETH",
        amount_in=1000.0,
        amount_out=0.32,
        usd_value=0.0,
        dex_name="Uniswap V3-like",
        pool_address="0xpool",
        log_index=1,
        block_timestamp=int(datetime(2026, 4, 18, 10, 0, 0).timestamp()),
    )

    assert event is not None
    assert event.content["usd_value"] == 0.0
    assert event.content["transaction_type"] == "swap"


def test_normalize_dex_swap_event_rejects_priced_below_threshold(monkeypatch):
    monkeypatch.setattr(onchain_collector.OnChainConfig, "MIN_TRANSACTION_VALUE_USD", 10000)

    event = onchain_collector.normalize_dex_swap_event(
        tx_hash="0xtxhash2",
        wallet_address="0xwallet",
        token_in="USDC",
        token_out="ETH",
        amount_in=1000.0,
        amount_out=0.32,
        usd_value=5000.0,
        dex_name="Uniswap V3-like",
        pool_address="0xpool",
        log_index=2,
        block_timestamp=int(datetime(2026, 4, 18, 10, 0, 0).timestamp()),
    )

    assert event is None
