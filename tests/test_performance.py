import time
from unittest.mock import patch, MagicMock
from app.modules.ingestion.application import rss_collector

def test_rss_collector_performance():
    # Simulate 10,000 events
    num_events = 10000
    with patch('app.modules.ingestion.application.rss_collector.requests.get') as mock_get, \
         patch('app.modules.ingestion.application.rss_collector.publish_event') as mock_publish, \
         patch('app.modules.ingestion.application.rss_collector.is_duplicate', return_value=False), \
         patch('app.modules.ingestion.application.rss_collector.mark_as_seen'), \
         patch('app.modules.ingestion.application.rss_collector.feedparser.parse') as mock_parse, \
         patch('app.modules.ingestion.application.rss_collector.normalize_entry') as mock_norm, \
         patch('app.modules.ingestion.application.rss_collector.POLL_INTERVAL', 0), \
         patch('time.sleep'):
        mock_parse.return_value.entries = [
            {'id': str(i), 'title': f'Test {i}', 'link': f'url{i}', 'summary': f'desc{i}'}
            for i in range(num_events)
        ]
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b''
        mock_get.return_value.raise_for_status = MagicMock()
        class DummyEvent:
            def __init__(self, id):
                self.id = id
                self.content = {'title': f'Test {id}'}
        mock_norm.side_effect = lambda entry, source: DummyEvent(entry['id'])
        start = time.time()
        rss_collector.run_collector()
        elapsed = time.time() - start
        # Assert throughput >= 10,000 events/hour (2.77 events/sec)
        assert mock_publish.call_count >= num_events
        assert elapsed < 3600, f"Throughput too low: {mock_publish.call_count} events in {elapsed} seconds"
