"""Unit tests for trade backfill event reconstruction."""

from types import SimpleNamespace

from app.modules.intelligence.application.backfill_trades import _to_event_dict


def test_to_event_dict_does_not_default_source_to_ethereum():
    processed = SimpleNamespace(
        id=123,
        timestamp="2026-04-18T10:00:00Z",
        event_data={
            "content": {
                "event_type": "price_update",
            }
        },
    )

    event = _to_event_dict(processed)

    assert event["source"] == ""
    assert event["content"]["event_type"] == "price_update"


def test_to_event_dict_preserves_explicit_source():
    processed = SimpleNamespace(
        id=456,
        timestamp="2026-04-18T10:05:00Z",
        event_data={
            "source": "ethereum",
            "content": {
                "event_type": "swap",
            },
        },
    )

    event = _to_event_dict(processed)

    assert event["source"] == "ethereum"
    assert event["content"]["event_type"] == "swap"
