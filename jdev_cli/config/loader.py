"""Configuration file loader with YAML support."""

import yaml
from pathlib import Path
from typing import Optional
from rich.console import Console

from .schema import QwenConfig
from .defaults import get_default_config
from .validator import ConfigValidator


console = Console()


class ConfigLoader:
    """Load and manage project configuration from YAML files."""

    CONFIG_FILENAMES = [
        ".qwenrc",
        ".qwenrc.yaml",
        ".qwenrc.yml",
        ".qwen/config.yaml",
        ".qwen/config.yml",
        "qwen.yaml",
        "qwen.yml",
    ]

    def __init__(self, cwd: Optional[Path] = None):
        """Initialize config loader.
        
        Args:
            cwd: Current working directory (default: Path.cwd())
        """
        self.cwd = cwd or Path.cwd()
        self.config: QwenConfig = get_default_config()
        self.config_file: Optional[Path] = None
        self._load()

    def _find_config_file(self) -> Optional[Path]:
        """Find first existing config file in CONFIG_FILENAMES.
        
        Returns:
            Path to config file or None if not found
        """
        for filename in self.CONFIG_FILENAMES:
            path = self.cwd / filename
            if path.exists() and path.is_file():
                return path
        return None

    def _load(self) -> None:
        """Load configuration from file or use defaults."""
        config_file = self._find_config_file()

        if config_file:
            try:
                with open(config_file, 'r') as f:
                    data = yaml.safe_load(f)

                if data:
                    self.config = QwenConfig.from_dict(data)
                    self.config_file = config_file

                    # Validate configuration
                    is_valid, errors, warnings = ConfigValidator.validate_config(
                        self.config, self.cwd
                    )

                    if not is_valid:
                        console.print("[red]✗ Security issues in config:[/red]")
                        for error in errors:
                            console.print(f"  [red]•[/red] {error}")

                    if warnings:
                        for warning in warnings:
                            console.print(f"[yellow]⚠[/yellow]  {warning}")

                    # Always sanitize if there are any issues
                    if not is_valid or warnings:
                        console.print("[yellow]Sanitizing config...[/yellow]")
                        self.config = ConfigValidator.sanitize_config(self.config, self.cwd)

                    console.print(f"[dim]Config loaded from:[/dim] {config_file.name}")
            except yaml.YAMLError as e:
                console.print(f"[yellow]Warning: Invalid YAML in {config_file}:[/yellow] {e}")
                console.print("[dim]Using default configuration[/dim]")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to load config:[/yellow] {e}")
                console.print("[dim]Using default configuration[/dim]")
        else:
            # No config file found, use defaults
            self.config = get_default_config()

    def save(self, path: Optional[Path] = None) -> None:
        """Save current configuration to YAML file.
        
        Args:
            path: Path to save config (default: .qwenrc in cwd)
        """
        if path is None:
            path = self.cwd / ".qwenrc"

        data = self.config.to_dict()

        try:
            with open(path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            console.print(f"[green]✓ Config saved to:[/green] {path}")
        except Exception as e:
            console.print(f"[red]✗ Failed to save config:[/red] {e}")
            raise

    def get_rules(self) -> list:
        """Get coding rules as list of strings."""
        return self.config.rules.rules

    def get_hooks(self, event: str) -> list:
        """Get hooks for specific event.
        
        Args:
            event: Hook event name (post_write, post_edit, post_delete, pre_commit)
            
        Returns:
            List of hook commands
        """
        return getattr(self.config.hooks, event, [])

    def is_path_allowed(self, path: Path) -> bool:
        """Check if path is in allowed paths.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is allowed
        """
        path = path.resolve()
        cwd = self.cwd.resolve()

        for allowed in self.config.safety.allowed_paths:
            allowed_path = (cwd / allowed).resolve()
            try:
                path.relative_to(allowed_path)
                return True
            except ValueError:
                continue

        return False

    def is_command_dangerous(self, command: str) -> bool:
        """Check if command contains dangerous patterns.
        
        Args:
            command: Command string to check
            
        Returns:
            True if command is dangerous
        """
        from ..security_hardening import normalise_command
        norm_cmd = normalise_command(command)
        for pattern in self.config.safety.dangerous_commands:
            if pattern in norm_cmd:
                return True
        return False

    def requires_approval(self, command: str) -> bool:
        """Check if command requires user approval.
        
        Args:
            command: Command string to check
            
        Returns:
            True if approval required
        """
        for pattern in self.config.safety.require_approval:
            if command.startswith(pattern):
                return True
        return False

    def get_context_patterns(self) -> tuple:
        """Get context include/exclude patterns.
        
        Returns:
            Tuple of (include_extensions, exclude_patterns)
        """
        return (
            self.config.context.file_extensions,
            self.config.context.exclude_patterns
        )

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load()
