#!/usr/bin/env python
"""
Test the consumer by manually processing a message from RabbitMQ
"""
import os
import json
import pika
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def test_consumer_manually():
    """Manually test consuming a message from RabbitMQ."""
    
    print("\n" + "="*60)
    print("CONSUMER TEST - Manual Message Processing")
    print("="*60 + "\n")
    
    # RabbitMQ config
    host = os.getenv("RABBITMQ_HOST", "localhost")
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")
    queue = os.getenv("RABBITMQ_QUEUE", "events")
    
    # Connect and check queue
    print(f"1️⃣  Connecting to RabbitMQ at {host}...")
    credentials = pika.PlainCredentials(user, password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    
    # Get first message
    print(f"2️⃣  Checking queue '{queue}'...\n")
    method, properties, body = channel.basic_get(queue, auto_ack=False)
    
    if not method:
        print(f"   📭 Queue is empty!")
        print(f"   No messages to process.\n")
        connection.close()
        return
    
    print(f"   📨 Found message! (delivery tag: {method.delivery_tag})")
    print(f"   Message body:\n{body.decode()}\n")
    
    # Try to process it like the consumer would
    try:
        from app.modules.ingestion.domain.models import Event
        from app.config.db import SessionLocal
        from app.modules.ingestion.infrastructure.models import EventORM
        
        data = json.loads(body)
        if 'event_type' in data:
            data['type'] = data.pop('event_type')
        
        print(f"3️⃣  Processing message...")
        event = Event(**data)
        
        # Validate
        if not event.id or not getattr(event, 'timestamp', None) or not event.content:
            print(f"   ❌ Validation failed")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            connection.close()
            return
        
        print(f"   ✅ Validation passed")
        
        # Store in DB
        print(f"4️⃣  Storing in database...")
        db = SessionLocal()
        
        # Parse timestamp string to datetime object
        # Event.timestamp is ISO8601 string (e.g., "2026-03-04T12:27:02Z")
        # EventORM.timestamp expects datetime object
        from datetime import datetime
        timestamp_str = getattr(event, "timestamp", None)
        if timestamp_str:
            # Remove 'Z' suffix and parse
            ts_clean = timestamp_str.rstrip('Z')
            timestamp_dt = datetime.fromisoformat(ts_clean)
        else:
            timestamp_dt = None
        
        db_event = EventORM(
            source=getattr(event, 'source', None),
            type=getattr(event, 'type', None),
            timestamp=timestamp_dt,
            content=event.content,
            raw=None
        )
        db.add(db_event)
        db.commit()
        print(f"   ✅ Event stored with ID: {db_event.id}")
        db.close()
        
        # Acknowledge the message
        channel.basic_ack(delivery_tag=method.delivery_tag)
        print(f"5️⃣  Message acknowledged from queue")
        
        print(f"\n✅ SUCCESS: Message processed and stored!")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        print(f"   Message returned to queue for retry")
    
    connection.close()
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_consumer_manually()
