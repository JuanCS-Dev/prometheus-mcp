"""
Week 3 Day 1: Auto-Indexing Tests

Tests for background auto-indexing on startup.

Boris Cherny: Type-safe background task testing
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from jdev_cli.shell import InteractiveShell
from jdev_cli.intelligence.indexer import SemanticIndexer


class TestAutoIndexing:
    """Test auto-indexing background task."""

    @pytest.mark.asyncio
    async def test_auto_index_task_created_on_startup(self):
        """Test that auto-index task is created when shell starts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple Python file to index
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    pass\n")

            # Create shell in temp directory
            with patch('jdev_cli.shell.os.getcwd', return_value=tmpdir):
                shell = object.__new__(InteractiveShell)
                shell.console = Mock()
                shell.indexer = SemanticIndexer(root_path=tmpdir)
                shell._indexer_initialized = False
                shell._auto_index_task = None

                # Call _auto_index_background directly
                await shell._auto_index_background()

                # Verify: indexer was called
                assert shell._indexer_initialized is True

    @pytest.mark.asyncio
    async def test_auto_index_does_not_block_shell(self):
        """Test that auto-indexing doesn't block interactive shell."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple files to index
            for i in range(5):
                test_file = Path(tmpdir) / f"test{i}.py"
                test_file.write_text(f"def func{i}():\n    pass\n")

            with patch('jdev_cli.shell.os.getcwd', return_value=tmpdir):
                shell = object.__new__(InteractiveShell)
                shell.console = Mock()
                shell.indexer = SemanticIndexer(root_path=tmpdir)
                shell._indexer_initialized = False

                # Start indexing task
                task = asyncio.create_task(shell._auto_index_background())

                # Simulate shell starting (should not be blocked)
                await asyncio.sleep(0.1)  # Shell should be responsive

                # Wait for indexing to complete
                await task

                # Verify: indexing completed
                assert shell._indexer_initialized is True

    @pytest.mark.asyncio
    async def test_auto_index_skips_if_already_initialized(self):
        """Test that auto-index skips if indexer already initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('jdev_cli.shell.os.getcwd', return_value=tmpdir):
                shell = object.__new__(InteractiveShell)
                shell.console = Mock()
                shell.indexer = SemanticIndexer(root_path=tmpdir)
                shell._indexer_initialized = True  # Already initialized

                # Mock index_codebase to track calls
                shell.indexer.index_codebase = Mock(return_value=0)

                # Call auto-index
                await shell._auto_index_background()

                # Verify: index_codebase was NOT called
                shell.indexer.index_codebase.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_index_handles_errors_gracefully(self):
        """Test that indexing errors don't crash the shell."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('jdev_cli.shell.os.getcwd', return_value=tmpdir):
                shell = object.__new__(InteractiveShell)
                shell.console = Mock()
                shell.indexer = SemanticIndexer(root_path=tmpdir)
                shell._indexer_initialized = False

                # Make index_codebase raise an error
                def raise_error(*args, **kwargs):
                    raise Exception("Simulated indexing error")

                shell.indexer.index_codebase = raise_error

                # Call auto-index (should not raise)
                await shell._auto_index_background()

                # Verify: shell survived (no exception raised)
                # indexer should NOT be marked as initialized on error
                assert shell._indexer_initialized is False

    @pytest.mark.asyncio
    async def test_auto_index_uses_cache(self):
        """Test that auto-index uses cache (force=False)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('jdev_cli.shell.os.getcwd', return_value=tmpdir):
                shell = object.__new__(InteractiveShell)
                shell.console = Mock()
                shell.indexer = SemanticIndexer(root_path=tmpdir)
                shell._indexer_initialized = False

                # Mock index_codebase to capture arguments
                shell.indexer.index_codebase = Mock(return_value=5)
                shell.indexer.get_stats = Mock(return_value={'total_symbols': 10, 'unique_symbols': 8})

                # Call auto-index
                await shell._auto_index_background()

                # Verify: index_codebase called with force=False
                shell.indexer.index_codebase.assert_called_once_with(force=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
