"""
E2E Tests: Senior Developer Perspective
=======================================

Tests that simulate a senior developer using the shell.
Seniors expect:
- Precision and correctness
- Proper error handling
- No data loss
- Professional behavior
- Transaction-like operations
"""

import pytest
import asyncio
import os
from pathlib import Path

# Import test infrastructure


@pytest.mark.senior
class TestSeniorFileOperations:
    """Senior developer file operation tests."""

    def test_ISSUE_001_file_creation_without_parent_directory(self, test_workspace, issue_collector):
        """
        ISSUE-001: Creating file in non-existent directory should fail gracefully.

        Senior expectation: Clear error message, no silent failure.
        """
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()

        # Try to create file in non-existent directory
        result = asyncio.run(tool._execute_validated(
            path=str(test_workspace / "nonexistent" / "deep" / "path" / "file.txt"),
            content="test content"
        ))

        # ISSUE: Many tools silently create parent directories or fail with cryptic errors
        if result.success:
            issue_collector.add_issue(
                severity="HIGH",
                category="UX",
                title="File created in non-existent directory without warning",
                description="WriteFileTool creates parent directories without asking user permission",
                reproduction_steps=[
                    "1. Call WriteFileTool with path containing non-existent directories",
                    "2. Tool silently creates all parent directories",
                    "3. User has no control over directory structure"
                ],
                expected="Error message asking user to create directory first, or explicit mkdir option",
                actual="Silently creates parent directories",
                component="tools/file_ops.py:WriteFileTool",
                persona="SENIOR"
            )
            pytest.fail("Tool should not silently create parent directories")

        # Check error message quality
        if result.error and "nonexistent" not in result.error.lower():
            issue_collector.add_issue(
                severity="MEDIUM",
                category="UX",
                title="Unhelpful error message for missing directory",
                description="Error message doesn't clearly indicate which directory is missing",
                reproduction_steps=[
                    "1. Call WriteFileTool with deeply nested non-existent path",
                    "2. Error message is generic"
                ],
                expected="Error: Directory 'nonexistent/deep/path' does not exist",
                actual=f"Error: {result.error}",
                component="tools/file_ops.py:WriteFileTool",
                persona="SENIOR"
            )

    def test_ISSUE_002_atomic_file_write_failure(self, test_workspace, issue_collector):
        """
        ISSUE-002: File writes should be atomic to prevent corruption.

        Senior expectation: Either the file is completely written or not touched.
        """
        test_file = test_workspace / "atomic_test.txt"
        original_content = "original content that must not be lost"
        test_file.write_text(original_content)

        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()

        # Simulate partial write (write something that might fail mid-way)
        large_content = "x" * (10 * 1024 * 1024)  # 10MB

        try:
            # This should be atomic - use temp file + rename
            result = asyncio.run(tool._execute_validated(
                path=str(test_file),
                content=large_content
            ))
        except Exception as e:
            # Check if original content is preserved
            if test_file.exists():
                current = test_file.read_text()
                if current != original_content and current != large_content:
                    issue_collector.add_issue(
                        severity="CRITICAL",
                        category="LOGIC",
                        title="Non-atomic file writes cause data corruption",
                        description="When file write fails mid-way, original content is lost",
                        reproduction_steps=[
                            "1. Create file with important content",
                            "2. Attempt to overwrite with large content",
                            "3. If write fails, check file state"
                        ],
                        expected="Original content preserved on failure",
                        actual=f"File corrupted: {current[:100]}...",
                        component="tools/file_ops.py:WriteFileTool",
                        persona="SENIOR"
                    )
                    pytest.fail("Non-atomic write caused data corruption")

    def test_ISSUE_003_git_operations_without_repo(self, tmp_path, issue_collector):
        """
        ISSUE-003: Git operations outside repo should have clear error.

        Senior expectation: Immediate, clear error - not cryptic git message.
        """
        os.chdir(tmp_path)

        from jdev_cli.tools.git_tools import GitStatusTool

        try:
            tool = GitStatusTool()
            result = asyncio.run(tool._execute_validated())

            if result.success:
                issue_collector.add_issue(
                    severity="HIGH",
                    category="LOGIC",
                    title="Git tool reports success outside git repo",
                    description="GitStatusTool returns success when not in a git repository",
                    reproduction_steps=[
                        "1. Navigate to non-git directory",
                        "2. Call GitStatusTool",
                        "3. Tool reports success"
                    ],
                    expected="Clear error: 'Not a git repository'",
                    actual=f"Success with data: {result.data}",
                    component="tools/git_tools.py:GitStatusTool",
                    persona="SENIOR"
                )
                pytest.fail("Git tool should fail outside git repo")

            # Check error message quality
            if result.error and "git" not in result.error.lower():
                issue_collector.add_issue(
                    severity="MEDIUM",
                    category="UX",
                    title="Git error message doesn't mention git",
                    description="Error message for git operations is not helpful",
                    reproduction_steps=[
                        "1. Run git command outside repo",
                        "2. Error doesn't clearly indicate git issue"
                    ],
                    expected="Error: Not a git repository (or any parent)",
                    actual=f"Error: {result.error}",
                    component="tools/git_tools.py",
                    persona="SENIOR"
                )

        except ImportError:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="INTEGRATION",
                title="GitStatusTool not importable",
                description="Cannot import GitStatusTool - tool may not exist",
                reproduction_steps=["1. Try to import GitStatusTool"],
                expected="Tool exists and is importable",
                actual="ImportError",
                component="tools/git_tools.py",
                persona="SENIOR"
            )

    def test_ISSUE_004_concurrent_file_access(self, test_workspace, issue_collector):
        """
        ISSUE-004: Concurrent access to same file should be handled.

        Senior expectation: Either locking or clear conflict error.
        """
        test_file = test_workspace / "concurrent_test.txt"
        test_file.write_text("initial")

        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()

        errors = []

        async def concurrent_writes():
            tasks = []
            for i in range(10):
                tasks.append(write_tool._execute_validated(
                    path=str(test_file),
                    content=f"content from task {i}"
                ))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        results = asyncio.run(concurrent_writes())

        # Check for race conditions
        final_content = test_file.read_text()
        if "content from task" not in final_content:
            issue_collector.add_issue(
                severity="CRITICAL",
                category="LOGIC",
                title="Concurrent writes cause data loss",
                description="Multiple concurrent writes to same file cause data corruption or loss",
                reproduction_steps=[
                    "1. Start 10 concurrent write operations to same file",
                    "2. Check final file content",
                    "3. Content may be corrupted or from wrong task"
                ],
                expected="Last write wins OR locking prevents concurrent access",
                actual=f"Content: {final_content[:100]}",
                component="tools/file_ops.py:WriteFileTool",
                persona="SENIOR"
            )

    def test_ISSUE_005_path_traversal_in_file_ops(self, test_workspace, issue_collector):
        """
        ISSUE-005: Path traversal should be blocked.

        Senior expectation: Security - can't escape workspace.
        """
        from jdev_cli.tools.file_ops import ReadFileTool

        tool = ReadFileTool()

        # Try various path traversal attacks
        malicious_paths = [
            "../../../etc/passwd",
            "....//....//etc/passwd",
            "/etc/passwd",
            "src/../../../etc/passwd",
            "src/..\\..\\..\\etc\\passwd",  # Windows style
        ]

        for malicious_path in malicious_paths:
            result = asyncio.run(tool._execute_validated(path=malicious_path))

            if result.success and result.data:
                issue_collector.add_issue(
                    severity="CRITICAL",
                    category="SECURITY",
                    title=f"Path traversal vulnerability: {malicious_path}",
                    description="ReadFileTool allows reading files outside workspace",
                    reproduction_steps=[
                        f"1. Call ReadFileTool with path: {malicious_path}",
                        "2. Tool reads file outside allowed directory"
                    ],
                    expected="Error: Path traversal blocked",
                    actual=f"Read succeeded, got {len(result.data)} bytes",
                    component="tools/file_ops.py:ReadFileTool",
                    persona="SENIOR"
                )
                pytest.fail(f"Path traversal vulnerability: {malicious_path}")

    def test_ISSUE_006_empty_file_handling(self, test_workspace, issue_collector):
        """
        ISSUE-006: Empty files should be handled correctly.

        Senior expectation: Empty file != error != non-existent.
        """
        empty_file = test_workspace / "empty.txt"
        empty_file.touch()

        from jdev_cli.tools.file_ops import ReadFileTool

        tool = ReadFileTool()
        result = asyncio.run(tool._execute_validated(path=str(empty_file)))

        if not result.success:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="LOGIC",
                title="Reading empty file reports as error",
                description="ReadFileTool treats empty file as error condition",
                reproduction_steps=[
                    "1. Create empty file",
                    "2. Read with ReadFileTool",
                    "3. Tool reports error"
                ],
                expected="Success with empty string content",
                actual=f"Error: {result.error}",
                component="tools/file_ops.py:ReadFileTool",
                persona="SENIOR"
            )

        if result.success and result.data is None:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="LOGIC",
                title="Empty file returns None instead of empty string",
                description="ReadFileTool returns None for empty files instead of ''",
                reproduction_steps=[
                    "1. Create empty file",
                    "2. Read with ReadFileTool",
                    "3. data is None, not ''"
                ],
                expected="result.data == ''",
                actual="result.data is None",
                component="tools/file_ops.py:ReadFileTool",
                persona="SENIOR"
            )

    def test_ISSUE_007_large_file_memory_handling(self, test_workspace, issue_collector):
        """
        ISSUE-007: Large files should not cause OOM.

        Senior expectation: Streaming or size limit with clear error.
        """
        large_file = test_workspace / "large.txt"

        # Create 100MB file
        with open(large_file, "w") as f:
            for _ in range(100):
                f.write("x" * (1024 * 1024))  # 1MB chunks

        from jdev_cli.tools.file_ops import ReadFileTool

        tool = ReadFileTool()

        import tracemalloc
        tracemalloc.start()

        result = asyncio.run(tool._execute_validated(path=str(large_file)))

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak should not be much more than file size (allow 50% overhead)
        if peak > 150 * 1024 * 1024:  # 150MB
            issue_collector.add_issue(
                severity="HIGH",
                category="PERFORMANCE",
                title="Large file read causes excessive memory usage",
                description=f"Reading 100MB file uses {peak / (1024*1024):.0f}MB memory",
                reproduction_steps=[
                    "1. Create 100MB file",
                    "2. Read with ReadFileTool",
                    "3. Monitor memory usage"
                ],
                expected="Memory usage proportional to file size (≤150MB)",
                actual=f"Peak memory: {peak / (1024*1024):.0f}MB",
                component="tools/file_ops.py:ReadFileTool",
                persona="SENIOR"
            )

        # Cleanup
        large_file.unlink()


