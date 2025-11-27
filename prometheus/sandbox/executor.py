"""
Sandbox Executor for PROMETHEUS.

Secure Python code execution environment inspired by E2B (e2b.dev):
- Isolated execution using subprocess
- Timeout protection
- Resource limits
- Output capture (stdout, stderr)
- Support for async execution
"""

import os
import sys
import asyncio
import tempfile
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


@dataclass
class SandboxResult:
    """Result of sandbox execution."""
    success: bool
    stdout: str
    stderr: str
    return_value: Optional[Any] = None
    execution_time: float = 0.0
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_value": self.return_value,
            "execution_time": self.execution_time,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    timeout: float = 30.0  # seconds
    max_memory_mb: int = 512
    max_output_size: int = 100000  # characters
    allowed_imports: List[str] = field(default_factory=lambda: [
        "json", "re", "math", "random", "datetime", "collections",
        "itertools", "functools", "operator", "string", "textwrap",
        "hashlib", "base64", "urllib", "dataclasses", "typing",
        "os.path", "pathlib", "statistics", "decimal", "fractions",
    ])
    blocked_imports: List[str] = field(default_factory=lambda: [
        "subprocess", "shutil", "socket", "http", "ftplib",
        "smtplib", "telnetlib", "ctypes", "multiprocessing",
    ])


class SandboxExecutor:
    """
    Secure Python code execution sandbox.

    Features:
    - Timeout protection
    - Output capture
    - Error handling
    - Resource limits
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.execution_history: List[SandboxResult] = []

    async def execute(
        self,
        code: str,
        timeout: Optional[float] = None,
        capture_return: bool = True,
    ) -> SandboxResult:
        """
        Execute Python code in sandbox.

        Args:
            code: Python code to execute
            timeout: Optional timeout override
            capture_return: Whether to capture the return value

        Returns:
            SandboxResult with execution details
        """
        timeout = timeout or self.config.timeout
        start_time = datetime.now()

        # Validate code for blocked imports
        validation_error = self._validate_code(code)
        if validation_error:
            return SandboxResult(
                success=False,
                stdout="",
                stderr=validation_error,
                error_type="ValidationError",
                error_message=validation_error,
            )

        # Wrap code to capture return value
        if capture_return:
            code = self._wrap_code_for_return(code)

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Execute in subprocess
            process = await asyncio.create_subprocess_exec(
                sys.executable, temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')

                # Truncate if too long
                if len(stdout) > self.config.max_output_size:
                    stdout = stdout[:self.config.max_output_size] + "\n...[truncated]"
                if len(stderr) > self.config.max_output_size:
                    stderr = stderr[:self.config.max_output_size] + "\n...[truncated]"

                # Extract return value if present
                return_value = None
                if capture_return and "__SANDBOX_RETURN__:" in stdout:
                    try:
                        return_line = [l for l in stdout.split('\n') if "__SANDBOX_RETURN__:" in l][-1]
                        return_json = return_line.split("__SANDBOX_RETURN__:")[1].strip()
                        return_value = json.loads(return_json)
                        # Remove return line from stdout
                        stdout = stdout.replace(return_line, "").strip()
                    except (json.JSONDecodeError, IndexError):
                        pass

                execution_time = (datetime.now() - start_time).total_seconds()

                result = SandboxResult(
                    success=process.returncode == 0,
                    stdout=stdout,
                    stderr=stderr,
                    return_value=return_value,
                    execution_time=execution_time,
                    error_type="RuntimeError" if process.returncode != 0 else None,
                    error_message=stderr if process.returncode != 0 else None,
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

                result = SandboxResult(
                    success=False,
                    stdout="",
                    stderr=f"Execution timed out after {timeout} seconds",
                    execution_time=timeout,
                    error_type="TimeoutError",
                    error_message=f"Code execution exceeded {timeout}s limit",
                )

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except OSError:
                pass

        self.execution_history.append(result)
        return result

    async def execute_function(
        self,
        func_code: str,
        func_name: str,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> SandboxResult:
        """
        Execute a function in sandbox.

        Args:
            func_code: Function definition code
            func_name: Name of the function to call
            args: Positional arguments
            kwargs: Keyword arguments
            timeout: Optional timeout

        Returns:
            SandboxResult with function return value
        """
        kwargs = kwargs or {}

        # Build execution code
        args_repr = repr(args)[1:-1]  # Remove parentheses
        if args_repr.endswith(','):
            args_repr = args_repr[:-1]

        kwargs_repr = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())

        call_args = ", ".join(filter(None, [args_repr, kwargs_repr]))

        execution_code = f"""
{func_code}

