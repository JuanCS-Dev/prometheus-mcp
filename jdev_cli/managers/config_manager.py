"""
Configuration Manager.

SCALE & SUSTAIN Phase 1.1.1 - Config Manager.

Manages application configuration with layered scopes:
- Default < System < User < Project < Environment

Author: JuanCS Dev
Date: 2025-11-26
"""

import json
import os
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic

T = TypeVar('T')


class ConfigScope(Enum):
    """Configuration scope hierarchy."""
    DEFAULT = auto()    # Built-in defaults
    SYSTEM = auto()     # System-wide (/etc/jdev/)
    USER = auto()       # User home (~/.config/jdev/)
    PROJECT = auto()    # Project root (.jdev/)
    ENVIRONMENT = auto() # Environment variables
    RUNTIME = auto()    # Runtime overrides


@dataclass
class ConfigValue(Generic[T]):
    """Configuration value with metadata."""
    value: T
    scope: ConfigScope
    source: str  # File path or "environment" or "default"

    def __repr__(self) -> str:
        return f"ConfigValue({self.value!r}, scope={self.scope.name})"


class ConfigManager:
    """
    Centralized configuration management.

    Features:
    - Layered configuration scopes
    - Type-safe access with defaults
    - Environment variable override
    - Project-specific configs
    - Hot reload support

    Example:
        config = ConfigManager()
        config.load_project("/path/to/project")

        model = config.get("llm.model", default="qwen2.5-coder")
        timeout = config.get("tools.timeout", default=30, type_=int)
    """

    # Default configuration values
    DEFAULTS: Dict[str, Any] = {
        # LLM settings
        "llm.provider": "ollama",
        "llm.model": "qwen2.5-coder:14b",
        "llm.temperature": 0.7,
        "llm.max_tokens": 4096,
        "llm.timeout": 120,

        # Tool settings
        "tools.timeout": 30,
        "tools.sandbox_enabled": True,
        "tools.max_output_size": 100000,

        # Session settings
        "session.auto_save": True,
        "session.history_limit": 100,
        "session.context_window": 8192,

        # Cache settings
        "cache.enabled": True,
        "cache.ttl": 3600,
        "cache.max_size_mb": 100,

        # UI settings
        "ui.theme": "dark",
        "ui.syntax_highlighting": True,
        "ui.show_tokens": False,
    }

    # Environment variable prefix
    ENV_PREFIX = "JDEV_"

    def __init__(self, project_path: Optional[Path] = None):
        self._configs: Dict[ConfigScope, Dict[str, Any]] = {
            scope: {} for scope in ConfigScope
        }
        self._configs[ConfigScope.DEFAULT] = self.DEFAULTS.copy()
        self._project_path: Optional[Path] = None
        self._loaded_files: List[str] = []

        # Load configs
        self._load_system_config()
        self._load_user_config()
        self._load_environment()

        if project_path:
            self.load_project(project_path)

    def _load_system_config(self) -> None:
        """Load system-wide configuration."""
        system_paths = [
            Path("/etc/jdev/config.json"),
            Path("/etc/jdev.json"),
        ]

        for path in system_paths:
            if path.exists():
                self._load_file(path, ConfigScope.SYSTEM)
                break

    def _load_user_config(self) -> None:
        """Load user configuration."""
        user_paths = [
            Path.home() / ".config" / "jdev" / "config.json",
            Path.home() / ".jdev" / "config.json",
            Path.home() / ".jdevrc.json",
        ]

        for path in user_paths:
            if path.exists():
                self._load_file(path, ConfigScope.USER)
                break

    def _load_environment(self) -> None:
        """Load configuration from environment variables."""
        env_config = {}

        for key, value in os.environ.items():
            if key.startswith(self.ENV_PREFIX):
                # JDEV_LLM_MODEL -> llm.model
                config_key = key[len(self.ENV_PREFIX):].lower().replace("_", ".")
                env_config[config_key] = self._parse_env_value(value)

        self._configs[ConfigScope.ENVIRONMENT] = env_config

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Boolean
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False

        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # JSON (for complex values)
        if value.startswith("{") or value.startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        return value

    def _load_file(self, path: Path, scope: ConfigScope) -> bool:
        """Load configuration from a file."""
        try:
            with open(path) as f:
                data = json.load(f)

            # Flatten nested config
            flat = self._flatten_dict(data)
            self._configs[scope].update(flat)
            self._loaded_files.append(str(path))
            return True

        except (json.JSONDecodeError, IOError):
            return False

    def _flatten_dict(self, d: Dict, parent_key: str = '') -> Dict[str, Any]:
        """Flatten nested dictionary with dot notation."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def load_project(self, project_path: Path) -> bool:
        """Load project-specific configuration."""
        self._project_path = Path(project_path)

        project_configs = [
            self._project_path / ".jdev" / "config.json",
            self._project_path / ".jdev.json",
            self._project_path / "jdev.config.json",
        ]

        for path in project_configs:
            if path.exists():
                return self._load_file(path, ConfigScope.PROJECT)

        return False

    def get(
        self,
        key: str,
        default: Optional[T] = None,
        type_: Optional[type] = None
    ) -> T:
        """
        Get configuration value.

        Args:
            key: Dot-notation config key (e.g., "llm.model")
            default: Default value if not found
            type_: Expected type for casting

        Returns:
            Configuration value
        """
        # Check scopes in reverse priority order
        for scope in reversed(list(ConfigScope)):
            if key in self._configs[scope]:
                value = self._configs[scope][key]
                if type_ is not None:
                    try:
                        return type_(value)
                    except (ValueError, TypeError):
                        pass
                return value

        return default

    def get_with_source(self, key: str) -> Optional[ConfigValue]:
        """Get configuration value with source information."""
        for scope in reversed(list(ConfigScope)):
            if key in self._configs[scope]:
                source = "default"
                if scope == ConfigScope.ENVIRONMENT:
                    source = "environment"
                elif self._loaded_files:
                    source = self._loaded_files[-1]

                return ConfigValue(
                    value=self._configs[scope][key],
                    scope=scope,
                    source=source
                )
        return None

    def set(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.RUNTIME
    ) -> None:
        """Set configuration value at runtime."""
        self._configs[scope][key] = value

    def get_section(self, prefix: str) -> Dict[str, Any]:
        """Get all configuration values under a prefix."""
        result = {}
        prefix_dot = f"{prefix}."

        for scope in ConfigScope:
            for key, value in self._configs[scope].items():
                if key.startswith(prefix_dot):
                    # Remove prefix
                    short_key = key[len(prefix_dot):]
                    result[short_key] = value

        return result

    def reload(self) -> None:
        """Reload all configuration files."""
        # Clear non-default configs
        for scope in ConfigScope:
            if scope != ConfigScope.DEFAULT:
                self._configs[scope] = {}

        self._loaded_files = []

        # Reload
        self._load_system_config()
        self._load_user_config()
        self._load_environment()

        if self._project_path:
            self.load_project(self._project_path)

    def export(self, scope: Optional[ConfigScope] = None) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        if scope:
            return self._configs[scope].copy()

        # Merge all scopes
        result = {}
        for s in ConfigScope:
            result.update(self._configs[s])
        return result

    @property
    def loaded_files(self) -> List[str]:
        """Get list of loaded configuration files."""
        return self._loaded_files.copy()

    @property
    def project_path(self) -> Optional[Path]:
        """Get current project path."""
        return self._project_path


__all__ = ['ConfigManager', 'ConfigScope', 'ConfigValue']
