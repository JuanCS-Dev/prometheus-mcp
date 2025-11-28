"""
Plugin Base Classes.

SCALE & SUSTAIN Phase 2.1 - Plugin Architecture.

Defines the core abstractions for the plugin system:
- Plugin: Abstract base class for all plugins
- PluginMetadata: Plugin information and dependencies
- PluginContext: Runtime context passed to plugins
- PluginState: Lifecycle state tracking

Author: JuanCS Dev
Date: 2025-11-26
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .registry import PluginRegistry


class PluginPriority(Enum):
    """Plugin loading priority."""
    CORE = 0        # System core, always loads first
    HIGH = 100      # Important plugins
    NORMAL = 500    # Standard plugins
    LOW = 900       # Optional plugins
    LAZY = 1000     # Load on demand only


class PluginState(Enum):
    """Plugin lifecycle state."""
    UNLOADED = auto()
    LOADING = auto()
    ACTIVE = auto()
    ERROR = auto()
    DEACTIVATING = auto()
    DISABLED = auto()


@dataclass
class PluginMetadata:
    """
    Plugin metadata and dependency information.

    Attributes:
        name: Unique plugin identifier (kebab-case recommended)
        version: Semantic version string
        description: Human-readable description
        author: Plugin author name
        priority: Loading priority
        dependencies: List of required plugin names
        provides: List of capabilities this plugin provides
        config_schema: Optional JSON schema for plugin config
    """
    name: str
    version: str
    description: str
    author: str
    priority: PluginPriority = PluginPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate metadata."""
        if not self.name:
            raise ValueError("Plugin name cannot be empty")
        if not self.version:
            raise ValueError("Plugin version cannot be empty")


@dataclass
class PluginContext:
    """
    Runtime context provided to plugins during activation.

    Provides access to:
    - Configuration
    - Service locator for other plugins
    - Event bus for inter-plugin communication
    - Logger
    """
    config: Dict[str, Any] = field(default_factory=dict)
    registry: Optional['PluginRegistry'] = None
    logger: Optional[Any] = None
    event_bus: Optional[Any] = None

    def get_plugin(self, name: str) -> Optional['Plugin']:
        """Get another plugin by name."""
        if self.registry:
            return self.registry.get(name)
        return None

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)


class Plugin(ABC):
    """
    Abstract base class for all plugins.

    Lifecycle:
        1. Plugin discovered by PluginLoader
        2. Dependencies resolved
        3. activate() called with PluginContext
        4. Plugin is now active and can respond to hooks
        5. deactivate() called on shutdown

    Example:
        class GitPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="git",
                    version="1.0.0",
                    description="Git integration",
                    author="JuanCS",
                    provides=["vcs", "git"]
                )

            async def activate(self, context: PluginContext) -> None:
                self.context = context
                # Register commands, tools, etc.

            async def deactivate(self) -> None:
                # Cleanup resources
                pass
    """

    def __init__(self):
        self._state = PluginState.UNLOADED
        self._context: Optional[PluginContext] = None
        self._error: Optional[str] = None

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @property
    def state(self) -> PluginState:
        """Get current plugin state."""
        return self._state

    @property
    def is_active(self) -> bool:
        """Check if plugin is active."""
        return self._state == PluginState.ACTIVE

    @property
    def error(self) -> Optional[str]:
        """Get error message if in ERROR state."""
        return self._error

    @abstractmethod
    async def activate(self, context: PluginContext) -> None:
        """
        Called when plugin is activated.

        Setup resources, register commands, etc.
        Raise exception to abort activation.
        """
        pass

    @abstractmethod
    async def deactivate(self) -> None:
        """
        Called when plugin is deactivated.

        Cleanup resources, unregister commands, etc.
        """
        pass

    # ========== Optional Hooks ==========

    def on_command(self, command: str, args: str) -> Optional[Any]:
        """
        Handle custom slash commands.

        Args:
            command: Command name (without slash)
            args: Command arguments string

        Returns:
            Result if handled, None to pass to next handler
        """
        return None

    def on_tool_execute(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Intercept tool execution.

        Args:
            tool_name: Name of tool being executed
            params: Tool parameters

        Returns:
            Modified params, result to short-circuit, or None to continue
        """
        return None

    def on_message(self, role: str, content: str) -> Optional[str]:
        """
        Process messages before/after LLM.

        Args:
            role: Message role (user, assistant, system)
            content: Message content

        Returns:
            Modified content or None to keep original
        """
        return None

    def on_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Handle errors.

        Args:
            error: The exception
            context: Error context information

        Returns:
            True if error was handled, False to propagate
        """
        return False

    # ========== Internal Methods ==========

    async def _do_activate(self, context: PluginContext) -> None:
        """Internal activation wrapper."""
        self._state = PluginState.LOADING
        self._context = context
        try:
            await self.activate(context)
            self._state = PluginState.ACTIVE
        except Exception as e:
            self._state = PluginState.ERROR
            self._error = str(e)
            raise

    async def _do_deactivate(self) -> None:
        """Internal deactivation wrapper."""
        self._state = PluginState.DEACTIVATING
        try:
            await self.deactivate()
        finally:
            self._state = PluginState.UNLOADED
            self._context = None


__all__ = [
    'Plugin',
    'PluginMetadata',
    'PluginPriority',
    'PluginContext',
    'PluginState',
]
