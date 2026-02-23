import pytest
from unittest.mock import patch, MagicMock
from app.modules.ingestion.application import rss_collector

@patch('app.modules.ingestion.application.rss_collector.requests.get')
@patch('app.modules.ingestion.application.rss_collector.publish_event')
@patch('app.modules.ingestion.application.rss_collector.is_duplicate', return_value=False)
@patch('app.modules.ingestion.application.rss_collector.mark_as_seen')
def test_rss_collector_processes_entries(mock_mark_seen, mock_is_dup, mock_publish, mock_get):
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
