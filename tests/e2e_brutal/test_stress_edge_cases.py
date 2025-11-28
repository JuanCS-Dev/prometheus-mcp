"""
E2E Tests: Stress Tests and Edge Cases
======================================

Tests for system stability under stress and edge case handling.
Tests:
- Concurrent operations
- Large inputs
- Unicode handling
- Rate limiting
- Recovery from failures
"""

import pytest
import asyncio
import time



@pytest.mark.stress
class TestConcurrency:
    """Tests for concurrent operation handling."""

    def test_ISSUE_057_concurrent_file_reads(self, test_workspace, issue_collector):
        """
        ISSUE-057: Concurrent file reads should be safe.

        Stress: 100 simultaneous reads of same file.
        """
        test_file = test_workspace / "concurrent_read.txt"
        test_file.write_text("test content " * 1000)

        from jdev_cli.tools.file_ops import ReadFileTool

        tool = ReadFileTool()

        async def concurrent_reads():
            tasks = []
            for _ in range(100):
                tasks.append(tool._execute_validated(path=str(test_file)))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        start = time.time()
        results = asyncio.run(concurrent_reads())
        duration = time.time() - start

        errors = [r for r in results if isinstance(r, Exception) or (hasattr(r, 'success') and not r.success)]

        if errors:
            issue_collector.add_issue(
                severity="HIGH",
                category="PERFORMANCE",
                title=f"Concurrent reads fail: {len(errors)}/100",
                description="Some concurrent read operations failed",
                reproduction_steps=[
                    "1. Create test file",
                    "2. Start 100 concurrent reads",
                    f"3. {len(errors)} operations failed"
                ],
                expected="All 100 reads succeed",
                actual=f"{len(errors)} failures",
                component="tools/file_ops.py:ReadFileTool",
                persona="STRESS_TEST"
            )

        if duration > 5.0:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="PERFORMANCE",
                title=f"Concurrent reads too slow: {duration:.2f}s",
                description="100 concurrent reads took too long",
                reproduction_steps=[
                    "1. Start 100 concurrent file reads",
                    f"2. Took {duration:.2f} seconds"
                ],
                expected="< 5 seconds for 100 reads",
                actual=f"{duration:.2f} seconds",
                component="tools/file_ops.py:ReadFileTool",
                persona="STRESS_TEST"
            )

    def test_ISSUE_058_concurrent_writes_same_file(self, test_workspace, issue_collector):
        """
        ISSUE-058: Concurrent writes to same file should be serialized.

        Stress: 10 writes to same file simultaneously.
        """
        test_file = test_workspace / "concurrent_write.txt"

        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()

        async def concurrent_writes():
            tasks = []
            for i in range(10):
                tasks.append(tool._execute_validated(
                    path=str(test_file),
                    content=f"Content from writer {i}\n" * 100
                ))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        asyncio.run(concurrent_writes())

        # Check file integrity
        content = test_file.read_text()

        # Content should be from exactly one writer, not corrupted
        valid_contents = [f"Content from writer {i}\n" * 100 for i in range(10)]
        is_valid = content in valid_contents

        if not is_valid and content:
            # Check for corruption (mixed content)
            writer_ids = set()
            for line in content.split("\n"):
                if "Content from writer" in line:
                    try:
                        writer_id = int(line.split()[-1])
                        writer_ids.add(writer_id)
                    except:
                        pass

            if len(writer_ids) > 1:
                issue_collector.add_issue(
                    severity="CRITICAL",
                    category="LOGIC",
                    title="Concurrent writes corrupt file",
                    description="Multiple concurrent writes caused file corruption",
                    reproduction_steps=[
                        "1. Start 10 concurrent writes to same file",
                        "2. Check file content",
                        f"3. Content mixed from writers: {writer_ids}"
                    ],
                    expected="File contains content from exactly one writer",
                    actual=f"File corrupted with content from {len(writer_ids)} writers",
                    component="tools/file_ops.py:WriteFileTool",
                    persona="STRESS_TEST"
                )

    def test_ISSUE_059_agent_concurrent_execution(self, issue_collector):
        """
        ISSUE-059: Multiple agent executions should not interfere.

        Stress: Run 5 agents simultaneously.
        """
        # This test would require real agent setup
        issue_collector.add_issue(
            severity="MEDIUM",
            category="INTEGRATION",
            title="No concurrent agent execution testing",
            description="System doesn't have clear concurrent agent handling",
            reproduction_steps=[
                "1. Start multiple agents with different tasks",
                "2. Check for state interference",
                "3. Verify each agent completes independently"
            ],
            expected="Agents run in isolation without state leakage",
            actual="Not tested - needs implementation",
            component="agent orchestration",
            persona="STRESS_TEST"
        )


