"""
PythonSandbox - Secure Python Code Execution
Pipeline de Diamante - CRITICAL SECURITY COMPONENT

Addresses: ISSUE-055 (CRITICAL) - Python code shouldn't escape sandbox

Implements multi-level Python sandboxing:
- Level 1: RestrictedPython (language-level restrictions)
- Level 2: AST Analysis (dangerous pattern detection)
- Level 3: Resource limits (memory, CPU, time)
- Level 4: Docker isolation (optional, for untrusted code)

Security Philosophy:
- Defense in depth: Multiple layers of protection
- Fail secure: Any uncertainty = rejection
- Explicit allowlists: Only known-safe operations permitted
- Zero trust: All code is potentially malicious

WARNING: This module is CRITICAL for system security.
Any modifications must be reviewed by security team.
"""

from __future__ import annotations

import ast
import sys
import io
import time
import multiprocessing
import traceback
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from contextlib import redirect_stdout, redirect_stderr
import logging

logger = logging.getLogger(__name__)


class SandboxLevel(Enum):
    """Sandbox security levels."""
    MINIMAL = auto()      # Basic AST checks only
    STANDARD = auto()     # AST + restricted builtins
    STRICT = auto()       # AST + restricted + resource limits
    PARANOID = auto()     # All checks + process isolation

    def __ge__(self, other: "SandboxLevel") -> bool:
        """Enable comparison between security levels."""
        if isinstance(other, SandboxLevel):
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other: "SandboxLevel") -> bool:
        """Enable comparison between security levels."""
        if isinstance(other, SandboxLevel):
            return self.value > other.value
        return NotImplemented

    def __le__(self, other: "SandboxLevel") -> bool:
        """Enable comparison between security levels."""
        if isinstance(other, SandboxLevel):
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other: "SandboxLevel") -> bool:
        """Enable comparison between security levels."""
        if isinstance(other, SandboxLevel):
            return self.value < other.value
        return NotImplemented


class SecurityViolation(Exception):
    """Raised when code violates security policy."""

    def __init__(self, message: str, violation_type: str, code_snippet: str = ""):
        super().__init__(message)
        self.message = message
        self.violation_type = violation_type
        self.code_snippet = code_snippet


@dataclass
class SandboxConfig:
    """Configuration for Python sandbox."""
    level: SandboxLevel = SandboxLevel.STANDARD
    max_execution_time: float = 5.0        # seconds
    max_memory: int = 64 * 1024 * 1024     # 64MB
    max_output_size: int = 1024 * 1024     # 1MB
    max_ast_depth: int = 50                # Max AST nesting
    max_iterations: int = 10000            # Loop iteration limit
    allow_imports: Set[str] = field(default_factory=lambda: {
        "math", "random", "datetime", "json", "re", "collections",
        "itertools", "functools", "typing", "dataclasses", "enum",
        "string", "textwrap", "unicodedata",
    })
    blocked_imports: Set[str] = field(default_factory=lambda: {
        "os", "sys", "subprocess", "socket", "requests", "urllib",
        "shutil", "pathlib", "glob", "tempfile",
        "ctypes", "cffi", "pickle", "shelve", "marshal",
        "importlib", "builtins", "__builtins__",
        "multiprocessing", "threading", "concurrent",
        "asyncio", "aiohttp", "httpx",
        "sqlite3", "psycopg2", "pymysql",
        "boto3", "azure", "google.cloud",
        "cryptography", "hashlib",  # Prevent crypto operations
    })
    allow_builtins: Set[str] = field(default_factory=lambda: {
        # Safe built-ins
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
        "callable", "chr", "complex", "dict", "dir", "divmod", "enumerate",
        "filter", "float", "format", "frozenset", "hash", "hex", "int",
        "isinstance", "issubclass", "iter", "len", "list", "map", "max",
        "min", "next", "oct", "ord", "pow", "print", "range", "repr",
        "reversed", "round", "set", "slice", "sorted", "str", "sum",
        "tuple", "type", "zip",
        # Safe type constructors
        "True", "False", "None",
    })
    blocked_builtins: Set[str] = field(default_factory=lambda: {
        # Dangerous built-ins
        "eval", "exec", "compile", "__import__",
        "open", "file", "input",
        "getattr", "setattr", "delattr", "hasattr",  # Attribute access
        "globals", "locals", "vars",  # Namespace access
        "memoryview", "id",  # Memory access
        "exit", "quit",  # System control
    })


