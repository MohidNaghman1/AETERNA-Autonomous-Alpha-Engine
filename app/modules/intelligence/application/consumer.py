"""
RabbitMQ Consumer for Agent A Event Processing
"""

import json
import pika
import os
from app.modules.intelligence.application.agent_a import score_event
# from app.modules.intelligence.infrastructure.models import save_processed_event  # To be implemented in next step

# Optionally load .env for local dev
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
QUEUE_NAME = os.environ.get('RABBITMQ_QUEUE', 'events')

# Dummy function for DB embeddings lookup (to be replaced with real DB call)
def get_recent_event_embeddings():
    # Return a list of embeddings from recent events (last 30 min)
    return []

def process_event(ch, method, properties, body):
    try:
        event = json.loads(body)
        db_embeddings = get_recent_event_embeddings()
        result = score_event(event, db_embeddings)
        event.update(result)
        # save_processed_event(event)  # To be implemented in next step
        print(f"Processed event: {event.get('id', 'N/A')} | Priority: {event['priority']} | Score: {event['score']:.2f}")
    except Exception as e:
        print(f"Error processing event: {e}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    print(f"[*] Waiting for messages in '{QUEUE_NAME}'. To exit press CTRL+C")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_event)
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()
