"""Configuration schema definitions using dataclasses."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ProjectConfig:
    """Project metadata and basic settings."""

    name: str = "my-project"
    type: str = "python"  # python, javascript, rust, go, etc.
    version: str = "1.0.0"
    description: str = ""


@dataclass
class RulesConfig:
    """Coding rules and conventions."""

    rules: List[str] = field(default_factory=list)
    style_guide: Optional[str] = None
    max_line_length: int = 100
    use_type_hints: bool = True
    docstring_style: str = "google"  # google, numpy, sphinx


@dataclass
class SafetyConfig:
    """Safety and security settings."""

    allowed_paths: List[str] = field(default_factory=lambda: ["./"])
    dangerous_commands: List[str] = field(default_factory=lambda: [
        "rm -rf",
        "chmod 777",
        "dd if=",
        "mkfs",
        "> /dev/",
    ])
    require_approval: List[str] = field(default_factory=lambda: [
        "git push",
        "docker run",
        "pip install",
        "npm install",
    ])
    max_file_size_mb: int = 10
    enable_sandbox: bool = False


@dataclass
class HooksConfig:
    """Post-action automation hooks."""

    post_write: List[str] = field(default_factory=list)
    post_edit: List[str] = field(default_factory=list)
    post_delete: List[str] = field(default_factory=list)
    pre_commit: List[str] = field(default_factory=list)

    # Hook variables available:
    # {file} - full file path
    # {file_name} - file name with extension
    # {file_stem} - file name without extension
    # {dir} - directory path


@dataclass
class ContextConfig:
    """Context management settings."""

    max_tokens: int = 32000
    include_git: bool = True
    include_tests: bool = True
    include_docs: bool = True
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "**/__pycache__/**",
        "**/node_modules/**",
        "**/venv/**",
        "**/.venv/**",
        "**/.git/**",
        "**/*.pyc",
        "**/.DS_Store",
    ])
    file_extensions: List[str] = field(default_factory=lambda: [
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".rs", ".go", ".java", ".cpp", ".c",
        ".md", ".txt", ".yaml", ".yml", ".json",
    ])


@dataclass
class QwenConfig:
    """Complete Qwen project configuration."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    hooks: HooksConfig = field(default_factory=HooksConfig)
    context: ContextConfig = field(default_factory=ContextConfig)

    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            'project': self.project.__dict__,
            'rules': self.rules.__dict__,
            'safety': self.safety.__dict__,
            'hooks': self.hooks.__dict__,
            'context': self.context.__dict__,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'QwenConfig':
        """Create config from dictionary."""
        return cls(
            project=ProjectConfig(**data.get('project', {})),
            rules=RulesConfig(**data.get('rules', {})),
            safety=SafetyConfig(**data.get('safety', {})),
            hooks=HooksConfig(**data.get('hooks', {})),
            context=ContextConfig(**data.get('context', {})),
        )
