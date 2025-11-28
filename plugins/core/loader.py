"""
Plugin Loader.

SCALE & SUSTAIN Phase 2.1 - Plugin Architecture.

Responsible for:
- Discovering plugins in configured directories
- Loading plugin modules dynamically
- Resolving dependencies
- Instantiating plugin classes

Author: JuanCS Dev
Date: 2025-11-26
"""

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional, Type

from .base import Plugin, PluginMetadata

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Raised when plugin loading fails."""
    def __init__(self, plugin_name: str, reason: str):
        self.plugin_name = plugin_name
        self.reason = reason
        super().__init__(f"Failed to load plugin '{plugin_name}': {reason}")


class DependencyError(PluginLoadError):
    """Raised when plugin dependencies cannot be resolved."""
    def __init__(self, plugin_name: str, missing: List[str]):
        self.missing = missing
        super().__init__(
            plugin_name,
            f"Missing dependencies: {', '.join(missing)}"
        )


class PluginLoader:
    """
    Load plugins from directories.

    Plugin Discovery:
        Plugins are discovered by looking for plugin.py files in
        subdirectories of the configured plugin directories.

        Example structure:
            plugins/
            ├── builtin/
            │   └── git/
            │       ├── __init__.py
            │       └── plugin.py  <- Contains GitPlugin class
            └── custom/
                └── my-plugin/
                    └── plugin.py

    Usage:
        loader = PluginLoader([Path("plugins/builtin"), Path("plugins/custom")])
        available = loader.discover()
        plugin = await loader.load("git")
    """

    PLUGIN_FILE = "plugin.py"
    PLUGIN_CLASS_SUFFIX = "Plugin"

    def __init__(self, plugin_dirs: List[Path]):
        """
        Initialize plugin loader.

        Args:
            plugin_dirs: List of directories to search for plugins
        """
        self.plugin_dirs = [Path(d) for d in plugin_dirs]
        self._discovered: Dict[str, Path] = {}
        self._loaded: Dict[str, Plugin] = {}
        self._metadata_cache: Dict[str, PluginMetadata] = {}

    def discover(self) -> List[PluginMetadata]:
        """
        Discover available plugins.

        Returns:
            List of plugin metadata, sorted by priority
        """
        self._discovered.clear()
        self._metadata_cache.clear()
        plugins = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                logger.debug(f"Plugin directory does not exist: {plugin_dir}")
                continue

            # Look for plugin.py in subdirectories
            for path in plugin_dir.glob(f"*/{self.PLUGIN_FILE}"):
                try:
                    meta = self._load_metadata(path)
                    if meta.name in self._discovered:
                        logger.warning(
                            f"Duplicate plugin '{meta.name}' found at {path}, "
                            f"using {self._discovered[meta.name]}"
                        )
                        continue

                    self._discovered[meta.name] = path
                    self._metadata_cache[meta.name] = meta
                    plugins.append(meta)
                    logger.debug(f"Discovered plugin: {meta.name} v{meta.version}")

                except Exception as e:
                    logger.warning(f"Failed to load plugin from {path}: {e}")

        # Sort by priority (lower value = higher priority)
        return sorted(plugins, key=lambda p: p.priority.value)

    def _load_metadata(self, plugin_path: Path) -> PluginMetadata:
        """Load metadata from a plugin file without fully loading it."""
        # Load module temporarily to get metadata
        spec = importlib.util.spec_from_file_location(
            f"_plugin_probe_{plugin_path.parent.name}",
            plugin_path
        )
        if spec is None or spec.loader is None:
            raise PluginLoadError(
                plugin_path.parent.name,
                "Could not create module spec"
            )

        module = importlib.util.module_from_spec(spec)

        # Don't add to sys.modules yet
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise PluginLoadError(
                plugin_path.parent.name,
                f"Failed to execute module: {e}"
            )

        # Find plugin class
        plugin_class = self._find_plugin_class(module, plugin_path.parent.name)
        if plugin_class is None:
            raise PluginLoadError(
                plugin_path.parent.name,
                f"No Plugin subclass found in {plugin_path}"
            )

        # Get metadata from class
        try:
            instance = plugin_class()
            return instance.metadata
        except Exception as e:
            raise PluginLoadError(
                plugin_path.parent.name,
                f"Failed to get metadata: {e}"
            )

    def _find_plugin_class(self, module, plugin_name: str) -> Optional[Type[Plugin]]:
        """Find the Plugin subclass in a module."""
        for name in dir(module):
            if name.startswith('_'):
                continue

            obj = getattr(module, name)
            if (
                isinstance(obj, type) and
                issubclass(obj, Plugin) and
                obj is not Plugin and
                name.endswith(self.PLUGIN_CLASS_SUFFIX)
            ):
                return obj

        return None

    async def load(self, name: str, context=None) -> Plugin:
        """
        Load and activate a plugin.

        Args:
            name: Plugin name to load
            context: Optional PluginContext for activation

        Returns:
            Activated Plugin instance

        Raises:
            PluginLoadError: If plugin cannot be loaded
            DependencyError: If dependencies are missing
        """
        # Return cached if already loaded
        if name in self._loaded:
            return self._loaded[name]

        # Ensure discovered
        if name not in self._discovered:
            # Try to discover first
            self.discover()
            if name not in self._discovered:
                raise PluginLoadError(name, "Plugin not found")

        # Check dependencies
        meta = self._metadata_cache[name]
        missing = self._check_dependencies(meta)
        if missing:
            raise DependencyError(name, missing)

        # Load dependencies first
        for dep in meta.dependencies:
            if dep not in self._loaded:
                await self.load(dep, context)

        # Load the plugin
        plugin_path = self._discovered[name]
        plugin = self._instantiate(plugin_path, name)

        # Activate if context provided
        if context:
            await plugin._do_activate(context)

        self._loaded[name] = plugin
        logger.info(f"Loaded plugin: {name} v{meta.version}")
        return plugin

    def _check_dependencies(self, meta: PluginMetadata) -> List[str]:
        """Check which dependencies are missing."""
        missing = []
        for dep in meta.dependencies:
            if dep not in self._discovered and dep not in self._loaded:
                missing.append(dep)
        return missing

    def _instantiate(self, plugin_path: Path, name: str) -> Plugin:
        """Instantiate a plugin from its file."""
        module_name = f"plugins.{plugin_path.parent.parent.name}.{plugin_path.parent.name}"

        spec = importlib.util.spec_from_file_location(module_name, plugin_path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(name, "Could not create module spec")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            del sys.modules[module_name]
            raise PluginLoadError(name, f"Failed to execute module: {e}")

        plugin_class = self._find_plugin_class(module, name)
        if plugin_class is None:
            raise PluginLoadError(name, "No Plugin subclass found")

        try:
            return plugin_class()
        except Exception as e:
            raise PluginLoadError(name, f"Failed to instantiate: {e}")

    async def unload(self, name: str) -> None:
        """
        Unload a plugin.

        Args:
            name: Plugin name to unload
        """
        if name not in self._loaded:
            return

        plugin = self._loaded[name]

        # Check if other plugins depend on this one
        dependents = self._get_dependents(name)
        if dependents:
            logger.warning(
                f"Unloading {name} which is required by: {', '.join(dependents)}"
            )

        await plugin._do_deactivate()
        del self._loaded[name]
        logger.info(f"Unloaded plugin: {name}")

    def _get_dependents(self, name: str) -> List[str]:
        """Get plugins that depend on the given plugin."""
        dependents = []
        for plugin_name, meta in self._metadata_cache.items():
            if name in meta.dependencies and plugin_name in self._loaded:
                dependents.append(plugin_name)
        return dependents

    def get_loaded(self) -> Dict[str, Plugin]:
        """Get all loaded plugins."""
        return dict(self._loaded)

    def is_loaded(self, name: str) -> bool:
        """Check if a plugin is loaded."""
        return name in self._loaded


__all__ = [
    'PluginLoader',
    'PluginLoadError',
    'DependencyError',
]
