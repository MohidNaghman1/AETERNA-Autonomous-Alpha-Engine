#!/usr/bin/env python3
"""Test the full ingestion pipeline locally."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("PIPELINE TEST - LOCAL")
print("=" * 60)

# Test 1: RSS Collection
print("\n[1] Testing RSS collector...")
try:
    from app.modules.ingestion.application.rss_collector import run_collector
    run_collector()
    print("[✅] RSS collector completed without errors")
except Exception as e:
    print(f"[❌] RSS collector failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Check RabbitMQ queue
print("\n[2] Checking RabbitMQ queue depth...")
try:
    import pika
    from dotenv import load_dotenv
    
    load_dotenv()
    
    RABBITMQ_URL = os.getenv("RABBITMQ_URL")
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "events")
    RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
    
    if RABBITMQ_URL:
        conn_params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection([conn_params])
    else:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=credentials,
            )
        )
    
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    
    # Get queue info
    method = channel.queue_declare(queue=RABBITMQ_QUEUE, passive=True)
    message_count = method.method.message_count
    consumer_count = method.method.consumer_count
    
    connection.close()
    
    print(f"[✅] RabbitMQ connected")
    print(f"    Queue: {RABBITMQ_QUEUE}")
    print(f"    Messages: {message_count}")
    print(f"    Consumers: {consumer_count}")
    
except Exception as e:
    print(f"[❌] Failed to check RabbitMQ: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Consumer polling
print("\n[3] Testing consumer polling...")
try:
    from app.modules.ingestion.application.consumer import run_consumer_poll
    count = run_consumer_poll(batch_size=10)
    print(f"[✅] Consumer polling completed, processed {count} messages")
except Exception as e:
    print(f"[❌] Consumer polling failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
