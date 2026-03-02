"""Monitoring and logging utilities.

Provides centralized logging configuration and Prometheus metrics for event processing
including event counters and processing time histograms.
"""

import logging
import sys
from prometheus_client import Counter, Histogram, start_http_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

EVENTS_PROCESSED = Counter(
    "events_processed_total", "Total events processed", ["collector"]
)
EVENT_PROCESSING_TIME = Histogram(
    "event_processing_seconds", "Time spent processing event", ["collector"]
)


def start_metrics_server(port: int = 8001) -> None:
    """Start Prometheus metrics HTTP server.

    Exposes metrics on the specified port for Prometheus scraping.

    Args:
        port: Port to expose metrics on (default: 8001)
    """
    start_http_server(port)
    logging.info(f"Prometheus metrics server started on port {port}")