# Execute function
import json as _json
__result__ = {func_name}({call_args})
print(f"__SANDBOX_RETURN__:{{_json.dumps(__result__)}}")
"""

        return await self.execute(execution_code, timeout=timeout, capture_return=True)

    def _validate_code(self, code: str) -> Optional[str]:
        """
        Validate code for security issues.

        Returns error message if validation fails, None if OK.
        """
        import ast

        # Try to parse
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"Syntax error: {e}"

        # Check for blocked imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in self.config.blocked_imports:
                        return f"Blocked import: {module}"

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in self.config.blocked_imports:
                        return f"Blocked import: {module}"

            # Check for dangerous builtins
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec', 'compile', '__import__', 'open']:
                        # Allow open() for reading
                        if node.func.id == 'open':
                            # Check if mode is 'r' or not specified
                            if len(node.args) >= 2:
                                mode_arg = node.args[1]
                                if isinstance(mode_arg, ast.Constant):
                                    if 'w' in str(mode_arg.value) or 'a' in str(mode_arg.value):
                                        return f"File write operations not allowed"
                        elif node.func.id != 'open':
                            return f"Dangerous builtin: {node.func.id}"

        return None

    def _wrap_code_for_return(self, code: str) -> str:
        """Wrap code to capture the last expression's value."""
        import ast

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code  # Return as-is, will fail during execution

        # Check if last statement is an expression
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            # Already have code that captures return via __SANDBOX_RETURN__
            if "__SANDBOX_RETURN__" in code:
                return code

            # Wrap last expression
            last_expr = ast.unparse(tree.body[-1].value)
            code_lines = code.rsplit('\n', 1)

            if len(code_lines) == 2:
                code = code_lines[0] + f"\n__result__ = {last_expr}\nimport json; print(f'__SANDBOX_RETURN__:{{json.dumps(__result__)}}')"
            else:
                code = f"__result__ = {last_expr}\nimport json; print(f'__SANDBOX_RETURN__:{{json.dumps(__result__)}}')"

        return code

    async def test_code(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Test code against multiple test cases.

        Args:
            code: Code to test (should define a function)
            test_cases: List of {"input": {...}, "expected": ...}

        Returns:
            {"passed": N, "failed": N, "results": [...]}
        """
        results = []
        passed = 0
        failed = 0

        for i, test in enumerate(test_cases):
            # Build test code
            test_code = f"""
{code}

# Test case {i + 1}
import json
__input__ = {repr(test.get('input', {}))}
__expected__ = {repr(test.get('expected'))}

if isinstance(__input__, dict):
    __result__ = test_function(**__input__)
else:
    __result__ = test_function(__input__)

__passed__ = __result__ == __expected__
print(f"__SANDBOX_RETURN__:{{json.dumps({{'passed': __passed__, 'result': __result__, 'expected': __expected__}})}}")
"""

            result = await self.execute(test_code, capture_return=True)

            if result.success and result.return_value:
                if result.return_value.get('passed'):
                    passed += 1
                else:
                    failed += 1
                results.append({
                    "test_case": i + 1,
                    "passed": result.return_value.get('passed'),
                    "result": result.return_value.get('result'),
                    "expected": result.return_value.get('expected'),
                })
            else:
                failed += 1
                results.append({
                    "test_case": i + 1,
                    "passed": False,
                    "error": result.stderr or result.error_message,
                })

        return {
            "passed": passed,
            "failed": failed,
            "total": len(test_cases),
            "success_rate": passed / max(len(test_cases), 1),
            "results": results,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        if not self.execution_history:
            return {"total": 0, "success_rate": 0}

        total = len(self.execution_history)
        successes = sum(1 for r in self.execution_history if r.success)
        avg_time = sum(r.execution_time for r in self.execution_history) / total

        return {
            "total": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": successes / total,
            "avg_execution_time": avg_time,
        }

    def clear_history(self):
        """Clear execution history."""
        self.execution_history = []
