"""Plugin system for lazy loading shell features."""

from typing import Dict, Any, Protocol, Optional
import asyncio
import importlib


class Plugin(Protocol):
    """Plugin interface."""
    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...


class PluginManager:
    """Manages lazy-loaded plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._loaded: Dict[str, bool] = {}
        
    async def load_plugin(self, name: str) -> Plugin:
        """Load plugin on-demand."""
        if name in self._plugins:
            return self._plugins[name]
            
        # Dynamic import
        # We assume plugins are in qwen_dev_cli.plugins package
        try:
            loop = asyncio.get_event_loop()
            module = await loop.run_in_executor(
                None,
                lambda: importlib.import_module(f'qwen_dev_cli.plugins.{name}_plugin')
            )
            
            # Instantiate plugin
            if not hasattr(module, 'Plugin'):
                raise ValueError(f"Plugin module {name} does not define 'Plugin' class")
                
            plugin = module.Plugin()
            
            # Initialize
            await plugin.initialize()
            
            self._plugins[name] = plugin
            self._loaded[name] = True
            
            return plugin
            
        except ImportError as e:
            raise ValueError(f"Plugin {name} not found: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load plugin {name}: {e}")

    async def shutdown_all(self):
        """Shutdown all loaded plugins."""
        for name, plugin in self._plugins.items():
            try:
                await plugin.shutdown()
            except Exception as e:
                print(f"Error shutting down plugin {name}: {e}")
