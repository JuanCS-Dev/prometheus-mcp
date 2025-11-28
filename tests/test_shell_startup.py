"""
Test shell startup and initialization order.

Boris Cherny - Week 4 Day 4 (Dogfooding)
"""

from jdev_cli.shell import InteractiveShell


class TestShellStartup:
    """Test shell initialization."""

    def test_shell_can_initialize(self):
        """Test that shell initializes without errors."""
        shell = InteractiveShell()

        # Verify critical components are initialized
        assert shell.indexer is not None
        assert shell.suggestion_engine is not None
        assert shell.lsp_client is not None
        assert shell.context_manager is not None
        assert shell.refactoring_engine is not None

    def test_indexer_before_suggestions(self):
        """Test that indexer is initialized before it's used by suggestions."""
        shell = InteractiveShell()

        # ContextSuggestionEngine requires indexer
        assert hasattr(shell, 'indexer')
        assert hasattr(shell, 'suggestion_engine')

        # Verify indexer is usable
        assert shell.suggestion_engine.indexer is shell.indexer

    def test_shell_has_dashboard(self):
        """Test that shell has dashboard initialized."""
        shell = InteractiveShell()

        # Verify dashboard exists
        assert hasattr(shell, 'dashboard')
        assert shell.dashboard is not None
