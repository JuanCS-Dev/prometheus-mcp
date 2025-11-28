"""
Hello World Example Plugin.

SCALE & SUSTAIN Phase 2.1 - Plugin Architecture.

A minimal example plugin to demonstrate the plugin system.

Author: JuanCS Dev
Date: 2025-11-26
"""

from typing import Optional, Any

from plugins.core import (
    Plugin,
    PluginMetadata,
    PluginPriority,
    PluginContext,
)


class HelloWorldPlugin(Plugin):
    """
    Minimal example plugin.

    Commands:
        /hello        - Say hello
        /hello <name> - Say hello to someone
    """

    def __init__(self):
        super().__init__()
        self._greet_count = 0

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="hello-world",
            version="1.0.0",
            description="A simple example plugin",
            author="JuanCS Dev",
            priority=PluginPriority.LOW,
            dependencies=[],
            provides=["greeting"],
        )

    async def activate(self, context: PluginContext) -> None:
        """Activate the plugin."""
        self._context = context
        print("Hello World plugin activated!")

    async def deactivate(self) -> None:
        """Deactivate the plugin."""
        print(f"Goodbye! Greeted {self._greet_count} times.")

    def on_command(self, command: str, args: str) -> Optional[Any]:
        """Handle /hello command."""
        if command != "hello":
            return None

        self._greet_count += 1
        name = args.strip() if args else "World"

        return {
            "type": "greeting",
            "message": f"Hello, {name}! 👋",
            "greet_count": self._greet_count
        }

    def on_message(self, role: str, content: str) -> Optional[str]:
        """Add greeting to messages (example of message hook)."""
        # Just pass through - example only
        return None


__all__ = ['HelloWorldPlugin']
