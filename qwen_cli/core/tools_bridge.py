"""
Tools Bridge Module - 47 Tools Integration
==========================================

Extracted from Bridge GOD CLASS (Nov 2025 Refactoring).

Features:
- Lazy loading tool registry
- File Operations (12), Terminal (9), Execution (2)
- Search (2), Git (2), Context (3), Web (6)
- Claude Code Parity Tools (7)
"""

from __future__ import annotations

from typing import Any, Dict, List


class ToolBridge:
    """
    Bridge to 47 tools from qwen_dev_cli.

    Lazy loading to keep startup fast.

    Categories:
    - File Operations (12): read, write, edit, list, delete, move, copy, mkdir, insert
    - Terminal (9): cd, ls, pwd, mkdir, rm, cp, mv, touch, cat
    - Execution (2): bash, bash_hardened
    - Search (2): search_files, get_directory_tree
    - Git (2): git_status, git_diff
    - Context (3): get_context, save_session, restore_backup
    - Web (6): web_search, fetch_url, download_file, http_request, package_search, search_docs
    """

    def __init__(self):
        self._registry = None
        self._load_errors: List[str] = []

    @property
    def registry(self):
        """Lazy load tool registry."""
        if self._registry is None:
            self._registry = self._create_registry()
        return self._registry

    def _create_registry(self):
        """Create and populate tool registry."""
        try:
            from qwen_dev_cli.tools.base import ToolRegistry

            registry = ToolRegistry()

            # File Operations (12 tools)
            try:
                from qwen_dev_cli.tools.file_ops import (
                    ReadFileTool, WriteFileTool, EditFileTool,
                    ListDirectoryTool, DeleteFileTool
                )
                from qwen_dev_cli.tools.file_mgmt import (
                    MoveFileTool, CopyFileTool, CreateDirectoryTool,
                    ReadMultipleFilesTool, InsertLinesTool
                )

                for tool_cls in [
                    ReadFileTool, WriteFileTool, EditFileTool,
                    ListDirectoryTool, DeleteFileTool,
                    MoveFileTool, CopyFileTool, CreateDirectoryTool,
                    ReadMultipleFilesTool, InsertLinesTool
                ]:
                    try:
                        registry.register(tool_cls())
                    except Exception as e:
                        self._load_errors.append(f"file_ops: {e}")
            except ImportError as e:
                self._load_errors.append(f"file_ops import: {e}")

            # Terminal (9 tools)
            try:
                from qwen_dev_cli.tools.terminal import (
                    CdTool, LsTool, PwdTool, MkdirTool, RmTool,
                    CpTool, MvTool, TouchTool, CatTool
                )

                for tool_cls in [
                    CdTool, LsTool, PwdTool, MkdirTool, RmTool,
                    CpTool, MvTool, TouchTool, CatTool
                ]:
                    try:
                        registry.register(tool_cls())
                    except Exception as e:
                        self._load_errors.append(f"terminal: {e}")
            except ImportError as e:
                self._load_errors.append(f"terminal import: {e}")

            # Execution (2 tools)
            try:
                from qwen_dev_cli.tools.exec_hardened import BashCommandTool
                registry.register(BashCommandTool())
            except ImportError as e:
                self._load_errors.append(f"exec import: {e}")

            # Search (2 tools)
            try:
                from qwen_dev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
                registry.register(SearchFilesTool())
                registry.register(GetDirectoryTreeTool())
            except ImportError as e:
                self._load_errors.append(f"search import: {e}")

            # Git (2 tools)
            try:
                from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool
                registry.register(GitStatusTool())
                registry.register(GitDiffTool())
            except ImportError as e:
                self._load_errors.append(f"git import: {e}")

            # Context (3 tools)
            try:
                from qwen_dev_cli.tools.context import (
                    GetContextTool, SaveSessionTool, RestoreBackupTool
                )
                registry.register(GetContextTool())
                registry.register(SaveSessionTool())
                registry.register(RestoreBackupTool())
            except ImportError as e:
                self._load_errors.append(f"context import: {e}")

            # Web (6 tools)
            try:
                from qwen_dev_cli.tools.web_search import WebSearchTool, SearchDocumentationTool
                from qwen_dev_cli.tools.web_access import (
                    FetchURLTool, DownloadFileTool, HTTPRequestTool, PackageSearchTool
                )

                for tool_cls in [
                    WebSearchTool, SearchDocumentationTool,
                    FetchURLTool, DownloadFileTool, HTTPRequestTool, PackageSearchTool
                ]:
                    try:
                        registry.register(tool_cls())
                    except Exception as e:
                        self._load_errors.append(f"web: {e}")
            except ImportError as e:
                self._load_errors.append(f"web import: {e}")

            # Claude Code Parity Tools (7 tools)
            try:
                from qwen_dev_cli.tools.claude_parity_tools import get_claude_parity_tools

                for tool in get_claude_parity_tools():
                    try:
                        registry.register(tool)
                    except Exception as e:
                        self._load_errors.append(f"parity: {e}")
            except ImportError as e:
                self._load_errors.append(f"claude_parity import: {e}")

            return registry

        except ImportError:
            # Return empty registry if qwen_dev_cli not available
            return MinimalRegistry()

    def get_tool(self, name: str):
        """Get tool by name."""
        return self.registry.get(name)

    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self.registry.get_all().keys())

    def get_tool_count(self) -> int:
        """Get number of loaded tools."""
        return len(self.registry.get_all())

    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name with given parameters."""
        tool = self.get_tool(name)
        if not tool:
            return {"success": False, "error": f"Tool not found: {name}"}

        try:
            result = await tool._execute_validated(**kwargs)
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "metadata": result.metadata
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_schemas_for_llm(self) -> List[Dict]:
        """Get tool schemas formatted for LLM function calling."""
        return self.registry.get_schemas()


class MinimalRegistry:
    """Minimal fallback tool registry."""

    def __init__(self):
        self.tools: Dict[str, Any] = {}

    def get_all(self):
        return self.tools

    def get(self, name):
        return self.tools.get(name)

    def get_schemas(self):
        return []


__all__ = [
    'ToolBridge',
    'MinimalRegistry',
]
