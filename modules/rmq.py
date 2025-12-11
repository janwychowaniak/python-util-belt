"""
RabbitMQ JSON messaging - Simple producer/consumer for JSON payloads.

This module provides simple, reliable JSON message passing via RabbitMQ.
Specialized for dict-to-dict messaging with flexible authentication and
configurable logging.

Key Features:
    - JSON-only payloads (send dict, receive dict)
    - One-shot send function for infrequent messages
    - Persistent connection class for high-frequency sending
    - Blocking consumer with manual acknowledgment and retry
    - Flexible authentication (explicit username/password or guest default)
    - Configurable logging (stdlib, loguru, or custom)
    - Automatic queue declaration
    - Connection health checking and error recovery

External Dependency:
    - Requires 'pika' library: pip install pika
    - This is the ONLY module in python-util-belt with external dependencies
    - Pragmatic choice: RabbitMQ functionality requires AMQP client

Basic Usage (Producer):
    >>> from rmq import send_json
    >>> send_json({'task': 'process', 'id': 123}, 'work_queue')
    True

    >>> send_json({'data': [1, 2, 3]}, 'tasks', host='rmq.prod.com')
    True

Persistent Producer (High Frequency):
    >>> from rmq import RMQProducer
    >>> with RMQProducer('tasks', host='localhost') as producer:
    ...     producer.send({'task': 'first'})
    ...     producer.send({'task': 'second'})
    True
    True

Consumer (Blocking):
    >>> from rmq import consume_json
    >>> def process(data: dict):
    ...     print(f"Task: {data['task']}")
    >>> consume_json('work_queue', process)  # Blocks forever

Authentication:
    # Default: guest/guest
    >>> send_json(data, queue)

    # Explicit username/password
    >>> send_json(data, queue, username='worker', password='pass123')

    # Persistent producer with auth
    >>> producer = RMQProducer('tasks', username='admin', password='secret')
    >>> producer.send(data)

Custom Logging:
    >>> from loguru import logger
    >>> send_json(data, queue, logger=logger)
    >>>
    >>> producer = RMQProducer('tasks', logger=logger)
    >>> producer.send(data)

Development/Testing (Disabled Producer):
    >>> producer = RMQProducer('tasks', enabled=False)
    >>> producer.send(data)  # Logs warning, no actual send
    True

Environment Variables:
    None (can be added in future if needed)

Functions:
    send_json(data, queue, host='localhost', **kwargs) -> bool
        One-shot JSON message sender

    RMQProducer(queue, host='localhost', **kwargs)
        Persistent connection producer class

    consume_json(queue, callback, host='localhost', **kwargs)
        Blocking consumer (auto-start, blocks forever)

Notes:
    - All functions use dict-to-dict JSON messaging (no raw bytes)
    - Consumer uses manual acknowledgment (ack after success, nack+requeue on failure)
    - Payloads over 1MB trigger warnings
    - Connections use heartbeat (default 600s producers, 1200s consumers)
    - Auto-reconnect NOT implemented (caller should retry on False)

Author: Jan 🪄
Version: 1.0
"""

import json
import logging
from typing import Optional, Any, Callable

try:
    import pika
    from pika.exceptions import AMQPConnectionError, AMQPChannelError
except ImportError:
    raise ImportError(
        "rmq module requires 'pika' library. Install with: pip install pika"
    )


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Private helper functions


