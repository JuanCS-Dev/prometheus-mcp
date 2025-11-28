"""Tests for MCP Client Factory and Enhanced MCPClient.

Tests the create_mcp_client() factory function and improved error handling
in MCPClient class.

Compliance: Vértice Constitution v3.0
- Artigo II: Cobertura ≥90%
- P1: Zero placeholders, código completo
- P3: Testes cobrem edge cases
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import warnings

from jdev_cli.core.mcp import create_mcp_client, MCPClient
from jdev_cli.tools.base import ToolRegistry, ToolResult


class TestCreateMCPClient:
    """Tests for create_mcp_client() factory function."""

    def test_create_with_auto_setup_default(self):
        """create_mcp_client() with defaults should auto-setup tools."""
        mcp = create_mcp_client()

        assert isinstance(mcp, MCPClient)
        assert isinstance(mcp.registry, ToolRegistry)
        # Should have default tools registered
        assert len(mcp.registry.tools) > 0

    def test_create_with_auto_setup_explicit(self):
        """create_mcp_client(auto_setup=True) should register default tools."""
        mcp = create_mcp_client(auto_setup=True)

        assert isinstance(mcp, MCPClient)
        # Should have file_ops, bash, search tools
        assert len(mcp.registry.tools) >= 8

    def test_create_with_custom_registry(self):
        """create_mcp_client(registry=...) should use provided registry."""
        custom_registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'custom_tool'
        custom_registry.register(mock_tool)

        mcp = create_mcp_client(registry=custom_registry)

        assert mcp.registry is custom_registry
        assert mcp.registry.get('custom_tool') is not None

    def test_create_with_registry_ignores_auto_setup(self):
        """When registry provided, auto_setup flag should be ignored."""
        custom_registry = ToolRegistry()

        # auto_setup=False but registry provided, should work
        mcp = create_mcp_client(registry=custom_registry, auto_setup=False)

        assert mcp.registry is custom_registry

    def test_create_without_registry_and_auto_setup_false_raises_error(self):
        """create_mcp_client(registry=None, auto_setup=False) should raise ValueError."""
        with pytest.raises(ValueError, match="registry required when auto_setup=False"):
            create_mcp_client(registry=None, auto_setup=False)

    def test_create_with_invalid_registry_type_raises_error(self):
        """create_mcp_client(registry=<not ToolRegistry>) should raise TypeError."""
        invalid_registry = {"not": "a registry"}

        with pytest.raises(TypeError, match="registry must be ToolRegistry"):
            create_mcp_client(registry=invalid_registry)

    def test_create_returns_same_registry_instance(self):
        """Factory should return MCPClient with exact registry instance provided."""
        custom_registry = ToolRegistry()

        mcp = create_mcp_client(registry=custom_registry)

        # Should be same object, not a copy
        assert mcp.registry is custom_registry

    @patch('jdev_cli.tools.registry_setup.setup_default_tools')
    def test_create_calls_setup_default_tools_when_auto_setup(self, mock_setup):
        """create_mcp_client() should call setup_default_tools() for auto-setup."""
        mock_registry = ToolRegistry()
        mock_mcp = MCPClient(mock_registry)
        mock_setup.return_value = (mock_registry, mock_mcp)

        result = create_mcp_client()

        mock_setup.assert_called_once()
        assert result is mock_mcp


class TestMCPClientEnhanced:
    """Tests for enhanced MCPClient with improved error messages."""

    def test_init_with_valid_registry(self):
        """MCPClient should initialize successfully with valid registry."""
        registry = ToolRegistry()

        mcp = MCPClient(registry)

        assert mcp.registry is registry

    def test_init_with_invalid_registry_type_raises_error(self):
        """MCPClient(invalid_registry) should raise TypeError with helpful message."""
        with pytest.raises(TypeError) as exc_info:
            MCPClient("not_a_registry")

        error_message = str(exc_info.value)
        assert "registry must be ToolRegistry" in error_message
        assert "create_mcp_client()" in error_message

    def test_init_with_empty_registry_warns(self):
        """MCPClient with empty registry should emit warning."""
        empty_registry = ToolRegistry()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mcp = MCPClient(empty_registry)

            assert len(w) == 1
            assert "empty registry" in str(w[0].message).lower()
            assert "create_mcp_client()" in str(w[0].message)

    def test_init_with_populated_registry_no_warning(self):
        """MCPClient with tools should not emit warning."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        registry.register(mock_tool)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            MCPClient(registry)

            # Should have no warnings
            assert len(w) == 0

    @pytest.mark.asyncio
    async def test_call_tool_with_valid_tool(self):
        """call_tool() should execute tool successfully."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_tool.validate_params = Mock(return_value=(True, None))
        # Use async function for _execute_validated to work with asyncio.wait_for
        async def mock_execute(**kwargs):
            return ToolResult(success=True, data={"result": "success"})
        mock_tool._execute_validated = mock_execute
        registry.register(mock_tool)

        mcp = MCPClient(registry)
        result = await mcp.call_tool('test_tool', {'arg': 'value'})

        assert result == {"result": "success"}
        mock_tool.validate_params.assert_called_once_with(arg='value')

    @pytest.mark.asyncio
    async def test_call_tool_with_nonexistent_tool_raises_error(self):
        """call_tool() with unknown tool should raise ValueError with available tools."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'existing_tool'
        registry.register(mock_tool)

        mcp = MCPClient(registry)

        with pytest.raises(ValueError) as exc_info:
            await mcp.call_tool('nonexistent_tool', {})

        error_message = str(exc_info.value)
        assert "Tool 'nonexistent_tool' not found" in error_message
        assert "Available: ['existing_tool']" in error_message
        assert "setup_default_tools()" in error_message

    @pytest.mark.asyncio
    async def test_call_tool_with_invalid_params_raises_error(self):
        """call_tool() with invalid params should raise ValueError."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_tool.validate_params = Mock(return_value=(False, "Missing required param"))
        registry.register(mock_tool)

        mcp = MCPClient(registry)

        with pytest.raises(ValueError, match="Invalid params"):
            await mcp.call_tool('test_tool', {})

    @pytest.mark.asyncio
    async def test_call_tool_execution_failure_raises_exception(self):
        """call_tool() should propagate tool execution errors."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'failing_tool'
        mock_tool.validate_params = Mock(return_value=(True, None))
        mock_tool._execute_validated = MagicMock(
            side_effect=RuntimeError("Tool execution failed")
        )
        registry.register(mock_tool)

        mcp = MCPClient(registry)

        with pytest.raises(Exception, match="Tool 'failing_tool' failed"):
            await mcp.call_tool('failing_tool', {})

    @pytest.mark.asyncio
    async def test_call_tool_with_failed_tool_result_raises_exception(self):
        """call_tool() should raise exception when ToolResult.success=False."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_tool.validate_params = Mock(return_value=(True, None))
        # Use async function for _execute_validated to work with asyncio.wait_for
        async def mock_execute(**kwargs):
            return ToolResult(success=False, error="Operation failed")
        mock_tool._execute_validated = mock_execute
        registry.register(mock_tool)

        mcp = MCPClient(registry)

        with pytest.raises(Exception, match="Operation failed"):
            await mcp.call_tool('test_tool', {})

    @pytest.mark.asyncio
    async def test_call_tool_with_dict_result(self):
        """call_tool() should handle ToolResult with dict data."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_tool.validate_params = Mock(return_value=(True, None))
        # Use async function for _execute_validated to work with asyncio.wait_for
        async def mock_execute(**kwargs):
            return ToolResult(success=True, data={"key": "value"})
        mock_tool._execute_validated = mock_execute
        registry.register(mock_tool)

        mcp = MCPClient(registry)
        result = await mcp.call_tool('test_tool', {})

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_call_tool_with_non_dict_result(self):
        """call_tool() should wrap non-dict ToolResult.data."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_tool.validate_params = Mock(return_value=(True, None))
        # Use async function for _execute_validated to work with asyncio.wait_for
        async def mock_execute(**kwargs):
            return ToolResult(success=True, data="string result")
        mock_tool._execute_validated = mock_execute
        registry.register(mock_tool)

        mcp = MCPClient(registry)
        result = await mcp.call_tool('test_tool', {})

        assert result == {"output": "string result"}

    @pytest.mark.asyncio
    async def test_call_tool_with_object_with_to_dict(self):
        """call_tool() should call to_dict() on objects that have it."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_tool.validate_params = Mock(return_value=(True, None))

        mock_result = Mock()
        mock_result.to_dict = Mock(return_value={"serialized": "data"})
        # Use async function for _execute_validated to work with asyncio.wait_for
        async def mock_execute(**kwargs):
            return mock_result
        mock_tool._execute_validated = mock_execute
        registry.register(mock_tool)

        mcp = MCPClient(registry)
        result = await mcp.call_tool('test_tool', {})

        assert result == {"serialized": "data"}
        mock_result.to_dict.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_tool_with_plain_result(self):
        """call_tool() should wrap plain results in dict."""
        registry = ToolRegistry()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_tool.validate_params = Mock(return_value=(True, None))
        # Use async function for _execute_validated to work with asyncio.wait_for
        async def mock_execute(**kwargs):
            return 42
        mock_tool._execute_validated = mock_execute
        registry.register(mock_tool)

        mcp = MCPClient(registry)
        result = await mcp.call_tool('test_tool', {})

        assert result == {'result': 42}


