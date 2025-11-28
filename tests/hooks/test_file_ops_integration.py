"""Test hooks integration with file operations tools.

Tests that WriteFileTool and EditFileTool properly execute hooks
after successful operations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from jdev_cli.tools.file_ops import WriteFileTool, EditFileTool
from jdev_cli.hooks import HookExecutor
from jdev_cli.config.schema import QwenConfig, HooksConfig


class TestFileOpsHooksIntegration:
    """Test file operations tools execute hooks correctly."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def mock_config_with_hooks(self):
        """Create mock config with hooks."""
        config = QwenConfig()
        config.hooks = HooksConfig(
            post_write=["echo 'post_write hook executed'"],
            post_edit=["echo 'post_edit hook executed'"]
        )

        mock_loader = Mock()
        mock_loader.config = config
        return mock_loader

    @pytest.fixture
    def mock_config_no_hooks(self):
        """Create mock config without hooks."""
        config = QwenConfig()
        config.hooks = HooksConfig()

        mock_loader = Mock()
        mock_loader.config = config
        return mock_loader

    @pytest.fixture
    def executor(self):
        """Create hook executor."""
        return HookExecutor(enable_sandbox=False, timeout_seconds=5)

    # ========== WRITE TOOL INTEGRATION ==========

    @pytest.mark.asyncio
    async def test_write_tool_executes_post_write_hook(
        self, temp_dir, executor, mock_config_with_hooks
    ):
        """Test WriteFileTool executes post_write hooks."""
        tool = WriteFileTool(
            hook_executor=executor,
            config_loader=mock_config_with_hooks
        )

        test_file = temp_dir / "test.py"

        # Change to temp directory
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            result = await tool.execute(
                path=str(test_file),
                content="x = 1"
            )

            assert result.success
            assert test_file.exists()

            # Hook should have been executed
            stats = executor.get_stats()
            assert stats['total_executions'] == 1
            assert stats['direct_executions'] == 1

        finally:
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_write_tool_no_hooks_configured(
        self, temp_dir, executor, mock_config_no_hooks
    ):
        """Test WriteFileTool when no hooks configured."""
        tool = WriteFileTool(
            hook_executor=executor,
            config_loader=mock_config_no_hooks
        )

        test_file = temp_dir / "test.py"

        result = await tool.execute(
            path=str(test_file),
            content="x = 1"
        )

        assert result.success
        assert test_file.exists()

        # No hooks should have been executed
        stats = executor.get_stats()
        assert stats['total_executions'] == 0

    @pytest.mark.asyncio
    async def test_write_tool_hook_failure_doesnt_block(
        self, temp_dir, executor, mock_config_with_hooks
    ):
        """Test WriteFileTool continues even if hook fails."""
        # Configure a failing hook
        mock_config_with_hooks.config.hooks.post_write = [
            "python -c 'import sys; sys.exit(1)'"
        ]

        tool = WriteFileTool(
            hook_executor=executor,
            config_loader=mock_config_with_hooks
        )

        test_file = temp_dir / "test.py"

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            result = await tool.execute(
                path=str(test_file),
                content="x = 1"
            )

            # File operation should succeed despite hook failure
            assert result.success
            assert test_file.exists()

        finally:
            os.chdir(old_cwd)

    # ========== EDIT TOOL INTEGRATION ==========

    @pytest.mark.asyncio
    async def test_edit_tool_executes_post_edit_hook(
        self, temp_dir, executor, mock_config_with_hooks
    ):
        """Test EditFileTool executes post_edit hooks."""
        tool = EditFileTool(
            hook_executor=executor,
            config_loader=mock_config_with_hooks
        )

        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1")

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            result = await tool.execute(
                path=str(test_file),
                edits=[{"search": "x = 1", "replace": "x = 2"}]
            )

            assert result.success
            assert test_file.read_text() == "x = 2"

            # Hook should have been executed
            stats = executor.get_stats()
            assert stats['total_executions'] == 1
            assert stats['direct_executions'] == 1

        finally:
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_edit_tool_no_hooks_configured(
        self, temp_dir, executor, mock_config_no_hooks
    ):
        """Test EditFileTool when no hooks configured."""
        tool = EditFileTool(
            hook_executor=executor,
            config_loader=mock_config_no_hooks
        )

        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1")

        result = await tool.execute(
            path=str(test_file),
            edits=[{"search": "x = 1", "replace": "x = 2"}]
        )

        assert result.success

        # No hooks should have been executed
        stats = executor.get_stats()
        assert stats['total_executions'] == 0

    # ========== HOOK EXECUTOR DISABLED ==========

    @pytest.mark.asyncio
    async def test_write_tool_no_executor(self, temp_dir):
        """Test WriteFileTool works without hook executor."""
        tool = WriteFileTool(
            hook_executor=None,
            config_loader=None
        )

        test_file = temp_dir / "test.py"

        result = await tool.execute(
            path=str(test_file),
            content="x = 1"
        )

        assert result.success
        assert test_file.exists()

    @pytest.mark.asyncio
    async def test_edit_tool_no_executor(self, temp_dir):
        """Test EditFileTool works without hook executor."""
        tool = EditFileTool(
            hook_executor=None,
            config_loader=None
        )

        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1")

        result = await tool.execute(
            path=str(test_file),
            edits=[{"search": "x = 1", "replace": "x = 2"}]
        )

        assert result.success

    # ========== MULTIPLE HOOKS ==========

    @pytest.mark.asyncio
    async def test_write_tool_multiple_hooks(
        self, temp_dir, executor, mock_config_with_hooks
    ):
        """Test WriteFileTool executes multiple hooks."""
        mock_config_with_hooks.config.hooks.post_write = [
            "echo 'hook1'",
            "echo 'hook2'",
            "echo 'hook3'"
        ]

        tool = WriteFileTool(
            hook_executor=executor,
            config_loader=mock_config_with_hooks
        )

        test_file = temp_dir / "test.py"

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            result = await tool.execute(
                path=str(test_file),
                content="x = 1"
            )

            assert result.success

            # All 3 hooks should have been executed
            stats = executor.get_stats()
            assert stats['total_executions'] == 3

        finally:
            os.chdir(old_cwd)

    # ========== VARIABLE SUBSTITUTION ==========

    @pytest.mark.asyncio
    async def test_hooks_use_correct_variables(
        self, temp_dir, executor, mock_config_with_hooks
    ):
        """Test hooks receive correct variable substitution."""
        mock_config_with_hooks.config.hooks.post_write = [
            "echo {file_name}"
        ]

        tool = WriteFileTool(
            hook_executor=executor,
            config_loader=mock_config_with_hooks
        )

        test_file = temp_dir / "myfile.py"

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            result = await tool.execute(
                path=str(test_file),
                content="x = 1"
            )

            assert result.success

            stats = executor.get_stats()
            assert stats['total_executions'] == 1

        finally:
            os.chdir(old_cwd)

    # ========== ERROR HANDLING ==========

    @pytest.mark.asyncio
    async def test_write_tool_hook_exception_handled(
        self, temp_dir, executor, mock_config_with_hooks
    ):
        """Test WriteFileTool handles hook exceptions gracefully."""
        # Configure a hook that will raise exception
        mock_config_with_hooks.config.hooks.post_write = [
            "nonexistent_command_xyz"
        ]

        tool = WriteFileTool(
            hook_executor=executor,
            config_loader=mock_config_with_hooks
        )

        test_file = temp_dir / "test.py"

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            result = await tool.execute(
                path=str(test_file),
                content="x = 1"
            )

            # File operation should succeed
            assert result.success
            assert test_file.exists()

        finally:
            os.chdir(old_cwd)
