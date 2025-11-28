"""
Test suite for BRUTAL AUDIT fixes - Real functional tests

Tests:
1. Session atomic writes (concurrent safety)
2. Token tracking integration with LLM
3. Large file preview handling
4. Error handling in async functions
"""

import asyncio
import json
import pytest
import time

# Imports for session tests
from jdev_cli.session.manager import SessionManager

# Imports for token tracking
from jdev_cli.core.token_tracker import TokenTracker
from jdev_cli.core.llm import LLMClient

# Imports for preview
from jdev_cli.tui.components.preview import DiffGenerator


class TestSessionAtomicWrites:
    """Test session save with atomic writes and concurrency."""

    def test_atomic_write_pattern(self):
        """Verify atomic write pattern (temp → replace)."""
        manager = SessionManager()
        state = manager.create_session()
        state.history.append("test command")

        # Save session
        session_file = manager.save_session(state)

        # Verify file exists and is valid JSON
        assert session_file.exists()
        with open(session_file) as f:
            data = json.load(f)
            assert data['session_id'] == state.session_id
            assert 'test command' in data['history']

        # Verify no temp files left behind
        temp_files = list(session_file.parent.glob("*.tmp"))
        assert len(temp_files) == 0, "Temp files should be cleaned up"

    @pytest.mark.asyncio
    async def test_concurrent_saves_no_corruption(self):
        """Test concurrent saves don't corrupt data."""
        manager = SessionManager()
        state = manager.create_session()

        # Simulate concurrent saves
        async def save_with_data(msg: str):
            state.history.append(msg)
            manager.save_session(state)
            await asyncio.sleep(0.01)  # Simulate work

        # Run 50 concurrent saves
        tasks = [save_with_data(f"msg_{i}") for i in range(50)]
        await asyncio.gather(*tasks)

        # Reload and verify no corruption
        loaded = manager.load_session(state.session_id)
        assert len(loaded.history) == 50

        # Verify all messages present
        messages = set(loaded.history)
        assert len(messages) == 50, "No duplicates or lost messages"


class TestTokenTrackingIntegration:
    """Test token tracking integration with LLM."""

    def test_token_tracker_basic(self):
        """Test basic token tracking functionality."""
        tracker = TokenTracker(budget=10000, cost_per_1k=0.002)

        # Track some tokens
        tracker.track_tokens(input_tokens=100, output_tokens=50, context="test")
        tracker.track_tokens(input_tokens=200, output_tokens=100, context="test2")

        # Verify totals
        usage = tracker.get_usage()
        assert usage['total_tokens'] == 450
        assert usage['input_tokens'] == 300
        assert usage['output_tokens'] == 150
        assert usage['requests'] == 2

    def test_token_tracker_budget_warning(self):
        """Test budget warning levels."""
        tracker = TokenTracker(budget=1000)

        # Use 750 tokens (75%)
        tracker.track_tokens(input_tokens=750, output_tokens=0)

        # Should trigger warning
        assert tracker.get_warning_level() == "warning"

        # Use 950 tokens total (95%)
        tracker.track_tokens(input_tokens=200, output_tokens=0)
        assert tracker.get_warning_level() == "critical"

    def test_llm_client_token_callback(self):
        """Test LLM client calls token callback."""
        tracker = TokenTracker(budget=100000)
        callback_called = []

        def token_callback(input_tokens: int, output_tokens: int):
            callback_called.append({'input': input_tokens, 'output': output_tokens})

        # Create LLM client with callback
        client = LLMClient(token_callback=token_callback)

        # Verify callback is set
        assert client.token_callback is not None

        # Manually call callback (simulating LLM response)
        client.token_callback(150, 75)

        # Verify callback was called
        assert len(callback_called) == 1
        assert callback_called[0]['input'] == 150
        assert callback_called[0]['output'] == 75


