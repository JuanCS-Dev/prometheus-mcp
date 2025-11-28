"""Tests for configuration loader."""

import tempfile
from pathlib import Path

from jdev_cli.config.loader import ConfigLoader


class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_init_without_config_file(self):
        """Test loader initializes with defaults when no config file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(cwd=Path(tmpdir))
            assert loader.config is not None
            assert loader.config_file is None
            assert loader.config.project.name == "my-project"

    def test_find_config_file(self):
        """Test finding config file with different names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create .qwenrc file
            config_file = tmpdir / ".qwenrc"
            config_file.write_text("project:\n  name: test\n")

            loader = ConfigLoader(cwd=tmpdir)
            assert loader.config_file == config_file
            assert loader.config.project.name == "test"

    def test_load_yaml_config(self):
        """Test loading YAML config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create config file
            config_file = tmpdir / ".qwenrc"
            config_content = """
project:
  name: my-awesome-project
  type: rust
  version: 2.0.0

rules:
  max_line_length: 120
  rules:
    - "Use Result<T, E>"
    - "Run cargo fmt"

safety:
  allowed_paths:
    - ./src
    - ./tests
  max_file_size_mb: 20
"""
            config_file.write_text(config_content)

            loader = ConfigLoader(cwd=tmpdir)

            assert loader.config.project.name == "my-awesome-project"
            assert loader.config.project.type == "rust"
            assert loader.config.rules.max_line_length == 120
            assert len(loader.config.rules.rules) == 2
            assert loader.config.safety.max_file_size_mb == 20

    def test_invalid_yaml_uses_defaults(self):
        """Test invalid YAML falls back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            config_file = tmpdir / ".qwenrc"
            config_file.write_text("invalid: yaml: syntax:")

            loader = ConfigLoader(cwd=tmpdir)

            # Should use defaults when YAML is invalid
            assert loader.config.project.name == "my-project"

    def test_save_config(self):
        """Test saving config to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            loader = ConfigLoader(cwd=tmpdir)
            loader.config.project.name = "saved-project"

            save_path = tmpdir / ".qwenrc"
            loader.save(save_path)

            assert save_path.exists()

            # Load it back
            loader2 = ConfigLoader(cwd=tmpdir)
            assert loader2.config.project.name == "saved-project"

    def test_get_rules(self):
        """Test getting rules list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(cwd=Path(tmpdir))
            loader.config.rules.rules = ["Rule 1", "Rule 2"]

            rules = loader.get_rules()
            assert len(rules) == 2
            assert "Rule 1" in rules

    def test_get_hooks(self):
        """Test getting hooks for events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(cwd=Path(tmpdir))
            loader.config.hooks.post_write = ["echo test"]
            loader.config.hooks.pre_commit = ["pytest"]

            assert loader.get_hooks("post_write") == ["echo test"]
            assert loader.get_hooks("pre_commit") == ["pytest"]
            assert loader.get_hooks("nonexistent") == []

    def test_is_path_allowed(self):
        """Test path allowed checking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            loader = ConfigLoader(cwd=tmpdir)
            loader.config.safety.allowed_paths = ["./src", "./tests"]

            # Create test paths
            (tmpdir / "src").mkdir()
            (tmpdir / "tests").mkdir()
            (tmpdir / "other").mkdir()

            src_file = tmpdir / "src" / "file.py"
            test_file = tmpdir / "tests" / "test.py"
            other_file = tmpdir / "other" / "file.py"

            assert loader.is_path_allowed(src_file)
            assert loader.is_path_allowed(test_file)
            assert not loader.is_path_allowed(other_file)

    def test_is_command_dangerous(self):
        """Test dangerous command detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(cwd=Path(tmpdir))

            assert loader.is_command_dangerous("rm -rf /")
            assert loader.is_command_dangerous("chmod 777 file")
            assert not loader.is_command_dangerous("ls -la")
            assert not loader.is_command_dangerous("git status")

    def test_requires_approval(self):
        """Test command approval requirement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(cwd=Path(tmpdir))

            assert loader.requires_approval("git push origin main")
            assert loader.requires_approval("docker run image")
            assert loader.requires_approval("pip install requests")
            assert not loader.requires_approval("git status")
            assert not loader.requires_approval("ls -la")

    def test_get_context_patterns(self):
        """Test getting context patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(cwd=Path(tmpdir))

            extensions, excludes = loader.get_context_patterns()

            assert ".py" in extensions
            assert ".js" in extensions
            assert any("__pycache__" in p for p in excludes)
            assert any("node_modules" in p for p in excludes)

    def test_reload(self):
        """Test reloading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            config_file = tmpdir / ".qwenrc"
            config_file.write_text("project:\n  name: original\n")

            loader = ConfigLoader(cwd=tmpdir)
            assert loader.config.project.name == "original"

            # Modify file
            config_file.write_text("project:\n  name: modified\n")

            # Reload
            loader.reload()
            assert loader.config.project.name == "modified"


class TestConfigPreference:
    """Test config file preference order."""

    def test_prefers_qwenrc_over_others(self):
        """Test .qwenrc is preferred over other names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple config files
            (tmpdir / ".qwenrc").write_text("project:\n  name: qwenrc\n")
            (tmpdir / "qwen.yaml").write_text("project:\n  name: qwen-yaml\n")

            loader = ConfigLoader(cwd=tmpdir)

            # Should prefer .qwenrc
            assert loader.config.project.name == "qwenrc"
            assert loader.config_file.name == ".qwenrc"
