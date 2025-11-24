"""MCP Client Adapter with Developer-Friendly Factory.

Philosophy (Boris Cherny):
    - Explicit is better than implicit
    - Fail fast with clear error messages
    - Type-safe interfaces
    - Zero-config convenience functions

Compliance: Vértice Constitution v3.0 - Artigo IX, P2, P3
"""

from typing import Any, Dict, Optional, TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from qwen_dev_cli.tools.base import ToolRegistry, ToolResult


def create_mcp_client(
    registry: Optional['ToolRegistry'] = None,
    auto_setup: bool = True
) -> 'MCPClient':
    """Create MCP client with optional auto-setup (RECOMMENDED).

    Args:
        registry: Pre-configured tool registry
        auto_setup: Auto-setup default tools when registry=None

    Returns:
        Configured MCPClient

    Raises:
        ValueError: If registry=None and auto_setup=False

    Example:
        >>> from qwen_dev_cli.core.mcp import create_mcp_client
        >>> mcp = create_mcp_client()  # Auto-setup
    """
    if registry is None:
        if not auto_setup:
            raise ValueError(
                "registry required when auto_setup=False. "
                "Quick start: mcp = create_mcp_client()"
            )

        from qwen_dev_cli.tools.registry_setup import setup_default_tools
        registry, mcp = setup_default_tools()
        return mcp

    from qwen_dev_cli.tools.base import ToolRegistry

    if not isinstance(registry, ToolRegistry):
        raise TypeError(
            f"registry must be ToolRegistry, got {type(registry).__name__}"
        )

    return MCPClient(registry)


class MCPClient:
    """Adapter for ToolRegistry to match MCP interface.

    PREFER: Use create_mcp_client() factory instead of direct instantiation.
    """

    def __init__(self, registry: 'ToolRegistry'):
        """Initialize MCP client."""
        from qwen_dev_cli.tools.base import ToolRegistry

        if not isinstance(registry, ToolRegistry):
            raise TypeError(
                f"registry must be ToolRegistry, got {type(registry).__name__}. "
                f"Use: from qwen_dev_cli.core.mcp import create_mcp_client; "
                f"mcp = create_mcp_client()"
            )

        self.registry = registry

        if len(registry.tools) == 0:
            warnings.warn(
                "MCPClient created with empty registry. "
                "Agents will fail. Use create_mcp_client() for auto-setup.",
                UserWarning,
                stacklevel=2
            )

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name."""
        tool = self.registry.get(tool_name)
        if not tool:
            available = list(self.registry.tools.keys())
            raise ValueError(
                f"Tool '{tool_name}' not found. "
                f"Available: {available}. "
                f"Use setup_default_tools() to register tools."
            )

        is_valid, error = tool.validate_params(**arguments)
        if not is_valid:
            raise ValueError(f"Invalid params for '{tool_name}': {error}")

        try:
            result = await tool._execute_validated(**arguments)
        except Exception as e:
            raise Exception(f"Tool '{tool_name}' failed: {str(e)}") from e

        from qwen_dev_cli.tools.base import ToolResult

        if isinstance(result, ToolResult):
            if not result.success:
                raise Exception(result.error or f"Tool '{tool_name}' failed")
            return result.data if isinstance(result.data, dict) else {"output": result.data}

        if hasattr(result, 'to_dict'):
            return result.to_dict()
        return {'result': result}


__all__ = ['MCPClient', 'create_mcp_client']