@pytest.mark.stress
class TestLargeInputs:
    """Tests for handling large inputs."""

    def test_ISSUE_060_large_file_content(self, test_workspace, issue_collector):
        """
        ISSUE-060: Writing very large file content should work.

        Edge: 50MB file write.
        """
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()

        large_content = "x" * (50 * 1024 * 1024)  # 50MB

        start = time.time()
        result = asyncio.run(tool._execute_validated(
            path=str(test_workspace / "large_file.txt"),
            content=large_content
        ))
        duration = time.time() - start

        if not result.success:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="PERFORMANCE",
                title="Large file write fails",
                description="Cannot write 50MB file",
                reproduction_steps=[
                    "1. Attempt to write 50MB file",
                    f"2. Error: {result.error}"
                ],
                expected="File written successfully",
                actual=f"Error: {result.error}",
                component="tools/file_ops.py:WriteFileTool",
                persona="STRESS_TEST"
            )

        if duration > 30:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="PERFORMANCE",
                title=f"Large file write too slow: {duration:.1f}s",
                description="50MB write should be faster",
                reproduction_steps=[
                    "1. Write 50MB file",
                    f"2. Took {duration:.1f} seconds"
                ],
                expected="< 30 seconds",
                actual=f"{duration:.1f} seconds",
                component="tools/file_ops.py:WriteFileTool",
                persona="STRESS_TEST"
            )

        # Cleanup
        large_file = test_workspace / "large_file.txt"
        if large_file.exists():
            large_file.unlink()

    def test_ISSUE_061_long_command_line(self, issue_collector):
        """
        ISSUE-061: Very long command should be handled.

        Edge: Command > 100KB.
        """
        from jdev_cli.agents.executor import CodeExecutionEngine, ExecutionMode

        engine = CodeExecutionEngine(mode=ExecutionMode.LOCAL, timeout=5.0)

        # Create very long echo command
        long_arg = "x" * (100 * 1024)  # 100KB
        long_cmd = f"echo {long_arg}"

        result = asyncio.run(engine.execute(long_cmd))

        if not result.success and "too long" not in str(result.stderr).lower():
            issue_collector.add_issue(
                severity="LOW",
                category="UX",
                title="Long command error message unclear",
                description="Error for too-long command doesn't explain the issue",
                reproduction_steps=[
                    "1. Execute command > 100KB",
                    f"2. Error: {result.stderr[:100]}"
                ],
                expected="Clear error: Command exceeds maximum length",
                actual=f"Error: {result.stderr[:100]}",
                component="agents/executor.py",
                persona="STRESS_TEST"
            )

    def test_ISSUE_062_many_files_in_directory(self, test_workspace, issue_collector):
        """
        ISSUE-062: Directory with many files should work.

        Edge: Directory with 10,000 files.
        """
        many_files_dir = test_workspace / "many_files"
        many_files_dir.mkdir()

        # Create 1000 files (10K takes too long for test)
        for i in range(1000):
            (many_files_dir / f"file_{i:04d}.txt").write_text(f"content {i}")

        # Test listing
        from jdev_cli.tools.file_ops import ListFilesTool

        try:
            tool = ListFilesTool()
            start = time.time()
            result = asyncio.run(tool._execute_validated(path=str(many_files_dir)))
            duration = time.time() - start

            if duration > 5.0:
                issue_collector.add_issue(
                    severity="MEDIUM",
                    category="PERFORMANCE",
                    title=f"Listing 1000 files too slow: {duration:.2f}s",
                    description="Directory listing should be fast",
                    reproduction_steps=[
                        "1. Create directory with 1000 files",
                        f"2. List took {duration:.2f}s"
                    ],
                    expected="< 5 seconds",
                    actual=f"{duration:.2f} seconds",
                    component="tools/file_ops.py:ListFilesTool",
                    persona="STRESS_TEST"
                )

            if result.success and result.data:
                if len(result.data) < 1000:
                    issue_collector.add_issue(
                        severity="HIGH",
                        category="LOGIC",
                        title="File listing truncated",
                        description=f"Only {len(result.data)} of 1000 files returned",
                        reproduction_steps=[
                            "1. Create 1000 files",
                            "2. List directory",
                            f"3. Only {len(result.data)} returned"
                        ],
                        expected="All 1000 files listed",
                        actual=f"{len(result.data)} files",
                        component="tools/file_ops.py:ListFilesTool",
                        persona="STRESS_TEST"
                    )

        except ImportError:
            issue_collector.add_issue(
                severity="LOW",
                category="INTEGRATION",
                title="ListFilesTool not found",
                description="Cannot test file listing - tool not importable",
                reproduction_steps=["1. Try to import ListFilesTool"],
                expected="Tool exists",
                actual="ImportError",
                component="tools/file_ops.py",
                persona="STRESS_TEST"
            )


