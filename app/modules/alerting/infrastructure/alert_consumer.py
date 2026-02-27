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


def alert_matches_user(alert, user_prefs=None):
    # Example: filter by priority, entity, etc. (expand as needed)
    if not user_prefs:
        return True
    if "priority" in user_prefs and alert.get("priority") not in user_prefs["priority"]:
        return False
    if "entities" in user_prefs and alert.get("entity") not in user_prefs["entities"]:
        return False
    return True

class AlertConsumer(Thread):
    def __init__(self, sio: AsyncServer, user_prefs_func=None):
        super().__init__(daemon=True)
        self.sio = sio
        self.connection = None
        self.channel = None
        self.user_prefs_func = user_prefs_func  # Callable: user_id -> prefs dict

    def run(self):
        creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        params = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=creds)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        self.channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=self.on_message, auto_ack=True)
        print("[AlertConsumer] Started listening for alerts...")
        self.channel.start_consuming()

    def on_message(self, ch, method, properties, body):
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
