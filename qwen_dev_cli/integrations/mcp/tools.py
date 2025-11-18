"""MCP Tools - Auto-expose CLI tools as MCP tools."""
import logging
from typing import Any, Optional
from qwen_dev_cli.tools.base import ToolRegistry
from qwen_dev_cli.integrations.mcp.shell_handler import ShellManager

logger = logging.getLogger(__name__)


class MCPToolsAdapter:
    """Adapter to expose CLI tools as MCP tools."""
    
    def __init__(self, registry: ToolRegistry, shell_manager: ShellManager):
        self.registry = registry
        self.shell_manager = shell_manager
        self._mcp_tools = {}
    
    def register_all(self, mcp_server):
        """Register all CLI tools as MCP tools."""
        for tool_name, tool_fn in self.registry.get_all_tools().items():
            self._register_tool(mcp_server, tool_name, tool_fn)
        
        self._register_shell_tools(mcp_server)
        logger.info(f"Registered {len(self._mcp_tools)} MCP tools")
    
    def _register_tool(self, mcp_server, tool_name: str, tool_fn):
        """Register single CLI tool as MCP tool."""
        
        @mcp_server.tool(name=tool_name)
        async def mcp_tool_wrapper(**kwargs) -> dict:
            """Auto-generated MCP tool wrapper."""
            try:
                result = await tool_fn(**kwargs)
                return {
                    "success": True,
                    "tool": tool_name,
                    "result": result
                }
            except Exception as e:
                logger.error(f"Tool {tool_name} error: {e}")
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": str(e)
                }
        
        self._mcp_tools[tool_name] = mcp_tool_wrapper
    
    def _register_shell_tools(self, mcp_server):
        """Register reverse shell tools."""
        
        @mcp_server.tool(name="create_shell")
        async def create_shell(session_id: str = "default", cwd: Optional[str] = None) -> dict:
            """Create interactive shell session."""
            try:
                session = await self.shell_manager.create_session(session_id, cwd)
                return {
                    "success": True,
                    "session_id": session_id,
                    "cwd": session.cwd,
                    "message": "Shell session created. Use execute_shell to run commands."
                }
            except Exception as e:
                logger.error(f"Failed to create shell: {e}")
                return {"success": False, "error": str(e)}
        
        @mcp_server.tool(name="execute_shell")
        async def execute_shell(
            command: str,
            session_id: str = "default",
            timeout: float = 30.0
        ) -> dict:
            """Execute command in shell session."""
            try:
                session = self.shell_manager.get_session(session_id)
                if not session:
                    session = await self.shell_manager.create_session(session_id)
                
                result = await session.execute(command, timeout)
                return {
                    "success": True,
                    **result
                }
            except Exception as e:
                logger.error(f"Shell execution error: {e}")
                return {"success": False, "error": str(e)}
        
        @mcp_server.tool(name="close_shell")
        async def close_shell(session_id: str = "default") -> dict:
            """Close shell session."""
            try:
                await self.shell_manager.close_session(session_id)
                return {
                    "success": True,
                    "session_id": session_id,
                    "message": "Shell session closed"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @mcp_server.tool(name="list_shell_sessions")
        async def list_shell_sessions() -> dict:
            """List active shell sessions."""
            sessions = [
                {"session_id": sid, "cwd": s.cwd, "pid": s.pid}
                for sid, s in self.shell_manager.sessions.items()
            ]
            return {
                "success": True,
                "sessions": sessions,
                "count": len(sessions)
            }
        
        self._mcp_tools.update({
            "create_shell": create_shell,
            "execute_shell": execute_shell,
            "close_shell": close_shell,
            "list_shell_sessions": list_shell_sessions
        })
