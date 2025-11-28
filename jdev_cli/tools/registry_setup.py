"""Tool Registry Setup - Zero-Config Default Tools.

This module provides factory functions for setting up ToolRegistry with
sensible defaults, eliminating the need for manual tool registration in
common use cases.

Philosophy (Boris Cherny):
    - Zero-config defaults that work out-of-box
    - Explicit overrides when customization is needed
    - Type-safe, predictable behavior
    - Clear error messages that guide to solution

Compliance:
    - Vértice Constitution v3.0: Artigo IX (Tool Use Mandatório)
    - P2 (Validação Preventiva): Validates tool registration
    - P4 (Rastreabilidade): Clear provenance of each tool
"""

from typing import List, Optional, Tuple
import logging

from jdev_cli.tools.base import ToolRegistry
from jdev_cli.core.mcp_client import MCPClient

logger = logging.getLogger(__name__)


def setup_default_tools(
    include_file_ops: bool = True,
    include_bash: bool = True,
    include_search: bool = True,
    include_git: bool = True,
    include_prometheus: bool = True,
    custom_tools: Optional[List] = None
) -> Tuple[ToolRegistry, MCPClient]:
    """Setup tool registry with default tools pre-registered.

    This is the recommended way to initialize tools for agent use.
    Provides a curated set of tools that cover most common use cases:
    - File operations (read, write, edit, move, copy, mkdir)
    - Bash command execution
    - Code search and directory tree exploration
    - Git operations (status, diff)

    Args:
        include_file_ops: Register file operation tools (read, write, edit, etc.)
                         Default: True
        include_bash: Register bash command execution tool
                     Default: True
        include_search: Register search and directory tree tools
                       Default: True
        include_git: Register git operation tools (status, diff)
                    Default: True
        include_prometheus: Register PROMETHEUS tools (execute, memory, etc.)
                           Default: True
        custom_tools: Additional custom tool instances to register
                     Default: None

    Returns:
        Tuple of (ToolRegistry, MCPClient) ready for immediate agent use

    Raises:
        ImportError: If required tool module is missing (should not happen)
        ValueError: If custom_tools contains invalid tool instances

    Example:
        >>> # Quick start - all defaults
        >>> from jdev_cli.tools import setup_default_tools
        >>> from jdev_cli.core.llm import LLMClient
        >>> from jdev_cli.agents.planner import PlannerAgent
        >>>
        >>> llm = LLMClient()
        >>> registry, mcp = setup_default_tools()
        >>> agent = PlannerAgent(llm, mcp)
        >>> # Agent is now ready to use all registered tools

        >>> # Custom configuration
        >>> registry, mcp = setup_default_tools(
        ...     include_bash=False,  # Disable bash for security
        ...     custom_tools=[MyCustomTool()]
        ... )

    Note:
        - Tools are registered with their default names (e.g., 'read_file')
        - Duplicate registrations are handled safely (last wins)
        - Empty registry is valid but agents may fail if they need tools
    """
    registry = ToolRegistry()
    tools_registered = 0

    # File Operations Tools
    if include_file_ops:
        try:
            from jdev_cli.tools.file_ops import (
                ReadFileTool,
                WriteFileTool,
                EditFileTool
            )
            from jdev_cli.tools.file_mgmt import (
                CreateDirectoryTool,
                MoveFileTool,
                CopyFileTool
            )

            for tool_class in [
                ReadFileTool,
                WriteFileTool,
                EditFileTool,
                CreateDirectoryTool,
                MoveFileTool,
                CopyFileTool
            ]:
                tool = tool_class()
                registry.register(tool)
                tools_registered += 1

            logger.debug(f"Registered {tools_registered} file operation tools")

        except ImportError as e:
            logger.error(f"Failed to import file operation tools: {e}")
            raise ImportError(
                f"File operation tools not available: {e}. "
                f"Ensure jdev_cli is properly installed."
            )

    # Bash Execution Tool
    if include_bash:
        try:
            from jdev_cli.tools.exec import BashCommandTool

            tool = BashCommandTool()
            registry.register(tool)
            tools_registered += 1
            logger.debug("Registered bash command tool")

        except ImportError as e:
            logger.error(f"Failed to import bash tool: {e}")
            raise ImportError(
                f"Bash command tool not available: {e}. "
                f"Ensure jdev_cli is properly installed."
            )

    # Search and Tree Tools
    if include_search:
        try:
            from jdev_cli.tools.search import (
                SearchFilesTool,
                GetDirectoryTreeTool
            )

            for tool_class in [SearchFilesTool, GetDirectoryTreeTool]:
                tool = tool_class()
                registry.register(tool)
                tools_registered += 1

            logger.debug("Registered 2 search tools")

        except ImportError as e:
            logger.error(f"Failed to import search tools: {e}")
            raise ImportError(
                f"Search tools not available: {e}. "
                f"Ensure jdev_cli is properly installed."
            )

    # Git Operations Tools
    if include_git:
        try:
            from jdev_cli.tools.git_ops import (
                GitStatusTool,
                GitDiffTool
            )

            for tool_class in [GitStatusTool, GitDiffTool]:
                tool = tool_class()
                registry.register(tool)
                tools_registered += 1

            logger.debug("Registered 2 git tools")

        except ImportError as e:
            # Git tools são opcionais, só avisar
            logger.warning(f"Git tools not available: {e}")

    # PROMETHEUS Tools
    if include_prometheus:
        try:
            from jdev_cli.tools.prometheus_tools import (
                PrometheusExecuteTool,
                PrometheusMemoryQueryTool,
                PrometheusSimulateTool,
                PrometheusEvolveTool,
                PrometheusReflectTool,
                PrometheusCreateToolTool,
                PrometheusGetStatusTool,
                PrometheusBenchmarkTool
            )
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

            # Initialize provider lazily
            provider = PrometheusProvider()

            tools = [
                PrometheusExecuteTool(provider),
                PrometheusMemoryQueryTool(provider),
                PrometheusSimulateTool(provider),
                PrometheusEvolveTool(provider),
                PrometheusReflectTool(provider),
                PrometheusCreateToolTool(provider),
                PrometheusGetStatusTool(provider),
                PrometheusBenchmarkTool(provider)
            ]

            for tool in tools:
                registry.register(tool)
                tools_registered += 1

            logger.debug(f"Registered {len(tools)} PROMETHEUS tools")

        except ImportError as e:
            logger.warning(f"PROMETHEUS tools not available: {e}")


    # Custom Tools
    if custom_tools:
        if not isinstance(custom_tools, list):
            raise ValueError(
                f"custom_tools must be a list, got {type(custom_tools).__name__}"
            )

        for tool in custom_tools:
            if not hasattr(tool, 'name'):
                raise ValueError(
                    f"Invalid custom tool: {tool}. "
                    f"Tools must have a 'name' attribute."
                )

            registry.register(tool)
            tools_registered += 1
            logger.debug(f"Registered custom tool: {tool.name}")

    # Create MCP client
    mcp = MCPClient(registry)

    logger.info(
        f"Tool registry setup complete: {tools_registered} tools registered"
    )

    return registry, mcp


