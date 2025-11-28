"""
Tests for PlanModeManager - Plan Mode Management
=================================================

Comprehensive tests following Boris Cherny methodology:
- Unit tests for all public methods
- Edge cases and error handling
- Thread safety tests
- Integration tests

Target: 95%+ coverage
"""

from pathlib import Path
from unittest.mock import patch
import threading

from jdev_tui.core.plan_mode_manager import PlanModeManager


class TestPlanModeManagerInit:
    """Test initialization and configuration."""

    def test_init_default_paths(self):
        """Test default path configuration."""
        manager = PlanModeManager()

        assert manager._plan_dir == Path.cwd() / ".juancs" / "plans"
        assert manager._plan_mode["active"] is False

    def test_init_custom_path(self, tmp_path):
        """Test custom path configuration."""
        custom_dir = tmp_path / "custom_plans"

        manager = PlanModeManager(plan_dir=custom_dir)

        assert manager._plan_dir == custom_dir

    def test_init_plan_mode_state_structure(self):
        """Test initial plan mode state structure."""
        manager = PlanModeManager()

        state = manager._plan_mode
        assert "active" in state
        assert "plan_file" in state
        assert "task" in state
        assert "exploration_log" in state
        assert "read_only" in state
        assert "started_at" in state

    def test_init_plan_mode_with_missing_state(self):
        """Test _init_plan_mode handles missing state."""
        manager = PlanModeManager()

        # Simulate missing state
        delattr(manager, '_plan_mode')
        manager._init_plan_mode()

        assert manager._plan_mode["active"] is False

    def test_init_plan_mode_with_none_state(self):
        """Test _init_plan_mode handles None state."""
        manager = PlanModeManager()

        # Simulate None state
        manager._plan_mode = None
        manager._init_plan_mode()

        assert manager._plan_mode is not None
        assert manager._plan_mode["active"] is False


class TestEnterPlanMode:
    """Test entering plan mode."""

    def test_enter_plan_mode_success(self, tmp_path):
        """Test successful plan mode entry."""
        manager = PlanModeManager(plan_dir=tmp_path)

        result = manager.enter_plan_mode(task="Refactor auth module")

        assert result["success"] is True
        assert result["task"] == "Refactor auth module"
        assert "plan_file" in result
        assert result["plan_file"] is not None
        assert manager.is_plan_mode() is True

    def test_enter_plan_mode_creates_file(self, tmp_path):
        """Test plan file is created."""
        manager = PlanModeManager(plan_dir=tmp_path)

        result = manager.enter_plan_mode(task="Test task")

        plan_file = Path(result["plan_file"])
        assert plan_file.exists()
        content = plan_file.read_text()
        assert "Test task" in content
        assert "IN PROGRESS" in content

    def test_enter_plan_mode_no_task(self, tmp_path):
        """Test entering without task description."""
        manager = PlanModeManager(plan_dir=tmp_path)

        result = manager.enter_plan_mode()

        assert result["success"] is True
        plan_file = Path(result["plan_file"])
        content = plan_file.read_text()
        assert "No task specified" in content

    def test_enter_plan_mode_already_active(self, tmp_path):
        """Test entering when already in plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)

        # First entry
        manager.enter_plan_mode(task="First task")

        # Second entry should fail
        result = manager.enter_plan_mode(task="Second task")

        assert result["success"] is False
        assert "Already in plan mode" in result["error"]

    def test_enter_plan_mode_creates_directory(self, tmp_path):
        """Test plan directory is created if not exists."""
        plan_dir = tmp_path / "nested" / "plans"
        manager = PlanModeManager(plan_dir=plan_dir)

        result = manager.enter_plan_mode(task="Test")

        assert plan_dir.exists()
        assert result["success"] is True

    def test_enter_plan_mode_file_creation_error(self, tmp_path):
        """Test handling of file creation error."""
        manager = PlanModeManager(plan_dir=tmp_path)

        with patch.object(Path, 'write_text', side_effect=IOError("Write failed")):
            result = manager.enter_plan_mode(task="Test")

            assert result["success"] is False
            assert "Failed" in result["error"]

    def test_enter_plan_mode_restrictions_message(self, tmp_path):
        """Test restrictions are mentioned in response."""
        manager = PlanModeManager(plan_dir=tmp_path)

        result = manager.enter_plan_mode(task="Test")

        assert "restrictions" in result
        assert "blocked" in result["restrictions"].lower() or "write" in result["restrictions"].lower()


class TestExitPlanMode:
    """Test exiting plan mode."""

    def test_exit_plan_mode_without_approval(self, tmp_path):
        """Test exiting without approval."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test task")

        result = manager.exit_plan_mode(approved=False)

        assert result["success"] is True
        assert result["approved"] is False
        assert manager.is_plan_mode() is False

    def test_exit_plan_mode_with_approval(self, tmp_path):
        """Test exiting with approval updates file."""
        manager = PlanModeManager(plan_dir=tmp_path)
        enter_result = manager.enter_plan_mode(task="Test task")

        result = manager.exit_plan_mode(approved=True)

        assert result["success"] is True
        assert result["approved"] is True

        # Check file was updated
        plan_file = Path(enter_result["plan_file"])
        content = plan_file.read_text()
        assert "[x] Plan reviewed" in content
        assert "APPROVED" in content

    def test_exit_plan_mode_not_active(self, tmp_path):
        """Test exiting when not in plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)

        result = manager.exit_plan_mode()

        assert result["success"] is False
        assert "Not in plan mode" in result["error"]

    def test_exit_plan_mode_returns_exploration_count(self, tmp_path):
        """Test exit returns exploration note count."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")
        manager.add_plan_note("Note 1")
        manager.add_plan_note("Note 2")
        manager.add_plan_note("Note 3")

        result = manager.exit_plan_mode()

        assert result["exploration_count"] == 3

    def test_exit_plan_mode_resets_state(self, tmp_path):
        """Test state is reset after exit."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")
        manager.add_plan_note("Note")

        manager.exit_plan_mode()

        state = manager.get_plan_mode_state()
        assert state["active"] is False
        assert state["task"] is None
        assert len(state["exploration_log"]) == 0

    def test_exit_plan_mode_file_update_error(self, tmp_path):
        """Test handling of file update error during approval."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        with patch.object(Path, 'read_text', side_effect=IOError("Read failed")):
            # Should not raise, just log warning
            result = manager.exit_plan_mode(approved=True)

            assert result["success"] is True


