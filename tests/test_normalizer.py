import pytest
from app.modules.ingestion.domain.models import Event
from datetime import datetime

def test_event_id_deduplication():
    content = {"title": "Test", "summary": "Test summary"}
    ts = datetime.utcnow()
    e1 = Event.create("coindesk", "news", ts, content)
    e2 = Event.create("coindesk", "news", ts, content)
    assert e1.id == e2.id

def test_event_validation():
    content = {"title": "Test", "summary": "Test summary"}
    ts = datetime.utcnow()
    e = Event.create("coindesk", "news", ts, content)
    assert e.id
    assert e.timestamp
    assert e.content
    assert len(str(e.content)) > 10

def test_event_scoring_entities():
    content = {"title": "BTC pumps!", "summary": "Bitcoin rises."}
    ts = datetime.utcnow()
    e = Event.create("coindesk", "news", ts, content, entities=["BTC"])
    assert e.quality_score >= 20

def test_event_scoring_price():
    content = {"id": "btc", "symbol": "BTC", "name": "Bitcoin", "current_price": 50000}
    ts = datetime.utcnow()
    e = Event.create("coingecko", "price", ts, content, entities=["BTC"])
    assert e.quality_score >= 15
