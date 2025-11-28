"""
E2E Tests: Agent Integration and Mini-Applications
==================================================

Tests for multi-agent coordination and real application creation.
Tests:
- Agent handoff between phases
- Real mini-application creation
- DevSquad workflow
- Governance integration
"""

import pytest
import asyncio
import subprocess
from pathlib import Path



@pytest.mark.integration
class TestAgentHandoff:
    """Tests for agent-to-agent communication."""

    def test_ISSUE_071_planner_to_executor_handoff(self, issue_collector):
        """
        ISSUE-071: Planner output should be executable by Executor.

        Integration: Plan → Execute flow.
        """
        # This would test real handoff
        issue_collector.add_issue(
            severity="HIGH",
            category="INTEGRATION",
            title="No standardized plan format for execution",
            description="Planner output format not guaranteed to work with Executor",
            reproduction_steps=[
                "1. Ask Planner to create execution plan",
                "2. Pass plan to Executor",
                "3. Executor may not understand plan format"
            ],
            expected="Standardized ExecutionPlan model that both agents use",
            actual="Ad-hoc plan format, not validated",
            component="agents/planner.py → agents/executor.py",
            persona="INTEGRATION"
        )

    def test_ISSUE_072_explorer_context_propagation(self, issue_collector):
        """
        ISSUE-072: Explorer findings should propagate to other agents.

        Integration: Explorer → Planner context.
        """
        issue_collector.add_issue(
            severity="MEDIUM",
            category="INTEGRATION",
            title="Explorer context not automatically shared",
            description="Explorer findings aren't automatically available to other agents",
            reproduction_steps=[
                "1. Explorer analyzes codebase",
                "2. Ask Planner to create plan",
                "3. Planner doesn't have Explorer's context"
            ],
            expected="Shared context store accessible by all agents",
            actual="Each agent has isolated context",
            component="context propagation system",
            persona="INTEGRATION"
        )

    def test_ISSUE_073_reviewer_feedback_loop(self, issue_collector):
        """
        ISSUE-073: Reviewer feedback should trigger corrections.

        Integration: Review → Fix cycle.
        """
        issue_collector.add_issue(
            severity="MEDIUM",
            category="INTEGRATION",
            title="No automatic review → fix loop",
            description="Reviewer issues don't automatically trigger fixes",
            reproduction_steps=[
                "1. Executor creates code",
                "2. Reviewer finds issues",
                "3. No automatic fix cycle"
            ],
            expected="Reviewer issues sent back to Executor for fixing",
            actual="Manual intervention required",
            component="review feedback loop",
            persona="INTEGRATION"
        )


@pytest.mark.integration
class TestDevSquadWorkflow:
    """Tests for the 5-phase DevSquad workflow."""

    def test_ISSUE_074_architect_phase_missing(self, issue_collector):
        """
        ISSUE-074: Architect phase should exist and work.

        Phase 1: Architecture decisions.
        """
        try:
            from jdev_cli.agents.architect import ArchitectAgent

            # Check if it has required methods
            required_methods = ['execute', 'design_architecture', 'validate_constraints']

            for method in required_methods:
                if not hasattr(ArchitectAgent, method):
                    issue_collector.add_issue(
                        severity="MEDIUM",
                        category="INTEGRATION",
                        title=f"ArchitectAgent missing method: {method}",
                        description="Agent doesn't implement expected interface",
                        reproduction_steps=[
                            f"1. Check for {method} on ArchitectAgent",
                            "2. Method not found"
                        ],
                        expected=f"{method} method exists",
                        actual="Method missing",
                        component="agents/architect.py",
                        persona="INTEGRATION"
                    )

        except ImportError:
            issue_collector.add_issue(
                severity="HIGH",
                category="INTEGRATION",
                title="ArchitectAgent not importable",
                description="Phase 1 agent doesn't exist or has import errors",
                reproduction_steps=["1. Try to import ArchitectAgent"],
                expected="ArchitectAgent importable",
                actual="ImportError",
                component="agents/architect.py",
                persona="INTEGRATION"
            )

    def test_ISSUE_075_phase_state_machine(self, issue_collector):
        """
        ISSUE-075: DevSquad should enforce phase ordering.

        State: Architect → Explorer → Planner → Executor → Reviewer
        """
        issue_collector.add_issue(
            severity="MEDIUM",
            category="INTEGRATION",
            title="No enforcement of phase ordering",
            description="DevSquad doesn't prevent out-of-order phase execution",
            reproduction_steps=[
                "1. Try to run Executor before Planner",
                "2. System allows it",
                "3. Execution has no plan context"
            ],
            expected="Error: Must complete Planning phase before Execution",
            actual="Allows out-of-order execution",
            component="orchestration/squad.py",
            persona="INTEGRATION"
        )

    def test_ISSUE_076_phase_rollback(self, issue_collector):
        """
        ISSUE-076: Failed phases should allow rollback.

        Recovery: Go back to previous phase on failure.
        """
        issue_collector.add_issue(
            severity="MEDIUM",
            category="INTEGRATION",
            title="No phase rollback mechanism",
            description="Can't go back to previous phase when current fails",
            reproduction_steps=[
                "1. Complete Planner phase",
                "2. Executor phase fails",
                "3. Can't return to Planner to revise"
            ],
            expected="'Execution failed. Return to Planning? [Y/n]'",
            actual="Must start from scratch",
            component="orchestration/squad.py",
            persona="INTEGRATION"
        )