@pytest.mark.senior
class TestSeniorAgentBehavior:
    """Tests for agent behavior from senior perspective."""

    def test_ISSUE_008_agent_task_validation(self, issue_collector):
        """
        ISSUE-008: Agent should validate tasks before execution.

        Senior expectation: Fail fast on invalid input.
        """
        from jdev_cli.agents.base import AgentTask

        # Test empty request
        try:
            task = AgentTask(request="")
            issue_collector.add_issue(
                severity="MEDIUM",
                category="LOGIC",
                title="AgentTask accepts empty request",
                description="AgentTask doesn't validate that request is non-empty",
                reproduction_steps=[
                    "1. Create AgentTask with empty string request",
                    "2. No validation error raised"
                ],
                expected="ValidationError: request cannot be empty",
                actual="Task created successfully with empty request",
                component="agents/base.py:AgentTask",
                persona="SENIOR"
            )
        except Exception:
            pass  # Good - validation exists

        # Test whitespace-only request
        try:
            task = AgentTask(request="   \n\t  ")
            issue_collector.add_issue(
                severity="MEDIUM",
                category="LOGIC",
                title="AgentTask accepts whitespace-only request",
                description="AgentTask doesn't strip/validate whitespace requests",
                reproduction_steps=[
                    "1. Create AgentTask with whitespace-only request",
                    "2. No validation error raised"
                ],
                expected="ValidationError: request cannot be blank",
                actual="Task created with whitespace request",
                component="agents/base.py:AgentTask",
                persona="SENIOR"
            )
        except Exception:
            pass

    def test_ISSUE_009_agent_response_consistency(self, issue_collector):
        """
        ISSUE-009: Agent responses should have consistent structure.

        Senior expectation: Same response structure always.
        """
        from jdev_cli.agents.base import AgentResponse

        # Success response
        success = AgentResponse(success=True, data={"result": "ok"})

        # Error response
        error = AgentResponse(success=False, error="Something went wrong")

        # Check for inconsistencies
        issues_found = []

        # Both should have reasoning
        if not hasattr(success, 'reasoning') or not hasattr(error, 'reasoning'):
            issues_found.append("reasoning field missing")

        # Error should not have data, or data should be empty
        if error.success is False and error.data:
            issues_found.append("error response has non-empty data")

        # Success should not have error
        if success.success is True and success.error:
            issues_found.append("success response has error message")

        if issues_found:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="LOGIC",
                title="Inconsistent AgentResponse structure",
                description=f"AgentResponse has inconsistencies: {issues_found}",
                reproduction_steps=[
                    "1. Create success and error AgentResponse",
                    "2. Compare structures"
                ],
                expected="Consistent fields: success=True → no error; success=False → no data",
                actual=f"Issues: {issues_found}",
                component="agents/base.py:AgentResponse",
                persona="SENIOR"
            )

    def test_ISSUE_010_capability_enforcement(self, issue_collector):
        """
        ISSUE-010: Agents should strictly enforce capabilities.

        Senior expectation: PLANNER can't write files.
        """
        from jdev_cli.agents.base import AgentCapability
        from jdev_cli.agents.planner import PlannerAgent

        # Create planner (should be READ_ONLY + DESIGN)
        mock_llm = type('MockLLM', (), {
            'generate': lambda self, **kwargs: "test response"
        })()

        try:
            planner = PlannerAgent(mock_llm, None)

            # Check capabilities
            if AgentCapability.FILE_EDIT in planner.capabilities:
                issue_collector.add_issue(
                    severity="CRITICAL",
                    category="SECURITY",
                    title="PlannerAgent has FILE_EDIT capability",
                    description="Planner should be read-only but has file edit capability",
                    reproduction_steps=[
                        "1. Create PlannerAgent",
                        "2. Check capabilities",
                        "3. FILE_EDIT is present"
                    ],
                    expected="Capabilities: [READ_ONLY, DESIGN]",
                    actual=f"Capabilities: {planner.capabilities}",
                    component="agents/planner.py:PlannerAgent",
                    persona="SENIOR"
                )

            if AgentCapability.BASH_EXEC in planner.capabilities:
                issue_collector.add_issue(
                    severity="CRITICAL",
                    category="SECURITY",
                    title="PlannerAgent has BASH_EXEC capability",
                    description="Planner should not be able to execute bash commands",
                    reproduction_steps=[
                        "1. Create PlannerAgent",
                        "2. Check capabilities",
                        "3. BASH_EXEC is present"
                    ],
                    expected="Capabilities: [READ_ONLY, DESIGN]",
                    actual=f"Capabilities: {planner.capabilities}",
                    component="agents/planner.py:PlannerAgent",
                    persona="SENIOR"
                )

        except Exception as e:
            issue_collector.add_issue(
                severity="HIGH",
                category="CRASH",
                title="PlannerAgent fails to initialize",
                description=f"Cannot create PlannerAgent: {e}",
                reproduction_steps=[
                    "1. Try to create PlannerAgent with mock LLM",
                    "2. Exception raised"
                ],
                expected="PlannerAgent initializes successfully",
                actual=f"Exception: {e}",
                component="agents/planner.py:PlannerAgent",
                persona="SENIOR"
            )


