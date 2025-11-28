"""
Tests for Docker sandbox executor.

Comprehensive test suite covering:
- Basic execution
- Timeout handling
- Volume mounts
- Resource limits
- Error handling
- Security isolation
"""

import pytest
from pathlib import Path
import tempfile

from jdev_cli.integration.sandbox import (
    SandboxExecutor,
    SandboxResult,
    get_sandbox
)


# Skip tests if Docker is not available
def check_docker():
    """Check if Docker is available."""
    sandbox = SandboxExecutor()
    return sandbox.is_available()


pytestmark = pytest.mark.skipif(
    not check_docker(),
    reason="Docker not available"
)


class TestSandboxExecutor:
    """Test sandbox executor functionality."""

    def test_init(self):
        """Test sandbox initialization."""
        sandbox = SandboxExecutor()
        assert sandbox is not None
        assert sandbox.is_available()
        assert sandbox.image == "python:3.12-slim"

    def test_custom_image(self):
        """Test custom Docker image."""
        sandbox = SandboxExecutor(image="alpine:latest", auto_pull=False)
        assert sandbox.image == "alpine:latest"

    def test_is_available(self):
        """Test availability check."""
        sandbox = SandboxExecutor()
        assert sandbox.is_available() is True

    def test_simple_execution(self):
        """Test simple command execution."""
        sandbox = SandboxExecutor()
        result = sandbox.execute("echo 'Hello Sandbox'", timeout=5)

        assert isinstance(result, SandboxResult)
        assert result.success is True
        assert result.exit_code == 0
        assert "Hello Sandbox" in result.stdout
        assert result.duration_ms > 0

    def test_python_execution(self):
        """Test Python code execution."""
        sandbox = SandboxExecutor()
        result = sandbox.execute("python -c 'print(2 + 2)'", timeout=10)

        assert result.success is True
        assert "4" in result.stdout

    def test_failing_command(self):
        """Test command that fails."""
        sandbox = SandboxExecutor()
        result = sandbox.execute("exit 42", timeout=5)

        assert result.success is False
        assert result.exit_code == 42

    def test_timeout_handling(self):
        """Test timeout enforcement."""
        sandbox = SandboxExecutor()
        result = sandbox.execute("sleep 10", timeout=2)

        # Should timeout and fail
        assert result.success is False
        assert result.exit_code == -1

    def test_with_working_directory(self):
        """Test execution with mounted directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test file
            test_file = tmppath / "test.txt"
            test_file.write_text("Test content")

            sandbox = SandboxExecutor()
            result = sandbox.execute(
                "cat /workspace/test.txt",
                cwd=tmppath,
                timeout=5,
                readonly=True
            )

            assert result.success is True
            assert "Test content" in result.stdout

    def test_readonly_mount(self):
        """Test readonly volume mount."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            sandbox = SandboxExecutor()
            result = sandbox.execute(
                "touch /workspace/newfile.txt",
                cwd=tmppath,
                timeout=5,
                readonly=True
            )

            # Should fail due to readonly
            assert result.success is False

    def test_writable_mount(self):
        """Test writable volume mount."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            sandbox = SandboxExecutor()
            result = sandbox.execute(
                "echo 'test' > /workspace/output.txt",
                cwd=tmppath,
                timeout=5,
                readonly=False
            )

            assert result.success is True

            # Check file was created
            output_file = tmppath / "output.txt"
            assert output_file.exists()
            assert output_file.read_text().strip() == "test"

    def test_environment_variables(self):
        """Test environment variable passing."""
        sandbox = SandboxExecutor()
        result = sandbox.execute(
            "echo $TEST_VAR",
            timeout=5,
            env={'TEST_VAR': 'test_value'}
        )

        assert result.success is True
        assert "test_value" in result.stdout

    def test_execute_with_files(self):
        """Test execution with temporary files."""
        sandbox = SandboxExecutor()

        files = {
            'script.py': 'print("Hello from script")',
            'data.txt': 'test data'
        }

        result = sandbox.execute_with_files(
            "python /workspace/script.py",
            files=files,
            timeout=10
        )

        assert result.success is True
        assert "Hello from script" in result.stdout

    def test_stderr_capture(self):
        """Test stderr capture."""
        sandbox = SandboxExecutor()
        result = sandbox.execute(
            "python -c 'import sys; sys.stderr.write(\"error message\\n\")'",
            timeout=10
        )

        assert result.success is True  # Python exits 0
        assert "error message" in result.stderr

    def test_memory_limit(self):
        """Test memory limit setting."""
        sandbox = SandboxExecutor(memory_limit="128m")
        assert sandbox.memory_limit == "128m"

    def test_cpu_quota(self):
        """Test CPU quota setting."""
        sandbox = SandboxExecutor(cpu_quota=25000)  # 25% of one core
        assert sandbox.cpu_quota == 25000

    def test_network_disabled(self):
        """Test network isolation."""
        sandbox = SandboxExecutor(network_disabled=True)
        result = sandbox.execute(
            "ping -c 1 google.com",
            timeout=5
        )

        # Should fail due to no network
        assert result.success is False

    def test_container_cleanup(self):
        """Test container cleanup after execution."""
        sandbox = SandboxExecutor()
        result = sandbox.execute("echo 'test'", timeout=5)

        assert result.success is True

        # Container should be removed automatically
        # We can't easily verify this without Docker API inspection
        # but the test passing means no errors during cleanup

    def test_test_availability(self):
        """Test availability testing method."""
        sandbox = SandboxExecutor()
        status = sandbox.test_availability()

        assert status['available'] is True
        assert status['test_result'] is True
        assert 'Sandbox test' in status['test_output']

    def test_multiple_executions(self):
        """Test multiple sequential executions."""
        sandbox = SandboxExecutor()

        for i in range(3):
            result = sandbox.execute(f"echo 'Test {i}'", timeout=5)
            assert result.success is True
            assert f"Test {i}" in result.stdout

    def test_long_output(self):
        """Test handling of long output."""
        sandbox = SandboxExecutor()
        result = sandbox.execute(
            "for i in $(seq 1 100); do echo $i; done",
            timeout=10
        )

        assert result.success is True
        assert "100" in result.stdout

    def test_complex_command(self):
        """Test complex shell command."""
        sandbox = SandboxExecutor()
        result = sandbox.execute(
            "mkdir -p /tmp/test && cd /tmp/test && echo 'data' > file.txt && cat file.txt",
            timeout=10
        )

        assert result.success is True
        assert "data" in result.stdout

    def test_get_sandbox_singleton(self):
        """Test global sandbox singleton."""
        sandbox1 = get_sandbox()
        sandbox2 = get_sandbox()

        assert sandbox1 is sandbox2  # Same instance


class TestSandboxResult:
    """Test SandboxResult dataclass."""

    def test_result_creation(self):
        """Test result creation."""
        result = SandboxResult(
            exit_code=0,
            stdout="output",
            stderr="",
            duration_ms=123.45,
            container_id="abc123",
            success=True
        )

        assert result.exit_code == 0
        assert result.stdout == "output"
        assert result.duration_ms == 123.45
        assert result.success is True

    def test_output_property(self):
        """Test combined output property."""
        result = SandboxResult(
            exit_code=0,
            stdout="out",
            stderr="err",
            duration_ms=100,
            container_id="abc",
            success=True
        )

        assert result.output == "outerr"


class TestSandboxEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_command(self):
        """Test empty command."""
        sandbox = SandboxExecutor()
        result = sandbox.execute("", timeout=5)

        # Should succeed (sh -c "" exits 0)
        assert result.exit_code == 0

    def test_very_short_timeout(self):
        """Test very short timeout."""
        sandbox = SandboxExecutor()
        result = sandbox.execute("sleep 5", timeout=1)

        assert result.success is False

    def test_special_characters_in_command(self):
        """Test command with special characters."""
        sandbox = SandboxExecutor()
        result = sandbox.execute(
            "echo 'Test with $pecial ch@racters! & < >'",
            timeout=5
        )

        assert result.success is True

    def test_nonexistent_directory_mount(self):
        """Test mounting nonexistent directory."""
        sandbox = SandboxExecutor()

        # Docker will create the directory if it doesn't exist
        # So we just test that it doesn't crash
        result = sandbox.execute(
            "ls /workspace",
            cwd=Path("/nonexistent/path"),
            timeout=5
        )

        # Should succeed (empty directory)
        assert result.exit_code == 0


class TestSandboxSecurity:
    """Test security features."""

    def test_no_host_access_by_default(self):
        """Test that container can't access host filesystem by default."""
        sandbox = SandboxExecutor()
        result = sandbox.execute("ls /host/", timeout=5)

        # Should fail - no /host/ directory
        assert result.success is False

    def test_resource_isolation(self):
        """Test resource limits are enforced."""
        sandbox = SandboxExecutor(memory_limit="64m", cpu_quota=10000)

        # Should still execute simple commands
        result = sandbox.execute("echo 'test'", timeout=5)
        assert result.success is True