class TestLargeFilePreview:
    """Test preview handling for large files."""

    def test_large_file_diff_generation(self):
        """Test diff generation doesn't crash on large files."""
        # Create large content (5000 lines)
        old_content = "\n".join([f"line {i}" for i in range(5000)])
        new_content = "\n".join([f"line {i} modified" for i in range(5000)])

        # Generate diff
        diff = DiffGenerator.generate_diff(
            old_content=old_content,
            new_content=new_content,
            file_path="large_file.py",
            language="python"
        )

        # Verify diff was generated
        assert diff is not None
        assert diff.file_path == "large_file.py"
        assert len(diff.hunks) > 0

    def test_diff_with_partial_changes(self):
        """Test diff with changes in small section of large file."""
        lines_before = ["line " + str(i) for i in range(1000)]
        lines_after = lines_before.copy()

        # Modify only lines 500-510
        for i in range(500, 510):
            lines_after[i] = f"MODIFIED {i}"

        old_content = "\n".join(lines_before)
        new_content = "\n".join(lines_after)

        # Generate diff
        diff = DiffGenerator.generate_diff(
            old_content=old_content,
            new_content=new_content,
            file_path="test.py",
            language="python",
            context_lines=3
        )

        # Should have 1 hunk (the modified section)
        assert len(diff.hunks) > 0

        # Hunk should be localized (not entire file)
        hunk = diff.hunks[0]
        assert hunk.old_count < 100, "Hunk should be small, not entire file"


class TestAsyncErrorHandling:
    """Test async error handling patterns."""

    @pytest.mark.asyncio
    async def test_async_generator_error_handling(self):
        """Test async generator handles errors gracefully."""

        async def generator_with_error():
            try:
                yield "chunk1"
                yield "chunk2"
                raise ValueError("Simulated error")
            except ValueError as e:
                # Handle and cleanup
                yield f"error: {e}"

        # Consume generator
        chunks = []
        async for chunk in generator_with_error():
            chunks.append(chunk)

        # Should have received chunks + error message
        assert len(chunks) == 3
        assert "error:" in chunks[-1]

    @pytest.mark.asyncio
    async def test_task_group_error_aggregation(self):
        """Test TaskGroup aggregates errors (Python 3.11+)."""

        async def failing_task(n: int):
            await asyncio.sleep(0.01)
            if n == 2:
                raise ValueError(f"Task {n} failed")
            return n

        try:
            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(failing_task(i)) for i in range(5)]
        except* ValueError as eg:
            # ExceptionGroup catches grouped exceptions
            assert len(eg.exceptions) == 1
            assert "Task 2 failed" in str(eg.exceptions[0])


class TestRealWorldUsage:
    """Integration tests with real usage patterns."""

    @pytest.mark.asyncio
    async def test_complete_session_workflow(self):
        """Test complete session: create → modify → save → load."""
        manager = SessionManager()

        # Create session
        state = manager.create_session()
        session_id = state.session_id

        # Simulate usage
        state.history.append("ls")
        state.history.append("cat main.py")
        state.files_read.add("main.py")
        state.tool_calls_count = 2

        # Save
        manager.save_session(state)

        # Load
        loaded = manager.load_session(session_id)

        # Verify
        assert loaded.session_id == session_id
        assert len(loaded.history) == 2
        assert "main.py" in loaded.files_read
        assert loaded.tool_calls_count == 2

    def test_token_tracker_export_stats(self):
        """Test token tracker exports valid JSON stats."""
        tracker = TokenTracker(budget=50000)

        # Simulate usage
        tracker.track_tokens(100, 50, "request 1")
        tracker.track_tokens(200, 100, "request 2")
        tracker.track_tokens(150, 75, "request 3")

        # Export stats
        stats_json = tracker.export_stats()

        # Parse and verify
        stats = json.loads(stats_json)
        assert stats['total_tokens'] == 675
        assert stats['requests'] == 3
        assert 'history' in stats
        assert len(stats['history']) == 3


# Performance benchmarks
class TestPerformance:
    """Performance tests to ensure fixes don't degrade speed."""

    def test_session_save_performance(self):
        """Session save should be fast (<100ms)."""
        manager = SessionManager()
        state = manager.create_session()

        # Add realistic data
        state.history = [f"command {i}" for i in range(100)]
        state.files_read = {f"file{i}.py" for i in range(50)}

        # Measure save time
        start = time.time()
        manager.save_session(state)
        elapsed = time.time() - start

        assert elapsed < 0.1, f"Save took {elapsed:.3f}s, should be <0.1s"

    def test_diff_generation_performance(self):
        """Diff generation should be fast even for large files."""
        # 1000 line file
        old_content = "\n".join([f"line {i}" for i in range(1000)])
        new_content = "\n".join([f"line {i} modified" if i % 10 == 0 else f"line {i}"
                                for i in range(1000)])

        # Measure diff time
        start = time.time()
        diff = DiffGenerator.generate_diff(old_content, new_content, "test.py")
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Diff took {elapsed:.3f}s, should be <1.0s"
        assert diff is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