@pytest.mark.senior
class TestSeniorErrorHandling:
    """Tests for error handling from senior perspective."""

    def test_ISSUE_011_llm_timeout_handling(self, issue_collector):
        """
        ISSUE-011: LLM timeout should be handled gracefully.

        Senior expectation: Clear timeout error, no hang.
        """
        from jdev_cli.core.llm import LLMClient

        client = LLMClient()

        # Check if timeout is configurable
        if not hasattr(client, 'timeout') and not hasattr(client, '_timeout'):
            issue_collector.add_issue(
                severity="HIGH",
                category="LOGIC",
                title="LLMClient has no timeout configuration",
                description="LLMClient doesn't expose timeout setting",
                reproduction_steps=[
                    "1. Create LLMClient",
                    "2. Check for timeout attribute"
                ],
                expected="client.timeout or client._timeout exists",
                actual="No timeout attribute found",
                component="core/llm.py:LLMClient",
                persona="SENIOR"
            )

    def test_ISSUE_012_network_error_handling(self, issue_collector):
        """
        ISSUE-012: Network errors should have retry logic.

        Senior expectation: Exponential backoff, configurable retries.
        """
        from jdev_cli.core.llm import LLMClient

        client = LLMClient()

        # Check for retry logic
        has_retry = any([
            hasattr(client, 'max_retries'),
            hasattr(client, '_retries'),
            hasattr(client, 'retry_count'),
        ])

        if not has_retry:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="LOGIC",
                title="LLMClient has no retry configuration",
                description="LLMClient doesn't have configurable retry logic",
                reproduction_steps=[
                    "1. Create LLMClient",
                    "2. Check for retry attributes"
                ],
                expected="Retry configuration with exponential backoff",
                actual="No retry configuration found",
                component="core/llm.py:LLMClient",
                persona="SENIOR"
            )

    def test_ISSUE_013_graceful_shutdown(self, test_workspace, issue_collector):
        """
        ISSUE-013: Shell should handle SIGINT gracefully.

        Senior expectation: Clean shutdown, no orphan processes.
        """

        # Start shell in subprocess
        # Note: This is a simplified test - real test would need process management

        # Check for signal handlers in shell code
        shell_path = Path(__file__).parent.parent.parent / "jdev_cli" / "shell_simple.py"

        if shell_path.exists():
            content = shell_path.read_text()

            if "KeyboardInterrupt" not in content and "SIGINT" not in content:
                issue_collector.add_issue(
                    severity="MEDIUM",
                    category="UX",
                    title="Shell may not handle SIGINT gracefully",
                    description="No KeyboardInterrupt or SIGINT handler found in shell code",
                    reproduction_steps=[
                        "1. Start shell",
                        "2. Press Ctrl+C during operation",
                        "3. Check for clean shutdown"
                    ],
                    expected="Graceful shutdown with cleanup",
                    actual="No signal handling code found",
                    component="shell_simple.py",
                    persona="SENIOR"
                )

    def test_ISSUE_014_error_message_localization(self, issue_collector):
        """
        ISSUE-014: Error messages should be consistent language.

        Senior expectation: All English OR all Portuguese, not mixed.
        """
        # Scan for error messages
        src_dir = Path(__file__).parent.parent.parent / "jdev_cli"

        mixed_language_files = []

        portuguese_words = ["erro", "falha", "arquivo", "diretório", "não", "encontrado"]
        english_words = ["error", "failed", "file", "directory", "not", "found"]

        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text()

                has_portuguese = any(word in content.lower() for word in portuguese_words)
                has_english = any(word in content.lower() for word in english_words)

                # Check for Portuguese in error messages specifically
                if has_portuguese and '"erro' in content.lower():
                    mixed_language_files.append(str(py_file.relative_to(src_dir)))

            except Exception:
                continue

        if mixed_language_files:
            issue_collector.add_issue(
                severity="LOW",
                category="UX",
                title="Mixed language in error messages",
                description=f"Found Portuguese in: {mixed_language_files[:5]}",
                reproduction_steps=[
                    "1. Scan source files for error messages",
                    "2. Check for mixed English/Portuguese"
                ],
                expected="Consistent language (all English or all Portuguese)",
                actual=f"Mixed in {len(mixed_language_files)} files",
                component="Various",
                persona="SENIOR"
            )


