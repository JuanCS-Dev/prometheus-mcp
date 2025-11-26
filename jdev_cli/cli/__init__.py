"""CLI package for Juan-Dev-Code"""

# Setup logging FIRST
from jdev_cli.core.logging_setup import setup_logging
setup_logging()

from .repl_masterpiece import MasterpieceREPL, start_masterpiece_repl
from .shell_context import ShellContext
from .intent_detector import IntentDetector

# Re-export app and validate_output_path from cli_app module for backward compatibility
# This avoids circular import issues from jdev_cli.cli.py vs jdev_cli/cli/ package conflict
from jdev_cli.cli_app import app, validate_output_path


def main():
    """Main entry point for the CLI."""
    app()


__all__ = [
    "MasterpieceREPL",
    "start_masterpiece_repl",
    "ShellContext",
    "IntentDetector",
    "app",
    "validate_output_path",
    "main",
]