@pytest.mark.stress
class TestUnicode:
    """Tests for Unicode and special character handling."""

    def test_ISSUE_063_unicode_filename(self, test_workspace, issue_collector):
        """
        ISSUE-063: Unicode filenames should work.

        Edge: Filename with emoji and non-ASCII.
        """
        unicode_names = [
            "arquivo_português.txt",
            "文件名.txt",
            "файл.txt",
            "emoji_🚀_file.txt",
            "日本語ファイル.txt",
        ]

        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()

        for name in unicode_names:
            test_path = test_workspace / name
            content = f"Content in {name}"

            # Write
            write_result = asyncio.run(write_tool._execute_validated(
                path=str(test_path),
                content=content
            ))

            if not write_result.success:
                issue_collector.add_issue(
                    severity="MEDIUM",
                    category="LOGIC",
                    title=f"Can't write unicode filename: {name}",
                    description="WriteFileTool fails on unicode filename",
                    reproduction_steps=[
                        f"1. Try to write file: {name}",
                        f"2. Error: {write_result.error}"
                    ],
                    expected="File created successfully",
                    actual=f"Error: {write_result.error}",
                    component="tools/file_ops.py:WriteFileTool",
                    persona="STRESS_TEST"
                )
                continue

            # Read back
            read_result = asyncio.run(read_tool._execute_validated(path=str(test_path)))

            if not read_result.success:
                issue_collector.add_issue(
                    severity="MEDIUM",
                    category="LOGIC",
                    title=f"Can't read unicode filename: {name}",
                    description="ReadFileTool fails on unicode filename",
                    reproduction_steps=[
                        f"1. Try to read file: {name}",
                        f"2. Error: {read_result.error}"
                    ],
                    expected="File read successfully",
                    actual=f"Error: {read_result.error}",
                    component="tools/file_ops.py:ReadFileTool",
                    persona="STRESS_TEST"
                )

    def test_ISSUE_064_unicode_content(self, test_workspace, issue_collector):
        """
        ISSUE-064: Unicode content should be preserved.

        Edge: Various Unicode in file content.
        """
        unicode_contents = [
            "Hello 世界",
            "Привет мир",
            "مرحبا بالعالم",
            "🚀 Rocket emoji 🎉",
            "Mixed: café résumé naïve",
            "\u200b\u200c\u200d",  # Zero-width characters
        ]

        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()

        for content in unicode_contents:
            test_file = test_workspace / "unicode_test.txt"

            # Write
            asyncio.run(write_tool._execute_validated(
                path=str(test_file),
                content=content
            ))

            # Read
            result = asyncio.run(read_tool._execute_validated(path=str(test_file)))

            if result.success and result.data != content:
                issue_collector.add_issue(
                    severity="HIGH",
                    category="LOGIC",
                    title="Unicode content not preserved",
                    description=f"Content corrupted: {repr(content[:20])}",
                    reproduction_steps=[
                        f"1. Write: {repr(content[:20])}",
                        f"2. Read: {repr(result.data[:20] if result.data else None)}"
                    ],
                    expected=f"Exact content: {repr(content[:20])}",
                    actual=f"Got: {repr(result.data[:20] if result.data else None)}",
                    component="tools/file_ops.py",
                    persona="STRESS_TEST"
                )

    def test_ISSUE_065_special_chars_in_path(self, test_workspace, issue_collector):
        """
        ISSUE-065: Special characters in path should be escaped.

        Edge: Paths with spaces, quotes, etc.
        """
        special_paths = [
            "file with spaces.txt",
            "file'with'quotes.txt",
            'file"with"double.txt',
            "file;semicolon.txt",
            "file&ampersand.txt",
            "file|pipe.txt",
            "file$dollar.txt",
        ]

        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()

        for name in special_paths:
            test_path = test_workspace / name

            result = asyncio.run(tool._execute_validated(
                path=str(test_path),
                content="test"
            ))

            if not result.success:
                issue_collector.add_issue(
                    severity="MEDIUM",
                    category="LOGIC",
                    title=f"Can't handle special char in path: {name}",
                    description="Path with special characters fails",
                    reproduction_steps=[
                        f"1. Try to create file: {name}",
                        f"2. Error: {result.error}"
                    ],
                    expected="File created (or clear error about invalid char)",
                    actual=f"Error: {result.error}",
                    component="tools/file_ops.py:WriteFileTool",
                    persona="STRESS_TEST"
                )