@pytest.mark.senior
class TestSeniorCLIInterface:
    """Tests for CLI interface from senior perspective."""

    def test_ISSUE_015_cli_help_completeness(self, issue_collector):
        """
        ISSUE-015: CLI help should be comprehensive.

        Senior expectation: All commands documented with examples.
        """
        import subprocess

        result = subprocess.run(
            ["python", "-m", "jdev_cli.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        help_text = result.stdout

        # Check for essential information
        required_sections = [
            "usage",
            "commands",
            "options"
        ]

        missing_sections = []
        for section in required_sections:
            if section.lower() not in help_text.lower():
                missing_sections.append(section)

        if missing_sections:
            issue_collector.add_issue(
                severity="LOW",
                category="UX",
                title="CLI help missing sections",
                description=f"Help text missing: {missing_sections}",
                reproduction_steps=[
                    "1. Run: python -m jdev_cli.cli --help",
                    "2. Check for standard sections"
                ],
                expected="Usage, Commands, Options sections present",
                actual=f"Missing: {missing_sections}",
                component="cli.py",
                persona="SENIOR"
            )

    def test_ISSUE_016_cli_version_format(self, issue_collector):
        """
        ISSUE-016: Version should follow semver.

        Senior expectation: x.y.z format, not "v0.1.0" hardcoded.
        """
        cli_path = Path(__file__).parent.parent.parent / "jdev_cli" / "cli.py"

        if cli_path.exists():
            content = cli_path.read_text()

            import re
            version_matches = re.findall(r'v?\d+\.\d+\.\d+', content)

            if version_matches:
                # Check if version is hardcoded
                if '"v0.1.0"' in content or "'v0.1.0'" in content:
                    issue_collector.add_issue(
                        severity="LOW",
                        category="UX",
                        title="Version is hardcoded in CLI",
                        description="Version should come from pyproject.toml or __version__",
                        reproduction_steps=[
                            "1. Check cli.py for version string",
                            "2. Version is hardcoded"
                        ],
                        expected="Version from package metadata",
                        actual="Hardcoded 'v0.1.0'",
                        component="cli.py",
                        persona="SENIOR"
                    )

    def test_ISSUE_017_exit_codes(self, issue_collector):
        """
        ISSUE-017: CLI should use proper exit codes.

        Senior expectation: 0=success, 1=error, specific codes for specific errors.
        """
        import subprocess

        # Test success case
        result = subprocess.run(
            ["python", "-m", "jdev_cli.cli", "version"],
            capture_output=True,
            cwd=Path(__file__).parent.parent.parent
        )

        if result.returncode != 0:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="UX",
                title="CLI version command returns non-zero exit code",
                description="Version command should return 0 on success",
                reproduction_steps=[
                    "1. Run: python -m jdev_cli.cli version",
                    "2. Check exit code"
                ],
                expected="Exit code 0",
                actual=f"Exit code {result.returncode}",
                component="cli.py",
                persona="SENIOR"
            )

        # Test invalid command
        result = subprocess.run(
            ["python", "-m", "jdev_cli.cli", "nonexistent_command"],
            capture_output=True,
            cwd=Path(__file__).parent.parent.parent
        )

        if result.returncode == 0:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="UX",
                title="CLI returns 0 for invalid command",
                description="Invalid command should return non-zero exit code",
                reproduction_steps=[
                    "1. Run: python -m jdev_cli.cli nonexistent_command",
                    "2. Check exit code"
                ],
                expected="Exit code != 0 (typically 1 or 2)",
                actual="Exit code 0",
                component="cli.py",
                persona="SENIOR"
            )
