"""CLI Adapter for streaming execution."""

import asyncio
from typing import AsyncIterator, Dict, Any
from pathlib import Path


class CLIAdapter:
    """Simple adapter for Gradio UI (Phase 1: MVP)."""
    
    def __init__(self):
        """Initialize adapter."""
        self.commands_executed = 0
        self.tokens_used = 0
    
    async def execute_streaming(
        self, 
        user_input: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute command with streaming updates.
        
        Yields:
            Dict with keys: type, content, metadata
        """
        # Yield thinking status
        yield {
            "type": "thinking",
            "content": "Processing request...",
            "metadata": {"progress": 0.1}
        }
        
        # Simulate processing
        await asyncio.sleep(0.5)
        
        try:
            # Phase 1: Simple echo response (will integrate real CLI later)
            response = f"✓ Received: {user_input}\n\n"
            response += "This is a minimal working prototype.\n"
            response += "Real CLI integration coming in Phase 2!"
            
            self.commands_executed += 1
            self.tokens_used += len(user_input) * 2  # Rough estimate
            
            # Yield result
            yield {
                "type": "result",
                "content": response,
                "metadata": {"progress": 1.0, "success": True}
            }
            
        except Exception as e:
            # Yield error
            yield {
                "type": "error",
                "content": f"Error: {str(e)}",
                "metadata": {"progress": 1.0, "success": False}
            }
    
    def get_session_state(self) -> Dict[str, Any]:
        """Get current session state."""
        return {
            "initialized": True,
            "cwd": str(Path.cwd()),
            "tokens_used": self.tokens_used,
            "commands_executed": self.commands_executed
        }