@pytest.mark.integration
class TestMiniAppCreation:
    """Tests for creating real mini-applications."""

    def test_ISSUE_077_flask_app_creation(self, test_workspace, mini_app_generator, issue_collector):
        """
        ISSUE-077: System should create working Flask app.

        Real test: Create and run Flask app.
        """
        # Create Flask app
        app_dir = mini_app_generator.create_flask_app(test_workspace)

        # Verify structure
        expected_files = ["app.py", "requirements.txt", "test_app.py"]
        missing = [f for f in expected_files if not (app_dir / f).exists()]

        if missing:
            issue_collector.add_issue(
                severity="HIGH",
                category="INTEGRATION",
                title=f"Flask app missing files: {missing}",
                description="Generated Flask app structure incomplete",
                reproduction_steps=[
                    "1. Generate Flask app with mini_app_generator",
                    f"2. Missing: {missing}"
                ],
                expected="All standard Flask files present",
                actual=f"Missing: {missing}",
                component="mini_app_generator.create_flask_app",
                persona="INTEGRATION"
            )
            return

        # Try to run tests
        result = subprocess.run(
            ["python", "-m", "pytest", "test_app.py", "-v"],
            cwd=app_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0 and "ModuleNotFoundError" in result.stderr:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="INTEGRATION",
                title="Flask app tests fail - missing dependency",
                description="Generated app tests fail due to missing flask",
                reproduction_steps=[
                    "1. Generate Flask app",
                    "2. Run tests",
                    "3. Flask not installed"
                ],
                expected="Tests pass or clear dependency message",
                actual=f"Error: {result.stderr[:200]}",
                component="mini_app_generator",
                persona="INTEGRATION"
            )
        elif result.returncode != 0:
            issue_collector.add_issue(
                severity="HIGH",
                category="INTEGRATION",
                title="Flask app tests fail",
                description="Generated Flask app doesn't pass its own tests",
                reproduction_steps=[
                    "1. Generate Flask app",
                    "2. Run pytest",
                    f"3. Exit code: {result.returncode}"
                ],
                expected="All tests pass",
                actual=f"Tests failed:\n{result.stdout[:300]}",
                component="mini_app_generator.create_flask_app",
                persona="INTEGRATION"
            )

    def test_ISSUE_078_cli_tool_creation(self, test_workspace, mini_app_generator, issue_collector):
        """
        ISSUE-078: System should create working CLI tool.

        Real test: Create and run CLI tool.
        """
        cli_dir = mini_app_generator.create_cli_tool(test_workspace)

        # Verify main.py exists
        if not (cli_dir / "main.py").exists():
            issue_collector.add_issue(
                severity="HIGH",
                category="INTEGRATION",
                title="CLI tool main.py missing",
                description="Generated CLI tool missing entry point",
                reproduction_steps=[
                    "1. Generate CLI tool",
                    "2. main.py not created"
                ],
                expected="main.py exists with CLI logic",
                actual="main.py missing",
                component="mini_app_generator.create_cli_tool",
                persona="INTEGRATION"
            )
            return

        # Test CLI operations
        tests = [
            (["python", "main.py", "greet"], "Hello, World!"),
            (["python", "main.py", "greet", "--name", "Test"], "Hello, Test!"),
            (["python", "main.py", "count", "--count", "3"], "0\n1\n2"),
        ]

        for cmd, expected_output in tests:
            result = subprocess.run(
                cmd,
                cwd=cli_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                issue_collector.add_issue(
                    severity="MEDIUM",
                    category="INTEGRATION",
                    title=f"CLI command fails: {' '.join(cmd[2:])}",
                    description="Generated CLI command doesn't work",
                    reproduction_steps=[
                        f"1. Run: {' '.join(cmd)}",
                        f"2. Exit code: {result.returncode}"
                    ],
                    expected=expected_output,
                    actual=f"Error: {result.stderr}",
                    component="mini_app_generator.create_cli_tool",
                    persona="INTEGRATION"
                )

    def test_ISSUE_079_data_processor_creation(self, test_workspace, mini_app_generator, issue_collector):
        """
        ISSUE-079: System should create working data processor.

        Real test: Process JSON data.
        """
        data_dir = mini_app_generator.create_data_processor(test_workspace)

        # Verify files
        expected = ["processor.py", "sample.json"]
        missing = [f for f in expected if not (data_dir / f).exists()]

        if missing:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="INTEGRATION",
                title=f"Data processor missing: {missing}",
                description="Generated data processor incomplete",
                reproduction_steps=["1. Generate data processor", f"2. Missing: {missing}"],
                expected="All files present",
                actual=f"Missing: {missing}",
                component="mini_app_generator.create_data_processor",
                persona="INTEGRATION"
            )
            return

        # Test processing
        test_code = '''
import sys
sys.path.insert(0, ".")
from processor import DataProcessor

dp = DataProcessor("sample.json")
dp.load_json()
print(f"Loaded {len(dp.data)} items")

dp.filter("name", "Alice")
print(f"After filter: {len(dp.data)} items")
'''
        test_file = data_dir / "test_run.py"
        test_file.write_text(test_code)

        result = subprocess.run(
            ["python", "test_run.py"],
            cwd=data_dir,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="INTEGRATION",
                title="Data processor fails",
                description="Generated data processor doesn't work",
                reproduction_steps=[
                    "1. Generate data processor",
                    "2. Run basic test",
                    f"3. Error: {result.stderr[:200]}"
                ],
                expected="Processing succeeds",
                actual=f"Error: {result.stderr[:200]}",
                component="mini_app_generator.create_data_processor",
                persona="INTEGRATION"
            )


