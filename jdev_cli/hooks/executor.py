"""Hook executor - runs hooks with variable substitution and safety checks."""

import asyncio
import shlex
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

from .events import HookEvent
from .context import HookContext
from .whitelist import SafeCommandWhitelist

logger = logging.getLogger(__name__)


@dataclass
class HookResult:
    """Result of a hook execution.
    
    Attributes:
        success: Whether the hook executed successfully
        command: The command that was executed
        stdout: Standard output from the command
        stderr: Standard error from the command
        exit_code: Exit code from the command
        execution_time_ms: Time taken to execute (milliseconds)
        executed_in_sandbox: Whether the command ran in sandbox
        error: Error message if execution failed
    """

    success: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0.0
    executed_in_sandbox: bool = False
    error: Optional[str] = None


class HookExecutor:
    """Executes hooks with security and performance optimization.
    
    Safe commands (whitelisted) execute directly for performance.
    Unsafe/unknown commands execute in Docker sandbox for security.
    """

    def __init__(
        self,
        sandbox_executor: Optional[object] = None,
        timeout_seconds: int = 30,
        enable_sandbox: bool = True
    ):
        """Initialize hook executor.
        
        Args:
            sandbox_executor: Optional SandboxExecutor for unsafe commands
            timeout_seconds: Maximum execution time per hook
            enable_sandbox: Whether to use sandbox for unsafe commands
        """
        self.sandbox_executor = sandbox_executor
        self.timeout_seconds = timeout_seconds
        self.enable_sandbox = enable_sandbox
        self.whitelist = SafeCommandWhitelist()

        self._execution_count = 0
        self._sandbox_count = 0
        self._direct_count = 0
        self._failed_count = 0

    async def execute_hooks(
        self,
        event: HookEvent,
        context: HookContext,
        hooks: List[str]
    ) -> List[HookResult]:
        """Execute all hooks for a given event.
        
        Args:
            event: Hook event that triggered execution
            context: Context with file information and variables
            hooks: List of hook commands to execute
            
        Returns:
            List of HookResult objects, one per hook
            
        Example:
            >>> executor = HookExecutor()
            >>> ctx = HookContext(Path("src/test.py"), "post_write")
            >>> hooks = ["black {file}", "ruff check {file}"]
            >>> results = await executor.execute_hooks(
            ...     HookEvent.POST_WRITE, ctx, hooks
            ... )
        """
        if not hooks:
            return []

        logger.info(f"Executing {len(hooks)} hooks for event: {event}")

        results = []
        for hook_command in hooks:
            result = await self.execute_hook(event, context, hook_command)
            results.append(result)

            # Log result
            if result.success:
                logger.debug(
                    f"Hook succeeded: {result.command} "
                    f"({result.execution_time_ms:.0f}ms)"
                )
            else:
                logger.warning(
                    f"Hook failed: {result.command} - {result.error}"
                )

        return results

    async def execute_hook(
        self,
        event: HookEvent,
        context: HookContext,
        command_template: str
    ) -> HookResult:
        """Execute a single hook command.
        
        Args:
            event: Hook event
            context: Execution context with variables
            command_template: Command template with variables (e.g., "black {file}")
            
        Returns:
            HookResult with execution details
        """
        import time
        start_time = time.time()

        self._execution_count += 1

        try:
            # Substitute variables
            command = self._substitute_variables(command_template, context)

            # Check if command is safe
            is_safe, reason = self.whitelist.is_safe(command)

            if is_safe:
                # Execute directly (fast path)
                result = await self._execute_direct(command, context.cwd)
                self._direct_count += 1
            elif self.enable_sandbox and self.sandbox_executor:
                # Execute in sandbox (secure path)
                result = await self._execute_sandboxed(command, context.cwd)
                self._sandbox_count += 1
            else:
                # Not safe and no sandbox available - REJECT
                self._failed_count += 1
                return HookResult(
                    success=False,
                    command=command,
                    error=f"Command not whitelisted and sandbox disabled: {reason}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time

            if not result.success:
                self._failed_count += 1

            return result

        except Exception as e:
            self._failed_count += 1
            return HookResult(
                success=False,
                command=command_template,
                error=f"Hook execution failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def _substitute_variables(
        self,
        command_template: str,
        context: HookContext
    ) -> str:
        """Substitute variables in command template.
        
        Args:
            command_template: Template with {var} placeholders
            context: Context with variable values
            
        Returns:
            Command with variables substituted
            
        Example:
            >>> ctx = HookContext(Path("src/test.py"), "post_write")
            >>> executor._substitute_variables("black {file}", ctx)
            "black src/test.py"
        """
        variables = context.get_variables()
        command = command_template

        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            command = command.replace(placeholder, var_value)

        return command

    async def _execute_direct(
        self,
        command: str,
        cwd: Path
    ) -> HookResult:
        """Execute command directly via subprocess.
        
        Args:
            command: Command to execute
            cwd: Working directory
            
        Returns:
            HookResult with execution details
        """
        try:
            # Use shlex to properly parse command
            args = shlex.split(command)

            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd)
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds
            )

            return HookResult(
                success=process.returncode == 0,
                command=command,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                exit_code=process.returncode,
                executed_in_sandbox=False
            )

        except asyncio.TimeoutError:
            return HookResult(
                success=False,
                command=command,
                error=f"Command timed out after {self.timeout_seconds}s",
                executed_in_sandbox=False
            )
        except Exception as e:
            return HookResult(
                success=False,
                command=command,
                error=str(e),
                executed_in_sandbox=False
            )

    async def _execute_sandboxed(
        self,
        command: str,
        cwd: Path
    ) -> HookResult:
        """Execute command in Docker sandbox.
        
        Args:
            command: Command to execute
            cwd: Working directory (mounted in sandbox)
            
        Returns:
            HookResult with execution details
        """
        if not self.sandbox_executor:
            return HookResult(
                success=False,
                command=command,
                error="Sandbox executor not available",
                executed_in_sandbox=False
            )

        try:
            sandbox_result = self.sandbox_executor.execute_sandboxed(
                command=command,
                cwd=cwd,
                timeout=self.timeout_seconds,
                readonly=False
            )

            return HookResult(
                success=sandbox_result.get('success', False),
                command=command,
                stdout=sandbox_result.get('output', ''),
                stderr=sandbox_result.get('output', ''),
                exit_code=sandbox_result.get('exit_code', 1),
                executed_in_sandbox=True,
                error=sandbox_result.get('error')
            )

        except Exception as e:
            return HookResult(
                success=False,
                command=command,
                error=f"Sandbox execution failed: {str(e)}",
                executed_in_sandbox=True
            )

    def get_stats(self) -> Dict[str, int]:
        """Get execution statistics.
        
        Returns:
            Dictionary with execution counts
        """
        return {
            'total_executions': self._execution_count,
            'direct_executions': self._direct_count,
            'sandboxed_executions': self._sandbox_count,
            'failed_executions': self._failed_count,
            'success_rate': (
                (self._execution_count - self._failed_count) / self._execution_count * 100
                if self._execution_count > 0 else 0
            )
        }
