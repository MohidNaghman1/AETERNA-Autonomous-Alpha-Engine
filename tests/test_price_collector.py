import pytest
from unittest.mock import patch, MagicMock
from app.modules.ingestion.application import price_collector

@patch('app.modules.ingestion.application.price_collector.requests.get')
@patch('app.modules.ingestion.application.price_collector.publish_event')
@patch('app.modules.ingestion.application.price_collector.is_duplicate', return_value=False)
@patch('app.modules.ingestion.application.price_collector.mark_as_seen')
def test_price_collector_processes_items(mock_mark_seen, mock_is_dup, mock_publish, mock_get):
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
