"""Lazy loaded tools plugin.

Provides tool_registry singleton that initializes on first access.
Zero async complexity, zero event loop conflicts.
"""

from jdev_cli.tools.base import ToolRegistry

# Singleton registry
_tool_registry = None


def _create_registry():
    """Create and populate tool registry."""
    # Import tools locally (lazy loading)
    from jdev_cli.tools.file_ops import (
        ReadFileTool, WriteFileTool, EditFileTool,
        ListDirectoryTool, DeleteFileTool
    )
    from jdev_cli.tools.file_mgmt import (
        MoveFileTool, CopyFileTool, CreateDirectoryTool,
        ReadMultipleFilesTool, InsertLinesTool
    )
    from jdev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
    from jdev_cli.tools.exec_hardened import BashCommandTool
    from jdev_cli.tools.git_ops import GitStatusTool, GitDiffTool
    from jdev_cli.tools.context import GetContextTool, SaveSessionTool, RestoreBackupTool
    from jdev_cli.tools.terminal import (
        CdTool, LsTool, PwdTool, MkdirTool, RmTool,
        CpTool, MvTool, TouchTool, CatTool
    )

    # Create registry
    registry = ToolRegistry()

    # Register all tools
    tools = [
        # File reading
        ReadFileTool(), ReadMultipleFilesTool(), ListDirectoryTool(),
        # File writing
        WriteFileTool(), EditFileTool(), InsertLinesTool(), DeleteFileTool(),
        # File management
        MoveFileTool(), CopyFileTool(), CreateDirectoryTool(),
        # Search
        SearchFilesTool(), GetDirectoryTreeTool(),
        # Execution
        BashCommandTool(),
        # Git
        GitStatusTool(), GitDiffTool(),
        # Context
        GetContextTool(), SaveSessionTool(), RestoreBackupTool(),
        # Terminal
        CdTool(), LsTool(), PwdTool(), MkdirTool(), RmTool(),
        CpTool(), MvTool(), TouchTool(), CatTool()
    ]

    for tool in tools:
        registry.register(tool)

    return registry


def __getattr__(name):
    """Lazy load tool_registry on first access."""
    global _tool_registry

    if name == 'tool_registry':
        if _tool_registry is None:
            _tool_registry = _create_registry()
        return _tool_registry

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