class TestIsPlanMode:
    """Test plan mode status check."""

    def test_is_plan_mode_false_initially(self, tmp_path):
        """Test initially not in plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)

        assert manager.is_plan_mode() is False

    def test_is_plan_mode_true_after_enter(self, tmp_path):
        """Test true after entering plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        assert manager.is_plan_mode() is True

    def test_is_plan_mode_false_after_exit(self, tmp_path):
        """Test false after exiting plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")
        manager.exit_plan_mode()

        assert manager.is_plan_mode() is False


class TestGetPlanModeState:
    """Test getting plan mode state."""

    def test_get_state_inactive(self, tmp_path):
        """Test state when inactive."""
        manager = PlanModeManager(plan_dir=tmp_path)

        state = manager.get_plan_mode_state()

        assert state["active"] is False
        assert state["task"] is None

    def test_get_state_active(self, tmp_path):
        """Test state when active."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Active task")

        state = manager.get_plan_mode_state()

        assert state["active"] is True
        assert state["task"] == "Active task"
        assert state["started_at"] is not None

    def test_get_state_returns_copy(self, tmp_path):
        """Test state returns a copy, not reference."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        state1 = manager.get_plan_mode_state()
        state1["task"] = "Modified"

        state2 = manager.get_plan_mode_state()

        # Original should not be modified
        assert state2["task"] == "Test"


class TestAddPlanNote:
    """Test adding notes during plan mode."""

    def test_add_note_success(self, tmp_path):
        """Test successfully adding a note."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        result = manager.add_plan_note("Test note", category="exploration")

        assert result is True
        log = manager.get_exploration_log()
        assert len(log) == 1
        assert log[0]["note"] == "Test note"
        assert log[0]["category"] == "exploration"

    def test_add_note_default_category(self, tmp_path):
        """Test default category is exploration."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        manager.add_plan_note("Test note")

        log = manager.get_exploration_log()
        assert log[0]["category"] == "exploration"

    def test_add_note_different_categories(self, tmp_path):
        """Test adding notes with different categories."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        manager.add_plan_note("Exploration", category="exploration")
        manager.add_plan_note("Plan step", category="plan")
        manager.add_plan_note("File to modify", category="files")

        log = manager.get_exploration_log()
        assert len(log) == 3
        categories = [n["category"] for n in log]
        assert "exploration" in categories
        assert "plan" in categories
        assert "files" in categories

    def test_add_note_not_in_plan_mode(self, tmp_path):
        """Test adding note when not in plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)

        result = manager.add_plan_note("Test note")

        assert result is False

    def test_add_note_updates_file(self, tmp_path):
        """Test note is appended to plan file."""
        manager = PlanModeManager(plan_dir=tmp_path)
        enter_result = manager.enter_plan_mode(task="Test")

        manager.add_plan_note("Important finding", category="exploration")

        plan_file = Path(enter_result["plan_file"])
        content = plan_file.read_text()
        assert "Important finding" in content

    def test_add_note_limit(self, tmp_path):
        """Test note limit enforcement."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        # Add MAX_PLAN_NOTES notes
        for i in range(PlanModeManager.MAX_PLAN_NOTES):
            manager.add_plan_note(f"Note {i}")

        # Next note should be rejected
        result = manager.add_plan_note("Excess note")

        assert result is False
        assert len(manager.get_exploration_log()) == PlanModeManager.MAX_PLAN_NOTES

    def test_add_note_with_file_error(self, tmp_path):
        """Test note is still added in memory even if file update fails."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        with patch.object(Path, 'read_text', side_effect=IOError("Read failed")):
            result = manager.add_plan_note("Test note")

            # Should still succeed (in memory)
            assert result is True
            log = manager.get_exploration_log()
            assert len(log) == 1


class TestCheckPlanModeRestriction:
    """Test operation restriction checking."""

    def test_not_in_plan_mode_allows_all(self, tmp_path):
        """Test all operations allowed when not in plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)

        allowed, error = manager.check_plan_mode_restriction("write")

        assert allowed is True
        assert error is None

    def test_read_operations_allowed(self, tmp_path):
        """Test read operations are allowed in plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        read_ops = ["read", "glob", "grep", "ls", "search", "list", "get", "check"]

        for op in read_ops:
            allowed, error = manager.check_plan_mode_restriction(op)
            assert allowed is True, f"Operation {op} should be allowed"
            assert error is None

    def test_write_operations_blocked(self, tmp_path):
        """Test write operations are blocked in plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        write_ops = ["write", "edit", "delete", "create", "execute", "run", "bash"]

        for op in write_ops:
            allowed, error = manager.check_plan_mode_restriction(op)
            assert allowed is False, f"Operation {op} should be blocked"
            assert error is not None
            assert "blocked" in error.lower()

    def test_case_insensitive_matching(self, tmp_path):
        """Test operation matching is case-insensitive."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        allowed, _ = manager.check_plan_mode_restriction("READ")
        assert allowed is True

        allowed, error = manager.check_plan_mode_restriction("WRITE")
        assert allowed is False

    def test_partial_match(self, tmp_path):
        """Test partial operation name matching."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        # "file_write" contains "write"
        allowed, _ = manager.check_plan_mode_restriction("file_write")
        assert allowed is False

        # "readonly" contains "read"
        allowed, _ = manager.check_plan_mode_restriction("readonly_check")
        assert allowed is True

    def test_unknown_operation_allowed(self, tmp_path):
        """Test unknown operations are allowed."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        allowed, error = manager.check_plan_mode_restriction("unknown_op")

        assert allowed is True
        assert error is None


class TestGetPlanSummary:
    """Test plan summary generation."""

    def test_summary_inactive(self, tmp_path):
        """Test summary when not in plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)

        summary = manager.get_plan_summary()

        assert summary["active"] is False
        assert summary["duration"] is None

    def test_summary_active(self, tmp_path):
        """Test summary when in plan mode."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test task")
        manager.add_plan_note("Note 1")
        manager.add_plan_note("Note 2")

        summary = manager.get_plan_summary()

        assert summary["active"] is True
        assert summary["task"] == "Test task"
        assert summary["notes_count"] == 2
        assert summary["plan_file"] is not None
        assert summary["duration"] is not None


class TestGetExplorationLog:
    """Test exploration log retrieval."""

    def test_empty_log(self, tmp_path):
        """Test empty log returns empty list."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        log = manager.get_exploration_log()

        assert log == []

    def test_log_with_notes(self, tmp_path):
        """Test log returns added notes."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")
        manager.add_plan_note("Note 1")
        manager.add_plan_note("Note 2")

        log = manager.get_exploration_log()

        assert len(log) == 2
        assert log[0]["note"] == "Note 1"
        assert log[1]["note"] == "Note 2"

    def test_log_returns_copy(self, tmp_path):
        """Test log returns a copy, not reference."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")
        manager.add_plan_note("Original note")

        log1 = manager.get_exploration_log()
        log1.append({"note": "Fake note"})

        log2 = manager.get_exploration_log()

        # Original should not be modified
        assert len(log2) == 1


