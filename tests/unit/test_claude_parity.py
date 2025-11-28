"""Tests for Claude Code Parity Features.

Tests Sprint 1 & 2 implementations:
- Memory System (CLAUDE.md/MEMORY.md)
- AskUserQuestion tool
- Edit replace_all parameter
- NotebookEdit tool
- EnterPlanMode/ExitPlanMode tools
- Task resume capability
"""

import pytest
import tempfile
from pathlib import Path


# =============================================================================
# MEMORY SYSTEM TESTS
# =============================================================================

class TestMemorySystem:
    """Test CLAUDE.md/MEMORY.md memory system."""

    def test_memory_manager_import(self):
        """Test MemoryManager can be imported."""
        from jdev_cli.core.memory import MemoryManager, get_memory_manager
        assert MemoryManager is not None
        assert get_memory_manager is not None

    def test_memory_manager_creation(self):
        """Test MemoryManager can be created."""
        from jdev_cli.core.memory import MemoryManager

        manager = MemoryManager()
        assert manager is not None
        assert not manager.is_loaded

    def test_memory_manager_load_no_file(self):
        """Test loading when no CLAUDE.md exists."""
        from jdev_cli.core.memory import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(project_root=Path(tmpdir))
            result = manager.load()
            # Should return False when no memory files exist
            assert result is False
            assert not manager.has_project_memory

    def test_memory_manager_load_with_file(self):
        """Test loading when JUAN.md exists."""
        from jdev_cli.core.memory import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create JUAN.md (primary) or CLAUDE.md (compatibility)
            memory_file = tmpdir / "JUAN.md"
            memory_file.write_text("""# Project Memory

## Instructions

- Use TypeScript for all new code
- Follow Boris Cherny patterns
- Always write tests

## Preferences

- **code_style**: functional
- **testing**: pytest
""")

            manager = MemoryManager(project_root=tmpdir)
            result = manager.load()

            assert result is True
            assert manager.has_project_memory
            assert len(manager.get_instructions()) >= 3
            assert manager.get_preference("code_style") == "functional"
            assert manager.get_preference("testing") == "pytest"

    def test_memory_context_generation(self):
        """Test context generation for LLM."""
        from jdev_cli.core.memory import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            memory_file = tmpdir / "CLAUDE.md"
            memory_file.write_text("""## Instructions

- Rule 1
- Rule 2
""")

            manager = MemoryManager(project_root=tmpdir)
            manager.load()

            context = manager.get_context()
            assert "Project Memory" in context
            assert "Rule 1" in context

    def test_session_memory(self):
        """Test session memory tracking."""
        from jdev_cli.core.memory import MemoryManager

        manager = MemoryManager()
        manager.add_session_entry("User prefers dark mode")
        manager.add_key_decision("Using TypeScript")
        manager.track_modified_file("src/main.ts")

        assert len(manager.session_memory.entries) == 1
        assert len(manager.session_memory.key_decisions) == 1
        assert "src/main.ts" in manager.session_memory.modified_files


# =============================================================================
# ASK USER QUESTION TESTS
# =============================================================================

class TestAskUserQuestion:
    """Test AskUserQuestion tool."""

    def test_tool_import(self):
        """Test tool can be imported."""
        from jdev_cli.tools.claude_parity_tools import AskUserQuestionTool
        assert AskUserQuestionTool is not None

    def test_tool_creation(self):
        """Test tool creation."""
        from jdev_cli.tools.claude_parity_tools import AskUserQuestionTool

        tool = AskUserQuestionTool()
        assert tool.name == "ask_user_question"
        assert "questions" in tool.parameters

    @pytest.mark.asyncio
    async def test_ask_question(self):
        """Test asking a question."""
        from jdev_cli.tools.claude_parity_tools import AskUserQuestionTool

        tool = AskUserQuestionTool()

        result = await tool._execute_validated(questions=[
            {
                "question": "Which framework to use?",
                "header": "Framework",
                "options": [
                    {"label": "React", "description": "Popular UI library"},
                    {"label": "Vue", "description": "Progressive framework"},
                ],
                "multiSelect": False
            }
        ])

        assert result.success is True
        assert "question_id" in result.data
        assert result.data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_max_questions_limit(self):
        """Test max 4 questions limit."""
        from jdev_cli.tools.claude_parity_tools import AskUserQuestionTool

        tool = AskUserQuestionTool()

        # 5 questions should fail
        questions = [
            {"question": f"Q{i}?", "header": f"H{i}", "options": [
                {"label": "A", "description": "a"},
                {"label": "B", "description": "b"}
            ], "multiSelect": False}
            for i in range(5)
        ]

        result = await tool._execute_validated(questions=questions)
        assert result.success is False
        assert "Maximum 4" in result.error


