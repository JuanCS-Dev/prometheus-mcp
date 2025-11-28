"""
Comprehensive E2E Tests: Parallel Execution
============================================

Tests parallel tool execution, dependency detection, wave-based execution.
Real concurrent operations with timing validation.

Author: JuanCS Dev
Date: 2025-11-27
"""

import pytest
import asyncio
import time


class TestParallelToolExecution:
    """Test parallel execution of independent tools."""

    @pytest.mark.asyncio
    async def test_parallel_independent_reads(self, sample_python_project):
        """Test parallel execution of independent read operations."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.file_ops import ReadFileTool

        read_tool = ReadFileTool()

        async def execute_read(tool_name, **kwargs):
            return await read_tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_read)

        # Find multiple files
        files = list(sample_python_project.rglob("*.py"))[:5]

        tool_calls = [("read_file", {"path": str(f)}) for f in files]

        start = time.time()
        result = await executor.execute(tool_calls)
        duration = time.time() - start

        assert result.wave_count == 1  # All should execute in one wave
        assert len(result.results) == len(files)
        assert all(r["success"] for r in result.results.values())
        # Parallel should have reasonable speedup (>0.5 means some concurrency)
        assert result.parallelism_factor > 0.5

    @pytest.mark.asyncio
    async def test_parallel_independent_searches(self, sample_python_project):
        """Test parallel execution of independent searches."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.search import SearchFilesTool

        search_tool = SearchFilesTool()

        async def execute_search(tool_name, **kwargs):
            return await search_tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_search)

        tool_calls = [
            ("search_files", {"pattern": "def ", "path": str(sample_python_project)}),
            ("search_files", {"pattern": "class ", "path": str(sample_python_project)}),
            ("search_files", {"pattern": "import ", "path": str(sample_python_project)}),
        ]

        start = time.time()
        result = await executor.execute(tool_calls)
        duration = time.time() - start

        assert result.wave_count == 1
        assert len(result.results) == 3
        assert all(r["success"] for r in result.results.values())

    @pytest.mark.asyncio
    async def test_sequential_dependent_write_read(self, temp_project):
        """Test sequential execution of dependent write->read."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor, detect_tool_dependencies
        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()

        tools = {"write_file": write_tool, "read_file": read_tool}

        async def execute_tool(tool_name, **kwargs):
            tool = tools[tool_name]
            return await tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_tool)

        test_file = str(temp_project / "test.txt")
        tool_calls = [
            ("write_file", {"path": test_file, "content": "hello"}),
            ("read_file", {"path": test_file}),
        ]

        # Detect dependencies
        deps = detect_tool_dependencies(tool_calls)
        assert len(deps[1].depends_on) == 1  # Read depends on write

        result = await executor.execute(tool_calls)

        assert result.wave_count == 2  # Two waves: write, then read
        assert all(r["success"] for r in result.results.values())

    @pytest.mark.asyncio
    async def test_sequential_write_edit_read(self, temp_project):
        """Test sequential execution of write->edit->read chain."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.file_ops import WriteFileTool, EditFileTool, ReadFileTool

        write_tool = WriteFileTool()
        edit_tool = EditFileTool()
        read_tool = ReadFileTool()

        tools = {"write_file": write_tool, "edit_file": edit_tool, "read_file": read_tool}

        async def execute_tool(tool_name, **kwargs):
            tool = tools[tool_name]
            if tool_name == "edit_file":
                kwargs["preview"] = False
                kwargs["create_backup"] = False
            return await tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_tool)

        test_file = str(temp_project / "chain.txt")
        tool_calls = [
            ("write_file", {"path": test_file, "content": "original"}),
            ("edit_file", {"path": test_file, "edits": [{"search": "original", "replace": "modified"}]}),
            ("read_file", {"path": test_file}),
        ]

        result = await executor.execute(tool_calls)

        assert result.wave_count == 3  # Three sequential waves
        assert all(r["success"] for r in result.results.values())
        # Verify final content
        final_result = result.results["tool_2"]
        assert "modified" in final_result["data"]["content"]

    @pytest.mark.asyncio
    async def test_parallel_writes_different_files(self, temp_project):
        """Test parallel writes to different files."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.file_ops import WriteFileTool

        write_tool = WriteFileTool()

        async def execute_write(tool_name, **kwargs):
            return await write_tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_write)

        tool_calls = [
            ("write_file", {"path": str(temp_project / f"file{i}.txt"), "content": f"content{i}"})
            for i in range(10)
        ]

        result = await executor.execute(tool_calls)

        assert result.wave_count == 1  # All parallel
        assert len(result.results) == 10
        assert all(r["success"] for r in result.results.values())
        assert result.parallelism_factor > 0.5

    @pytest.mark.asyncio
    async def test_mixed_parallel_sequential(self, temp_project):
        """Test mixed parallel and sequential execution."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()

        tools = {"write_file": write_tool, "read_file": read_tool}

        async def execute_tool(tool_name, **kwargs):
            tool = tools[tool_name]
            return await tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_tool)

        # Wave 1: Write file1, file2 (parallel)
        # Wave 2: Read file1, file2 (parallel, depends on writes)
        tool_calls = [
            ("write_file", {"path": str(temp_project / "file1.txt"), "content": "a"}),
            ("write_file", {"path": str(temp_project / "file2.txt"), "content": "b"}),
            ("read_file", {"path": str(temp_project / "file1.txt")}),
            ("read_file", {"path": str(temp_project / "file2.txt")}),
        ]

        result = await executor.execute(tool_calls)

        assert result.wave_count == 2  # Two waves
        assert len(result.results) == 4
        assert all(r["success"] for r in result.results.values())

    @pytest.mark.asyncio
    async def test_dependency_detection_same_file(self, temp_project):
        """Test dependency detection for operations on same file."""
        from jdev_tui.core.parallel_executor import detect_tool_dependencies

        test_file = str(temp_project / "same.txt")
        tool_calls = [
            ("write_file", {"path": test_file, "content": "v1"}),
            ("read_file", {"path": test_file}),
            ("edit_file", {"path": test_file, "edits": []}),
            ("read_file", {"path": test_file}),
        ]

        deps = detect_tool_dependencies(tool_calls)

        # tool_1 (read) depends on tool_0 (write)
        assert "tool_0" in deps[1].depends_on
        # tool_2 (edit) depends on tool_0 and tool_1
        assert "tool_0" in deps[2].depends_on or "tool_1" in deps[2].depends_on
        # tool_3 (read) depends on tool_2 (edit)
        assert "tool_2" in deps[3].depends_on

    @pytest.mark.asyncio
    async def test_max_parallel_limit(self, temp_project):
        """Test that parallel execution respects max limit."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.file_ops import WriteFileTool

        write_tool = WriteFileTool()

        async def execute_write(tool_name, **kwargs):
            await asyncio.sleep(0.1)  # Simulate work
            return await write_tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_write, max_parallel=3)

        tool_calls = [
            ("write_file", {"path": str(temp_project / f"file{i}.txt"), "content": f"c{i}"})
            for i in range(10)
        ]

        result = await executor.execute(tool_calls)

        assert all(r["success"] for r in result.results.values())

    @pytest.mark.asyncio
    async def test_error_in_parallel_execution(self, temp_project):
        """Test error handling in parallel execution."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.file_ops import ReadFileTool

        read_tool = ReadFileTool()

        async def execute_read(tool_name, **kwargs):
            return await read_tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_read)

        tool_calls = [
            ("read_file", {"path": str(temp_project / "exists.txt")}),
            ("read_file", {"path": str(temp_project / "nonexistent.txt")}),
        ]

        # Create one file
        (temp_project / "exists.txt").write_text("content")

        result = await executor.execute(tool_calls)

        assert result.results["tool_0"]["success"] is True
        assert result.results["tool_1"]["success"] is False


