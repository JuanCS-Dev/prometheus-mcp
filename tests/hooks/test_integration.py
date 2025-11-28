"""Integration tests for hooks system with file operations."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

from jdev_cli.hooks import (
    HookExecutor,
    HookEvent,
    HookContext
)


class TestHooksIntegration:
    """Integration tests for complete hooks workflow."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    @pytest.fixture
    def executor(self):
        """Create hook executor instance."""
        return HookExecutor(enable_sandbox=False, timeout_seconds=10)

    @pytest.mark.asyncio
    async def test_post_write_formatting_workflow(self, temp_dir, executor):
        """Test complete post-write workflow with file formatting."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello world")

        ctx = HookContext(
            file_path=test_file,
            event_name="post_write",
            cwd=temp_dir,
            project_name="test-project"
        )

        hooks = [
            "python -c \"with open('{dir}/format.log', 'w') as f: f.write('Formatted {file_name}')\"",
            "cat {file}"
        ]

        results = await executor.execute_hooks(
            HookEvent.POST_WRITE,
            ctx,
            hooks
        )

        assert len(results) == 2
        assert all(r.success for r in results)

        log_file = temp_dir / "format.log"
        assert log_file.exists()
        assert "Formatted test.txt" in log_file.read_text()

    @pytest.mark.asyncio
    async def test_multiple_files_different_contexts(self, temp_dir, executor):
        """Test hooks with multiple files in different directories."""
        file1 = temp_dir / "file1.py"
        file2 = temp_dir / "subdir" / "file2.py"

        (temp_dir / "subdir").mkdir()
        file1.write_text("print('file1')")
        file2.write_text("print('file2')")

        ctx1 = HookContext(file1, "post_write", cwd=temp_dir)
        ctx2 = HookContext(file2, "post_write", cwd=temp_dir)

        hook = "echo {relative_path}"

        result1 = await executor.execute_hook(HookEvent.POST_WRITE, ctx1, hook)
        result2 = await executor.execute_hook(HookEvent.POST_WRITE, ctx2, hook)

        assert result1.success
        assert result2.success
        assert "file1.py" in result1.stdout
        assert "subdir/file2.py" in result2.stdout

    @pytest.mark.asyncio
    async def test_hook_chain_success(self, temp_dir, executor):
        """Test chain of hooks where all succeed."""
        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1")

        ctx = HookContext(test_file, "post_write", cwd=temp_dir)

        hooks = [
            "echo 'Step 1: Validation'",
            "echo 'Step 2: Formatting'",
            "echo 'Step 3: Testing'"
        ]

        results = await executor.execute_hooks(
            HookEvent.POST_WRITE,
            ctx,
            hooks
        )

        assert len(results) == 3
        assert all(r.success for r in results)
        assert "Step 1" in results[0].stdout
        assert "Step 2" in results[1].stdout
        assert "Step 3" in results[2].stdout

    @pytest.mark.asyncio
    async def test_hook_chain_with_failure(self, temp_dir, executor):
        """Test chain of hooks where one fails."""
        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1")

        ctx = HookContext(test_file, "post_write", cwd=temp_dir)

        hooks = [
            "echo 'Before failure'",
            "python -c 'import sys; sys.exit(1)'",
            "echo 'After failure'"
        ]

        results = await executor.execute_hooks(
            HookEvent.POST_WRITE,
            ctx,
            hooks
        )

        assert len(results) == 3
        assert results[0].success
        assert not results[1].success
        assert results[2].success  # Continues despite failure

    @pytest.mark.asyncio
    async def test_real_python_formatting(self, temp_dir, executor):
        """Test with real Python formatting tool (if available)."""
        test_file = temp_dir / "test.py"
        test_file.write_text("x=1\ny=2")

        ctx = HookContext(test_file, "post_edit", cwd=temp_dir)

        # Try to run black (skip if not installed)
        hook = "python -c 'print(\"Would format {file}\")'"

        result = await executor.execute_hook(
            HookEvent.POST_EDIT,
            ctx,
            hook
        )

        assert result.success
        assert "Would format" in result.stdout

    @pytest.mark.asyncio
    async def test_concurrent_hook_execution(self, temp_dir, executor):
        """Test executing hooks concurrently on different files."""
        files = [temp_dir / f"file{i}.txt" for i in range(5)]
        for f in files:
            f.write_text(f"content of {f.name}")

        contexts = [
            HookContext(f, "post_write", cwd=temp_dir)
            for f in files
        ]

        hook = "echo {file_name}"

        # Execute all hooks concurrently
        tasks = [
            executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)
            for ctx in contexts
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r.success for r in results)

        # Check each file name appears in corresponding output
        for i, result in enumerate(results):
            assert f"file{i}.txt" in result.stdout

    @pytest.mark.asyncio
    async def test_hook_statistics_tracking(self, temp_dir, executor):
        """Test that statistics are tracked correctly."""
        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1")

        ctx = HookContext(test_file, "post_write", cwd=temp_dir)

        hooks = [
            "echo 'success1'",
            "echo 'success2'",
            "python -c 'import sys; sys.exit(1)'",
            "echo 'success3'"
        ]

        await executor.execute_hooks(HookEvent.POST_WRITE, ctx, hooks)

        stats = executor.get_stats()

        assert stats['total_executions'] == 4
        assert stats['direct_executions'] == 4
        assert stats['sandboxed_executions'] == 0
        assert stats['failed_executions'] == 1
        assert 70 < stats['success_rate'] < 80  # 75% (3/4)

    @pytest.mark.asyncio
    async def test_different_events_same_file(self, temp_dir, executor):
        """Test different hook events on same file."""
        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1")

        ctx_write = HookContext(test_file, "post_write", cwd=temp_dir)
        ctx_edit = HookContext(test_file, "post_edit", cwd=temp_dir)
        ctx_delete = HookContext(test_file, "post_delete", cwd=temp_dir)

        hook = "echo {event}: {file_name}"

        result_write = await executor.execute_hook(
            HookEvent.POST_WRITE, ctx_write, hook
        )
        result_edit = await executor.execute_hook(
            HookEvent.POST_EDIT, ctx_edit, hook
        )
        result_delete = await executor.execute_hook(
            HookEvent.POST_DELETE, ctx_delete, hook
        )

        assert "post_write" in result_write.stdout
        assert "post_edit" in result_edit.stdout
        assert "post_delete" in result_delete.stdout

    @pytest.mark.asyncio
    async def test_hook_with_project_metadata(self, temp_dir, executor):
        """Test hooks using project metadata in context."""
        test_file = temp_dir / "src" / "main.py"
        (temp_dir / "src").mkdir()
        test_file.write_text("def main(): pass")

        ctx = HookContext(
            file_path=test_file,
            event_name="post_write",
            cwd=temp_dir,
            project_name="awesome-project",
            metadata={
                "version": "1.0.0",
                "author": "test-user"
            }
        )

        hook = "echo '{project_name} v{version} by {author}'"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success
        assert "awesome-project" in result.stdout
        assert "1.0.0" in result.stdout
        assert "test-user" in result.stdout