# =============================================================================
# EDIT REPLACE_ALL TESTS
# =============================================================================

class TestEditReplaceAll:
    """Test EditFileTool replace_all parameter."""

    def test_tool_has_replace_all(self):
        """Test replace_all parameter exists."""
        from jdev_cli.tools.file_ops import EditFileTool

        tool = EditFileTool()
        assert "replace_all" in tool.parameters
        assert tool.parameters["replace_all"]["type"] == "boolean"

    @pytest.mark.asyncio
    async def test_replace_single_occurrence(self):
        """Test default behavior replaces only first occurrence."""
        from jdev_cli.tools.file_ops import EditFileTool

        tool = EditFileTool()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("foo bar foo bar foo")

            result = await tool._execute_validated(
                path=str(test_file),
                edits=[{"search": "foo", "replace": "baz"}],
                create_backup=False,
                replace_all=False,
                preview=False
            )

            assert result.success is True
            content = test_file.read_text()
            assert content == "baz bar foo bar foo"  # Only first replaced

    @pytest.mark.asyncio
    async def test_replace_all_occurrences(self):
        """Test replace_all=True replaces all occurrences."""
        from jdev_cli.tools.file_ops import EditFileTool

        tool = EditFileTool()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("foo bar foo bar foo")

            result = await tool._execute_validated(
                path=str(test_file),
                edits=[{"search": "foo", "replace": "baz"}],
                create_backup=False,
                replace_all=True,
                preview=False
            )

            assert result.success is True
            content = test_file.read_text()
            assert content == "baz bar baz bar baz"  # All replaced
            assert result.metadata["changes"] == 3


# =============================================================================
# PLAN MODE TESTS
# =============================================================================

class TestPlanMode:
    """Test EnterPlanMode/ExitPlanMode tools."""

    def test_tools_import(self):
        """Test tools can be imported."""
        from jdev_cli.tools.plan_mode import (
            EnterPlanModeTool,
            ExitPlanModeTool,
        )
        assert EnterPlanModeTool is not None
        assert ExitPlanModeTool is not None

    @pytest.mark.asyncio
    async def test_enter_plan_mode(self):
        """Test entering plan mode."""
        from jdev_cli.tools.plan_mode import (
            EnterPlanModeTool,
            get_plan_state,
            reset_plan_state,
        )

        reset_plan_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / ".qwen/plans/test_plan.md"

            tool = EnterPlanModeTool()
            result = await tool._execute_validated(
                task_description="Add authentication",
                plan_file=str(plan_file)
            )

            assert result.success is True
            assert result.data["status"] == "plan_mode_active"
            assert get_plan_state().active is True
            assert plan_file.exists()

    @pytest.mark.asyncio
    async def test_exit_plan_mode_without_entry(self):
        """Test exiting plan mode when not active."""
        from jdev_cli.tools.plan_mode import ExitPlanModeTool, reset_plan_state

        reset_plan_state()

        tool = ExitPlanModeTool()
        result = await tool._execute_validated()

        assert result.success is False
        assert "Not currently in plan mode" in result.error

    @pytest.mark.asyncio
    async def test_full_plan_cycle(self):
        """Test full enter -> write -> exit cycle."""
        from jdev_cli.tools.plan_mode import (
            EnterPlanModeTool,
            ExitPlanModeTool,
            reset_plan_state,
        )

        reset_plan_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "plan.md"

            # Enter plan mode
            enter_tool = EnterPlanModeTool()
            result = await enter_tool._execute_validated(
                task_description="Implement dark mode",
                plan_file=str(plan_file)
            )
            assert result.success is True

            # Add substantial content to plan
            content = plan_file.read_text()
            content += "\n\n## Implementation\n\nAdd theme context provider..." * 10
            plan_file.write_text(content)

            # Exit plan mode
            exit_tool = ExitPlanModeTool()
            result = await exit_tool._execute_validated(
                summary="Dark mode implementation plan"
            )

            assert result.success is True
            assert result.data["status"] == "plan_submitted"
            assert result.data["approval_required"] is True


