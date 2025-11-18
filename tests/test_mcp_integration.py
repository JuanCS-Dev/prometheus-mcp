"""Tests for MCP integration."""
import pytest
import asyncio
from qwen_dev_cli.integrations.mcp import (
    MCPConfig,
    ShellSession,
    ShellManager,
    QwenMCPServer
)
from qwen_dev_cli.tools.registry_helper import get_default_registry


class TestMCPConfig:
    """Test MCP configuration."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = MCPConfig()
        assert config.enabled == False
        assert config.host == "localhost"
        assert config.port == 8765
        assert config.enable_shell == True
    
    def test_config_from_env(self, monkeypatch):
        """Test loading from environment."""
        monkeypatch.setenv("MCP_ENABLED", "true")
        monkeypatch.setenv("MCP_PORT", "9000")
        
        config = MCPConfig.from_env()
        assert config.enabled == True
        assert config.port == 9000


@pytest.mark.asyncio
class TestShellSession:
    """Test shell session management."""
    
    async def test_shell_session_creation(self):
        """Test creating shell session."""
        session = ShellSession("test_session")
        assert session.session_id == "test_session"
        assert session._running == False
    
    async def test_shell_execute(self):
        """Test executing command in shell."""
        session = ShellSession("test_exec")
        result = await session.execute("echo 'hello'")
        
        assert result["success"] == True
        assert "hello" in result["output"]
        assert result["session_id"] == "test_exec"
        
        await session.close()
    
    async def test_shell_multiple_commands(self):
        """Test multiple commands in same session."""
        session = ShellSession("test_multi")
        
        result1 = await session.execute("export TEST_VAR=hello")
        result2 = await session.execute("echo $TEST_VAR")
        
        assert "hello" in result2["output"]
        
        await session.close()


@pytest.mark.asyncio
class TestShellManager:
    """Test shell manager."""
    
    async def test_manager_create_session(self):
        """Test creating session via manager."""
        manager = ShellManager()
        session = await manager.create_session("managed_session")
        
        assert session.session_id == "managed_session"
        assert manager.get_session("managed_session") is not None
        
        await manager.close_all()
    
    async def test_manager_multiple_sessions(self):
        """Test managing multiple sessions."""
        manager = ShellManager()
        
        session1 = await manager.create_session("session1")
        session2 = await manager.create_session("session2")
        
        assert len(manager.sessions) == 2
        assert manager.get_session("session1") is not None
        assert manager.get_session("session2") is not None
        
        await manager.close_all()


class TestMCPServer:
    """Test MCP server initialization."""
    
    def test_server_creation(self):
        """Test creating MCP server."""
        config = MCPConfig(enabled=False)
        server = QwenMCPServer(config)
        
        assert server.config.enabled == False
        assert server.is_running() == False
    
    def test_server_initialization(self):
        """Test initializing server with registry."""
        registry = get_default_registry()
        server = QwenMCPServer()
        server.initialize(registry)
        
        assert server.tools_adapter is not None
        assert len(server.tools_adapter._mcp_tools) > 0
