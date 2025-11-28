"""
UI Launcher - Lazy TUI imports to break circular dependency.

This module provides lazy loading of jdev_tui components to prevent
circular imports between jdev_cli and jdev_tui.

The dependency direction should be:
    jdev_tui → jdev_cli  (TUI imports CLI)
    jdev_cli → jdev_tui  (CLI should NOT import TUI directly)

This launcher provides the bridge for CLI to launch TUI when needed.

Author: Boris Cherny style
Date: 2025-11-26
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncGenerator

if TYPE_CHECKING:
    from jdev_tui.core.bridge import Bridge


def launch_tui() -> None:
    """
    Launch the Textual TUI application.

    Lazy import to avoid circular dependency.
    """
    from jdev_tui.app import QwenApp
    app = QwenApp()
    app.run()


def get_bridge() -> "Bridge":
    """
    Get the TUI bridge instance.

    Lazy import to avoid circular dependency.

    Returns:
        Bridge instance for CLI-TUI communication
    """
    from jdev_tui.core.bridge import get_bridge
    return get_bridge()


def get_agent_registry() -> dict:
    """
    Get the agent registry from TUI.

    Lazy import to avoid circular dependency.

    Returns:
        Dictionary of registered agents
    """
    from jdev_tui.core.bridge import AGENT_REGISTRY
    return AGENT_REGISTRY


async def chat_via_bridge(prompt: str) -> AsyncGenerator[Any, None]:
    """
    Chat via the TUI bridge.

    Lazy import to avoid circular dependency.

    Args:
        prompt: User prompt to send

    Yields:
        Response chunks from the LLM
    """
    bridge = get_bridge()
    async for chunk in bridge.chat(prompt):
        yield chunk


__all__ = [
    'launch_tui',
    'get_bridge',
    'get_agent_registry',
    'chat_via_bridge',
]
