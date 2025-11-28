"""
Plugin Registry.

SCALE & SUSTAIN Phase 2.1 - Plugin Architecture.

Central registry for managing plugins:
- Plugin lifecycle management
- Capability-based lookup
- Event dispatch to plugins

Author: JuanCS Dev
Date: 2025-11-26
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from .base import Plugin, PluginMetadata, PluginContext
from .loader import PluginLoader

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for plugin management.

    Provides:
    - Plugin discovery and loading
    - Capability-based lookup
    - Hook dispatch to all active plugins
    - Configuration management

    Usage:
        registry = PluginRegistry()
        registry.add_plugin_dir(Path("plugins/builtin"))

        # Discover and load all plugins
        await registry.load_all()

        # Get plugin by name
        git_plugin = registry.get("git")

        # Find plugins by capability
        vcs_plugins = registry.find_by_capability("vcs")

        # Dispatch hook to all plugins
        results = await registry.dispatch_command("status", "")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin registry.

        Args:
            config: Global configuration dict
        """
        self._config = config or {}
        self._plugin_dirs: List[Path] = []
        self._loader: Optional[PluginLoader] = None
        self._plugins: Dict[str, Plugin] = {}
        self._capabilities: Dict[str, Set[str]] = {}  # capability -> plugin names
        self._context: Optional[PluginContext] = None

    def add_plugin_dir(self, path: Path) -> None:
        """Add a directory to search for plugins."""
        if path not in self._plugin_dirs:
            self._plugin_dirs.append(path)
            self._loader = None  # Reset loader

    def _get_loader(self) -> PluginLoader:
        """Get or create plugin loader."""
        if self._loader is None:
            self._loader = PluginLoader(self._plugin_dirs)
        return self._loader

    def _get_context(self) -> PluginContext:
        """Get or create plugin context."""
        if self._context is None:
            self._context = PluginContext(
                config=self._config,
                registry=self,
                logger=logger
            )
        return self._context

    def discover(self) -> List[PluginMetadata]:
        """Discover available plugins."""
        return self._get_loader().discover()

    async def load(self, name: str) -> Plugin:
        """
        Load a single plugin.

        Args:
            name: Plugin name

        Returns:
            Loaded and activated plugin
        """
        loader = self._get_loader()
        context = self._get_context()

        plugin = await loader.load(name, context)
        self._plugins[name] = plugin
        self._index_capabilities(plugin)

        return plugin

    async def load_all(self, priority_filter: Optional[int] = None) -> List[Plugin]:
        """
        Load all discovered plugins.

        Args:
            priority_filter: Only load plugins with priority <= this value

        Returns:
            List of loaded plugins
        """
        loader = self._get_loader()
        available = loader.discover()

        loaded = []
        for meta in available:
            if priority_filter is not None and meta.priority.value > priority_filter:
                logger.debug(f"Skipping {meta.name} (priority {meta.priority.value})")
                continue

            try:
                plugin = await self.load(meta.name)
                loaded.append(plugin)
            except Exception as e:
                logger.error(f"Failed to load {meta.name}: {e}")

        return loaded

    async def unload(self, name: str) -> None:
        """Unload a plugin."""
        if name in self._plugins:
            plugin = self._plugins[name]
            self._remove_capabilities(plugin)
            await self._get_loader().unload(name)
            del self._plugins[name]

    async def unload_all(self) -> None:
        """Unload all plugins."""
        # Unload in reverse priority order
        plugins = sorted(
            self._plugins.items(),
            key=lambda x: x[1].metadata.priority.value,
            reverse=True
        )
        for name, _ in plugins:
            await self.unload(name)

    def _index_capabilities(self, plugin: Plugin) -> None:
        """Index plugin capabilities."""
        for cap in plugin.metadata.provides:
            if cap not in self._capabilities:
                self._capabilities[cap] = set()
            self._capabilities[cap].add(plugin.metadata.name)

    def _remove_capabilities(self, plugin: Plugin) -> None:
        """Remove plugin from capability index."""
        for cap in plugin.metadata.provides:
            if cap in self._capabilities:
                self._capabilities[cap].discard(plugin.metadata.name)

    # ========== Lookup Methods ==========

    def get(self, name: str) -> Optional[Plugin]:
        """Get plugin by name."""
        return self._plugins.get(name)

    def get_all(self) -> Dict[str, Plugin]:
        """Get all loaded plugins."""
        return dict(self._plugins)

    def find_by_capability(self, capability: str) -> List[Plugin]:
        """Find plugins that provide a capability."""
        plugin_names = self._capabilities.get(capability, set())
        return [self._plugins[name] for name in plugin_names if name in self._plugins]

    def has_capability(self, capability: str) -> bool:
        """Check if any plugin provides a capability."""
        return bool(self._capabilities.get(capability))

    # ========== Hook Dispatch ==========

    async def dispatch_command(
        self,
        command: str,
        args: str
    ) -> Optional[Any]:
        """
        Dispatch command to plugins.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            First non-None result from plugins
        """
        for plugin in self._active_plugins():
            try:
                result = plugin.on_command(command, args)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(f"Plugin {plugin.metadata.name} command error: {e}")
        return None

    async def dispatch_tool_execute(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Dispatch tool execution to plugins.

        Args:
            tool_name: Tool name
            params: Tool parameters

        Returns:
            Modified params, result, or None
        """
        for plugin in self._active_plugins():
            try:
                result = plugin.on_tool_execute(tool_name, params)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(f"Plugin {plugin.metadata.name} tool error: {e}")
        return None

    def dispatch_message(self, role: str, content: str) -> str:
        """
        Dispatch message through plugins.

        Args:
            role: Message role
            content: Message content

        Returns:
            Potentially modified content
        """
        current = content
        for plugin in self._active_plugins():
            try:
                result = plugin.on_message(role, current)
                if result is not None:
                    current = result
            except Exception as e:
                logger.error(f"Plugin {plugin.metadata.name} message error: {e}")
        return current

    def dispatch_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Dispatch error to plugins.

        Args:
            error: The exception
            context: Error context

        Returns:
            True if any plugin handled the error
        """
        for plugin in self._active_plugins():
            try:
                if plugin.on_error(error, context):
                    return True
            except Exception as e:
                logger.error(f"Plugin {plugin.metadata.name} error handler failed: {e}")
        return False

    def _active_plugins(self) -> List[Plugin]:
        """Get list of active plugins sorted by priority."""
        return sorted(
            [p for p in self._plugins.values() if p.is_active],
            key=lambda p: p.metadata.priority.value
        )

    # ========== Status ==========

    def get_status(self) -> Dict[str, Any]:
        """Get registry status."""
        return {
            "plugin_dirs": [str(p) for p in self._plugin_dirs],
            "loaded_count": len(self._plugins),
            "plugins": {
                name: {
                    "version": p.metadata.version,
                    "state": p.state.name,
                    "provides": p.metadata.provides,
                }
                for name, p in self._plugins.items()
            },
            "capabilities": {
                cap: list(names)
                for cap, names in self._capabilities.items()
            }
        }


__all__ = ['PluginRegistry']