# =============================================================================
# NOTEBOOK EDIT TESTS
# =============================================================================

class TestNotebookEdit:
    """Test NotebookEdit tool."""

    def test_tool_import(self):
        """Test tool can be imported."""
        from jdev_cli.tools.claude_parity_tools import NotebookEditTool
        assert NotebookEditTool is not None

    @pytest.mark.asyncio
    async def test_edit_nonexistent_notebook(self):
        """Test editing nonexistent notebook."""
        from jdev_cli.tools.claude_parity_tools import NotebookEditTool

        tool = NotebookEditTool()
        result = await tool._execute_validated(
            notebook_path="/nonexistent/path.ipynb",
            new_source="print('hello')"
        )

        assert result.success is False
        assert "not found" in result.error.lower()


# =============================================================================
# TASK RESUME TESTS
# =============================================================================

class TestTaskResume:
    """Test Task tool resume capability."""

    def test_tool_has_resume(self):
        """Test resume parameter exists."""
        from jdev_cli.tools.claude_parity_tools import TaskTool

        tool = TaskTool()
        assert "resume" in tool.parameters

    @pytest.mark.asyncio
    async def test_create_and_resume_task(self):
        """Test creating and resuming a task."""
        from jdev_cli.tools.claude_parity_tools import TaskTool

        tool = TaskTool()

        # Create initial task
        result = await tool._execute_validated(
            prompt="Explore the codebase",
            subagent_type="explore",
            description="Initial exploration"
        )

        assert result.success is True
        subagent_id = result.data["subagent_id"]
        assert result.data["can_resume"] is True

        # Resume with new prompt
        result2 = await tool._execute_validated(
            prompt="Now look for test files",
            subagent_type="explore",
            resume=subagent_id
        )

        assert result2.success is True
        # Same subagent should be returned
        assert result2.data["subagent_id"] == subagent_id


# =============================================================================
# INTEGRATION TEST
# =============================================================================

class TestClaudeParityIntegration:
    """Integration tests for all Claude Code parity features."""

    def test_all_tools_registered(self):
        """Test all parity tools are registered in __init__."""
        from jdev_cli.tools import (
            EditFileTool,
            EnterPlanModeTool,
            ExitPlanModeTool,
            AskUserQuestionTool,
            TaskTool,
            NotebookEditTool,
            get_claude_parity_tools,
            get_plan_mode_tools,
        )

        # All should be importable
        assert EditFileTool is not None
        assert EnterPlanModeTool is not None
        assert ExitPlanModeTool is not None
        assert AskUserQuestionTool is not None
        assert TaskTool is not None
        assert NotebookEditTool is not None

        # Helper functions should work
        parity_tools = get_claude_parity_tools()
        assert len(parity_tools) >= 10

        plan_tools = get_plan_mode_tools()
        assert len(plan_tools) >= 4

    def test_memory_manager_from_core(self):
        """Test memory manager accessible from core."""
        from jdev_cli.core import MemoryManager, get_memory_manager

        assert MemoryManager is not None
        manager = get_memory_manager(auto_load=False)
        assert manager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
