"""Tests for configuration schema."""

from jdev_cli.config.schema import (
    QwenConfig,
    ProjectConfig,
    RulesConfig,
    SafetyConfig,
    HooksConfig,
    ContextConfig,
)


class TestProjectConfig:
    """Test ProjectConfig dataclass."""

    def test_default_values(self):
        """Test default project config values."""
        config = ProjectConfig()
        assert config.name == "my-project"
        assert config.type == "python"
        assert config.version == "1.0.0"
        assert config.description == ""

    def test_custom_values(self):
        """Test custom project config values."""
        config = ProjectConfig(
            name="test-project",
            type="rust",
            version="2.0.0",
            description="Test project"
        )
        assert config.name == "test-project"
        assert config.type == "rust"


class TestRulesConfig:
    """Test RulesConfig dataclass."""

    def test_default_values(self):
        """Test default rules config."""
        config = RulesConfig()
        assert config.rules == []
        assert config.style_guide is None
        assert config.max_line_length == 100
        assert config.use_type_hints is True

    def test_with_rules(self):
        """Test rules config with custom rules."""
        config = RulesConfig(
            rules=["Rule 1", "Rule 2"],
            style_guide="PEP 8",
            max_line_length=120
        )
        assert len(config.rules) == 2
        assert config.style_guide == "PEP 8"


class TestSafetyConfig:
    """Test SafetyConfig dataclass."""

    def test_default_dangerous_commands(self):
        """Test default dangerous commands list."""
        config = SafetyConfig()
        assert "rm -rf" in config.dangerous_commands
        assert "chmod 777" in config.dangerous_commands
        assert len(config.dangerous_commands) > 0

    def test_default_require_approval(self):
        """Test default commands requiring approval."""
        config = SafetyConfig()
        assert "git push" in config.require_approval
        assert "docker run" in config.require_approval

    def test_allowed_paths(self):
        """Test allowed paths configuration."""
        config = SafetyConfig(allowed_paths=["./src", "./tests"])
        assert "./src" in config.allowed_paths
        assert "./tests" in config.allowed_paths


class TestHooksConfig:
    """Test HooksConfig dataclass."""

    def test_default_empty_hooks(self):
        """Test hooks are empty by default."""
        config = HooksConfig()
        assert config.post_write == []
        assert config.post_edit == []
        assert config.post_delete == []
        assert config.pre_commit == []

    def test_custom_hooks(self):
        """Test custom hook configuration."""
        config = HooksConfig(
            post_write=["ruff check {file}"],
            pre_commit=["pytest tests/"]
        )
        assert len(config.post_write) == 1
        assert len(config.pre_commit) == 1


class TestContextConfig:
    """Test ContextConfig dataclass."""

    def test_default_values(self):
        """Test default context config."""
        config = ContextConfig()
        assert config.max_tokens == 32000
        assert config.include_git is True
        assert config.include_tests is True
        assert len(config.exclude_patterns) > 0

    def test_exclude_patterns(self):
        """Test exclude patterns include common dirs."""
        config = ContextConfig()
        assert any("__pycache__" in p for p in config.exclude_patterns)
        assert any("node_modules" in p for p in config.exclude_patterns)
        assert any("venv" in p for p in config.exclude_patterns)

    def test_file_extensions(self):
        """Test default file extensions."""
        config = ContextConfig()
        assert ".py" in config.file_extensions
        assert ".js" in config.file_extensions
        assert ".md" in config.file_extensions


class TestQwenConfig:
    """Test QwenConfig main class."""

    def test_default_initialization(self):
        """Test QwenConfig creates all sub-configs."""
        config = QwenConfig()
        assert isinstance(config.project, ProjectConfig)
        assert isinstance(config.rules, RulesConfig)
        assert isinstance(config.safety, SafetyConfig)
        assert isinstance(config.hooks, HooksConfig)
        assert isinstance(config.context, ContextConfig)

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = QwenConfig()
        data = config.to_dict()

        assert 'project' in data
        assert 'rules' in data
        assert 'safety' in data
        assert 'hooks' in data
        assert 'context' in data

        assert isinstance(data['project'], dict)
        assert isinstance(data['rules'], dict)

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            'project': {'name': 'test', 'type': 'python'},
            'rules': {'max_line_length': 120},
            'safety': {'max_file_size_mb': 20},
            'hooks': {'post_write': ['echo test']},
            'context': {'max_tokens': 16000},
        }

        config = QwenConfig.from_dict(data)

        assert config.project.name == 'test'
        assert config.rules.max_line_length == 120
        assert config.safety.max_file_size_mb == 20
        assert config.hooks.post_write == ['echo test']
        assert config.context.max_tokens == 16000

    def test_from_dict_partial(self):
        """Test from_dict with partial data uses defaults."""
        data = {
            'project': {'name': 'partial'},
        }

        config = QwenConfig.from_dict(data)

        assert config.project.name == 'partial'
        # Should use defaults for missing fields
        assert config.project.type == 'python'
        assert config.rules.max_line_length == 100