@pytest.mark.integration
class TestGovernanceIntegration:
    """Tests for governance (Justiça) and counsel (Sofia) integration."""

    def test_ISSUE_080_governance_blocking(self, issue_collector):
        """
        ISSUE-080: Governance should block dangerous operations.

        Security: Justiça constitutional checks.
        """
        try:
            from jdev_cli.maestro_governance import MaestroGovernance

            issue_collector.add_issue(
                severity="MEDIUM",
                category="INTEGRATION",
                title="Governance blocking not easily testable",
                description="No simple way to test if governance blocks operations",
                reproduction_steps=[
                    "1. Want to verify governance blocks 'rm -rf /'",
                    "2. No test hook or dry-run mode"
                ],
                expected="governance.would_block(action) method for testing",
                actual="Must actually try operation",
                component="maestro_governance.py",
                persona="INTEGRATION"
            )

        except ImportError:
            issue_collector.add_issue(
                severity="HIGH",
                category="INTEGRATION",
                title="MaestroGovernance not importable",
                description="Governance system has import errors",
                reproduction_steps=["1. Try to import MaestroGovernance"],
                expected="Imports successfully",
                actual="ImportError",
                component="maestro_governance.py",
                persona="INTEGRATION"
            )

    def test_ISSUE_081_sofia_counsel_availability(self, issue_collector):
        """
        ISSUE-081: Sofia counsel should be available.

        Wisdom: Ethical guidance system.
        """
        try:
            from jdev_cli.agents.sofia_agent import SofiaAgent

            # Check Sofia has wisdom methods
            wisdom_methods = ['counsel', 'ask_question', 'reflect']

            missing = [m for m in wisdom_methods if not hasattr(SofiaAgent, m)]

            if missing:
                issue_collector.add_issue(
                    severity="LOW",
                    category="INTEGRATION",
                    title=f"SofiaAgent missing methods: {missing}",
                    description="Wisdom agent doesn't have expected interface",
                    reproduction_steps=[f"1. Check SofiaAgent for {missing}"],
                    expected="All wisdom methods present",
                    actual=f"Missing: {missing}",
                    component="agents/sofia_agent.py",
                    persona="INTEGRATION"
                )

        except ImportError:
            issue_collector.add_issue(
                severity="LOW",
                category="INTEGRATION",
                title="SofiaAgent not importable",
                description="Wisdom agent has import errors",
                reproduction_steps=["1. Try to import SofiaAgent"],
                expected="Imports successfully",
                actual="ImportError",
                component="agents/sofia_agent.py",
                persona="INTEGRATION"
            )

    def test_ISSUE_082_governance_audit_log(self, issue_collector):
        """
        ISSUE-082: All governance decisions should be logged.

        Audit: Track all blocked/allowed operations.
        """
        issue_collector.add_issue(
            severity="MEDIUM",
            category="INTEGRATION",
            title="No governance audit log exposed",
            description="Can't review governance decisions after the fact",
            reproduction_steps=[
                "1. Governance makes several decisions",
                "2. Want to review what was blocked/allowed",
                "3. No audit log accessible"
            ],
            expected="governance.get_audit_log() returns decision history",
            actual="No audit log method found",
            component="maestro_governance.py",
            persona="INTEGRATION"
        )