def _get_connection_params(
    host: str,
    port: int = 5672,
    virtual_host: str = "/",
    username: Optional[str] = None,
    password: Optional[str] = None,
    heartbeat: int = 600,
    logger: Optional[Any] = None
) -> pika.ConnectionParameters:
    """
    Build pika ConnectionParameters with flexible authentication.

    Priority: explicit params > guest/guest default

    Args:
        host: RabbitMQ broker hostname
        port: RabbitMQ broker port
        virtual_host: Virtual host name
        username: Optional explicit username
        password: Optional explicit password
        heartbeat: Heartbeat interval in seconds
        logger: Logger instance

    Returns:
        pika.ConnectionParameters object
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Priority 1: Explicit parameters
    if username and password:
        credentials = pika.PlainCredentials(username, password)
        logger.debug(f"Using explicit credentials for {username}@{host}")
    else:
        # Priority 2: Default guest/guest
        credentials = pika.PlainCredentials("guest", "guest")
        logger.debug(f"Using default guest credentials for {host}")

    return pika.ConnectionParameters(
        host=host,
        port=port,
        virtual_host=virtual_host,
        credentials=credentials,
        heartbeat=heartbeat
    )


def _serialize_json(data: dict, logger: Any) -> Optional[str]:
    """
    Serialize dict to JSON string with error handling.

    Args:
        data: Dictionary to serialize
        logger: Logger instance

    Returns:
        JSON string, or None on error
    """
    try:
        # Serialize with compact encoding, preserve Unicode
        payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

        # Warn on large payloads (>1MB)
        size_bytes = len(payload.encode("utf-8"))
        if size_bytes > 1_000_000:
            size_mb = size_bytes / 1_000_000
            logger.warning(f"Large payload: {size_mb:.2f}MB (consider chunking)")

        return payload

    except (TypeError, ValueError) as e:
        logger.error(f"JSON serialization failed: {e}")
        return None


def _deserialize_json(body: bytes, logger: Any) -> Optional[dict]:
    """
    Deserialize JSON bytes to dict with error handling.

    Args:
        body: Raw message body (bytes)
        logger: Logger instance

    Returns:
        Dictionary, or None on error
    """
    try:
        # Decode bytes to string
        text = body.decode("utf-8")

        # Parse JSON
        data = json.loads(text)

        # Validate it's a dict
        if not isinstance(data, dict):
            logger.error(f"Expected dict, got {type(data).__name__}: {text[:100]}")
            return None

        return data

    except UnicodeDecodeError as e:
        logger.error(f"Invalid UTF-8 encoding: {e}")
        return None

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e} - Body: {body[:100]}")
        return None


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Producer functions (one-shot)


def send_json(
    data: dict,
    queue: str,
    host: str = "localhost",
    port: int = 5672,
    virtual_host: str = "/",
    username: Optional[str] = None,
    password: Optional[str] = None,
    declare_queue: bool = True,
    timeout: float = 5.0,
    logger: Optional[Any] = None
) -> bool:
    """
    Send a JSON message to RabbitMQ queue (one-shot connection).

    Opens connection, sends message, closes connection. Suitable for
    infrequent sends. For high-frequency sending, use RMQProducer class.

    Args:
        data: Dictionary to send as JSON payload
        queue: Target queue name
        host: RabbitMQ broker hostname
        port: RabbitMQ broker port
        virtual_host: Virtual host name
        username: Authentication username (overrides default)
        password: Authentication password (overrides default)
        declare_queue: Auto-declare queue if it doesn't exist
        timeout: Connection timeout in seconds (unused, for future)
        logger: Optional logger instance (defaults to stdlib logging)

    Returns:
        True if message sent successfully, False otherwise

    Examples:
        >>> send_json({'task': 'process'}, 'work_queue')
        True

        >>> send_json({'data': [1,2,3]}, 'tasks', host='rmq.prod.com',
        ...           username='worker', password='secret')
        True
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Input validation
    if not isinstance(data, dict):
        logger.error(f"send_json() requires dict, got {type(data).__name__}")
        return False

    try:
        # Serialize to JSON
        payload = _serialize_json(data, logger)
        if payload is None:
            return False

        # Build connection params (heartbeat=0 for one-shot)
        params = _get_connection_params(
            host, port, virtual_host, username, password,
            heartbeat=0,
            logger=logger
        )

        # Connect and send
        with pika.BlockingConnection(params) as connection:
            channel = connection.channel()

            if declare_queue:
                channel.queue_declare(queue=queue)
                logger.debug(f"Queue '{queue}' declared")

            channel.basic_publish(
                exchange="",
                routing_key=queue,
                body=payload
            )

            logger.info(f"Sent {len(data)} keys to {host}/{queue}")
            return True

    except AMQPConnectionError as e:
        logger.error(f"Connection failed to {host}:{port}: {e}")
        return False

    except AMQPChannelError as e:
        logger.error(f"Channel error on {queue}: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error sending to {queue}: {e}")
        return False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Producer class (persistent connection)


