"""MCP Server Configuration."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class MCPConfig:
    """MCP server configuration."""
    
    enabled: bool = False
    host: str = "localhost"
    port: int = 8765
    max_connections: int = 10
    session_timeout: int = 3600
    enable_shell: bool = True
    shell_timeout: int = 300
    allowed_commands: Optional[list[str]] = None
    
    @classmethod
    def from_env(cls) -> "MCPConfig":
        """Load config from environment variables."""
        import os
        return cls(
            enabled=os.getenv("MCP_ENABLED", "false").lower() == "true",
            host=os.getenv("MCP_HOST", "localhost"),
            port=int(os.getenv("MCP_PORT", "8765")),
            max_connections=int(os.getenv("MCP_MAX_CONN", "10")),
            session_timeout=int(os.getenv("MCP_SESSION_TIMEOUT", "3600")),
            enable_shell=os.getenv("MCP_ENABLE_SHELL", "true").lower() == "true",
            shell_timeout=int(os.getenv("MCP_SHELL_TIMEOUT", "300")),
        )