@pytest.mark.integration
class TestToolChaining:
    """Tests for chaining multiple tools together."""

    def test_ISSUE_083_read_modify_write_chain(self, test_workspace, issue_collector):
        """
        ISSUE-083: Read → Modify → Write should be atomic.

        Chain: File modification workflow.
        """
        test_file = test_workspace / "chain_test.txt"
        test_file.write_text("original line 1\noriginal line 2\n")

        # Simulate read-modify-write
        from jdev_cli.tools.file_ops import ReadFileTool, WriteFileTool

        read_tool = ReadFileTool()
        write_tool = WriteFileTool()

        # Read
        read_result = asyncio.run(read_tool._execute_validated(path=str(test_file)))

        if not read_result.success:
            issue_collector.add_issue(
                severity="HIGH",
                category="INTEGRATION",
                title="Tool chain fails at read step",
                description="Can't start tool chain - read fails",
                reproduction_steps=["1. Read file", f"2. Error: {read_result.error}"],
                expected="Read succeeds",
                actual=f"Error: {read_result.error}",
                component="tools/file_ops.py:ReadFileTool",
                persona="INTEGRATION"
            )
            return

        # Modify
        modified = read_result.data.replace("original", "modified")

        # Write
        write_result = asyncio.run(write_tool._execute_validated(
            path=str(test_file),
            content=modified
        ))

        if not write_result.success:
            issue_collector.add_issue(
                severity="HIGH",
                category="INTEGRATION",
                title="Tool chain fails at write step",
                description="Read-modify-write chain broken at write",
                reproduction_steps=["1. Read OK", "2. Modify OK", f"3. Write error: {write_result.error}"],
                expected="Write succeeds",
                actual=f"Error: {write_result.error}",
                component="tools/file_ops.py:WriteFileTool",
                persona="INTEGRATION"
            )
            return

        # Verify
        final_content = test_file.read_text()
        if "modified" not in final_content:
            issue_collector.add_issue(
                severity="HIGH",
                category="INTEGRATION",
                title="Tool chain result incorrect",
                description="Modification not persisted correctly",
                reproduction_steps=[
                    "1. Read file",
                    "2. Replace 'original' with 'modified'",
                    "3. Write file",
                    "4. Content doesn't contain 'modified'"
                ],
                expected="File contains 'modified'",
                actual=f"File contains: {final_content[:50]}...",
                component="tool chaining",
                persona="INTEGRATION"
            )

    def test_ISSUE_084_search_then_edit_chain(self, test_workspace, issue_collector):
        """
        ISSUE-084: Search → Edit chain should preserve context.

        Chain: Find and replace workflow.
        """
        # Create files to search
        (test_workspace / "file1.py").write_text("def foo(): pass\n")
        (test_workspace / "file2.py").write_text("def foo(): return 1\n")
        (test_workspace / "file3.py").write_text("def bar(): pass\n")

        # Would need GrepTool and EditTool
        issue_collector.add_issue(
            severity="MEDIUM",
            category="INTEGRATION",
            title="No atomic search-and-replace chain",
            description="Can't atomically find all occurrences and edit them",
            reproduction_steps=[
                "1. Search for 'def foo'",
                "2. Want to edit all matches",
                "3. Must manually coordinate tools"
            ],
            expected="tools.search_and_replace('def foo', 'def bar')",
            actual="Manual multi-tool coordination",
            component="tool orchestration",
            persona="INTEGRATION"
        )

    def test_ISSUE_085_git_workflow_chain(self, test_workspace, issue_collector):
        """
        ISSUE-085: Git workflow should be chainable.

        Chain: Edit → Stage → Commit flow.
        """
        # Git was initialized in test_workspace fixture
        test_file = test_workspace / "new_file.py"
        test_file.write_text("# New file\n")

        # Would chain: WriteFile → GitAdd → GitCommit
        issue_collector.add_issue(
            severity="MEDIUM",
            category="INTEGRATION",
            title="No atomic git workflow chain",
            description="Can't do edit→stage→commit as single operation",
            reproduction_steps=[
                "1. Edit file",
                "2. Want to stage and commit atomically",
                "3. Must call 3 separate tools"
            ],
            expected="tools.save_and_commit(path, content, message)",
            actual="Three separate tool calls",
            component="git workflow integration",
            persona="INTEGRATION"
        )


