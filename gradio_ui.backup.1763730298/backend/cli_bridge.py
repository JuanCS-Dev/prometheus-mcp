"""
CLI Backend Bridge - Connect Gradio UI to InteractiveShell
Zero duplication - uses existing CLI infrastructure.
"""
from typing import Iterator, Optional
from pathlib import Path
import sys

# Add parent to path to import qwen_dev_cli
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qwen_dev_cli.shell import InteractiveShell


class CLIBridge:
    """Bridge between Gradio UI and CLI backend."""
    
    def __init__(self):
        """Initialize CLI shell."""
        self.shell = InteractiveShell()
        
    def execute_command(self, command: str) -> Iterator[str]:
        """
        Execute command via CLI shell and stream results.
        
        Args:
            command: Natural language or system command
            
        Yields:
            Output chunks for streaming display
        """
        if not command.strip():
            yield "❌ Empty command"
            return
            
        try:
            # Process command through shell
            yield f"⏳ Processing: {command}\n"
            
            # Execute via shell (this already handles all command types)
            result = self.shell.process_command(command)
            
            # Stream result
            if result:
                yield result
            else:
                yield "✅ Command executed successfully"
                
        except Exception as e:
            yield f"❌ Error: {str(e)}"
    
    def get_context_files(self) -> list[str]:
        """Get list of files in current context."""
        return [str(f) for f in self.shell.context_manager.context_files]
    
    def get_token_usage(self) -> dict:
        """Get current token usage stats."""
        tracker = self.shell.token_tracker
        return {
            "total": tracker.total_tokens,
            "input": tracker.input_tokens,
            "output": tracker.output_tokens,
            "cost": tracker.get_total_cost()
        }
    
    def get_command_history(self) -> list[dict]:
        """Get recent command history."""
        # TODO: Add history tracking to shell
        return []
