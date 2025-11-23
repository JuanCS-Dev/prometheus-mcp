"""Lazy loaded DevSquad plugin."""

class Plugin:
    """DevSquad orchestration plugin."""
    
    def __init__(self):
        self.squad = None
        self.mcp_client = None
        
    async def initialize(self) -> None:
        """Initialize DevSquad."""
        from qwen_dev_cli.orchestration.squad import DevSquad
        from qwen_dev_cli.core.mcp_client import MCPClient
        from qwen_dev_cli.tools.base import ToolRegistry
        
        # We need a registry for MCP
        # Ideally we should share the registry from tools_plugin
        # For now, creating a new one or we need a way to pass dependencies
        registry = ToolRegistry() 
        
        self.mcp_client = MCPClient(registry)
        
        # We need LLM client too. 
        # This shows a dependency injection need in the plugin system.
        # For simplicity in this phase, we'll load default LLM here if needed
        # or expect it to be passed.
        # Let's use lazy load of LLM here as well
        from qwen_dev_cli.core.llm import llm_client
        
        self.squad = DevSquad(llm_client, self.mcp_client)
        
    async def shutdown(self) -> None:
        pass