def setup_minimal_tools() -> Tuple[ToolRegistry, MCPClient]:
    """Setup with only essential tools (read, write, edit files).

    Use this when you want minimal overhead or when operating in
    restricted environments where bash/git are not available.

    Returns:
        Tuple of (ToolRegistry, MCPClient) with 3 essential tools

    Example:
        >>> registry, mcp = setup_minimal_tools()
        >>> # Only read_file, write_file, edit_file available
    """
    return setup_default_tools(
        include_file_ops=True,
        include_bash=False,
        include_search=False,
        include_git=False
    )


def setup_readonly_tools() -> Tuple[ToolRegistry, MCPClient]:
    """Setup with only read-only tools (read, search, git status).

    Use this when you want agents to explore and analyze code without
    any modification capabilities. Safe for untrusted agent execution.

    Returns:
        Tuple of (ToolRegistry, MCPClient) with read-only tools

    Example:
        >>> registry, mcp = setup_readonly_tools()
        >>> # Agent can read and search, but cannot modify anything
    """
    return setup_default_tools(
        include_file_ops=False,  # Desabilita write/edit
        include_bash=False,      # Bash pode modificar sistema
        include_search=True,     # Search é read-only
        include_git=True         # Git status/diff são read-only
    )


def setup_custom_tools(tools: List) -> Tuple[ToolRegistry, MCPClient]:
    """Setup with specific tools only (no defaults).

    Use this when you have specific requirements and want full control
    over which tools are available.

    Args:
        tools: List of tool instances to register

    Returns:
        Tuple of (ToolRegistry, MCPClient) with only specified tools

    Raises:
        ValueError: If tools list is empty or contains invalid tools

    Example:
        >>> from jdev_cli.tools.file_ops import ReadFileTool
        >>> registry, mcp = setup_custom_tools([
        ...     ReadFileTool(),
        ...     MyCustomTool()
        ... ])
    """
    if not tools:
        raise ValueError(
            "tools list cannot be empty. "
            "Use setup_minimal_tools() if you want minimal setup."
        )

    return setup_default_tools(
        include_file_ops=False,
        include_bash=False,
        include_search=False,
        include_git=False,
        custom_tools=tools
    )


# Convenience exports for common patterns
__all__ = [
    'setup_default_tools',
    'setup_minimal_tools',
    'setup_readonly_tools',
    'setup_custom_tools',
]
