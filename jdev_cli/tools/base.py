"""Base tool class and utilities for tool-based architecture."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum


class ToolCategory(Enum):
    """Tool categories for organization."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_MGMT = "file_mgmt"
    SEARCH = "search"
    EXECUTION = "execution"
    GIT = "git"
    CONTEXT = "context"
    SYSTEM = "system"


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def output(self) -> Any:
        """Alias for data."""
        return self.data

    @property
    def output(self) -> Any:
        """Alias for data (API compatibility)."""
        return self.data



class Tool(ABC):
    """Base class for all tools."""

    def __init__(self):
        # Convert CamelCase to snake_case for consistency
        import re
        class_name = self.__class__.__name__.replace("Tool", "")
        self.name: str = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        self.category: ToolCategory = ToolCategory.FILE_READ
        self.description: str = ""
        self.parameters: Dict[str, Any] = {}

    @abstractmethod
    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with execution outcome
        """
        raise NotImplementedError(f"{self.__class__.__name__}.execute() must be implemented")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate tool parameters.
        
        Returns:
            (is_valid, error_message)
        """
        required = [k for k, v in self.parameters.items() if v.get('required', False)]
        missing = [k for k in required if k not in kwargs]

        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"

        return True, None

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for LLM tool use."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": [k for k, v in self.parameters.items() if v.get('required', False)]
            }
        }


class ToolRegistry:
    """Registry for all available tools."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)

    def get_all(self) -> Dict[str, Tool]:
        """Get all registered tools."""
        return self.tools

    def get_schemas(self) -> list[Dict[str, Any]]:
        """Get all tool schemas for LLM."""
        return [tool.get_schema() for tool in self.tools.values()]

    def get_by_category(self, category: ToolCategory) -> list[Tool]:
        """Get all tools in a category."""
        return [t for t in self.tools.values() if t.category == category]
