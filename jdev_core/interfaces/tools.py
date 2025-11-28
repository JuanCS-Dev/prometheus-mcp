"""
Tool Execution Interface.

SCALE & SUSTAIN Phase 2.2 - Interface Extraction.

Defines interfaces for tool execution:
- ITool: Individual tool interface
- IToolExecutor: Tool execution engine
- ToolResult: Standardized result format

Author: JuanCS Dev
Date: 2025-11-26
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class ToolCategory(Enum):
    """Tool categories for organization."""
    FILE = "file"
    GIT = "git"
    SHELL = "shell"
    SEARCH = "search"
    NETWORK = "network"
    DATABASE = "database"
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass
class ToolResult:
    """
    Standardized result from tool execution.

    Attributes:
        success: Whether execution succeeded
        data: Result data (tool-specific)
        error: Error message if failed
        metadata: Additional info (timing, tokens, etc.)
    """
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Dict[str, Any] = None, **kwargs) -> 'ToolResult':
        """Create successful result."""
        return cls(
            success=True,
            data=data or {},
            metadata=kwargs
        )

    @classmethod
    def fail(cls, error: str, **kwargs) -> 'ToolResult':
        """Create failed result."""
        return cls(
            success=False,
            error=error,
            metadata=kwargs
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from data dict."""
        return self.data.get(key, default)


@dataclass
class ToolSchema:
    """JSON Schema for tool parameters."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str] = field(default_factory=list)

    def to_function_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required
            }
        }


class ITool(ABC):
    """
    Interface for individual tools.

    Tools are atomic operations that can be invoked by agents.

    Example:
        class ReadFileTool(ITool):
            @property
            def name(self) -> str:
                return "read_file"

            @property
            def description(self) -> str:
                return "Read contents of a file"

            async def execute(self, **params) -> ToolResult:
                path = params.get("path")
                content = Path(path).read_text()
                return ToolResult.ok({"content": content})
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (unique identifier)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass

    @property
    def category(self) -> ToolCategory:
        """Tool category."""
        return ToolCategory.CUSTOM

    @property
    def schema(self) -> Optional[ToolSchema]:
        """Parameter schema for validation."""
        return None

    @abstractmethod
    async def execute(self, **params) -> ToolResult:
        """
        Execute the tool.

        Args:
            **params: Tool-specific parameters

        Returns:
            ToolResult with execution outcome
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Validate parameters before execution.

        Returns:
            Error message if invalid, None if valid
        """
        return None


class IToolExecutor(ABC):
    """
    Interface for tool execution engine.

    Manages tool registration and execution.

    Example:
        executor = MyToolExecutor()
        executor.register(ReadFileTool())
        result = await executor.execute("read_file", path="main.py")
    """

    @abstractmethod
    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            params: Tool parameters

        Returns:
            Execution result
        """
        pass

    @abstractmethod
    def register(self, tool: ITool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register
        """
        pass

    @abstractmethod
    def unregister(self, tool_name: str) -> bool:
        """
        Unregister a tool.

        Args:
            tool_name: Name of tool to remove

        Returns:
            True if tool was removed
        """
        pass

    @abstractmethod
    def get(self, tool_name: str) -> Optional[ITool]:
        """
        Get tool by name.

        Args:
            tool_name: Tool name

        Returns:
            Tool instance or None
        """
        pass

    @abstractmethod
    def get_available_tools(self) -> List[str]:
        """
        Get list of available tool names.

        Returns:
            List of registered tool names
        """
        pass

    @abstractmethod
    def get_schemas(self) -> List[ToolSchema]:
        """
        Get schemas for all registered tools.

        Returns:
            List of tool schemas for LLM function calling
        """
        pass

    def get_by_category(self, category: ToolCategory) -> List[ITool]:
        """
        Get tools by category.

        Default implementation filters all tools.
        """
        return [
            self.get(name) for name in self.get_available_tools()
            if self.get(name) and self.get(name).category == category
        ]


__all__ = [
    'ITool',
    'IToolExecutor',
    'ToolResult',
    'ToolSchema',
    'ToolCategory',
]
