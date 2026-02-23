import logging
import sys
from prometheus_client import Counter, Histogram, start_http_server

# Set up root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Prometheus metrics
EVENTS_PROCESSED = Counter('events_processed_total', 'Total events processed', ['collector'])
EVENT_PROCESSING_TIME = Histogram('event_processing_seconds', 'Time spent processing event', ['collector'])

def start_metrics_server(port=8001):
    start_http_server(port)
    logging.info(f"Prometheus metrics server started on port {port}")