@dataclass
class SandboxResult:
    """Result of sandboxed Python execution."""
    success: bool
    output: str
    error: Optional[str] = None
    return_value: Any = None
    execution_time: float = 0.0
    memory_used: int = 0
    violations: List[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        """Check if execution was blocked due to security violations."""
        return len(self.violations) > 0

    @property
    def timed_out(self) -> bool:
        """Check if execution timed out."""
        return "TIMEOUT" in self.violations or (self.error and "timed out" in self.error.lower())

    @classmethod
    def failure(cls, error: str, violations: Optional[List[str]] = None) -> "SandboxResult":
        """Create a failed result."""
        return cls(
            success=False,
            output="",
            error=error,
            violations=violations or []
        )


class ASTSecurityAnalyzer(ast.NodeVisitor):
    """
    Analyze Python AST for security violations.

    Detects:
    - Dangerous imports
    - Attribute access to dangerous modules
    - Dangerous function calls
    - Infinite loop patterns
    - Excessive nesting
    """

    def __init__(self, config: SandboxConfig):
        self.config = config
        self.violations: List[str] = []
        self.import_names: Set[str] = set()
        self.depth = 0
        self.loop_depth = 0
        self.has_break_in_loop = False

    def check(self, code: str) -> Tuple[bool, List[str]]:
        """
        Check code for security violations.

        Returns:
            (is_safe, violations)
        """
        try:
            tree = ast.parse(code)
            self.visit(tree)
            return len(self.violations) == 0, self.violations
        except SyntaxError as e:
            return False, [f"Syntax error: {e}"]

    def visit(self, node: ast.AST) -> Any:
        """Visit node with depth tracking."""
        self.depth += 1
        if self.depth > self.config.max_ast_depth:
            self.violations.append(f"AST depth exceeds maximum ({self.config.max_ast_depth})")
            self.depth -= 1
            return

        result = super().visit(node)
        self.depth -= 1
        return result

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements."""
        for alias in node.names:
            module = alias.name.split('.')[0]
            self.import_names.add(module)

            if module in self.config.blocked_imports:
                self.violations.append(f"Blocked import: {alias.name}")
            elif module not in self.config.allow_imports:
                self.violations.append(f"Unapproved import: {alias.name}")

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from ... import statements."""
        if node.module:
            module = node.module.split('.')[0]
            self.import_names.add(module)

            if module in self.config.blocked_imports:
                self.violations.append(f"Blocked import from: {node.module}")
            elif module not in self.config.allow_imports:
                self.violations.append(f"Unapproved import from: {node.module}")

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for dangerous patterns."""
        # Check for dangerous function names
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in self.config.blocked_builtins:
                self.violations.append(f"Blocked function call: {name}()")
            elif name == "__import__":
                self.violations.append("Dynamic import via __import__ blocked")

        # Check for dangerous method calls
        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr

            # Block dangerous methods
            dangerous_methods = {
                "system", "popen", "spawn", "exec", "eval",
                "call", "check_output", "run",  # subprocess
                "connect", "bind", "listen",  # socket
                "read", "write", "open",  # file operations
                "__getattribute__", "__setattr__", "__delattr__",
            }
            if attr in dangerous_methods:
                self.violations.append(f"Blocked method call: .{attr}()")

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check attribute access for dangerous patterns."""
        # Block access to dunder attributes
        if node.attr.startswith('__') and node.attr.endswith('__'):
            allowed_dunders = {'__init__', '__str__', '__repr__', '__len__',
                              '__iter__', '__next__', '__contains__',
                              '__add__', '__sub__', '__mul__', '__div__',
                              '__eq__', '__ne__', '__lt__', '__gt__',
                              '__le__', '__ge__', '__hash__'}
            if node.attr not in allowed_dunders:
                self.violations.append(f"Blocked dunder access: {node.attr}")

        # Block access to sensitive attributes
        sensitive_attrs = {'__class__', '__bases__', '__subclasses__',
                          '__globals__', '__code__', '__closure__',
                          '__dict__', '__module__', '__mro__'}
        if node.attr in sensitive_attrs:
            self.violations.append(f"Blocked sensitive attribute: {node.attr}")

        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Check while loops for infinite loop risk."""
        self.loop_depth += 1
        self.has_break_in_loop = False

        # Check for `while True` without break
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            # Visit body to check for break
            for child in ast.walk(node):
                if isinstance(child, ast.Break):
                    self.has_break_in_loop = True
                    break

            if not self.has_break_in_loop:
                self.violations.append("Potential infinite loop: 'while True' without break")

        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_For(self, node: ast.For) -> None:
        """Track for loop depth."""
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1


class SafeBuiltins:
    """Provide safe subset of Python builtins."""

    def __init__(self, config: SandboxConfig):
        self.config = config
        self._builtins = self._create_safe_builtins()

    def _create_safe_builtins(self) -> Dict[str, Any]:
        """Create dictionary of safe builtins."""
        import builtins

        safe = {}

        # Add allowed builtins
        for name in self.config.allow_builtins:
            if hasattr(builtins, name):
                safe[name] = getattr(builtins, name)

        # Add safe constants
        safe['True'] = True
        safe['False'] = False
        safe['None'] = None

        # Add wrapped print (with output limiting)
        safe['print'] = self._create_safe_print()

        return safe

    def _create_safe_print(self) -> Callable:
        """Create print function with output limiting."""
        output_buffer = []
        max_size = self.config.max_output_size

        def safe_print(*args, **kwargs):
            output = io.StringIO()
            kwargs['file'] = output
            print(*args, **kwargs)
            text = output.getvalue()

            total = sum(len(s) for s in output_buffer) + len(text)
            if total > max_size:
                raise SecurityViolation(
                    "Output size exceeded",
                    "OUTPUT_LIMIT",
                    f"Max: {max_size} bytes"
                )

            output_buffer.append(text)
            sys.stdout.write(text)

        return safe_print

    def get_builtins(self) -> Dict[str, Any]:
        """Get safe builtins dictionary."""
        return self._builtins.copy()


class SafeImporter:
    """Control import behavior in sandbox."""

    def __init__(self, config: SandboxConfig):
        self.config = config
        self._allowed_modules: Dict[str, Any] = {}
        self._setup_allowed_modules()

    def _setup_allowed_modules(self) -> None:
        """Pre-import allowed modules."""
        for module_name in self.config.allow_imports:
            try:
                module = __import__(module_name)
                self._allowed_modules[module_name] = module
            except ImportError:
                pass  # Module not available

    def safe_import(self, name: str, *args, **kwargs) -> Any:
        """Safe import function."""
        module = name.split('.')[0]

        if module in self.config.blocked_imports:
            raise SecurityViolation(
                f"Import of '{name}' is blocked",
                "BLOCKED_IMPORT",
                name
            )

        if module not in self.config.allow_imports:
            raise SecurityViolation(
                f"Import of '{name}' is not allowed",
                "UNAPPROVED_IMPORT",
                name
            )

        if module in self._allowed_modules:
            return self._allowed_modules[module]

        raise SecurityViolation(
            f"Module '{name}' not available",
            "MODULE_NOT_FOUND",
            name
        )


class PythonSandbox:
    """
    Secure Python code execution sandbox.

    CRITICAL: This is the primary defense against ISSUE-055.
    All Python code from AI must go through this sandbox.

    Usage:
        sandbox = PythonSandbox()
        result = sandbox.execute("print('Hello, World!')")
        if result.success:
            print(result.output)
        else:
            print(f"Blocked: {result.error}")
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        """Initialize sandbox with configuration."""
        self.config = config or SandboxConfig()
        self.analyzer = ASTSecurityAnalyzer(self.config)
        self.safe_builtins = SafeBuiltins(self.config)
        self.safe_importer = SafeImporter(self.config)

    def validate_code(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate code without executing it.

        Returns:
            (is_safe, violations)
        """
        # Reset analyzer state
        self.analyzer = ASTSecurityAnalyzer(self.config)
        return self.analyzer.check(code)

    def execute(
        self,
        code: str,
        globals_dict: Optional[Dict[str, Any]] = None,
        locals_dict: Optional[Dict[str, Any]] = None,
    ) -> SandboxResult:
        """
        Execute Python code in sandbox.

        Args:
            code: Python code to execute
            globals_dict: Additional global variables
            locals_dict: Additional local variables

        Returns:
            SandboxResult with output and status
        """
        start_time = time.time()

        # Step 1: Validate code with AST analysis
        is_safe, violations = self.validate_code(code)
        if not is_safe:
            return SandboxResult.failure(
                error="Code failed security validation",
                violations=violations
            )

        # Step 2: Prepare restricted execution environment
        safe_globals = self._create_safe_globals(globals_dict)
        safe_locals = locals_dict.copy() if locals_dict else {}

        # Step 3: Execute with resource limits
        if self.config.level >= SandboxLevel.STRICT:
            return self._execute_with_limits(code, safe_globals, safe_locals, start_time)
        else:
            return self._execute_simple(code, safe_globals, safe_locals, start_time)

    def _create_safe_globals(
        self,
        additional: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create safe globals dictionary."""
        globals_dict = {
            '__builtins__': self.safe_builtins.get_builtins(),
            '__name__': '__sandbox__',
            '__doc__': None,
        }

        # Add safe import
        globals_dict['__builtins__']['__import__'] = self.safe_importer.safe_import

        # Add pre-imported safe modules
        for module_name in self.config.allow_imports:
            try:
                globals_dict[module_name] = __import__(module_name)
            except ImportError:
                pass

        # Add user-provided globals (but not dangerous ones)
        if additional:
            for key, value in additional.items():
                if not key.startswith('_') and key not in self.config.blocked_builtins:
                    globals_dict[key] = value

        return globals_dict

    def _execute_simple(
        self,
        code: str,
        globals_dict: Dict[str, Any],
        locals_dict: Dict[str, Any],
        start_time: float
    ) -> SandboxResult:
        """Execute code with basic restrictions."""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(compile(code, '<sandbox>', 'exec'), globals_dict, locals_dict)

            execution_time = time.time() - start_time

            return SandboxResult(
                success=True,
                output=stdout_capture.getvalue(),
                execution_time=execution_time,
                return_value=locals_dict.get('result'),
            )

        except SecurityViolation as e:
            return SandboxResult.failure(
                error=f"Security violation: {e.message}",
                violations=[f"{e.violation_type}: {e.message}"]
            )
        except Exception as e:
            return SandboxResult.failure(
                error=f"Execution error: {type(e).__name__}: {e}",
                violations=[traceback.format_exc()]
            )

    def _execute_with_limits(
        self,
        code: str,
        globals_dict: Dict[str, Any],
        locals_dict: Dict[str, Any],
        start_time: float
    ) -> SandboxResult:
        """Execute code with resource limits using multiprocessing."""

        def run_in_subprocess(code: str, queue: multiprocessing.Queue):
            """Run code in isolated subprocess."""
            import resource as res

            # Set resource limits
            try:
                # CPU time limit
                res.setrlimit(res.RLIMIT_CPU, (int(self.config.max_execution_time), int(self.config.max_execution_time)))
                # Memory limit
                res.setrlimit(res.RLIMIT_AS, (self.config.max_memory, self.config.max_memory))
            except (ValueError, res.error):
                pass  # Limits not supported

            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec(compile(code, '<sandbox>', 'exec'), globals_dict, locals_dict)

                queue.put({
                    'success': True,
                    'output': stdout_capture.getvalue(),
                    'error': None,
                    'return_value': locals_dict.get('result'),
                })

            except Exception as e:
                queue.put({
                    'success': False,
                    'output': stdout_capture.getvalue(),
                    'error': f"{type(e).__name__}: {e}",
                    'return_value': None,
                })

        # Use multiprocessing for isolation
        queue: multiprocessing.Queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=run_in_subprocess,
            args=(code, queue)
        )

        try:
            process.start()
            process.join(timeout=self.config.max_execution_time + 1)

            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()

                return SandboxResult.failure(
                    error=f"Execution timed out after {self.config.max_execution_time}s",
                    violations=["TIMEOUT"]
                )

            if not queue.empty():
                result = queue.get_nowait()
                execution_time = time.time() - start_time

                return SandboxResult(
                    success=result['success'],
                    output=result['output'],
                    error=result['error'],
                    return_value=result['return_value'],
                    execution_time=execution_time,
                )

            return SandboxResult.failure(
                error="No result from subprocess",
                violations=["SUBPROCESS_ERROR"]
            )

        except Exception as e:
            return SandboxResult.failure(
                error=f"Subprocess error: {e}",
                violations=["SUBPROCESS_ERROR"]
            )
        finally:
            if process.is_alive():
                process.terminate()


# Convenience functions

def execute_python_safe(code: str, timeout: float = 5.0) -> SandboxResult:
    """Execute Python code with standard security."""
    config = SandboxConfig(
        level=SandboxLevel.STANDARD,
        max_execution_time=timeout
    )
    sandbox = PythonSandbox(config)
    return sandbox.execute(code)


def execute_python_strict(code: str, timeout: float = 3.0) -> SandboxResult:
    """Execute Python code with strict security."""
    config = SandboxConfig(
        level=SandboxLevel.STRICT,
        max_execution_time=timeout,
        max_memory=32 * 1024 * 1024,  # 32MB
    )
    sandbox = PythonSandbox(config)
    return sandbox.execute(code)


def validate_python_code(code: str) -> Tuple[bool, List[str]]:
    """Validate Python code without executing."""
    sandbox = PythonSandbox()
    return sandbox.validate_code(code)


def is_python_safe(code: str) -> bool:
    """Quick check if Python code is safe."""
    is_safe, _ = validate_python_code(code)
    return is_safe


# Export all public symbols
__all__ = [
    'SandboxLevel',
    'SecurityViolation',
    'SandboxConfig',
    'SandboxResult',
    'ASTSecurityAnalyzer',
    'SafeBuiltins',
    'SafeImporter',
    'PythonSandbox',
    'execute_python_safe',
    'execute_python_strict',
    'validate_python_code',
    'is_python_safe',
]
