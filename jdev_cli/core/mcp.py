"""MCP Client Adapter with Developer-Friendly Factory.

Philosophy (Boris Cherny):
    - Explicit is better than implicit
    - Fail fast with clear error messages
    - Type-safe interfaces
    - Zero-config convenience functions

Compliance: Vértice Constitution v3.0 - Artigo IX, P2, P3

CHAOS ORCHESTRATOR - RESILIENCE ENGINEERING (Nov 2025):
    - Circuit Breaker pattern for fault tolerance
    - Timeout protection on tool calls
    - Graceful fallback for failures
"""

import asyncio
import time
from typing import Any, Dict, Optional, TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from jdev_cli.tools.base import ToolRegistry

# Import circuit breaker from llm_client
from jdev_tui.core.llm_client import CircuitBreaker, CircuitBreakerConfig


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
        >>> from jdev_cli.core.mcp import create_mcp_client
        >>> mcp = create_mcp_client()  # Auto-setup
    """
    if registry is None:
        if not auto_setup:
            raise ValueError(
                "registry required when auto_setup=False. "
                "Quick start: mcp = create_mcp_client()"
            )

        from jdev_cli.tools.registry_setup import setup_default_tools
        registry, mcp = setup_default_tools()
        return mcp

    from jdev_cli.tools.base import ToolRegistry

    if not isinstance(registry, ToolRegistry):
        raise TypeError(
            f"registry must be ToolRegistry, got {type(registry).__name__}"
        )

    return MCPClient(registry)


class MCPClient:
    """Adapter for ToolRegistry to match MCP interface.

    PREFER: Use create_mcp_client() factory instead of direct instantiation.

    CHAOS ORCHESTRATOR Features:
    - Circuit breaker for fault tolerance
    - Timeout protection on tool calls
    - Per-tool failure tracking
    """

    # Timeout configuration
    TOOL_TIMEOUT: float = 30.0          # Default tool timeout
    DANGEROUS_TOOL_TIMEOUT: float = 60.0  # Timeout for long-running tools

    # Tools that may take longer
    LONG_RUNNING_TOOLS = {
        'bash_command', 'git_status', 'git_diff', 'git_clone',
        'web_search', 'fetch_url', 'http_request', 'download_file',
        'search_files', 'get_directory_tree',
        'prometheus_simulate', 'prometheus_execute'
    }

    def __init__(
        self,
        registry: 'ToolRegistry',
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize MCP client with resilience features."""
        from jdev_cli.tools.base import ToolRegistry

        if not isinstance(registry, ToolRegistry):
            raise TypeError(
                f"registry must be ToolRegistry, got {type(registry).__name__}. "
                f"Use: from jdev_cli.core.mcp import create_mcp_client; "
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

        # Circuit breaker for tool execution resilience
        self._circuit_breaker = CircuitBreaker(
            name="mcp_tools",
            config=circuit_breaker_config or CircuitBreakerConfig(
                failure_threshold=3,       # Open after 3 failures
                success_threshold=2,       # Close after 2 successes
                timeout=20.0,              # Try again after 20s
                half_open_max_calls=2,     # 2 test calls in half-open
            )
        )

        # Per-tool failure tracking for observability
        self._tool_stats: Dict[str, Dict[str, int]] = {}

    def _get_tool_timeout(self, tool_name: str) -> float:
        """Get appropriate timeout for a tool."""
        if tool_name in self.LONG_RUNNING_TOOLS:
            return self.DANGEROUS_TOOL_TIMEOUT
        return self.TOOL_TIMEOUT

    def _record_tool_call(self, tool_name: str, success: bool, duration: float) -> None:
        """Record tool call statistics."""
        if tool_name not in self._tool_stats:
            self._tool_stats[tool_name] = {
                'calls': 0,
                'successes': 0,
                'failures': 0,
                'total_duration': 0.0,
            }
        stats = self._tool_stats[tool_name]
        stats['calls'] += 1
        stats['total_duration'] += duration
        if success:
            stats['successes'] += 1
        else:
            stats['failures'] += 1

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with resilience features.

        Features:
        - Circuit breaker protection
        - Timeout protection
        - Per-tool statistics
        """
        start_time = time.time()

        # Check circuit breaker
        if not await self._circuit_breaker.can_execute():
            duration = time.time() - start_time
            self._record_tool_call(tool_name, False, duration)
            return {
                'error': "MCP tools temporarily unavailable (circuit breaker open)",
                'retry_after': self._circuit_breaker.config.timeout,
                'fallback': True
            }

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
            # Execute with timeout protection
            timeout = self._get_tool_timeout(tool_name)
            result = await asyncio.wait_for(
                tool._execute_validated(**arguments),
                timeout=timeout
            )

            duration = time.time() - start_time
            self._record_tool_call(tool_name, True, duration)
            self._circuit_breaker.record_success()

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self._record_tool_call(tool_name, False, duration)
            self._circuit_breaker.record_failure(f"Tool '{tool_name}' timeout after {timeout}s")
            return {
                'error': f"Tool '{tool_name}' timed out after {timeout}s",
                'timeout': True,
                'fallback': True
            }
        except Exception as e:
            duration = time.time() - start_time
            self._record_tool_call(tool_name, False, duration)
            self._circuit_breaker.record_failure(str(e))
            raise Exception(f"Tool '{tool_name}' failed: {str(e)}") from e

        from jdev_cli.tools.base import ToolResult

        if isinstance(result, ToolResult):
            if not result.success:
                raise Exception(result.error or f"Tool '{tool_name}' failed")
            return result.data if isinstance(result.data, dict) else {"output": result.data}

        if hasattr(result, 'to_dict'):
            return result.to_dict()
        return {'result': result}

    async def call_tool_with_fallback(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        fallback_fn: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Execute tool with optional fallback on failure.

        Args:
            tool_name: Tool to execute
            arguments: Tool arguments
            fallback_fn: Optional async function to call on failure

        Returns:
            Tool result or fallback result
        """
        try:
            return await self.call_tool(tool_name, arguments)
        except Exception as e:
            if fallback_fn:
                try:
                    return await fallback_fn(tool_name, arguments, e)
                except Exception as fallback_error:
                    return {
                        'error': str(e),
                        'fallback_error': str(fallback_error),
                        'fallback': True
                    }
            return {
                'error': str(e),
                'fallback': True
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Get MCP client health status for observability."""
        cb_status = self._circuit_breaker.get_status()

        # Calculate tool stats summary
        total_calls = sum(s['calls'] for s in self._tool_stats.values())
        total_failures = sum(s['failures'] for s in self._tool_stats.values())
        failure_rate = total_failures / total_calls if total_calls > 0 else 0.0

        return {
            'service': 'mcp_tools',
            'healthy': self._circuit_breaker.is_closed,
            'tools_registered': len(self.registry.tools),
            'circuit_breaker': cb_status,
            'stats': {
                'total_calls': total_calls,
                'total_failures': total_failures,
                'failure_rate': f"{failure_rate:.2%}",
                'per_tool': self._tool_stats,
            }
        }

    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker (for recovery)."""
        from jdev_tui.core.llm_client import CircuitState
        self._circuit_breaker._transition_to(CircuitState.CLOSED)


# Aliases for backward compatibility with tests
MCPManager = MCPClient  # Alias: MCPManager -> MCPClient
mcp_manager = create_mcp_client  # Alias: mcp_manager -> create_mcp_client

__all__ = ['MCPClient', 'create_mcp_client', 'MCPManager', 'mcp_manager']