class RMQProducer:
    """
    Persistent connection producer for efficient multiple sends.

    Maintains open connection across multiple send operations. More efficient
    than send_json() for high-frequency sending. Connection is reused until
    explicitly closed or context manager exits.

    Examples:
        # Context manager (recommended)
        >>> with RMQProducer('tasks', host='rmq.local') as producer:
        ...     producer.send({'task': 'first'})
        ...     producer.send({'task': 'second'})
        True
        True

        # Manual lifecycle
        >>> producer = RMQProducer('work_queue')
        >>> producer.connect()
        >>> producer.send({'data': 123})
        >>> producer.close()
        True

        # Disabled producer (for testing/development)
        >>> producer = RMQProducer('tasks', enabled=False)
        >>> producer.send({'data': 'test'})  # Logs warning, returns True
        True
    """

    def __init__(
        self,
        queue: str,
        host: str = "localhost",
        port: int = 5672,
        virtual_host: str = "/",
        username: Optional[str] = None,
        password: Optional[str] = None,
        declare_queue: bool = True,
        heartbeat: int = 600,
        enabled: bool = True,
        logger: Optional[Any] = None
    ):
        """
        Initialize producer (connection opened on first send or explicit connect()).

        Args:
            queue: Target queue name
            host: RabbitMQ broker hostname
            port: RabbitMQ broker port
            virtual_host: Virtual host name
            username: Authentication username
            password: Authentication password
            declare_queue: Auto-declare queue on connect
            heartbeat: Heartbeat interval in seconds (0 = disabled)
            enabled: If False, send() logs warning and no-ops (for dev/testing)
            logger: Optional logger instance
        """
        self.queue = queue
        self.host = host
        self.enabled = enabled
        self.declare_queue = declare_queue
        self._logger = logger or logging.getLogger(__name__)

        # Connection state
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel = None

        # Store params for lazy connection
        self._params = _get_connection_params(
            host, port, virtual_host, username, password,
            heartbeat, self._logger
        )

    def connect(self) -> bool:
        """
        Explicitly open connection (lazy - also happens on first send()).

        Returns:
            True if connected, False on error
        """
        if not self.enabled:
            self._logger.warning(f"Producer disabled: {self.host}/{self.queue}")
            return False

        if self._connection and self._connection.is_open:
            self._logger.debug("Connection already open")
            return True

        try:
            self._connection = pika.BlockingConnection(self._params)
            self._channel = self._connection.channel()

            if self.declare_queue:
                self._channel.queue_declare(queue=self.queue)
                self._logger.debug(f"Queue '{self.queue}' declared")

            self._logger.info(f"Connected to {self.host}/{self.queue}")
            return True

        except AMQPConnectionError as e:
            self._logger.error(f"Connection failed: {e}")
            return False

    def send(self, data: dict) -> bool:
        """
        Send JSON message (opens connection if needed).

        Args:
            data: Dictionary to send as JSON

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            self._logger.warning(f"Send disabled to {self.host}/{self.queue}")
            return True  # Considered "success" for enabled=False mode

        # Validate input
        if not isinstance(data, dict):
            self._logger.error(f"send() requires dict, got {type(data).__name__}")
            return False

        # Ensure connected
        if not self._connection or not self._connection.is_open:
            if not self.connect():
                return False

        try:
            payload = _serialize_json(data, self._logger)
            if payload is None:
                return False

            self._channel.basic_publish(
                exchange="",
                routing_key=self.queue,
                body=payload
            )

            self._logger.info(f"Sent {len(data)} keys to {self.queue}")
            return True

        except AMQPChannelError as e:
            self._logger.error(f"Channel error: {e}")
            return False

        except Exception as e:
            self._logger.error(f"Send error: {e}")
            return False

    def close(self):
        """Close connection gracefully."""
        if self._connection and self._connection.is_open:
            self._connection.close()
            self._logger.debug(f"Connection closed to {self.host}")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Consumer function


def consume_json(
    queue: str,
    callback: Callable[[dict], None],
    host: str = "localhost",
    port: int = 5672,
    virtual_host: str = "/",
    username: Optional[str] = None,
    password: Optional[str] = None,
    heartbeat: int = 1200,
    logger: Optional[Any] = None
):
    """
    Blocking consumer for JSON messages with manual acknowledgment.

    Automatically starts consuming, blocks forever. Messages are acknowledged
    AFTER successful callback execution, providing natural retry on failure.

    Args:
        queue: Queue name to consume from
        callback: Function(data: dict) to process messages
        host: RabbitMQ broker hostname
        port: RabbitMQ broker port
        virtual_host: Virtual host name
        username: Authentication username
        password: Authentication password
        heartbeat: Heartbeat interval in seconds
        logger: Optional logger instance

    Examples:
        >>> def process_task(data: dict):
        ...     print(f"Processing: {data['task']}")
        ...     time.sleep(1)
        ...     # Message acked here after successful processing

        >>> consume_json('work_queue', process_task)
        # Blocks forever, processing messages

    Note:
        This function blocks indefinitely. Use Ctrl+C to stop (or wrap in
        catch_signals.assist_signals() for graceful shutdown).

        Messages are acknowledged AFTER callback completes successfully.
        If callback raises exception, message is NOT acknowledged and will
        be redelivered (natural retry mechanism).
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    params = _get_connection_params(
        host, port, virtual_host, username, password, heartbeat, logger
    )

    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=queue)

    # Wrapper to deserialize JSON, call callback, then ack (or nack+requeue, if callback fails)
    def _internal_callback(ch, method, properties, body):
        data = _deserialize_json(body, logger)
        if data is None:
            # JSON parse failed - reject message (don't requeue)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            logger.warning("Message with invalid JSON rejected (not requeued)")
            return

        try:
            # Execute user callback
            callback(data)

            # Acknowledge AFTER successful processing
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            # Callback failed - nack with requeue for immediate retry
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            logger.error(f"Callback failed, message requeued for retry: {e}")

    channel.basic_consume(
        queue=queue,
        on_message_callback=_internal_callback,
        auto_ack=False  # Manual acknowledgment
    )

    logger.info(f"Starting consumer on {host}/{queue} (Ctrl+C to stop)")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.warning("Consumer stopped by user")
        channel.stop_consuming()
