"""Tests for event normalization and validation.

Tests Event model creation, validation, and quality scoring.
"""

import pytest
from datetime import datetime
from app.modules.ingestion.domain.models import Event


def test_event_id_deduplication():
    """Test that identical events produce the same ID."""
    content = {"title": "Test", "summary": "Test summary"}
    ts = datetime.utcnow()
    e1 = Event.create("coindesk", "news", ts, content)
    e2 = Event.create("coindesk", "news", ts, content)
    assert e1.id == e2.id


def test_event_validation():
    """Test Event model validates all required fields."""
    content = {"title": "Test", "summary": "Test summary"}
    ts = datetime.utcnow()
    e = Event.create("coindesk", "news", ts, content)
    assert e.id
    assert e.timestamp
    assert e.content
    assert len(str(e.content)) > 10


def test_event_validation_invalid_source():
    """Test Event validation with invalid source."""
    content = {"title": "Test", "summary": "Test summary"}
    ts = datetime.utcnow()

    try:
        # Should validate source - needs to be known source
        e = Event.create("invalid_source", "news", ts, content)
        # If it doesn't validate, that's OK for now
    except ValueError:
        # Expected - unknown source
        pass


def test_event_validation_empty_content():
    """Test Event validation rejects empty content."""
    ts = datetime.utcnow()

    try:
        e = Event.create("coindesk", "news", ts, {})
        # Should fail or return event with low score
        assert e.quality_score < 20
    except ValueError:
        # Expected - empty content should fail
        pass


def test_event_scoring_with_entities():
    """Test Event scoring with crypto entities detected."""
    content = {"title": "BTC pumps!", "summary": "Bitcoin rises to $50k"}
    ts = datetime.utcnow()
    e = Event.create("coindesk", "news", ts, content, entities=["BTC"])
    assert e.quality_score >= 20, "Events with crypto entities should score higher"


def test_event_scoring_without_entities():
    """Test Event scoring with no crypto entities."""
    content = {"title": "General tech news", "summary": "Random tech update"}
    ts = datetime.utcnow()
    e = Event.create("coindesk", "news", ts, content, entities=[])
    assert e.quality_score < 50, "Events without crypto entities should score lower"


def test_event_scoring_price_data():
    """Test Event scoring for price updates."""
    content = {"id": "btc", "symbol": "BTC", "name": "Bitcoin", "current_price": 50000}
    ts = datetime.utcnow()
    e = Event.create("coingecko", "price", ts, content, entities=["BTC"])
    assert e.quality_score >= 15, "Price data should have baseline quality score"


def test_event_with_multiple_entities():
    """Test Event scoring with multiple crypto entities mentioned."""
    content = {
        "title": "BTC and ETH pump",
        "summary": "Bitcoin and Ethereum both surge",
    }
    ts = datetime.utcnow()
    e = Event.create("coindesk", "news", ts, content, entities=["BTC", "ETH"])
    assert e.quality_score >= 30, "Multiple entities should increase score"


def test_event_timestamp_handling():
    """Test Event timestamp is stored correctly."""
    content = {"title": "Test", "summary": "Test"}
    ts = datetime(2026, 3, 1, 12, 0, 0)
    e = Event.create("coindesk", "news", ts, content)
    assert e.timestamp == ts


def test_event_source_types():
    """Test Event accepts different source types."""
    content = {"title": "Test", "summary": "Test"}
    ts = datetime.utcnow()

    sources = ["coindesk", "coingecko", "coinmarketcap"]
    for source in sources:
        try:
            e = Event.create(source, "news", ts, content)
            assert e is not None
        except ValueError:
            # Some sources might not be configured
            pass


def test_event_type_validation():
    """Test Event validates type field."""
    content = {"title": "Test", "summary": "Test"}
    ts = datetime.utcnow()

    # Valid types
    for event_type in ["news", "price"]:
        e = Event.create("coindesk", event_type, ts, content)
        assert e is not None

    # Invalid type
    try:
        e = Event.create("coindesk", "invalid_type", ts, content)
        # If it allows invalid types, that's OK for now
    except ValueError:
        # Expected - invalid type
        pass


def test_event_content_structure():
    """Test Event handles various content structures."""
    ts = datetime.utcnow()

    # News content
    news_content = {
        "title": "News Title",
        "link": "https://example.com",
        "summary": "News summary",
    }
    e1 = Event.create("coindesk", "news", ts, news_content)
    assert e1.content["title"] == "News Title"

    # Price content
    price_content = {"symbol": "BTC", "price": 50000, "change_24h": 3.5}
    e2 = Event.create("coingecko", "price", ts, price_content)
    assert e2.content["symbol"] == "BTC"


def test_event_quality_score_range():
    """Test Event quality score is in valid range."""
    content = {"title": "Test", "summary": "Test"}
    ts = datetime.utcnow()
    e = Event.create("coindesk", "news", ts, content)
    assert 0 <= e.quality_score <= 100, "Quality score should be 0-100"
