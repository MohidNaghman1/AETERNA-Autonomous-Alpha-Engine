"""RabbitMQ publisher with connection pooling and retry logic.

Provides a thread-safe publisher with configurable connection pool,
automatic reconnection, and exponential backoff retry strategy.
"""

import pika
import threading
import time
import logging
from queue import Queue, Empty


class RabbitMQPublisher:
    """RabbitMQ message publisher with connection pooling.

    Maintains a pool of reusable RabbitMQ connections to improve performance.
    Implements automatic reconnection and exponential backoff retry logic.
    Thread-safe for concurrent publishing.

    Attributes:
        host: RabbitMQ server hostname
        user: RabbitMQ username
        password: RabbitMQ password
        queue_name: Target queue name
        pool_size: Maximum number of pooled connections
        retry_attempts: Number of retry attempts for failed publishes
    """

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        queue_name: str,
        pool_size: int = 2,
        retry_attempts: int = 3,
    ):
        """Initialize RabbitMQ publisher with connection pool.

        Args:
            host: RabbitMQ server hostname
            user: RabbitMQ username
            password: RabbitMQ password
            queue_name: Target queue name
            pool_size: Maximum connections in pool (default: 2)
            retry_attempts: Max retry attempts (default: 3)
        """
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

    def _setup_pool(self) -> None:
        """Initialize connection pool with configured size.

        Creates and stores RabbitMQ connections in the pool for reuse.
        """
        for _ in range(self.pool_size):
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host,
                    credentials=pika.PlainCredentials(self.user, self.password),
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
            )
            channel = conn.channel()
            channel.queue_declare(queue=self.queue_name, durable=True)
            self._pool.put((conn, channel))

    def publish(self, body: str) -> bool:
        """Publish message to queue with retries and auto-reconnection.

        Attempts to publish with exponential backoff retry logic.
        Automatically reconnects failed connections.

        Args:
            body: Message content to publish

        Returns:
            bool: True if published successfully, False after all retries exhausted
        """
        for attempt in range(self.retry_attempts):
            try:
                conn, channel = self._pool.get(timeout=5)
                try:
                    channel.basic_publish(exchange="", routing_key=self.queue_name, body=body)
                    self._pool.put((conn, channel))
                    return True
                except Exception as e:
                    self.logger.error(f"Publish failed: {e}")
                    try:
                        conn.close()
                    except Exception:
                        pass
                    new_conn = pika.BlockingConnection(
                        pika.ConnectionParameters(
                            host=self.host,
                            credentials=pika.PlainCredentials(self.user, self.password),
                            heartbeat=600,
                            blocked_connection_timeout=300,
                        )
                    )
                    new_channel = new_conn.channel()
                    new_channel.queue_declare(queue=self.queue_name, durable=True)
                    self._pool.put((new_conn, new_channel))
                    time.sleep(2**attempt)
            except Empty:
                self.logger.error("No available RabbitMQ connections in pool.")
                time.sleep(2**attempt)
        self.logger.error("Failed to publish after retries.")
        return False

    def close(self) -> None:
        """Close all connections in the pool.

        Safely closes all pooled connections. Exceptions during close
        are caught and logged but do not raise.
        """
        while not self._pool.empty():
            conn, _ = self._pool.get()
            try:
                conn.close()
            except Exception:
                pass