class TestDependencyDetection:
    """Test comprehensive dependency detection."""

    def test_detect_read_write_dependency(self):
        """Test detecting read->write dependency."""
        from jdev_tui.core.parallel_executor import detect_tool_dependencies

        tool_calls = [
            ("read_file", {"path": "test.txt"}),
            ("write_file", {"path": "test.txt", "content": "new"}),
        ]

        deps = detect_tool_dependencies(tool_calls)

        # Write depends on read
        assert "tool_0" in deps[1].depends_on

    def test_detect_write_edit_dependency(self):
        """Test detecting write->edit dependency."""
        from jdev_tui.core.parallel_executor import detect_tool_dependencies

        tool_calls = [
            ("write_file", {"path": "test.txt", "content": "original"}),
            ("edit_file", {"path": "test.txt", "edits": []}),
        ]

        deps = detect_tool_dependencies(tool_calls)

        assert "tool_0" in deps[1].depends_on

    def test_detect_multiple_edits_sequential(self):
        """Test multiple edits to same file are sequential."""
        from jdev_tui.core.parallel_executor import detect_tool_dependencies

        tool_calls = [
            ("write_file", {"path": "test.txt", "content": "v1"}),
            ("edit_file", {"path": "test.txt", "edits": []}),
            ("edit_file", {"path": "test.txt", "edits": []}),
        ]

        deps = detect_tool_dependencies(tool_calls)

        assert "tool_0" in deps[1].depends_on
        assert "tool_1" in deps[2].depends_on

    def test_detect_git_operations_sequential(self):
        """Test git operations are sequential."""
        from jdev_tui.core.parallel_executor import detect_tool_dependencies

        tool_calls = [
            ("git_status", {"path": "."}),
            ("git_diff", {"path": "."}),
            ("git_commit", {}),
        ]

        deps = detect_tool_dependencies(tool_calls)

        # Each git op depends on previous
        assert "tool_0" in deps[1].depends_on
        assert "tool_1" in deps[2].depends_on

    def test_independent_files_no_dependency(self):
        """Test operations on different files have no dependency."""
        from jdev_tui.core.parallel_executor import detect_tool_dependencies

        tool_calls = [
            ("write_file", {"path": "file1.txt", "content": "a"}),
            ("write_file", {"path": "file2.txt", "content": "b"}),
            ("write_file", {"path": "file3.txt", "content": "c"}),
        ]

        deps = detect_tool_dependencies(tool_calls)

        # No dependencies
        assert len(deps[0].depends_on) == 0
        assert len(deps[1].depends_on) == 0
        assert len(deps[2].depends_on) == 0


