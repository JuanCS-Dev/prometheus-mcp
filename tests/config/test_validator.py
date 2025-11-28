"""Tests for configuration validator."""

import tempfile
from pathlib import Path

from jdev_cli.config.validator import ConfigValidator
from jdev_cli.config.schema import QwenConfig


class TestPathValidation:
    """Test path traversal validation."""

    def test_valid_paths(self):
        """Test validation accepts valid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            valid_paths = ["./", "./src", "./tests", "docs/"]
            is_valid, errors = ConfigValidator.validate_allowed_paths(valid_paths, tmpdir)

            assert is_valid
            assert len(errors) == 0

    def test_path_traversal_detected(self):
        """Test validation detects path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            traversal_paths = ["../../../etc", "../../etc/passwd"]
            is_valid, errors = ConfigValidator.validate_allowed_paths(traversal_paths, tmpdir)

            assert not is_valid
            assert len(errors) > 0
            assert any("traversal" in err.lower() for err in errors)

    def test_mixed_paths(self):
        """Test validation with mix of valid and invalid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mixed_paths = ["./src", "../../../etc", "./tests"]
            is_valid, errors = ConfigValidator.validate_allowed_paths(mixed_paths, tmpdir)

            assert not is_valid
            assert len(errors) == 1


class TestNumericBounds:
    """Test numeric value validation."""

    def test_valid_bounds(self):
        """Test validation accepts valid numeric values."""
        config = QwenConfig()
        config.context.max_tokens = 16000
        config.safety.max_file_size_mb = 10
        config.rules.max_line_length = 100

        is_valid, warnings = ConfigValidator.validate_numeric_bounds(config)

        assert is_valid
        assert len(warnings) == 0

    def test_max_tokens_too_high(self):
        """Test validation detects too high max_tokens."""
        config = QwenConfig()
        config.context.max_tokens = 9999999

        is_valid, warnings = ConfigValidator.validate_numeric_bounds(config)

        assert not is_valid
        assert any("max_tokens too high" in w for w in warnings)

    def test_max_tokens_too_low(self):
        """Test validation detects too low max_tokens."""
        config = QwenConfig()
        config.context.max_tokens = 500

        is_valid, warnings = ConfigValidator.validate_numeric_bounds(config)

        assert not is_valid
        assert any("max_tokens too low" in w for w in warnings)

    def test_negative_file_size(self):
        """Test validation detects negative file size."""
        config = QwenConfig()
        config.safety.max_file_size_mb = -1

        is_valid, warnings = ConfigValidator.validate_numeric_bounds(config)

        assert not is_valid
        assert any("cannot be negative" in w for w in warnings)

    def test_line_length_too_short(self):
        """Test validation detects too short line length."""
        config = QwenConfig()
        config.rules.max_line_length = 10

        is_valid, warnings = ConfigValidator.validate_numeric_bounds(config)

        assert not is_valid
        assert any("too short" in w for w in warnings)


class TestHookValidation:
    """Test hook command validation."""

    def test_safe_hooks(self):
        """Test validation accepts safe hook commands."""
        hooks = ["pytest tests/", "black {file}", "echo 'done'"]
        dangerous = ["rm -rf", "chmod 777"]

        is_safe, warnings = ConfigValidator.validate_hooks(hooks, dangerous)

        assert is_safe
        assert len(warnings) == 0

    def test_dangerous_hooks(self):
        """Test validation detects dangerous hooks."""
        hooks = ["echo test && rm -rf /", "chmod 777 {file}"]
        dangerous = ["rm -rf", "chmod 777"]

        is_safe, warnings = ConfigValidator.validate_hooks(hooks, dangerous)

        assert not is_safe
        assert len(warnings) == 2
        assert any("rm -rf" in w for w in warnings)
        assert any("chmod 777" in w for w in warnings)


class TestFullValidation:
    """Test complete configuration validation."""

    def test_valid_config(self):
        """Test validation passes for valid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            config = QwenConfig()
            config.safety.allowed_paths = ["./src", "./tests"]

            is_valid, errors, warnings = ConfigValidator.validate_config(config, tmpdir)

            assert is_valid
            assert len(errors) == 0

    def test_config_with_errors(self):
        """Test validation detects errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            config = QwenConfig()
            config.safety.allowed_paths = ["../../../etc"]

            is_valid, errors, warnings = ConfigValidator.validate_config(config, tmpdir)

            assert not is_valid
            assert len(errors) > 0

    def test_config_with_warnings(self):
        """Test validation detects warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            config = QwenConfig()
            config.context.max_tokens = 9999999
            config.hooks.post_write = ["rm -rf {file}"]

            is_valid, errors, warnings = ConfigValidator.validate_config(config, tmpdir)

            # Should have warnings but no errors
            assert is_valid
            assert len(errors) == 0
            assert len(warnings) > 0


class TestSanitization:
    """Test configuration sanitization."""

    def test_sanitize_path_traversal(self):
        """Test sanitization removes path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            config = QwenConfig()
            config.safety.allowed_paths = ["../../../etc", "./src", "../../bad"]

            sanitized = ConfigValidator.sanitize_config(config, tmpdir)

            assert "../../../etc" not in sanitized.safety.allowed_paths
            assert "../../bad" not in sanitized.safety.allowed_paths
            assert "./src" in sanitized.safety.allowed_paths

    def test_sanitize_numeric_bounds(self):
        """Test sanitization clamps numeric values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            config = QwenConfig()
            config.context.max_tokens = 9999999
            config.safety.max_file_size_mb = -10
            config.rules.max_line_length = 5

            sanitized = ConfigValidator.sanitize_config(config, tmpdir)

            assert sanitized.context.max_tokens <= 1000000
            assert sanitized.safety.max_file_size_mb >= 1
            assert sanitized.rules.max_line_length >= 40

    def test_sanitize_empty_allowed_paths(self):
        """Test sanitization provides default if all paths removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            config = QwenConfig()
            config.safety.allowed_paths = ["../../../etc"]

            sanitized = ConfigValidator.sanitize_config(config, tmpdir)

            # Should default to current directory
            assert "./" in sanitized.safety.allowed_paths
