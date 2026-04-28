"""Monitoring and logging utilities.

Provides centralized logging configuration and Prometheus metrics for event processing
including event counters and processing time histograms.
"""

import logging
import os
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

_METRICS_SERVER_STARTED = False


def start_metrics_server(port: int = 8001) -> None:
    """Start Prometheus metrics HTTP server.

    Exposes metrics on the specified port for Prometheus scraping.

    Args:
        port: Port to expose metrics on (default: 8001)
    """
    global _METRICS_SERVER_STARTED

    if _METRICS_SERVER_STARTED:
        return

    enabled = os.getenv("ENABLE_PROMETHEUS_HTTP_SERVER", "true").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        logging.info("Prometheus metrics HTTP server disabled by config")
        return

    metrics_port = int(os.getenv("METRICS_PORT", str(port)))
    start_http_server(metrics_port)
    _METRICS_SERVER_STARTED = True
    logging.info(f"Prometheus metrics server started on port {metrics_port}")
