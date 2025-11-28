"""
Tool Manager.

SCALE & SUSTAIN Phase 1.1.4 - Tool Manager.

Manages tool registration, validation, and execution.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
import threading


class ToolCategory(Enum):
    """Tool categories."""
    FILE_SYSTEM = auto()   # read, write, glob, etc.
    CODE = auto()          # edit, search, refactor
    SHELL = auto()         # bash, exec
    NETWORK = auto()       # http, fetch
    AGENT = auto()         # task, sub-agents
    UTILITY = auto()       # misc helpers


@dataclass
class ToolRegistration:
    """Tool registration metadata."""
    name: str
    description: str
    handler: Callable
    category: ToolCategory = ToolCategory.UTILITY
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    timeout: int = 30
    enabled: bool = True
    aliases: List[str] = field(default_factory=list)

    def to_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema for LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class ToolExecutionContext:
    """Context for tool execution."""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    working_directory: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    sandbox: bool = True
    approved_tools: Set[str] = field(default_factory=set)

    def is_approved(self, tool_name: str) -> bool:
        """Check if tool is pre-approved."""
        return tool_name in self.approved_tools or not self.sandbox


@dataclass
class ToolResult:
    """Result of tool execution."""
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


class ToolManager:
    """
    Manages tool registration and execution.

    Features:
    - Tool registration with schemas
    - Category-based organization
    - Execution with timeout and sandboxing
    - Pre-approval tracking
    - Execution statistics

    Example:
        manager = ToolManager()

        # Register tool
        @manager.register("read_file", category=ToolCategory.FILE_SYSTEM)
        async def read_file(path: str) -> str:
            ...

        # Execute tool
        result = await manager.execute("read_file", {"path": "/etc/hosts"}, context)

        # Get tools for LLM
        schemas = manager.get_tool_schemas()
    """

    def __init__(self):
        self._tools: Dict[str, ToolRegistration] = {}
        self._aliases: Dict[str, str] = {}  # alias -> tool_name
        self._stats: Dict[str, Dict[str, Any]] = {}  # tool_name -> stats
        self._lock = threading.RLock()

        # Register built-in tools
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in placeholder tools."""
        # These would be implemented by the actual tool handlers
        pass

    def register(
        self,
        name: str,
        description: str = "",
        category: ToolCategory = ToolCategory.UTILITY,
        parameters: Optional[Dict[str, Any]] = None,
        requires_approval: bool = False,
        timeout: int = 30,
        aliases: Optional[List[str]] = None
    ) -> Callable:
        """
        Decorator to register a tool handler.

        Args:
            name: Tool name
            description: Tool description for LLM
            category: Tool category
            parameters: JSON schema for parameters
            requires_approval: Whether tool requires user approval
            timeout: Execution timeout in seconds
            aliases: Alternative names for the tool

        Example:
            @tool_manager.register("bash", category=ToolCategory.SHELL)
            async def execute_bash(command: str) -> str:
                ...
        """
        def decorator(handler: Callable) -> Callable:
            registration = ToolRegistration(
                name=name,
                description=description or handler.__doc__ or "",
                handler=handler,
                category=category,
                parameters=parameters or {},
                requires_approval=requires_approval,
                timeout=timeout,
                aliases=aliases or [],
            )

            with self._lock:
                self._tools[name] = registration

                # Register aliases
                for alias in registration.aliases:
                    self._aliases[alias] = name

                # Initialize stats
                self._stats[name] = {
                    "calls": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_time": 0.0,
                }

            return handler
        return decorator

    def register_tool(self, registration: ToolRegistration) -> None:
        """Register a tool directly."""
        with self._lock:
            self._tools[registration.name] = registration

            for alias in registration.aliases:
                self._aliases[alias] = registration.name

            self._stats[registration.name] = {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "total_time": 0.0,
            }

    def get_tool(self, name: str) -> Optional[ToolRegistration]:
        """Get tool by name or alias."""
        # Check aliases first
        actual_name = self._aliases.get(name, name)
        return self._tools.get(actual_name)

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        enabled_only: bool = True
    ) -> List[ToolRegistration]:
        """List registered tools."""
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if enabled_only:
            tools = [t for t in tools if t.enabled]

        return tools

    def get_tool_schemas(
        self,
        category: Optional[ToolCategory] = None
    ) -> List[Dict[str, Any]]:
        """Get tool schemas for LLM."""
        tools = self.list_tools(category=category, enabled_only=True)
        return [t.to_schema() for t in tools]

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolResult:
        """
        Execute a tool.

        Args:
            tool_name: Tool name or alias
            parameters: Tool parameters
            context: Execution context

        Returns:
            ToolResult with output or error
        """
        context = context or ToolExecutionContext()
        start_time = time.time()

        # Resolve alias
        actual_name = self._aliases.get(tool_name, tool_name)
        tool = self._tools.get(actual_name)

        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                output=None,
                error=f"Unknown tool: {tool_name}",
            )

        if not tool.enabled:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                output=None,
                error=f"Tool disabled: {tool_name}",
            )

        # Check approval
        if tool.requires_approval and not context.is_approved(actual_name):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                output=None,
                error=f"Tool requires approval: {tool_name}",
                metadata={"requires_approval": True},
            )

        # Execute with timeout
        timeout = min(tool.timeout, context.timeout)

        try:
            handler = tool.handler

            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**parameters),
                    timeout=timeout
                )
            else:
                # Run sync handler in thread pool
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: handler(**parameters)),
                    timeout=timeout
                )

            execution_time = time.time() - start_time

            # Update stats
            with self._lock:
                self._stats[actual_name]["calls"] += 1
                self._stats[actual_name]["successes"] += 1
                self._stats[actual_name]["total_time"] += execution_time

            return ToolResult(
                tool_name=actual_name,
                success=True,
                output=result,
                execution_time=execution_time,
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time

            with self._lock:
                self._stats[actual_name]["calls"] += 1
                self._stats[actual_name]["failures"] += 1

            return ToolResult(
                tool_name=actual_name,
                success=False,
                output=None,
                error=f"Tool execution timed out after {timeout}s",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time

            with self._lock:
                self._stats[actual_name]["calls"] += 1
                self._stats[actual_name]["failures"] += 1

            return ToolResult(
                tool_name=actual_name,
                success=False,
                output=None,
                error=str(e),
                execution_time=execution_time,
            )

    def enable_tool(self, name: str) -> bool:
        """Enable a tool."""
        tool = self.get_tool(name)
        if tool:
            tool.enabled = True
            return True
        return False

    def disable_tool(self, name: str) -> bool:
        """Disable a tool."""
        tool = self.get_tool(name)
        if tool:
            tool.enabled = False
            return True
        return False

    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics."""
        if tool_name:
            actual_name = self._aliases.get(tool_name, tool_name)
            stats = self._stats.get(actual_name, {})
            if stats and stats["calls"] > 0:
                stats["avg_time"] = stats["total_time"] / stats["calls"]
                stats["success_rate"] = stats["successes"] / stats["calls"]
            return stats

        # All tools
        result = {}
        for name, stats in self._stats.items():
            result[name] = stats.copy()
            if stats["calls"] > 0:
                result[name]["avg_time"] = stats["total_time"] / stats["calls"]
                result[name]["success_rate"] = stats["successes"] / stats["calls"]

        return result

    def get_categories(self) -> Dict[str, List[str]]:
        """Get tools organized by category."""
        result: Dict[str, List[str]] = {}

        for tool in self._tools.values():
            category_name = tool.category.name
            if category_name not in result:
                result[category_name] = []
            result[category_name].append(tool.name)

        return result


__all__ = [
    'ToolManager',
    'ToolRegistration',
    'ToolExecutionContext',
    'ToolResult',
    'ToolCategory',
]
