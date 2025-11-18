"""MCP Server - FastMCP-based server for Claude Desktop integration."""
import asyncio
import logging
from typing import Optional
from fastmcp import FastMCP
from qwen_dev_cli.tools.base import ToolRegistry
from qwen_dev_cli.tools.registry_helper import get_default_registry
from qwen_dev_cli.integrations.mcp.config import MCPConfig
from qwen_dev_cli.integrations.mcp.shell_handler import ShellManager
from qwen_dev_cli.integrations.mcp.tools import MCPToolsAdapter

logger = logging.getLogger(__name__)


class QwenMCPServer:
    """MCP Server for Qwen Dev CLI."""
    
    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or MCPConfig.from_env()
        self.mcp = FastMCP("Qwen Dev CLI")
        self.shell_manager = ShellManager()
        self.tools_adapter: Optional[MCPToolsAdapter] = None
        self._running = False
    
    def initialize(self, registry: ToolRegistry):
        """Initialize server with tool registry."""
        self.tools_adapter = MCPToolsAdapter(registry, self.shell_manager)
        self.tools_adapter.register_all(self.mcp)
        
        logger.info(f"MCP Server initialized with {len(registry.get_all_tools())} tools")
    
    async def start(self):
        """Start MCP server."""
        if not self.config.enabled:
            logger.info("MCP server disabled in config")
            return
        
        if self._running:
            logger.warning("MCP server already running")
            return
        
        try:
            self._running = True
            logger.info(f"Starting MCP server on {self.config.host}:{self.config.port}")
            
            await self.mcp.run(
                transport="stdio",
            )
            
        except Exception as e:
            logger.error(f"MCP server error: {e}")
            self._running = False
            raise
    
    async def stop(self):
        """Stop MCP server."""
        if not self._running:
            return
        
        logger.info("Stopping MCP server...")
        self._running = False
        
        await self.shell_manager.close_all()
        logger.info("MCP server stopped")
    
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running


async def run_mcp_server(registry: ToolRegistry, config: Optional[MCPConfig] = None):
    """Run MCP server (entry point for standalone mode)."""
    server = QwenMCPServer(config)
    server.initialize(registry)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await server.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from qwen_dev_cli.tools.base import get_default_registry
    
    config = MCPConfig.from_env()
    config.enabled = True
    
    registry = get_default_registry()
    
    asyncio.run(run_mcp_server(registry, config))