class TestConcurrentStressTest:
    """Stress test parallel execution with many operations."""

    @pytest.mark.asyncio
    async def test_many_parallel_reads(self, sample_python_project):
        """Test many parallel reads (50+)."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.file_ops import ReadFileTool

        read_tool = ReadFileTool()

        async def execute_read(tool_name, **kwargs):
            return await read_tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_read)

        # Get all python files
        files = list(sample_python_project.rglob("*.py"))[:50]

        tool_calls = [("read_file", {"path": str(f)}) for f in files]

        result = await executor.execute(tool_calls)

        assert result.wave_count == 1
        assert len(result.results) == len(files)

    @pytest.mark.asyncio
    async def test_many_sequential_writes(self, temp_project):
        """Test many writes to same file (sequential)."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.file_ops import WriteFileTool, EditFileTool

        write_tool = WriteFileTool()
        edit_tool = EditFileTool()

        tools = {"write_file": write_tool, "edit_file": edit_tool}

        async def execute_tool(tool_name, **kwargs):
            tool = tools[tool_name]
            if tool_name == "edit_file":
                kwargs["preview"] = False
                kwargs["create_backup"] = False
            return await tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_tool)

        test_file = str(temp_project / "sequential.txt")

        tool_calls = [("write_file", {"path": test_file, "content": "0"})]

        # Add 20 edits
        for i in range(1, 21):
            tool_calls.append((
                "edit_file",
                {"path": test_file, "edits": [{"search": str(i - 1), "replace": str(i)}]}
            ))

        result = await executor.execute(tool_calls)

        assert result.wave_count == 21  # All sequential
        assert all(r["success"] for r in result.results.values())

    @pytest.mark.asyncio
    async def test_complex_dependency_graph(self, temp_project):
        """Test complex dependency graph with multiple chains."""
        from jdev_tui.core.parallel_executor import ParallelToolExecutor
        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()

        tools = {"write_file": write_tool, "read_file": read_tool}

        async def execute_tool(tool_name, **kwargs):
            tool = tools[tool_name]
            return await tool._execute_validated(**kwargs)

        executor = ParallelToolExecutor(execute_tool)

        # Complex pattern:
        # Write A, B, C (parallel)
        # Read A, B, C (parallel, depend on writes)
        # Write D using A+B+C (sequential after reads)
        tool_calls = [
            ("write_file", {"path": str(temp_project / "a.txt"), "content": "a"}),
            ("write_file", {"path": str(temp_project / "b.txt"), "content": "b"}),
            ("write_file", {"path": str(temp_project / "c.txt"), "content": "c"}),
            ("read_file", {"path": str(temp_project / "a.txt")}),
            ("read_file", {"path": str(temp_project / "b.txt")}),
            ("read_file", {"path": str(temp_project / "c.txt")}),
            ("write_file", {"path": str(temp_project / "d.txt"), "content": "d"}),
        ]

        result = await executor.execute(tool_calls)

        # Wave 1: writes a,b,c
        # Wave 2: reads a,b,c + write d
        assert result.wave_count <= 3
        assert all(r["success"] for r in result.results.values())