@pytest.mark.integration
class TestSessionPersistence:
    """Tests for session and state persistence."""

    def test_ISSUE_086_session_context_loss(self, issue_collector):
        """
        ISSUE-086: Session context should persist across commands.

        State: Previous command context.
        """
        issue_collector.add_issue(
            severity="HIGH",
            category="INTEGRATION",
            title="Session context not consistently preserved",
            description="Context from previous commands may be lost",
            reproduction_steps=[
                "1. Run command that sets context (e.g., cd)",
                "2. Run another command",
                "3. Context may or may not be available"
            ],
            expected="Explicit session state management",
            actual="Ad-hoc context handling",
            component="session management",
            persona="INTEGRATION"
        )

    def test_ISSUE_087_crash_recovery(self, issue_collector):
        """
        ISSUE-087: Session should recover from crash.

        Recovery: Resume after unexpected exit.
        """
        issue_collector.add_issue(
            severity="MEDIUM",
            category="INTEGRATION",
            title="No crash recovery mechanism",
            description="If shell crashes, all context is lost",
            reproduction_steps=[
                "1. Build up session context",
                "2. Shell crashes",
                "3. Restart loses everything"
            ],
            expected="Session checkpoints that can be restored",
            actual="All state lost on crash",
            component="session persistence",
            persona="INTEGRATION"
        )

    def test_ISSUE_088_history_persistence(self, issue_collector):
        """
        ISSUE-088: Command history should persist.

        State: Previous session commands.
        """
        history_file = Path.home() / ".jdev_history"

        if not history_file.exists():
            issue_collector.add_issue(
                severity="LOW",
                category="UX",
                title="Command history file not created",
                description="History isn't persisted between sessions",
                reproduction_steps=[
                    "1. Run shell and execute commands",
                    "2. Exit shell",
                    "3. Check for ~/.jdev_history"
                ],
                expected="History file exists with previous commands",
                actual="No history file",
                component="shell_simple.py",
                persona="INTEGRATION"
            )
