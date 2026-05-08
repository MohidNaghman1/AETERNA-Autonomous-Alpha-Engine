from datetime import datetime, timedelta

from app.shared.utils import deduplication


def test_mark_as_seen_uses_configured_default_ttl(monkeypatch):
    calls = {}

    class FakeRedis:
        def setex(self, key, ttl, value):
            calls["key"] = key
            calls["ttl"] = ttl
            calls["value"] = value

    monkeypatch.setattr(deduplication, "_redis_available", True)
    monkeypatch.setattr(deduplication, "_redis", FakeRedis())

    deduplication.mark_as_seen("rss-event-id")

    assert calls == {
        "key": "event:rss-event-id",
        "ttl": deduplication.DEDUP_TTL_SECONDS,
        "value": "1",
    }


def test_memory_cache_fallback_uses_configured_default_ttl(monkeypatch):
    now = datetime(2026, 5, 8, 11, 5, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def utcnow(cls):
            return now

    monkeypatch.setattr(deduplication, "_redis_available", False)
    monkeypatch.setattr(deduplication, "_redis", None)
    monkeypatch.setattr(deduplication, "_memory_cache", {})
    monkeypatch.setattr(deduplication, "datetime", FrozenDateTime)

    deduplication.mark_as_seen("rss-event-id")

    assert deduplication._memory_cache["event:rss-event-id"] == now + timedelta(
        seconds=deduplication.DEDUP_TTL_SECONDS
    )
