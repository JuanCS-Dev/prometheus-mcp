"""Code execution tools."""

import subprocess
import asyncio
from typing import Optional

from .base import Tool, ToolResult, ToolCategory
from .validated import ValidatedTool
from ..core.validation import Required, TypeCheck


class BashCommandTool(ValidatedTool):
    """Execute bash command."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.EXECUTION
        self.description = "Execute shell command safely"
        self.parameters = {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
                "required": True
            },
            "cwd": {
                "type": "string",
                "description": "Working directory",
                "required": False
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "required": False
            }
        }
    def get_validators(self):
        """Validate parameters."""
        return {}

    
    async def _execute_validated(self, command: str, cwd: Optional[str] = None, timeout: int = 30) -> ToolResult:
        """Execute bash command."""
        try:
            # Check for dangerous commands
            dangerous = ['rm -rf /', 'chmod -R 777', 'dd if=', ':(){:|:&};:']
            if any(d in command for d in dangerous):
                return ToolResult(
                    success=False,
                    error=f"Dangerous command blocked: {command}"
                )
            
            # Execute command
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
                
                return ToolResult(
                    success=proc.returncode == 0,
                    data={
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else "",
                        "exit_code": proc.returncode
                    },
                    metadata={
                        "command": command,
                        "cwd": cwd or ".",
                        "exit_code": proc.returncode
                    }
                )
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout}s"
                )
                
        except Exception as e:
            return ToolResult(success=False, error=str(e))
