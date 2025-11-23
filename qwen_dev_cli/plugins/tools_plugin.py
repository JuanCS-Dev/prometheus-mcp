"""Lazy loaded tools plugin."""

from typing import Any, Dict, List
from qwen_dev_cli.tools.base import ToolRegistry

class Plugin:
    """Tools plugin."""
    
    def __init__(self):
        self.registry = None
        
    async def initialize(self) -> None:
        """Initialize tool registry and load tools."""
        # This is where the heavy lifting happens
        # We import tools here to avoid top-level imports in shell.py
        
        self.registry = ToolRegistry()
        self._register_tools()
        
    def _register_tools(self):
        """Register all available tools."""
        # Import tools locally to avoid loading them until plugin init
        from qwen_dev_cli.tools.file_ops import (
            ReadFileTool, WriteFileTool, EditFileTool,
            ListDirectoryTool, DeleteFileTool
        )
        from qwen_dev_cli.tools.file_mgmt import (
            MoveFileTool, CopyFileTool, CreateDirectoryTool,
            ReadMultipleFilesTool, InsertLinesTool
        )
        from qwen_dev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
        from qwen_dev_cli.tools.exec_hardened import BashCommandTool
        from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool
        from qwen_dev_cli.tools.context import GetContextTool, SaveSessionTool, RestoreBackupTool
        from qwen_dev_cli.tools.terminal import (
            CdTool, LsTool, PwdTool, MkdirTool, RmTool,
            CpTool, MvTool, TouchTool, CatTool
        )
        
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
            CpTool(), MvTool(), TouchTool(), CatTool(),
        ]
        
        for tool in tools:
            self.registry.register(tool)
            
    async def shutdown(self) -> None:
        """Cleanup."""
        pass
