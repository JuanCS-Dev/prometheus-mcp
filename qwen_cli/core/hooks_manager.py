"""
HooksManager - File Operation Hooks System
==========================================

Extracted from Bridge GOD CLASS (Nov 2025 Refactoring).

Provides Claude Code-style hooks for file operations:
- post_write: Run after file write
- post_edit: Run after file edit
- post_delete: Run after file delete
- pre_commit: Run before git commit

Features:
- Persistent configuration (~/.juancs/hooks.json)
- Async execution with timeout
- Statistics tracking
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HooksManager:
    """
    Manages file operation hooks with persistence.

    Usage:
        hooks = HooksManager()
        hooks.set_hook("post_write", ["ruff check $FILE", "ruff format $FILE"])
        hooks.enable_hook("post_write", True)
        result = await hooks.execute_hook("post_write", "/path/to/file.py")
    """

    # Available hook types
    HOOK_TYPES = {
        "post_write": "Run after file write",
        "post_edit": "Run after file edit",
        "post_delete": "Run after file delete",
        "pre_commit": "Run before git commit",
    }

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize HooksManager.

        Args:
            config_dir: Directory for config file. Defaults to ~/.juancs
        """
        self._config_dir = config_dir or (Path.home() / ".juancs")
        self._config_path = self._config_dir / "hooks.json"
        self._hooks_executor = None
        self._hooks_config: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of hooks config."""
        if self._initialized:
            return

        # Set defaults
        self._hooks_config = {
            hook_name: {
                "enabled": False,
                "description": description,
                "commands": []
            }
            for hook_name, description in self.HOOK_TYPES.items()
        }

        # Load from config file
        self._load_config()
        self._initialized = True

    def _load_config(self) -> None:
        """Load hooks configuration from file."""
        if not self._config_path.exists():
            return

        try:
            with open(self._config_path, "r") as f:
                saved = json.load(f)
            for hook_name, hook_data in saved.items():
                if hook_name in self._hooks_config:
                    self._hooks_config[hook_name].update(hook_data)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load hooks config: {e}")

    def _save_config(self) -> None:
        """Save hooks configuration to file."""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump(self._hooks_config, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save hooks config: {e}")

    def get_hooks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all configured hooks.

        Returns:
            Dictionary of hook configurations
        """
        self._ensure_initialized()
        return self._hooks_config.copy()

    def get_hook(self, hook_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific hook.

        Args:
            hook_name: Name of the hook

        Returns:
            Hook configuration or None if not found
        """
        self._ensure_initialized()
        return self._hooks_config.get(hook_name)

    def set_hook(self, hook_name: str, commands: List[str]) -> bool:
        """
        Set commands for a specific hook.

        Args:
            hook_name: Name of the hook (post_write, pre_commit, etc.)
            commands: List of command templates to execute

        Returns:
            True if successful
        """
        self._ensure_initialized()

        if hook_name not in self._hooks_config:
            logger.warning(f"Unknown hook: {hook_name}")
            return False

        self._hooks_config[hook_name]["commands"] = commands
        self._hooks_config[hook_name]["enabled"] = len(commands) > 0
        self._save_config()
        return True

    def enable_hook(self, hook_name: str, enabled: bool = True) -> bool:
        """
        Enable or disable a hook.

        Args:
            hook_name: Name of the hook
            enabled: Whether to enable or disable

        Returns:
            True if successful
        """
        self._ensure_initialized()

        if hook_name not in self._hooks_config:
            return False

        self._hooks_config[hook_name]["enabled"] = enabled
        self._save_config()
        return True

    def add_command(self, hook_name: str, command: str) -> bool:
        """
        Add a command to a hook.

        Args:
            hook_name: Name of the hook
            command: Command template to add

        Returns:
            True if successful
        """
        self._ensure_initialized()

        if hook_name not in self._hooks_config:
            return False

        if command not in self._hooks_config[hook_name]["commands"]:
            self._hooks_config[hook_name]["commands"].append(command)
            self._hooks_config[hook_name]["enabled"] = True
            self._save_config()
        return True

    def remove_command(self, hook_name: str, command: str) -> bool:
        """
        Remove a command from a hook.

        Args:
            hook_name: Name of the hook
            command: Command to remove

        Returns:
            True if successful
        """
        self._ensure_initialized()

        if hook_name not in self._hooks_config:
            return False

        commands = self._hooks_config[hook_name]["commands"]
        if command in commands:
            commands.remove(command)
            if not commands:
                self._hooks_config[hook_name]["enabled"] = False
            self._save_config()
        return True

    async def execute_hook(self, hook_name: str, file_path: str) -> Dict[str, Any]:
        """
        Execute a hook for a specific file.

        Args:
            hook_name: Name of the hook to execute
            file_path: Path to the file that triggered the hook

        Returns:
            Dictionary with execution results
        """
        self._ensure_initialized()

        if hook_name not in self._hooks_config:
            return {"success": False, "error": f"Unknown hook: {hook_name}"}

        hook = self._hooks_config[hook_name]
        if not hook["enabled"] or not hook["commands"]:
            return {"success": True, "skipped": True, "reason": "Hook disabled or no commands"}

        # Lazy import of hook executor
        if self._hooks_executor is None:
            try:
                from qwen_dev_cli.hooks import HookExecutor
                self._hooks_executor = HookExecutor(timeout_seconds=30)
            except ImportError:
                return {"success": False, "error": "Hooks system not available"}

        # Map hook name to event
        try:
            from qwen_dev_cli.hooks import HookEvent, HookContext
        except ImportError:
            return {"success": False, "error": "Hooks module not available"}

        event_map = {
            "post_write": HookEvent.POST_WRITE,
            "post_edit": HookEvent.POST_EDIT,
            "post_delete": HookEvent.POST_DELETE,
            "pre_commit": HookEvent.PRE_COMMIT
        }

        event = event_map.get(hook_name)
        if not event:
            return {"success": False, "error": f"Invalid hook event: {hook_name}"}

        # Create context and execute
        context = HookContext(
            file_path=Path(file_path),
            event_name=hook_name,
            cwd=Path.cwd()
        )

        results = await self._hooks_executor.execute_hooks(
            event, context, hook["commands"]
        )

        return {
            "success": all(r.success for r in results),
            "results": [
                {
                    "command": r.command,
                    "success": r.success,
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                    "error": r.error,
                    "execution_time_ms": r.execution_time_ms
                }
                for r in results
            ]
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get hook execution statistics.

        Returns:
            Statistics dictionary
        """
        self._ensure_initialized()

        if self._hooks_executor is None:
            return {"total_executions": 0, "no_executor": True}

        return self._hooks_executor.get_stats()

    def is_hook_enabled(self, hook_name: str) -> bool:
        """
        Check if a hook is enabled.

        Args:
            hook_name: Name of the hook

        Returns:
            True if enabled
        """
        self._ensure_initialized()
        hook = self._hooks_config.get(hook_name)
        return hook is not None and hook.get("enabled", False)

    def get_hook_commands(self, hook_name: str) -> List[str]:
        """
        Get commands for a hook.

        Args:
            hook_name: Name of the hook

        Returns:
            List of command templates
        """
        self._ensure_initialized()
        hook = self._hooks_config.get(hook_name)
        return hook.get("commands", []) if hook else []
