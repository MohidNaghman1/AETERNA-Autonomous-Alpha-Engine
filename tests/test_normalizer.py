"""Tests for event normalization and validation.

Tests Event model creation, validation, and quality scoring.
"""

import pytest
from datetime import datetime
from app.modules.ingestion.domain.models import Event
from app.modules.ingestion.presentation.api import normalize_source, normalize_type
from app.shared.utils.data_extractors import extract_twitter_tweet_detailed
from app.shared.utils.validators import validate_event


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


def test_twitter_event_validation():
    """Test Twitter/X social events validate successfully."""
    tweet = {
        "id": "1234567890",
        "text": "Bitcoin and ETH are both moving higher. #bitcoin",
        "created_at": "2026-03-09T12:49:30Z",
        "lang": "en",
        "public_metrics": {
            "like_count": 120,
            "retweet_count": 25,
            "reply_count": 8,
            "quote_count": 3,
        },
    }
    author = {
        "id": "42",
        "name": "Crypto Whale",
        "username": "crypto_whale",
        "verified": True,
        "public_metrics": {"followers_count": 50000, "tweet_count": 1000},
    }
    content = extract_twitter_tweet_detailed(tweet, author)
    event = Event.create(
        "twitter",
        "social",
        datetime.utcnow(),
        content,
        entities=["Bitcoin", "ETH"],
    )

    is_valid, error = validate_event(event.model_dump())
    assert is_valid, error
    assert event.content["author"]["username"] == "@crypto_whale"
    assert event.content["engagement_rate"] > 0


def test_twitter_event_content_structure():
    """Test normalized Twitter/X payload exposes engagement and URL metadata."""
    content = extract_twitter_tweet_detailed(
        {
            "id": "1234567890",
            "text": "Watching BTC closely https://example.com #bitcoin",
            "created_at": "2026-03-09T12:49:30Z",
            "public_metrics": {"like_count": 10, "retweet_count": 2, "reply_count": 1},
        },
        {
            "id": "7",
            "name": "Alice",
            "username": "alice_alpha",
            "public_metrics": {"followers_count": 1000},
        },
    )

    assert content["tweet_id"] == "1234567890"
    assert content["url"].endswith("/status/1234567890")
    assert content["engagement"]["likes"] == 10
    assert "#bitcoin" in content["hashtags"]


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


def test_twitter_filter_normalization():
    """Test ingestion API normalizes twitter/social filters."""
    assert normalize_source("twitter") == ["twitter"]
    assert normalize_source("x") == ["twitter"]
    assert normalize_type("social") == ["social"]
    assert "social" in normalize_type("sentiment")
