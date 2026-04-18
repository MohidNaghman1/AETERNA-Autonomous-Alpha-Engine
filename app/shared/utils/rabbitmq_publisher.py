"""RabbitMQ publisher with connection pooling and retry logic.

Provides a thread-safe publisher with configurable connection pool,
automatic reconnection, and exponential backoff retry strategy.
"""

import pika
import threading
import time
import logging
from queue import Queue, Empty
import os


class RabbitMQPublisher:
    """RabbitMQ message publisher with connection pooling.

    Maintains a pool of reusable RabbitMQ connections to improve performance.
    Implements automatic reconnection and exponential backoff retry logic.
    Thread-safe for concurrent publishing.

    Supports both URL-based (CloudAMQP) and credential-based connections.

    Attributes:
        url: Optional RabbitMQ URL (CloudAMQP format)
        host: RabbitMQ server hostname (used if URL not provided)
        user: RabbitMQ username (used if URL not provided)
        password: RabbitMQ password (used if URL not provided)
        vhost: Virtual host name (used if URL not provided)
        queue_name: Target queue name
        pool_size: Maximum number of pooled connections
        retry_attempts: Number of retry attempts for failed publishes
    """

    def __init__(
        self,
        queue_name: str,
        url: str = None,
        host: str = None,
        user: str = "guest",
        password: str = "guest",
        vhost: str = "/",
        pool_size: int = 2,
        retry_attempts: int = 3,
    ):
        """Initialize RabbitMQ publisher with connection pool.

        Args:
            queue_name: Target queue name
            url: Optional RabbitMQ URL (CloudAMQP format: amqps://user:pass@host/vhost)
            host: RabbitMQ server hostname (fallback if URL not provided)
            user: RabbitMQ username (used if URL not provided)
            password: RabbitMQ password (used if URL not provided)
            vhost: Virtual host (used if URL not provided, default: "/")
            pool_size: Maximum connections in pool (default: 2)
            retry_attempts: Max retry attempts (default: 3)
        """
        self.url = url or os.getenv("RABBITMQ_URL")
        self.host = host or os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.user = user or os.getenv("RABBITMQ_USER", "guest")
        self.password = password or os.getenv("RABBITMQ_PASSWORD", "guest")
        self.vhost = vhost or os.getenv("RABBITMQ_VHOST", "/")
        self.queue_name = queue_name
        self.pool_size = pool_size
        self.retry_attempts = retry_attempts
        self._pool = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self.logger = logging.getLogger("rabbitmq-publisher")
        self._setup_pool()

    def _create_connection(self):
        """Create a RabbitMQ connection using either URL or credentials."""
        if self.url:
            try:
                self.logger.debug("Creating connection via URL")
                conn_params = pika.URLParameters(self.url)
                return pika.BlockingConnection([conn_params])
            except Exception as e:
                self.logger.warning(
                    f"URL connection failed: {e}, falling back to host-based"
                )

        # Fallback to host-based connection
        self.logger.debug(
            f"Creating connection to {self.host}:{self.port} vhost={self.vhost}"
        )
        conn = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.vhost,
                credentials=pika.PlainCredentials(self.user, self.password),
                heartbeat=600,
                blocked_connection_timeout=300,
            )
        )
        return conn

    def _setup_pool(self) -> None:
        """Initialize connection pool with configured size.

        Creates and stores RabbitMQ connections in the pool for reuse.
        Fails gracefully if RabbitMQ is unavailable during init.
        """
        try:
            for _ in range(self.pool_size):
                conn = self._create_connection()
                channel = conn.channel()
                channel.queue_declare(queue=self.queue_name, durable=True)
                self._pool.put((conn, channel))
            self.logger.info(
                f"Connection pool initialized with {self.pool_size} connections"
            )
        except pika.exceptions.AMQPConnectionError as e:
            self.logger.warning(
                f"Could not initialize RabbitMQ pool: {e}. "
                f"Will attempt to connect on first publish."
            )

    @staticmethod
    def _is_channel_usable(conn, channel) -> bool:
        """Return True when both connection and channel are open."""
        try:
            return bool(conn and channel and conn.is_open and channel.is_open)
        except Exception:
            return False

    def _create_connection_pair(self):
        """Create a fresh (connection, channel) pair with queue declared."""
        new_conn = self._create_connection()
        new_channel = new_conn.channel()
        new_channel.queue_declare(queue=self.queue_name, durable=True)
        return new_conn, new_channel

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

                # Heal stale pooled objects (e.g., broker closed socket/EOF).
                if not self._is_channel_usable(conn, channel):
                    try:
                        if conn and conn.is_open:
                            conn.close()
                    except Exception:
                        pass
                    conn, channel = self._create_connection_pair()

                try:
                    channel.basic_publish(
                        exchange="", routing_key=self.queue_name, body=body
                    )
                    self._pool.put((conn, channel))
                    return True
                except Exception as e:
                    self.logger.error(f"Publish failed: {e}")
                    try:
                        if conn and conn.is_open:
                            conn.close()
                    except Exception:
                        pass
                    # Create new connection to replace the failed one
                    try:
                        new_conn, new_channel = self._create_connection_pair()
                        self._pool.put((new_conn, new_channel))
                    except Exception as create_err:
                        self.logger.error(
                            f"Failed to create replacement connection: {create_err}"
                        )
                    time.sleep(2**attempt)
            except Empty:
                self.logger.error("No available RabbitMQ connections in pool.")
                # Pool may be empty after repeated failures - try to self-heal.
                try:
                    new_conn, new_channel = self._create_connection_pair()
                    self._pool.put((new_conn, new_channel))
                except Exception as create_err:
                    self.logger.error(
                        f"Failed to create connection while pool empty: {create_err}"
                    )
                time.sleep(2**attempt)
            except Exception as e:
                self.logger.error(f"Unexpected publisher error: {e}")
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
