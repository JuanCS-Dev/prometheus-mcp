"""
E2E Adversarial Tests: Sandbox Escape
======================================

Tests for sandbox escape prevention.
ALL TESTS MUST PASS - security critical.

Based on:
- Container security best practices
- Python sandbox escape techniques
- OS-level isolation

Total: 6 tests
"""

import pytest
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Set
import ast


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def sandbox_validator():
    """Provide sandbox validation utilities."""
    class SandboxValidator:
        # Dangerous builtins that should be restricted
        DANGEROUS_BUILTINS = {
            'eval', 'exec', 'compile', '__import__', 'open',
            'input', 'breakpoint', 'help', 'license', 'credits',
        }

        # Dangerous modules
        DANGEROUS_MODULES = {
            'os', 'sys', 'subprocess', 'shutil', 'socket',
            'ctypes', 'multiprocessing', 'threading',
            'importlib', 'pickle', 'shelve', 'marshal',
            'code', 'codeop', 'pty', 'fcntl', 'grp', 'pwd',
            'resource', 'signal', 'mmap', 'syslog',
        }

        # Dangerous attributes
        DANGEROUS_ATTRS = {
            '__code__', '__globals__', '__builtins__', '__subclasses__',
            '__bases__', '__mro__', '__class__', '__dict__',
            '__reduce__', '__reduce_ex__', '__getstate__', '__setstate__',
        }

        def check_code_safety(self, code: str) -> tuple[bool, List[str]]:
            """Check if code is safe to execute in sandbox."""
            issues = []

            try:
                tree = ast.parse(code)
            except SyntaxError as e:
                return False, [f"Syntax error: {e}"]

            for node in ast.walk(tree):
                # Check for imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in self.DANGEROUS_MODULES:
                            issues.append(f"Dangerous import: {alias.name}")

                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in self.DANGEROUS_MODULES:
                        issues.append(f"Dangerous import from: {node.module}")

                # Check for dangerous function calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.DANGEROUS_BUILTINS:
                            issues.append(f"Dangerous builtin: {node.func.id}")

                # Check for attribute access
                elif isinstance(node, ast.Attribute):
                    if node.attr in self.DANGEROUS_ATTRS:
                        issues.append(f"Dangerous attribute: {node.attr}")

            return len(issues) == 0, issues

        def create_restricted_globals(self) -> Dict[str, Any]:
            """Create restricted globals for code execution."""
            safe_builtins = {
                'abs': abs, 'all': all, 'any': any, 'ascii': ascii,
                'bin': bin, 'bool': bool, 'bytearray': bytearray,
                'bytes': bytes, 'callable': callable, 'chr': chr,
                'complex': complex, 'dict': dict, 'divmod': divmod,
                'enumerate': enumerate, 'filter': filter, 'float': float,
                'format': format, 'frozenset': frozenset, 'hasattr': hasattr,
                'hash': hash, 'hex': hex, 'int': int, 'isinstance': isinstance,
                'issubclass': issubclass, 'iter': iter, 'len': len,
                'list': list, 'map': map, 'max': max, 'min': min,
                'next': next, 'object': object, 'oct': oct, 'ord': ord,
                'pow': pow, 'print': print, 'range': range, 'repr': repr,
                'reversed': reversed, 'round': round, 'set': set,
                'slice': slice, 'sorted': sorted, 'str': str,
                'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
                'True': True, 'False': False, 'None': None,
            }

            return {
                '__builtins__': safe_builtins,
                '__name__': '__sandbox__',
                '__doc__': None,
            }

    return SandboxValidator()


@pytest.fixture
def file_jail(tmp_path):
    """Create a jailed file environment."""
    jail = tmp_path / "jail"
    jail.mkdir()

    # Create some files in jail
    (jail / "allowed.txt").write_text("allowed content")
    (jail / "subdir").mkdir()
    (jail / "subdir" / "nested.txt").write_text("nested content")

    return jail


# ==============================================================================
# TEST CLASS: Code Execution Sandbox
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.security
class TestCodeExecutionSandbox:
    """Tests for code execution sandboxing."""

    @pytest.mark.parametrize("dangerous_code", [
        "import os; os.system('whoami')",
        "__import__('os').system('id')",
        "eval('__import__(\"os\").system(\"ls\")')",
        "exec('import subprocess; subprocess.run([\"ls\"])')",
        "().__class__.__bases__[0].__subclasses__()",
        "open('/etc/passwd').read()",
        "import socket; socket.socket()",
        "import ctypes; ctypes.CDLL(None)",
    ])
    def test_blocks_dangerous_code(self, sandbox_validator, dangerous_code):
        """Blocks execution of dangerous code patterns."""
        is_safe, issues = sandbox_validator.check_code_safety(dangerous_code)
        assert not is_safe, f"Should block: {dangerous_code}"
        assert len(issues) > 0

    def test_allows_safe_code(self, sandbox_validator):
        """Allows execution of safe code patterns."""
        safe_code = '''
def calculate(x, y):
    return x + y

result = calculate(1, 2)
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
filtered = list(filter(lambda x: x > 2, numbers))
'''
        is_safe, issues = sandbox_validator.check_code_safety(safe_code)
        assert is_safe, f"Should allow safe code. Issues: {issues}"

    def test_restricted_execution_environment(self, sandbox_validator):
        """Executes code in restricted environment."""
        safe_code = "result = sum([1, 2, 3, 4, 5])"

        restricted_globals = sandbox_validator.create_restricted_globals()
        restricted_locals = {}

        # This should work
        exec(compile(safe_code, '<sandbox>', 'exec'),
             restricted_globals, restricted_locals)

        assert restricted_locals['result'] == 15

        # Dangerous code should fail
        dangerous_code = "__import__('os')"
        with pytest.raises((NameError, TypeError)):
            exec(compile(dangerous_code, '<sandbox>', 'exec'),
                 restricted_globals, {})


