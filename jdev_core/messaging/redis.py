"""
Redis Message Queue Implementation.

SCALE & SUSTAIN Phase 3.3 - Message Queue.

Redis-based message queue for production distributed systems.
Falls back to in-memory if Redis is not available.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .interface import (
    IMessageQueue,
    IMessageBroker,
    Message,
    MessageStatus,
    QueueConfig,
)

# Try to import redis
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False


@dataclass
class RedisConfig:
    """Redis connection configuration."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    max_connections: int = 10
    key_prefix: str = "jdev:mq:"

    @property
    def url(self) -> str:
        """Get Redis URL."""
        protocol = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{protocol}://{auth}{self.host}:{self.port}/{self.db}"


class RedisQueue(IMessageQueue):
    """
    Redis-based message queue implementation.

    Uses Redis lists for queue operations and sorted sets for delayed messages.

    Features:
    - Persistent messages
    - Delayed message delivery
    - Dead letter queue support
    - Message acknowledgment with visibility timeout
    """

    def __init__(self, config: QueueConfig, redis_config: RedisConfig):
        self._config = config
        self._redis_config = redis_config
        self._redis: Optional[Any] = None
        self._processing: Dict[str, Message] = {}

        # Key names
        self._prefix = redis_config.key_prefix
        self._queue_key = f"{self._prefix}queue:{config.name}"
        self._delayed_key = f"{self._prefix}delayed:{config.name}"
        self._processing_key = f"{self._prefix}processing:{config.name}"
        self._dlq_key = f"{self._prefix}dlq:{config.name}"

    async def connect(self) -> None:
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis package not installed. Install with: pip install redis")

        self._redis = aioredis.from_url(
            self._redis_config.url,
            socket_timeout=self._redis_config.socket_timeout,
            socket_connect_timeout=self._redis_config.socket_connect_timeout,
            max_connections=self._redis_config.max_connections,
            decode_responses=True
        )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is established."""
        if self._redis is None:
            await self.connect()

    async def publish(
        self,
        message: Message,
        delay: float = 0.0
    ) -> str:
        """Publish a message to the queue."""
        await self._ensure_connected()

        message.max_retries = self._config.max_retries
        message_data = json.dumps(message.to_dict())

        if delay > 0:
            # Add to delayed sorted set with score = delivery time
            delivery_time = time.time() + delay
            await self._redis.zadd(self._delayed_key, {message_data: delivery_time})
        else:
            # Add to main queue
            await self._redis.rpush(self._queue_key, message_data)

        return message.id

    async def consume(
        self,
        count: int = 1,
        timeout: float = 0.0
    ) -> List[Message]:
        """Consume messages from the queue."""
        await self._ensure_connected()

        # First, move any delayed messages that are now ready
        await self._process_delayed()

        messages = []

        for _ in range(count):
            try:
                if timeout > 0:
                    # Blocking pop with timeout
                    result = await self._redis.blpop(
                        self._queue_key,
                        timeout=timeout
                    )
                    if result:
                        _, message_data = result
                    else:
                        break
                else:
                    # Non-blocking pop
                    message_data = await self._redis.lpop(self._queue_key)
                    if not message_data:
                        break

                message = Message.from_dict(json.loads(message_data))
                message.mark_processing()

                # Store in processing set with visibility timeout
                visibility_timeout = time.time() + self._config.visibility_timeout
                await self._redis.zadd(
                    self._processing_key,
                    {json.dumps(message.to_dict()): visibility_timeout}
                )

                self._processing[message.id] = message
                messages.append(message)

            except Exception:
                break

        return messages

    async def _process_delayed(self) -> None:
        """Move delayed messages that are ready to main queue."""
        now = time.time()

        # Get all messages with score <= now
        ready_messages = await self._redis.zrangebyscore(
            self._delayed_key,
            '-inf',
            now
        )

        if ready_messages:
            # Move to main queue
            pipe = self._redis.pipeline()
            for msg in ready_messages:
                pipe.rpush(self._queue_key, msg)
            pipe.zremrangebyscore(self._delayed_key, '-inf', now)
            await pipe.execute()

    async def ack(self, message_id: str) -> bool:
        """Acknowledge message processing."""
        await self._ensure_connected()

        if message_id not in self._processing:
            return False

        message = self._processing.pop(message_id)
        message.mark_completed()

        # Remove from processing set
        # Need to find and remove the message
        processing_messages = await self._redis.zrange(self._processing_key, 0, -1)
        for msg_data in processing_messages:
            msg = Message.from_dict(json.loads(msg_data))
            if msg.id == message_id:
                await self._redis.zrem(self._processing_key, msg_data)
                break

        return True

    async def nack(
        self,
        message_id: str,
        requeue: bool = True
    ) -> bool:
        """Negative acknowledge message."""
        await self._ensure_connected()

        if message_id not in self._processing:
            return False

        message = self._processing.pop(message_id)
        message.mark_failed("Negative acknowledgement")

        # Remove from processing set
        processing_messages = await self._redis.zrange(self._processing_key, 0, -1)
        for msg_data in processing_messages:
            msg = Message.from_dict(json.loads(msg_data))
            if msg.id == message_id:
                await self._redis.zrem(self._processing_key, msg_data)
                break

        if message.status == MessageStatus.DEAD_LETTER:
            # Send to dead letter queue
            if self._config.dead_letter_queue:
                await self._redis.rpush(self._dlq_key, json.dumps(message.to_dict()))
        elif requeue:
            # Requeue with delay
            await self.publish(message, delay=self._config.retry_delay)

        return True

    async def size(self) -> int:
        """Get current queue size."""
        await self._ensure_connected()

        queue_size = await self._redis.llen(self._queue_key)
        delayed_size = await self._redis.zcard(self._delayed_key)
        return queue_size + delayed_size

    async def purge(self) -> int:
        """Purge all messages."""
        await self._ensure_connected()

        count = await self.size()

        pipe = self._redis.pipeline()
        pipe.delete(self._queue_key)
        pipe.delete(self._delayed_key)
        pipe.delete(self._processing_key)
        await pipe.execute()

        self._processing.clear()
        return count

    async def requeue_stale(self) -> int:
        """Requeue messages that exceeded visibility timeout."""
        await self._ensure_connected()

        now = time.time()

        # Get stale messages
        stale = await self._redis.zrangebyscore(
            self._processing_key,
            '-inf',
            now
        )

        if not stale:
            return 0

        # Requeue them
        pipe = self._redis.pipeline()
        for msg_data in stale:
            msg = Message.from_dict(json.loads(msg_data))
            msg.status = MessageStatus.PENDING
            pipe.rpush(self._queue_key, json.dumps(msg.to_dict()))
        pipe.zremrangebyscore(self._processing_key, '-inf', now)
        await pipe.execute()

        return len(stale)


class RedisBroker(IMessageBroker):
    """
    Redis-based message broker implementation.

    Provides queue management and pub/sub functionality using Redis.
    """

    def __init__(self, redis_config: Optional[RedisConfig] = None):
        self._redis_config = redis_config or RedisConfig()
        self._queues: Dict[str, RedisQueue] = {}
        self._subscriptions: Dict[str, tuple[str, Callable, Optional[str]]] = {}
        self._pubsub: Optional[Any] = None
        self._redis: Optional[Any] = None
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None

    async def _ensure_connected(self) -> None:
        """Ensure Redis connection."""
        if self._redis is None:
            if not REDIS_AVAILABLE:
                raise RuntimeError("redis package not installed")

            self._redis = aioredis.from_url(
                self._redis_config.url,
                decode_responses=True
            )

    async def create_queue(self, config: QueueConfig) -> IMessageQueue:
        """Create or get a queue."""
        if config.name not in self._queues:
            queue = RedisQueue(config, self._redis_config)
            await queue.connect()
            self._queues[config.name] = queue
        return self._queues[config.name]

    async def delete_queue(self, name: str) -> bool:
        """Delete a queue."""
        if name in self._queues:
            await self._queues[name].purge()
            await self._queues[name].disconnect()
            del self._queues[name]
            return True
        return False

    async def get_queue(self, name: str) -> Optional[IMessageQueue]:
        """Get an existing queue."""
        return self._queues.get(name)

    async def list_queues(self) -> List[str]:
        """List all queue names."""
        return list(self._queues.keys())

    async def subscribe(
        self,
        topic: str,
        handler: Callable[[Message], Any],
        queue_name: Optional[str] = None
    ) -> str:
        """Subscribe to a topic using Redis pub/sub."""
        await self._ensure_connected()

        subscription_id = str(uuid.uuid4())
        self._subscriptions[subscription_id] = (topic, handler, queue_name)

        # Start listener if not running
        if not self._running:
            await self._start_listener()

        # Subscribe to Redis channel
        if self._pubsub is None:
            self._pubsub = self._redis.pubsub()

        await self._pubsub.subscribe(topic)

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        if subscription_id not in self._subscriptions:
            return False

        topic, _, _ = self._subscriptions.pop(subscription_id)

        # Check if any other subscriptions use this topic
        topics_in_use = {t for t, _, _ in self._subscriptions.values()}
        if topic not in topics_in_use and self._pubsub:
            await self._pubsub.unsubscribe(topic)

        return True

    async def publish(
        self,
        topic: str,
        payload: Any,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """Publish to a topic."""
        await self._ensure_connected()

        message = Message(
            topic=topic,
            payload=payload,
            headers=headers or {}
        )

        await self._redis.publish(topic, json.dumps(message.to_dict()))
        return message.id

    async def _start_listener(self) -> None:
        """Start the pub/sub listener."""
        if self._running:
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self) -> None:
        """Listen for pub/sub messages."""
        while self._running and self._pubsub:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                if message and message['type'] == 'message':
                    await self._dispatch_message(
                        message['channel'],
                        message['data']
                    )
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.1)

    async def _dispatch_message(self, channel: str, data: str) -> None:
        """Dispatch received message to handlers."""
        try:
            msg = Message.from_dict(json.loads(data))
        except (json.JSONDecodeError, KeyError):
            return

        for sub_id, (topic, handler, queue_name) in self._subscriptions.items():
            if topic == channel:
                try:
                    result = handler(msg)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    pass  # Log in production

    async def close(self) -> None:
        """Close the broker."""
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            await self._pubsub.close()

        for queue in self._queues.values():
            await queue.disconnect()

        if self._redis:
            await self._redis.close()

        self._queues.clear()
        self._subscriptions.clear()


__all__ = [
    'RedisQueue',
    'RedisBroker',
    'RedisConfig',
    'REDIS_AVAILABLE',
]
