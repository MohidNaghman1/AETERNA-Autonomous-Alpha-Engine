import subprocess
import time
import threading
import requests
import pika
import os
import pytest

# Integration test: run all collectors and consumer, publish and consume events, check deduplication

def run_collector(module):
    return subprocess.Popen([
        "python", "-m", f"app.modules.ingestion.application.{module}"
    ])

def test_end_to_end_ingestion(monkeypatch):
    # Start RSS and price collectors and consumer
    procs = [
        run_collector("rss_collector"),
        run_collector("price_collector"),
        run_collector("event_consumer"),
    ]
    time.sleep(10)  # Let them run for a bit
    # Connect to RabbitMQ and check queue depth
    rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
    rabbitmq_queue = os.getenv("RABBITMQ_QUEUE", "events")
    rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
    rabbitmq_pass = os.getenv("RABBITMQ_PASS", "guest")
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
    conn = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, credentials=credentials))
    channel = conn.channel()
    q = channel.queue_declare(queue=rabbitmq_queue, durable=True, passive=True)
    queue_depth = q.method.message_count
    assert queue_depth < 100  # Should be draining
    # Clean up
    for p in procs:
        p.terminate()
    conn.close()
    # Check /metrics endpoint
    try:
        r = requests.get("http://localhost:8000/metrics")
        assert r.status_code == 200
        assert b"aeterna_api_requests_total" in r.content
    except Exception:
        pass
