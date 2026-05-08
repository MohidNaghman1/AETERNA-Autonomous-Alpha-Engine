from unittest.mock import MagicMock

from app.modules.ingestion.application import consumer


def test_flush_pending_batch_flushes_partial_valid_batch(monkeypatch):
    channel = MagicMock()
    flushed = {"called": False}

    monkeypatch.setattr(consumer, "_batch_orms", [object()])
    monkeypatch.setattr(consumer, "_batch_dlq", [])

    def fake_flush_batch(flush_channel):
        flushed["called"] = True
        assert flush_channel is channel

    monkeypatch.setattr(consumer, "flush_batch", fake_flush_batch)

    consumer.flush_pending_batch(channel)

    assert flushed["called"] is True


def test_schedule_periodic_flush_uses_configured_interval(monkeypatch):
    connection = MagicMock()
    channel = MagicMock()

    monkeypatch.setattr(consumer, "BATCH_FLUSH_INTERVAL_SECONDS", 10)

    consumer.schedule_periodic_flush(connection, channel)

    connection.call_later.assert_called_once()
    assert connection.call_later.call_args.args[0] == 10
    assert callable(connection.call_later.call_args.args[1])