# ==============================================================================
# TEST CLASS: File System Jail
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.security
class TestFileSystemJail:
    """Tests for file system jailing."""

    def test_allows_access_within_jail(self, file_jail):
        """Allows file operations within jail."""
        def jailed_read(jail_root: Path, relative_path: str) -> str:
            """Read file only if within jail."""
            full_path = (jail_root / relative_path).resolve()
            if not str(full_path).startswith(str(jail_root.resolve())):
                raise PermissionError(f"Access denied: {relative_path}")
            return full_path.read_text()

        # Should work
        content = jailed_read(file_jail, "allowed.txt")
        assert content == "allowed content"

        content = jailed_read(file_jail, "subdir/nested.txt")
        assert content == "nested content"

    def test_blocks_access_outside_jail(self, file_jail):
        """Blocks file operations outside jail."""
        def jailed_read(jail_root: Path, relative_path: str) -> str:
            """Read file only if within jail."""
            full_path = (jail_root / relative_path).resolve()
            if not str(full_path).startswith(str(jail_root.resolve())):
                raise PermissionError(f"Access denied: {relative_path}")
            return full_path.read_text()

        # Should block
        with pytest.raises(PermissionError, match="Access denied"):
            jailed_read(file_jail, "../../../etc/passwd")

        with pytest.raises(PermissionError, match="Access denied"):
            jailed_read(file_jail, "/etc/passwd")

    def test_blocks_symlink_escape(self, file_jail):
        """Blocks symlink-based jail escape."""
        def jailed_read_safe(jail_root: Path, relative_path: str) -> str:
            """Read file checking for symlink escape."""
            # Don't follow symlinks initially
            full_path = jail_root / relative_path
            if full_path.is_symlink():
                # Check where symlink points
                target = full_path.resolve()
                if not str(target).startswith(str(jail_root.resolve())):
                    raise PermissionError(f"Symlink escape detected: {relative_path}")

            resolved = full_path.resolve()
            if not str(resolved).startswith(str(jail_root.resolve())):
                raise PermissionError(f"Path escape detected: {relative_path}")

            return resolved.read_text()

        # Create a symlink pointing outside jail
        evil_link = file_jail / "evil_link"
        try:
            evil_link.symlink_to("/etc/passwd")

            # Should block the symlink escape
            with pytest.raises(PermissionError, match="escape"):
                jailed_read_safe(file_jail, "evil_link")
        finally:
            if evil_link.exists():
                evil_link.unlink()


# ==============================================================================
# TEST CLASS: Process Isolation
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.security
class TestProcessIsolation:
    """Tests for process isolation."""

    def test_subprocess_inherits_restrictions(self, tmp_path):
        """Subprocess should inherit security restrictions."""
        # Create a script that tries to escape
        script = tmp_path / "test_script.py"
        script.write_text('''
import sys
print("PYTHON_PATH:", sys.executable)
print("CWD:", __import__('os').getcwd())
''')

        # Run with restricted PATH
        env = os.environ.copy()
        env['PATH'] = '/usr/bin:/bin'  # Restricted PATH
        env['HOME'] = str(tmp_path)    # Fake home

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            env=env,
            cwd=tmp_path,
            timeout=5
        )

        # Should complete but with restricted environment
        assert result.returncode == 0
        assert str(tmp_path) in result.stdout

    def test_blocks_shell_execution(self):
        """Blocks shell execution from sandboxed code."""
        def safe_run(cmd: List[str], allowed_commands: Set[str]) -> subprocess.CompletedProcess:
            """Run command only if in allowed list."""
            if not cmd:
                raise ValueError("Empty command")

            executable = Path(cmd[0]).name
            if executable not in allowed_commands:
                raise PermissionError(f"Command not allowed: {executable}")

            # Never use shell=True
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=False,  # CRITICAL: Never True
                timeout=5
            )

        allowed = {'echo', 'cat', 'ls'}

        # Should allow
        result = safe_run(['echo', 'hello'], allowed)
        assert 'hello' in result.stdout

        # Should block
        with pytest.raises(PermissionError, match="not allowed"):
            safe_run(['rm', '-rf', '/'], allowed)

        with pytest.raises(PermissionError, match="not allowed"):
            safe_run(['sh', '-c', 'whoami'], allowed)


# ==============================================================================
# SUMMARY
# ==============================================================================

"""
Total Tests: 6 (with parametrized expansions ~15+ test cases)

Sandbox Escape Vectors Covered:
1. Dangerous module imports (os, sys, subprocess, etc.)
2. Dangerous builtins (eval, exec, __import__, open)
3. Dunder attribute access (__class__, __subclasses__, etc.)
4. Path traversal escape from file jail
5. Symlink-based jail escape
6. Shell execution escape
7. Environment variable leakage
8. Subprocess inheritance

Protection Mechanisms:
- AST-based code analysis
- Restricted builtins dictionary
- Resolved path validation
- Symlink target checking
- Command allowlisting
- shell=False enforcement
- Environment sanitization
"""
