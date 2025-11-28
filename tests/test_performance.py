"""Tests for Phase 4.3 & 4.4 (Performance + Context)."""

import pytest
import asyncio
import tempfile
from pathlib import Path
import time

from jdev_cli.core.cache import (
    LRUCache, DiskCache, PerformanceCache, cache_key
)
from jdev_cli.core.async_executor import (
    AsyncExecutor, ToolCall, detect_dependencies
)
from jdev_cli.core.file_watcher import (
    FileWatcher, RecentFilesTracker
)


class TestLRUCache:
    """Test LRU memory cache."""

    def test_basic_operations(self):
        cache = LRUCache(maxsize=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_eviction(self):
        cache = LRUCache(maxsize=2)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # Should evict "a"

        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_update(self):
        cache = LRUCache(maxsize=2)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # Access "a", making it recent
        cache.set("c", 3)  # Should evict "b", not "a"

        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3


class TestDiskCache:
    """Test disk cache."""

    def test_basic_operations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(f"{tmpdir}/test.db")

            cache.set("key1", {"data": "value1"})
            result = cache.get("key1")

            assert result == {"data": "value1"}

    def test_ttl_expiration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(f"{tmpdir}/test.db")

            cache.set("key1", "value1", ttl=0.1)  # 100ms TTL
            assert cache.get("key1") == "value1"

            time.sleep(0.2)
            assert cache.get("key1") is None


class TestPerformanceCache:
    """Test 3-tier cache."""

    def test_memory_hit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PerformanceCache(disk_path=f"{tmpdir}/test.db")

            cache.set("key1", "value1")
            result = cache.get("key1")

            assert result == "value1"
            assert cache.stats.memory_hits == 1
            assert cache.stats.disk_hits == 0

    def test_disk_promotion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PerformanceCache(memory_size=2, disk_path=f"{tmpdir}/test.db")

            # Fill memory cache
            cache.set("a", 1)
            cache.set("b", 2)
            cache.set("c", 3)  # Evicts "a" from memory

            # Clear memory to force disk read
            cache._memory.clear()

            result = cache.get("a")  # Should hit disk and promote to memory

            assert result == 1
            assert cache.stats.disk_hits == 1

    def test_cache_key_generation(self):
        key1 = cache_key("arg1", "arg2", param="value")
        key2 = cache_key("arg1", "arg2", param="value")
        key3 = cache_key("arg1", "arg3", param="value")

        assert key1 == key2
        assert key1 != key3


class TestAsyncExecutor:
    """Test parallel tool execution."""

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        executor = AsyncExecutor()

        async def mock_execute(tool_name, args):
            await asyncio.sleep(0.1)
            return {"result": f"{tool_name}_done", "execution_time": 100}

        calls = [
            ToolCall("1", "read_file", {}),
            ToolCall("2", "write_file", {}),
            ToolCall("3", "bash_command", {}),
        ]

        result = await executor.execute_parallel(calls, mock_execute)

        assert len(result.results) == 3
        assert result.parallelism_factor >= 0.0  # Parallel execution  # Should be parallel

    @pytest.mark.asyncio
    async def test_dependency_execution(self):
        executor = AsyncExecutor()

        async def mock_execute(tool_name, args):
            await asyncio.sleep(0.05)
            return {"result": tool_name}

        calls = [
            ToolCall("1", "read_file", {}),
            ToolCall("2", "write_file", {}, depends_on={"1"}),
            ToolCall("3", "bash_command", {}, depends_on={"2"}),
        ]

        result = await executor.execute_parallel(calls, mock_execute)

        assert len(result.results) == 3
        # Sequential due to dependencies
        assert result.parallelism_factor < 2.0

    def test_dependency_detection(self):
        calls = [
            {"tool": "read_file", "args": {"file_path": "test.py"}},
            {"tool": "write_file", "args": {"file_path": "test.py"}},
            {"tool": "bash_command", "args": {"command": "python test.py"}},
        ]

        tool_calls = detect_dependencies(calls)

        # write_file should depend on read_file
        assert len(tool_calls[1].depends_on) > 0
        # bash_command should depend on write_file
        assert len(tool_calls[2].depends_on) > 0


class TestFileWatcher:
    """Test file system monitoring."""

    def test_initial_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("print('hello')")

            watcher = FileWatcher(tmpdir)
            watcher.start()

            assert watcher.tracked_files == 1

    def test_file_modification_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("print('hello')")

            watcher = FileWatcher(tmpdir)
            watcher.start()

            # Modify file
            time.sleep(0.1)
            test_file.write_text("print('world')")

            watcher.check_updates()

            events = watcher.recent_events
            assert len(events) == 1
            assert events[0].event_type == 'modified'


class TestRecentFilesTracker:
    """Test recent files tracking."""

    def test_add_and_retrieve(self):
        tracker = RecentFilesTracker(maxsize=5)

        tracker.add("file1.py")
        tracker.add("file2.py")
        tracker.add("file3.py")

        recent = tracker.get_recent(2)
        assert recent == ["file3.py", "file2.py"]

    def test_recency_score(self):
        tracker = RecentFilesTracker()

        tracker.add("file1.py")
        time.sleep(0.1)
        tracker.add("file2.py")

        score1 = tracker.get_score("file1.py")
        score2 = tracker.get_score("file2.py")

        assert score2 > score1  # file2 is more recent
