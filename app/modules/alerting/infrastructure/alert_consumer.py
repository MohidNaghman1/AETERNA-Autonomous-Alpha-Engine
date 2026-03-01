"""Alert consumer for RabbitMQ.

Listens to the alerts queue and broadcasts alerts to connected users via WebSocket
, filtering based on user preferences.
"""
import asyncio
import json
import os
import pika
from threading import Thread
from socketio import AsyncServer

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_QUEUE = os.getenv("ALERT_QUEUE_NAME", "alerts")


def alert_matches_user(alert, user_prefs=None) -> bool:
    """Check if an alert matches user's preferences.
    
    Filters alerts based on priority and entity preferences.
    
    Args:
        alert: Alert dict with 'priority' and 'entity' keys
        user_prefs: User preferences dict, or None to accept all alerts
        
    Returns:
        bool: True if alert matches user preferences, False otherwise
    """
    if not user_prefs:
        return True
    if "priority" in user_prefs and alert.get("priority") not in user_prefs["priority"]:
        return False
    if "entities" in user_prefs and alert.get("entity") not in user_prefs["entities"]:
        return False
    return True

class AlertConsumer(Thread):
    """Consumer thread for processing alerts from RabbitMQ queue.
    
    Connects to RabbitMQ, listens for alert messages, applies user preference filters,
    and broadcasts alerts to connected WebSocket clients.
    
    Attributes:
        sio: AsyncServer instance for WebSocket communication
        connection: RabbitMQ connection
        channel: RabbitMQ channel
        user_prefs_func: Callable that takes user_id and returns user preferences dict
    """
    
    def __init__(self, sio: AsyncServer, user_prefs_func=None):
        """Initialize the AlertConsumer.
        
        Args:
            sio: AsyncServer instance for WebSocket communication
            user_prefs_func: Optional callable to get user preferences (user_id -> dict)
        """
        super().__init__(daemon=True)
        self.sio = sio
        self.connection = None
        self.channel = None
        self.user_prefs_func = user_prefs_func

    def run(self):
        """Start consuming alerts from RabbitMQ queue.
        
        Establishes RabbitMQ connection and begins consuming messages from the alerts queue.
        This method blocks indefinitely while consuming.
        """
        creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        params = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=creds)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        self.channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=self.on_message, auto_ack=True)
        print("[AlertConsumer] Started listening for alerts...")
        self.channel.start_consuming()

    def on_message(self, ch, method, properties, body):
        """Handle incoming alert message from RabbitMQ.
        
        Parses the alert, applies user preference filtering, and broadcasts to the user
        via WebSocket if filters pass.
        
        Args:
            ch: RabbitMQ channel
            method: Message delivery method
            properties: Message properties
            body: Message body (JSON-encoded alert)
        """
        try:
            alert = json.loads(body)
            user_id = str(alert.get("user_id"))
            if user_id:
                user_prefs = self.user_prefs_func(user_id) if self.user_prefs_func else None
                if alert_matches_user(alert, user_prefs):
                    asyncio.run_coroutine_threadsafe(
                        self.sio.emit("alert", alert, room=user_id),
                        self.sio.eio.loop
                    )
                    print(f"[AlertConsumer] Alert sent to user {user_id}")
                else:
                    print(f"[AlertConsumer] Alert filtered out for user {user_id}")
            else:
                print("[AlertConsumer] Alert missing user_id, not sent")
        except Exception as e:
            print(f"[AlertConsumer] Error handling alert: {e}")
