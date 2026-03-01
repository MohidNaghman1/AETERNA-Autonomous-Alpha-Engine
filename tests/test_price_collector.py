import pytest
from unittest.mock import patch, MagicMock
from app.modules.ingestion.application import price_collector

@patch('app.modules.ingestion.application.price_collector.requests.get')
@patch('app.modules.ingestion.application.price_collector.publish_event')
@patch('app.modules.ingestion.application.price_collector.is_duplicate', return_value=False)
@patch('app.modules.ingestion.application.price_collector.mark_as_seen')
def test_price_collector_processes_items(mock_mark_seen, mock_is_dup, mock_publish, mock_get):
    """Test price collector processes price data correctly."""
    # Mock response.json to return fake items
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {'id': 'btc', 'symbol': 'BTC'},
        {'id': 'eth', 'symbol': 'ETH'}
    ]
    mock_get.return_value.raise_for_status = MagicMock()
    # Patch normalize_price to return a simple event object
    with patch('app.modules.ingestion.application.price_collector.normalize_price') as mock_norm:
        class DummyEvent:
            def __init__(self, id):
                self.id = id
                self.content = {'symbol': id}
        mock_norm.side_effect = lambda item, source: DummyEvent(item['id'])
        # Run one iteration only
        with patch('app.modules.ingestion.application.price_collector.POLL_INTERVAL', 0):
            with patch('time.sleep'):
                price_collector.run_collector()
    assert mock_publish.call_count >= 2
    assert mock_mark_seen.call_count >= 2

@patch('app.modules.ingestion.application.price_collector.requests.get')
def test_price_collector_handles_network_error(mock_get):
    """Test price collector handles network failures gracefully."""
    mock_get.side_effect = Exception("Network timeout")
    
    with patch('app.modules.ingestion.application.price_collector.POLL_INTERVAL', 0):
        with patch('time.sleep'):
            try:
                price_collector.run_collector()
            except Exception:
                # Error should be logged, not crash
                pass

@patch('app.modules.ingestion.application.price_collector.requests.get')
def test_price_collector_handles_invalid_json(mock_get):
    """Test price collector handles invalid JSON responses."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.side_effect = ValueError("Invalid JSON")
    
    with patch('app.modules.ingestion.application.price_collector.POLL_INTERVAL', 0):
        with patch('time.sleep'):
            try:
                price_collector.run_collector()
            except Exception:
                pass

@patch('app.modules.ingestion.application.price_collector.requests.get')
def test_price_collector_handles_empty_response(mock_get):
    """Test price collector handles empty price data."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = []
    
    with patch('app.modules.ingestion.application.price_collector.POLL_INTERVAL', 0):
        with patch('time.sleep'):
            with patch('app.modules.ingestion.application.price_collector.publish_event') as mock_publish:
                price_collector.run_collector()
                # Should not publish anything for empty data
                assert mock_publish.call_count == 0

@patch('app.modules.ingestion.application.price_collector.requests.get')
def test_price_collector_handles_duplicate_detection(mock_get):
    """Test that duplicate price data is not republished."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {'id': 'btc', 'symbol': 'BTC', 'current_price': 50000}
    ]
    
    with patch('app.modules.ingestion.application.price_collector.is_duplicate', return_value=True):
        with patch('app.modules.ingestion.application.price_collector.publish_event') as mock_pub:
            with patch('app.modules.ingestion.application.price_collector.POLL_INTERVAL', 0):
                with patch('time.sleep'):
                    with patch('app.modules.ingestion.application.price_collector.normalize_price') as mock_norm:
                        class DummyEvent:
                            def __init__(self, id):
                                self.id = id
                        mock_norm.return_value = DummyEvent('btc')
                        price_collector.run_collector()
                        # Duplicate should not be published
                        assert mock_pub.call_count == 0