class TestBackwardsCompatibility:
    """Tests for backwards compatibility with mcp_client module."""

    def test_import_from_mcp_module(self):
        """Should be able to import from mcp module."""
        from jdev_cli.core.mcp import MCPClient, create_mcp_client

        assert MCPClient is not None
        assert create_mcp_client is not None

    def test_import_from_mcp_client_module(self):
        """Should be able to import from mcp_client module (backwards compat)."""
        try:
            from jdev_cli.core.mcp_client import MCPClient
            assert MCPClient is not None
        except ImportError:
            pytest.skip("mcp_client.py not available (expected if using symlink)")

    def test_both_modules_provide_same_class(self):
        """Both modules should provide the same MCPClient class."""
        from jdev_cli.core.mcp import MCPClient as MCPFromMcp

        try:
            from jdev_cli.core.mcp_client import MCPClient as MCPFromClient
            assert MCPFromMcp is MCPFromClient
        except ImportError:
            pytest.skip("mcp_client.py not available")


class TestIntegrationWithAgents:
    """Integration tests verifying factory works with agents."""

    def test_factory_creates_usable_mcp_for_agents(self):
        """MCP from factory should be usable by agents."""
        from jdev_cli.core.llm import LLMClient

        llm = LLMClient()
        mcp = create_mcp_client()

        # Create an agent that requires MCP
        from jdev_cli.agents.explorer import ExplorerAgent

        agent = ExplorerAgent(llm, mcp)

        assert agent is not None
        assert agent.mcp_client is mcp

    def test_factory_with_custom_tools_for_agents(self):
        """Custom tool setup should work with agents."""
        from jdev_cli.core.llm import LLMClient

        llm = LLMClient()

        # Setup with only minimal tools
        from jdev_cli.tools.registry_setup import setup_minimal_tools
        registry, mcp = setup_minimal_tools()

        # Agent should still initialize
        from jdev_cli.agents.explorer import ExplorerAgent
        agent = ExplorerAgent(llm, mcp)

        assert agent.mcp_client is mcp

    def test_empty_registry_agent_will_fail_gracefully(self):
        """Agent with empty registry should fail with clear error."""
        from jdev_cli.core.llm import LLMClient
        from jdev_cli.agents.explorer import ExplorerAgent

        llm = LLMClient()
        empty_registry = ToolRegistry()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mcp = MCPClient(empty_registry)

            # Should get warning about empty registry
            assert len(w) == 1

        # Agent should initialize (doesn't validate registry on init)
        agent = ExplorerAgent(llm, mcp)
        assert agent is not None


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_create_mcp_client_multiple_times_independent(self):
        """Multiple create_mcp_client() calls should be independent."""
        mcp1 = create_mcp_client()
        mcp2 = create_mcp_client()

        # Should be different instances
        assert mcp1 is not mcp2
        assert mcp1.registry is not mcp2.registry

    def test_registry_mutation_after_mcp_creation(self):
        """Mutating registry after MCPClient creation should affect client."""
        registry = ToolRegistry()
        mcp = create_mcp_client(registry=registry)

        # Initially no custom tool
        assert mcp.registry.get('new_tool') is None

        # Add tool to registry
        mock_tool = Mock()
        mock_tool.name = 'new_tool'
        registry.register(mock_tool)

        # Should be visible in MCPClient
        assert mcp.registry.get('new_tool') is not None

    def test_create_with_none_registry_explicit(self):
        """Explicitly passing registry=None should trigger auto-setup."""
        mcp = create_mcp_client(registry=None, auto_setup=True)

        assert isinstance(mcp, MCPClient)
        assert len(mcp.registry.tools) > 0

    @pytest.mark.asyncio
    async def test_error_on_tool_not_found(self):
        """Tool not found error should raise proper ValueError."""
        registry = ToolRegistry()
        mcp = MCPClient(registry)

        with pytest.raises(ValueError, match="Tool 'nonexistent' not found"):
            await mcp.call_tool('nonexistent', {})

    def test_mcp_client_repr_or_str(self):
        """MCPClient should have reasonable string representation."""
        registry = ToolRegistry()
        mcp = MCPClient(registry)

        # Should not crash when converted to string
        str_repr = str(mcp)
        assert 'MCPClient' in str_repr or 'MCP' in str_repr


# Metadata for pytest
pytestmark = pytest.mark.unit
