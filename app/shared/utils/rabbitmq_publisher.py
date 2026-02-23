import pika
import threading
import time
import logging
from queue import Queue, Empty

class RabbitMQPublisher:
    def __init__(self, host, user, password, queue_name, pool_size=2, retry_attempts=3):
        self.host = host
        self.user = user
        self.password = password
        self.queue_name = queue_name
        self.pool_size = pool_size
        self.retry_attempts = retry_attempts
        self._pool = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._setup_pool()
        self.logger = logging.getLogger("rabbitmq-publisher")

    def _setup_pool(self):
        for _ in range(self.pool_size):
            conn = pika.BlockingConnection(pika.ConnectionParameters(
                host=self.host,
                credentials=pika.PlainCredentials(self.user, self.password),
                heartbeat=600,
                blocked_connection_timeout=300
            ))
            channel = conn.channel()
            channel.queue_declare(queue=self.queue_name, durable=True)
            self._pool.put((conn, channel))

    def publish(self, body):
        for attempt in range(self.retry_attempts):
            try:
                conn, channel = self._pool.get(timeout=5)
                try:
                    channel.basic_publish(
                        exchange='',
                        routing_key=self.queue_name,
                        body=body
                    )
                    self._pool.put((conn, channel))
                    return True
                except Exception as e:
                    self.logger.error(f"Publish failed: {e}")
                    # Try to reconnect this slot
                    try:
                        conn.close()
                    except Exception:
                        pass
                    new_conn = pika.BlockingConnection(pika.ConnectionParameters(
                        host=self.host,
                        credentials=pika.PlainCredentials(self.user, self.password),
                        heartbeat=600,
                        blocked_connection_timeout=300
                    ))
                    new_channel = new_conn.channel()
                    new_channel.queue_declare(queue=self.queue_name, durable=True)
                    self._pool.put((new_conn, new_channel))
                    time.sleep(2 ** attempt)
            except Empty:
                self.logger.error("No available RabbitMQ connections in pool.")
                time.sleep(2 ** attempt)
        self.logger.error("Failed to publish after retries.")
        return False

    def close(self):
        while not self._pool.empty():
            conn, _ = self._pool.get()
            try:
                conn.close()
            except Exception:
                pass
