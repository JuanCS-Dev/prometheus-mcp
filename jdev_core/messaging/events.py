"""
Event Bus System.

SCALE & SUSTAIN Phase 3.3 - Message Queue.

Simple event bus for intra-process communication.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar


@dataclass
class Event:
    """Base event class."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """Get event type name."""
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'type': self.event_type,
            'timestamp': self.timestamp,
            'source': self.source,
            'data': self.data,
        }


E = TypeVar('E', bound=Event)
EventHandler = Callable[[E], Any]


class EventBus:
    """
    Simple async event bus.

    Usage:
        bus = EventBus()

        @bus.on(UserCreatedEvent)
        async def handle_user_created(event: UserCreatedEvent):
            print(f"User created: {event.data['username']}")

        await bus.emit(UserCreatedEvent(data={'username': 'john'}))
    """

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._lock = asyncio.Lock()
        self._event_history: List[Event] = []
        self._max_history: int = 1000

    def on(
        self,
        event_type: Optional[Type[Event]] = None
    ) -> Callable[[EventHandler], EventHandler]:
        """
        Decorator to register an event handler.

        Args:
            event_type: Event type to handle. If None, handles all events.

        Returns:
            Decorator function
        """
        def decorator(handler: EventHandler) -> EventHandler:
            if event_type is None:
                self._wildcard_handlers.append(handler)
            else:
                type_name = event_type.__name__
                if type_name not in self._handlers:
                    self._handlers[type_name] = []
                self._handlers[type_name].append(handler)
            return handler
        return decorator

    def subscribe(
        self,
        event_type: Type[Event],
        handler: EventHandler
    ) -> str:
        """
        Subscribe to an event type.

        Args:
            event_type: Event type to handle
            handler: Handler function

        Returns:
            Subscription ID
        """
        type_name = event_type.__name__
        if type_name not in self._handlers:
            self._handlers[type_name] = []
        self._handlers[type_name].append(handler)
        return f"{type_name}:{id(handler)}"

    def unsubscribe(
        self,
        event_type: Type[Event],
        handler: EventHandler
    ) -> bool:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Event type
            handler: Handler function

        Returns:
            True if unsubscribed
        """
        type_name = event_type.__name__
        if type_name in self._handlers:
            try:
                self._handlers[type_name].remove(handler)
                return True
            except ValueError:
                pass
        return False

    async def emit(
        self,
        event: Event,
        wait: bool = True
    ) -> List[Any]:
        """
        Emit an event to all subscribers.

        Args:
            event: Event to emit
            wait: Whether to wait for handlers to complete

        Returns:
            List of handler results (if wait=True)
        """
        # Store in history
        async with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]

        # Get handlers for this event type
        type_name = event.event_type
        handlers = self._handlers.get(type_name, []) + self._wildcard_handlers

        if not handlers:
            return []

        # Create tasks for all handlers
        tasks = []
        for handler in handlers:
            task = self._invoke_handler(handler, event)
            tasks.append(task)

        if wait:
            return await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for task in tasks:
                asyncio.create_task(task)
            return []

    async def _invoke_handler(
        self,
        handler: EventHandler,
        event: Event
    ) -> Any:
        """Invoke a handler safely."""
        try:
            result = handler(event)
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            # Log error in production
            return e

    def emit_sync(self, event: Event) -> None:
        """
        Emit event without waiting (fire and forget).

        Args:
            event: Event to emit
        """
        asyncio.create_task(self.emit(event, wait=False))

    def get_history(
        self,
        event_type: Optional[Type[Event]] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Get recent event history.

        Args:
            event_type: Filter by event type
            limit: Maximum events to return

        Returns:
            List of recent events
        """
        if event_type:
            type_name = event_type.__name__
            events = [e for e in self._event_history if e.event_type == type_name]
        else:
            events = self._event_history

        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()

    @property
    def handler_count(self) -> int:
        """Get total number of registered handlers."""
        count = len(self._wildcard_handlers)
        for handlers in self._handlers.values():
            count += len(handlers)
        return count


def event_handler(
    event_type: Type[Event]
) -> Callable[[EventHandler], EventHandler]:
    """
    Decorator to mark a function as an event handler.

    Usage:
        @event_handler(UserCreatedEvent)
        async def handle_user_created(event: UserCreatedEvent):
            print(f"User: {event.data['username']}")

    Note: Must be registered with an EventBus to be active.
    """
    def decorator(func: EventHandler) -> EventHandler:
        func._event_type = event_type
        return func
    return decorator


# Common event types
@dataclass
class SystemEvent(Event):
    """System-level event."""
    pass


@dataclass
class TaskStartedEvent(Event):
    """Task started event."""
    pass


@dataclass
class TaskCompletedEvent(Event):
    """Task completed event."""
    pass


@dataclass
class TaskFailedEvent(Event):
    """Task failed event."""
    pass


@dataclass
class AgentMessageEvent(Event):
    """Agent message event."""
    pass


# Global event bus
_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


__all__ = [
    'Event',
    'EventBus',
    'EventHandler',
    'event_handler',
    'SystemEvent',
    'TaskStartedEvent',
    'TaskCompletedEvent',
    'TaskFailedEvent',
    'AgentMessageEvent',
    'get_event_bus',
]