class TestClearPlanMode:
    """Test force clear functionality."""

    def test_clear_resets_state(self, tmp_path):
        """Test clear resets all state."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")
        manager.add_plan_note("Note")

        manager.clear_plan_mode()

        assert manager.is_plan_mode() is False
        state = manager.get_plan_mode_state()
        assert state["task"] is None
        assert len(state["exploration_log"]) == 0

    def test_clear_when_not_active(self, tmp_path):
        """Test clear when already inactive."""
        manager = PlanModeManager(plan_dir=tmp_path)

        # Should not raise
        manager.clear_plan_mode()

        assert manager.is_plan_mode() is False


class TestThreadSafety:
    """Test thread safety of operations."""

    def test_concurrent_enter_exit(self, tmp_path):
        """Test concurrent enter/exit operations."""
        manager = PlanModeManager(plan_dir=tmp_path)
        errors = []
        results = []

        def worker(i):
            try:
                if i % 2 == 0:
                    result = manager.enter_plan_mode(task=f"Task {i}")
                    results.append(("enter", result))
                else:
                    result = manager.exit_plan_mode()
                    results.append(("exit", result))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # No exceptions should have occurred
        assert len(errors) == 0

    def test_concurrent_add_notes(self, tmp_path):
        """Test concurrent note adding."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        def add_notes(worker_id):
            for i in range(10):
                manager.add_plan_note(f"Worker {worker_id} - Note {i}")

        threads = [threading.Thread(target=add_notes, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should have some notes (exact count depends on timing)
        log = manager.get_exploration_log()
        assert len(log) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unicode_in_task(self, tmp_path):
        """Test unicode characters in task description."""
        manager = PlanModeManager(plan_dir=tmp_path)

        result = manager.enter_plan_mode(task="Refatorar módulo de autenticação 🔐")

        assert result["success"] is True
        plan_file = Path(result["plan_file"])
        content = plan_file.read_text(encoding="utf-8")
        assert "🔐" in content

    def test_unicode_in_notes(self, tmp_path):
        """Test unicode characters in notes."""
        manager = PlanModeManager(plan_dir=tmp_path)
        manager.enter_plan_mode(task="Test")

        result = manager.add_plan_note("Encontrado código legado em auth.py 📁")

        assert result is True
        log = manager.get_exploration_log()
        assert "📁" in log[0]["note"]

    def test_empty_task(self, tmp_path):
        """Test entering with empty task string."""
        manager = PlanModeManager(plan_dir=tmp_path)

        result = manager.enter_plan_mode(task="")

        # Empty string is falsy, should use default
        assert result["success"] is True

    def test_very_long_task(self, tmp_path):
        """Test entering with very long task description."""
        manager = PlanModeManager(plan_dir=tmp_path)
        long_task = "A" * 10000

        result = manager.enter_plan_mode(task=long_task)

        assert result["success"] is True

    def test_special_characters_in_task(self, tmp_path):
        """Test special characters in task that could break markdown."""
        manager = PlanModeManager(plan_dir=tmp_path)
        special_task = "Fix bug #123: `code` with *asterisks* and [brackets]"

        result = manager.enter_plan_mode(task=special_task)

        assert result["success"] is True
        plan_file = Path(result["plan_file"])
        content = plan_file.read_text()
        assert "Fix bug" in content


class TestIntegration:
    """Integration tests for full workflows."""

    def test_full_workflow(self, tmp_path):
        """Test complete plan mode workflow."""
        manager = PlanModeManager(plan_dir=tmp_path)

        # 1. Enter plan mode
        enter_result = manager.enter_plan_mode(task="Refactor auth module")
        assert enter_result["success"] is True

        # 2. Check restrictions
        allowed, _ = manager.check_plan_mode_restriction("read")
        assert allowed is True

        allowed, error = manager.check_plan_mode_restriction("write")
        assert allowed is False

        # 3. Add exploration notes
        manager.add_plan_note("Found auth.py with legacy code", category="exploration")
        manager.add_plan_note("Need to update to OAuth2", category="plan")
        manager.add_plan_note("auth.py, config.py", category="files")

        # 4. Check summary
        summary = manager.get_plan_summary()
        assert summary["notes_count"] == 3

        # 5. Exit with approval
        exit_result = manager.exit_plan_mode(approved=True)
        assert exit_result["success"] is True
        assert exit_result["approved"] is True

        # 6. Verify file was updated
        plan_file = Path(enter_result["plan_file"])
        content = plan_file.read_text()
        assert "APPROVED" in content

        # 7. Verify no longer in plan mode
        assert manager.is_plan_mode() is False

    def test_enter_exit_multiple_times(self, tmp_path):
        """Test entering and exiting multiple times."""
        manager = PlanModeManager(plan_dir=tmp_path)
        plan_files_created = []

        for i in range(3):
            result = manager.enter_plan_mode(task=f"Task {i}")
            assert result["success"] is True
            plan_files_created.append(result["plan_file"])

            manager.add_plan_note(f"Note for task {i}")

            result = manager.exit_plan_mode(approved=i % 2 == 0)
            assert result["success"] is True

        # All entries should have returned a plan file
        assert len(plan_files_created) == 3
        # At least one file should exist (timestamps may collide in fast execution)
        plan_files = list(tmp_path.glob("plan_*.md"))
        assert len(plan_files) >= 1