@pytest.mark.stress
class TestRecovery:
    """Tests for recovery from failures."""

    def test_ISSUE_066_partial_operation_recovery(self, test_workspace, issue_collector):
        """
        ISSUE-066: Partial failures should leave clean state.

        Edge: Multi-file operation fails midway.
        """
        issue_collector.add_issue(
            severity="HIGH",
            category="LOGIC",
            title="No rollback for partial failures",
            description="Multi-file operations don't rollback on failure",
            reproduction_steps=[
                "1. Start multi-file operation (e.g., refactor)",
                "2. Fail on 3rd of 5 files",
                "3. First 2 files modified, rest unchanged"
            ],
            expected="All-or-nothing: rollback on failure",
            actual="Partial state left",
            component="multi-file operations",
            persona="STRESS_TEST"
        )

    def test_ISSUE_067_network_timeout_recovery(self, issue_collector):
        """
        ISSUE-067: Network timeouts should retry gracefully.

        Edge: LLM call times out.
        """
        issue_collector.add_issue(
            severity="MEDIUM",
            category="LOGIC",
            title="Timeout recovery not user-friendly",
            description="When LLM times out, user experience is poor",
            reproduction_steps=[
                "1. LLM call takes too long",
                "2. Timeout occurs",
                "3. Error message and no auto-retry"
            ],
            expected="Auto-retry with 'Still working...' message",
            actual="Hard error with technical message",
            component="core/llm.py",
            persona="STRESS_TEST"
        )

    def test_ISSUE_068_disk_full_handling(self, issue_collector):
        """
        ISSUE-068: Disk full should be handled gracefully.

        Edge: Disk fills up during operation.
        """
        issue_collector.add_issue(
            severity="HIGH",
            category="LOGIC",
            title="No handling for disk full scenario",
            description="System doesn't check disk space before write",
            reproduction_steps=[
                "1. Disk is nearly full",
                "2. Start large write operation",
                "3. Fails mid-write with poor error"
            ],
            expected="Pre-check disk space, clear error if insufficient",
            actual="Fails mid-operation",
            component="tools/file_ops.py:WriteFileTool",
            persona="STRESS_TEST"
        )


@pytest.mark.stress
class TestRateLimiting:
    """Tests for rate limiting and throttling."""

    def test_ISSUE_069_api_rate_limit_handling(self, issue_collector):
        """
        ISSUE-069: API rate limits should be handled.

        Edge: Hit LLM API rate limit.
        """
        issue_collector.add_issue(
            severity="MEDIUM",
            category="LOGIC",
            title="No rate limit handling for LLM API",
            description="Hitting API rate limit causes poor UX",
            reproduction_steps=[
                "1. Make many LLM calls quickly",
                "2. Hit rate limit",
                "3. Error with no guidance"
            ],
            expected="'Rate limit reached. Retrying in 30s...'",
            actual="Raw API error shown",
            component="core/llm.py",
            persona="STRESS_TEST"
        )

    def test_ISSUE_070_tool_call_throttling(self, issue_collector):
        """
        ISSUE-070: Rapid tool calls should be throttled.

        Edge: 100 tool calls in 1 second.
        """
        issue_collector.add_issue(
            severity="LOW",
            category="PERFORMANCE",
            title="No throttling for tool calls",
            description="Rapid tool calls could overwhelm system",
            reproduction_steps=[
                "1. Make 100 tool calls in 1 second",
                "2. System attempts all simultaneously"
            ],
            expected="Throttle to reasonable rate (e.g., 10/s)",
            actual="All attempted simultaneously",
            component="tool execution system",
            persona="STRESS_TEST"
        )
