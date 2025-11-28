"""Configuration validation with security checks."""

from pathlib import Path
from typing import List, Tuple
from rich.console import Console

from .schema import QwenConfig


console = Console()


class ConfigValidator:
    """Validate configuration for security and correctness."""

    @staticmethod
    def validate_allowed_paths(paths: List[str], cwd: Path) -> Tuple[bool, List[str]]:
        """Validate allowed paths don't contain traversal.
        
        Args:
            paths: List of allowed path strings
            cwd: Current working directory
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        cwd = cwd.resolve()

        for path_str in paths:
            try:
                # Resolve relative to cwd
                path = (cwd / path_str).resolve()

                # Check if resolved path is within or above cwd
                try:
                    path.relative_to(cwd)
                except ValueError:
                    errors.append(
                        f"Path traversal detected in allowed_paths: '{path_str}' "
                        f"resolves outside project directory"
                    )
            except Exception as e:
                errors.append(f"Invalid path in allowed_paths: '{path_str}' - {e}")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_numeric_bounds(config: QwenConfig) -> Tuple[bool, List[str]]:
        """Validate numeric values are within reasonable bounds.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []

        # Max tokens (1k - 1M reasonable range)
        if config.context.max_tokens < 1000:
            warnings.append(f"max_tokens too low: {config.context.max_tokens} (minimum: 1000)")
        elif config.context.max_tokens > 1000000:
            warnings.append(f"max_tokens too high: {config.context.max_tokens} (maximum: 1000000)")

        # Max file size (must be positive, max 1GB)
        if config.safety.max_file_size_mb < 0:
            warnings.append(f"max_file_size_mb cannot be negative: {config.safety.max_file_size_mb}")
        elif config.safety.max_file_size_mb > 1024:
            warnings.append(f"max_file_size_mb too large: {config.safety.max_file_size_mb}MB (maximum: 1024MB)")

        # Max line length (must be reasonable)
        if config.rules.max_line_length < 40:
            warnings.append(f"max_line_length too short: {config.rules.max_line_length} (minimum: 40)")
        elif config.rules.max_line_length > 500:
            warnings.append(f"max_line_length too long: {config.rules.max_line_length} (maximum: 500)")

        return (len(warnings) == 0, warnings)

    @staticmethod
    def validate_hooks(hooks: List[str], dangerous_patterns: List[str]) -> Tuple[bool, List[str]]:
        """Validate hook commands for dangerous patterns.
        
        Args:
            hooks: List of hook commands
            dangerous_patterns: Patterns to check against
            
        Returns:
            Tuple of (is_safe, list_of_warnings)
        """
        warnings = []

        for hook in hooks:
            for pattern in dangerous_patterns:
                if pattern in hook:
                    warnings.append(
                        f"Potentially dangerous command in hook: '{hook}' "
                        f"contains '{pattern}'"
                    )
                    break

        return (len(warnings) == 0, warnings)

    @staticmethod
    def validate_config(config: QwenConfig, cwd: Path) -> Tuple[bool, List[str], List[str]]:
        """Validate entire configuration.
        
        Args:
            config: Configuration to validate
            cwd: Current working directory
            
        Returns:
            Tuple of (is_valid, critical_errors, warnings)
        """
        errors = []
        warnings = []

        # Critical: Path traversal check
        path_valid, path_errors = ConfigValidator.validate_allowed_paths(
            config.safety.allowed_paths, cwd
        )
        if not path_valid:
            errors.extend(path_errors)

        # Warning: Numeric bounds
        bounds_valid, bounds_warnings = ConfigValidator.validate_numeric_bounds(config)
        if not bounds_valid:
            warnings.extend(bounds_warnings)

        # Warning: Dangerous hooks
        all_hooks = (
            config.hooks.post_write +
            config.hooks.post_edit +
            config.hooks.post_delete +
            config.hooks.pre_commit
        )
        hooks_safe, hook_warnings = ConfigValidator.validate_hooks(
            all_hooks,
            config.safety.dangerous_commands
        )
        if not hooks_safe:
            warnings.extend(hook_warnings)

        return (len(errors) == 0, errors, warnings)

    @staticmethod
    def sanitize_config(config: QwenConfig, cwd: Path) -> QwenConfig:
        """Sanitize config by removing invalid values.
        
        Args:
            config: Configuration to sanitize
            cwd: Current working directory
            
        Returns:
            Sanitized configuration
        """
        cwd = cwd.resolve()

        # Filter out paths with traversal
        safe_paths = []
        for path_str in config.safety.allowed_paths:
            try:
                path = (cwd / path_str).resolve()
                try:
                    path.relative_to(cwd)
                    safe_paths.append(path_str)
                except ValueError:
                    console.print(
                        f"[yellow]Warning: Removed path traversal from config:[/yellow] {path_str}"
                    )
            except Exception:
                pass

        config.safety.allowed_paths = safe_paths if safe_paths else ["./"]

        # Clamp numeric values
        config.context.max_tokens = max(1000, min(config.context.max_tokens, 1000000))
        config.safety.max_file_size_mb = max(1, min(config.safety.max_file_size_mb, 1024))
        config.rules.max_line_length = max(40, min(config.rules.max_line_length, 500))

        return config
