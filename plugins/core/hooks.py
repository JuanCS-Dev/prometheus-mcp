"""
Plugin Hooks.

SCALE & SUSTAIN Phase 2.1 - Plugin Architecture.

Defines the hook system for plugin communication:
- HookType: Standard hook types
- PluginHook: Decorator for registering hook handlers
- HookResult: Result wrapper for hook execution

Author: JuanCS Dev
Date: 2025-11-26
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from functools import wraps

T = TypeVar('T')


class HookType(Enum):
    """Standard plugin hook types."""
    # Lifecycle hooks
    PRE_ACTIVATE = auto()
    POST_ACTIVATE = auto()
    PRE_DEACTIVATE = auto()
    POST_DEACTIVATE = auto()

    # Command hooks
    PRE_COMMAND = auto()
    POST_COMMAND = auto()
    COMMAND_ERROR = auto()

    # Tool hooks
    PRE_TOOL_EXECUTE = auto()
    POST_TOOL_EXECUTE = auto()
    TOOL_ERROR = auto()

    # Message hooks
    PRE_MESSAGE = auto()
    POST_MESSAGE = auto()

    # LLM hooks
    PRE_LLM_CALL = auto()
    POST_LLM_CALL = auto()
    LLM_STREAM_CHUNK = auto()

    # File hooks
    FILE_READ = auto()
    FILE_WRITE = auto()
    FILE_DELETE = auto()

    # Session hooks
    SESSION_START = auto()
    SESSION_END = auto()

    # Custom hooks
    CUSTOM = auto()


@dataclass
class HookResult(Generic[T]):
    """
    Result wrapper for hook execution.

    Attributes:
        success: Whether hook executed successfully
        data: Result data
        error: Error message if failed
        stop_propagation: If True, don't call remaining hooks
        modified_input: Modified input to pass to next hooks
    """
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    stop_propagation: bool = False
    modified_input: Optional[Any] = None

    @classmethod
    def ok(cls, data: T = None) -> 'HookResult[T]':
        """Create successful result."""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> 'HookResult[T]':
        """Create failed result."""
        return cls(success=False, error=error)

    @classmethod
    def stop(cls, data: T = None) -> 'HookResult[T]':
        """Create result that stops propagation."""
        return cls(success=True, data=data, stop_propagation=True)

    @classmethod
    def modify(cls, modified_input: Any) -> 'HookResult[T]':
        """Create result with modified input."""
        return cls(success=True, modified_input=modified_input)


@dataclass
class HookRegistration:
    """Internal hook registration."""
    hook_type: HookType
    handler: Callable
    priority: int = 0
    plugin_name: Optional[str] = None


class HookRegistry:
    """
    Registry for plugin hooks.

    Manages hook registration and dispatch.
    """

    def __init__(self):
        self._hooks: Dict[HookType, List[HookRegistration]] = {}

    def register(
        self,
        hook_type: HookType,
        handler: Callable,
        priority: int = 0,
        plugin_name: Optional[str] = None
    ) -> None:
        """
        Register a hook handler.

        Args:
            hook_type: Type of hook
            handler: Handler function
            priority: Lower = higher priority
            plugin_name: Owning plugin name
        """
        if hook_type not in self._hooks:
            self._hooks[hook_type] = []

        registration = HookRegistration(
            hook_type=hook_type,
            handler=handler,
            priority=priority,
            plugin_name=plugin_name
        )

        self._hooks[hook_type].append(registration)
        self._hooks[hook_type].sort(key=lambda r: r.priority)

    def unregister(self, plugin_name: str) -> int:
        """
        Unregister all hooks for a plugin.

        Returns:
            Number of hooks removed
        """
        count = 0
        for hook_type in self._hooks:
            before = len(self._hooks[hook_type])
            self._hooks[hook_type] = [
                r for r in self._hooks[hook_type]
                if r.plugin_name != plugin_name
            ]
            count += before - len(self._hooks[hook_type])
        return count

    async def dispatch(
        self,
        hook_type: HookType,
        *args,
        **kwargs
    ) -> List[HookResult]:
        """
        Dispatch hook to all registered handlers.

        Args:
            hook_type: Type of hook to dispatch
            *args, **kwargs: Arguments to pass to handlers

        Returns:
            List of results from handlers
        """
        results = []
        handlers = self._hooks.get(hook_type, [])

        current_args = args
        current_kwargs = kwargs

        for registration in handlers:
            try:
                result = registration.handler(*current_args, **current_kwargs)

                # Handle async handlers
                if hasattr(result, '__await__'):
                    result = await result

                # Wrap raw results
                if not isinstance(result, HookResult):
                    result = HookResult.ok(result)

                results.append(result)

                # Check for propagation stop
                if result.stop_propagation:
                    break

                # Apply input modifications
                if result.modified_input is not None:
                    if isinstance(result.modified_input, tuple):
                        current_args = result.modified_input
                    elif isinstance(result.modified_input, dict):
                        current_kwargs = result.modified_input

            except Exception as e:
                results.append(HookResult.fail(str(e)))

        return results

    def get_handlers(self, hook_type: HookType) -> List[HookRegistration]:
        """Get registered handlers for a hook type."""
        return list(self._hooks.get(hook_type, []))


def PluginHook(
    hook_type: HookType,
    priority: int = 0
) -> Callable:
    """
    Decorator for registering plugin hook handlers.

    Usage:
        class MyPlugin(Plugin):
            @PluginHook(HookType.PRE_COMMAND)
            def before_command(self, command: str, args: str):
                # Modify or intercept command
                return HookResult.ok()

            @PluginHook(HookType.POST_LLM_CALL, priority=10)
            async def after_llm(self, response: str):
                # Process LLM response
                return HookResult.modify(response.upper())
    """
    def decorator(func: Callable) -> Callable:
        # Store hook metadata on function
        func._plugin_hook = {
            'type': hook_type,
            'priority': priority
        }

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._plugin_hook = func._plugin_hook
        return wrapper

    return decorator


__all__ = [
    'HookType',
    'HookResult',
    'HookRegistry',
    'HookRegistration',
    'PluginHook',
]
