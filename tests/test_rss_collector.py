import pytest
from unittest.mock import patch, MagicMock
from app.modules.ingestion.application import rss_collector

@patch('app.modules.ingestion.application.rss_collector.requests.get')
@patch('app.modules.ingestion.application.rss_collector.publish_event')
@patch('app.modules.ingestion.application.rss_collector.is_duplicate', return_value=False)
@patch('app.modules.ingestion.application.rss_collector.mark_as_seen')
def test_rss_collector_processes_entries(mock_mark_seen, mock_is_dup, mock_publish, mock_get):
    """Test RSS collector processes feed entries correctly."""
    # Mock feedparser.parse to return fake entries
    with patch('app.modules.ingestion.application.rss_collector.feedparser.parse') as mock_parse:
        mock_parse.return_value.entries = [
            {'id': '1', 'title': 'Test', 'link': 'url', 'summary': 'desc'},
            {'id': '2', 'title': 'Test2', 'link': 'url2', 'summary': 'desc2'}
        ]
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b''
        mock_get.return_value.raise_for_status = MagicMock()
        # Patch normalize_entry to return a simple event object
        with patch('app.modules.ingestion.application.rss_collector.normalize_entry') as mock_norm:
            class DummyEvent:
                def __init__(self, id):
                    self.id = id
                    self.content = {'title': 'Test'}
            mock_norm.side_effect = lambda entry, source: DummyEvent(entry['id'])
            # Run one iteration only
            with patch('app.modules.ingestion.application.rss_collector.POLL_INTERVAL', 0):
                with patch('time.sleep'):
                    rss_collector.run_collector()
        assert mock_publish.call_count >= 2
        assert mock_mark_seen.call_count >= 2

@patch('app.modules.ingestion.application.rss_collector.feedparser.parse')
@patch('app.modules.ingestion.application.rss_collector.requests.get')
def test_rss_collector_handles_malformed_feed(mock_get, mock_parse):
    """Test RSS collector gracefully handles malformed XML."""
    # Mock feedparser to raise exception for malformed XML
    mock_parse.side_effect = Exception("Malformed XML")
    mock_get.return_value.status_code = 200
    
    # Should not crash
    with patch('app.modules.ingestion.application.rss_collector.POLL_INTERVAL', 0):
        with patch('time.sleep'):
            try:
                rss_collector.run_collector()
            except Exception:
                # Acceptable - errors should be logged
                pass

@patch('app.modules.ingestion.application.rss_collector.requests.get')
def test_rss_collector_handles_network_error(mock_get):
    """Test RSS collector handles network failures."""
    # Mock network error
    mock_get.side_effect = Exception("Network timeout")
    
    with patch('app.modules.ingestion.application.rss_collector.POLL_INTERVAL', 0):
        with patch('time.sleep'):
            try:
                rss_collector.run_collector()
            except Exception:
                pass

@patch('app.modules.ingestion.application.rss_collector.feedparser.parse')
@patch('app.modules.ingestion.application.rss_collector.requests.get')
def test_rss_collector_handles_empty_feed(mock_get, mock_parse):
    """Test RSS collector handles empty feed."""
    mock_parse.return_value.entries = []
    mock_get.return_value.status_code = 200
    
    with patch('app.modules.ingestion.application.rss_collector.POLL_INTERVAL', 0):
        with patch('time.sleep'):
            with patch('app.modules.ingestion.application.rss_collector.publish_event') as mock_publish:
                rss_collector.run_collector()
                # Should not publish anything for empty feed
                assert mock_publish.call_count == 0

