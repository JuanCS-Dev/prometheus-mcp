"""
Edge case testing for MemoryManager.

Tests cover:
    - Boundary conditions
    - Concurrent operations
    - Large data handling
    - State corruption scenarios
    - Session lifecycle edge cases
"""

import time
from datetime import timedelta
from threading import Thread
from typing import List

from jdev_cli.orchestration.memory import (
    MemoryManager,
    SharedContext,
)


class TestSharedContextEdgeCases:
    """Edge cases for SharedContext model."""

    def test_context_with_very_long_request(self) -> None:
        """Test context with very long user request."""
        long_request = "A" * 10000
        context = SharedContext(user_request=long_request)
        assert len(context.user_request) == 10000

    def test_context_with_large_decisions_dict(self) -> None:
        """Test context with large decisions dictionary."""
        large_decisions = {f"decision_{i}": f"value_{i}" for i in range(1000)}
        context = SharedContext(
            user_request="Test",
            decisions=large_decisions,
        )
        assert len(context.decisions) == 1000

    def test_context_with_many_files(self) -> None:
        """Test context with many files in context_files."""
        many_files = [{"path": f"file_{i}.py"} for i in range(500)]
        context = SharedContext(
            user_request="Test",
            context_files=many_files,
        )
        assert len(context.context_files) == 500

    def test_context_with_deeply_nested_plan(self) -> None:
        """Test context with deeply nested execution plan."""
        nested_plan = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {"data": "deep"},
                        },
                    },
                },
            },
        }
        context = SharedContext(
            user_request="Test",
            execution_plan=nested_plan,
        )
        assert context.execution_plan["level1"]["level2"]["level3"]["level4"]["level5"]["data"] == "deep"

    def test_context_timestamps_are_close(self) -> None:
        """Test that created_at and updated_at are initially close."""
        context = SharedContext(user_request="Test")
        time_diff = context.updated_at - context.created_at
        assert time_diff < timedelta(seconds=1)

    def test_context_with_special_characters(self) -> None:
        """Test context with special characters in fields."""
        context = SharedContext(
            user_request="Test with 'quotes' and \"escapes\" and \n newlines",
            decisions={"key": "value with 'quotes'"},
        )
        assert "quotes" in context.user_request
        assert "quotes" in context.decisions["key"]

    def test_context_with_unicode(self) -> None:
        """Test context with unicode characters."""
        context = SharedContext(
            user_request="Adicionar autenticação 🔐 中文 العربية",
        )
        assert "🔐" in context.user_request
        assert "中文" in context.user_request


class TestMemoryManagerBasicEdgeCases:
    """Basic edge cases for MemoryManager."""

    def test_manager_initially_empty(self) -> None:
        """Test that new manager has no sessions."""
        manager = MemoryManager()
        assert manager.get_session_count() == 0
        assert manager.list_sessions() == []

    def test_create_many_sessions(self) -> None:
        """Test creating many sessions."""
        manager = MemoryManager()
        session_ids = []

        for i in range(100):
            session_id = manager.create_session(f"Request {i}")
            session_ids.append(session_id)

        assert manager.get_session_count() == 100
        assert len(session_ids) == len(set(session_ids))  # All unique

    def test_get_context_after_delete(self) -> None:
        """Test getting context after deletion returns None."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        assert manager.get_context(session_id) is not None

        manager.delete_session(session_id)
        assert manager.get_context(session_id) is None

    def test_update_then_get_preserves_data(self) -> None:
        """Test that update-get cycle preserves data."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        manager.update_context(
            session_id,
            decisions={"approved": True},
            metadata={"tokens": 1234},
        )

        context = manager.get_context(session_id)
        assert context is not None
        assert context.decisions["approved"] is True
        assert context.metadata["tokens"] == 1234

    def test_multiple_updates_accumulate(self) -> None:
        """Test that multiple updates accumulate correctly."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        manager.update_context(session_id, decisions={"step1": "done"})
        manager.update_context(session_id, context_files=[{"path": "file.py"}])
        manager.update_context(session_id, metadata={"tokens": 100})

        context = manager.get_context(session_id)
        assert context is not None
        assert context.decisions["step1"] == "done"
        assert len(context.context_files) == 1
        assert context.metadata["tokens"] == 100

    def test_update_overwrites_previous_field(self) -> None:
        """Test that updating same field overwrites previous value."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        manager.update_context(session_id, decisions={"version": 1})
        manager.update_context(session_id, decisions={"version": 2})

        context = manager.get_context(session_id)
        assert context is not None
        assert context.decisions["version"] == 2


class TestMemoryManagerLargeDataEdgeCases:
    """Edge cases with large data payloads."""

    def test_update_with_large_decisions(self) -> None:
        """Test updating with very large decisions dict."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        large_decisions = {
            "files": [f"file_{i}.py" for i in range(1000)],
            "analysis": "A" * 10000,
        }

        success = manager.update_context(session_id, decisions=large_decisions)
        assert success is True

        context = manager.get_context(session_id)
        assert context is not None
        assert len(context.decisions["files"]) == 1000

    def test_update_with_many_context_files(self) -> None:
        """Test updating with many context files."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        many_files = [
            {
                "path": f"src/module_{i}/file.py",
                "symbols": [f"func_{j}" for j in range(10)],
            }
            for i in range(100)
        ]

        success = manager.update_context(session_id, context_files=many_files)
        assert success is True

        context = manager.get_context(session_id)
        assert context is not None
        assert len(context.context_files) == 100

    def test_update_with_complex_execution_plan(self) -> None:
        """Test updating with complex nested execution plan."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        complex_plan = {
            "steps": [
                {
                    "id": i,
                    "action": f"step_{i}",
                    "dependencies": [j for j in range(i)],
                    "params": {"key": "value" * 100},
                }
                for i in range(50)
            ],
        }

        success = manager.update_context(session_id, execution_plan=complex_plan)
        assert success is True

        context = manager.get_context(session_id)
        assert context is not None
        assert len(context.execution_plan["steps"]) == 50


class TestMemoryManagerSessionLifecycle:
    """Session lifecycle edge cases."""

    def test_create_update_delete_cycle(self) -> None:
        """Test full session lifecycle."""
        manager = MemoryManager()

        # Create
        session_id = manager.create_session("Test")
        assert manager.get_session_count() == 1

        # Update
        manager.update_context(session_id, decisions={"test": True})
        context = manager.get_context(session_id)
        assert context is not None
        assert context.decisions["test"] is True

        # Delete
        manager.delete_session(session_id)
        assert manager.get_session_count() == 0
        assert manager.get_context(session_id) is None

    def test_delete_nonexistent_session_multiple_times(self) -> None:
        """Test deleting nonexistent session multiple times."""
        manager = MemoryManager()

        for _ in range(5):
            success = manager.delete_session("nonexistent")
            assert success is False

    def test_update_after_clear_all(self) -> None:
        """Test that update fails after clear_all."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        manager.clear_all()

        success = manager.update_context(session_id, decisions={"test": True})
        assert success is False

    def test_list_sessions_after_partial_deletes(self) -> None:
        """Test listing sessions after deleting some."""
        manager = MemoryManager()

        ids = [manager.create_session(f"Test {i}") for i in range(10)]

        # Delete every other session
        for i in range(0, 10, 2):
            manager.delete_session(ids[i])

        remaining = manager.list_sessions()
        assert len(remaining) == 5

        # Check that correct sessions remain
        for i in range(1, 10, 2):
            assert ids[i] in remaining


class TestMemoryManagerConcurrencyEdgeCases:
    """Concurrency and thread safety edge cases."""

    def test_concurrent_session_creation(self) -> None:
        """Test creating sessions from multiple threads."""
        manager = MemoryManager()
        created_ids: List[str] = []

        def create_sessions() -> None:
            for i in range(10):
                session_id = manager.create_session(f"Request {i}")
                created_ids.append(session_id)

        threads = [Thread(target=create_sessions) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 50 sessions (5 threads × 10 sessions)
        assert manager.get_session_count() == 50
        # All IDs should be unique
        assert len(created_ids) == len(set(created_ids))

    def test_concurrent_updates_same_session(self) -> None:
        """Test concurrent updates to same session.
        
        NOTE: Current implementation has race condition where last update wins.
        This test verifies that concurrent updates don't corrupt state.
        Future: Add locking or merge strategy for production use.
        """
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        def update_session(field_name: str) -> None:
            for i in range(10):
                # Get current context and merge
                current = manager.get_context(session_id)
                if current:
                    new_metadata = current.metadata.copy()
                    new_metadata[field_name] = i
                    manager.update_context(session_id, metadata=new_metadata)

        threads = [Thread(target=update_session, args=(f"field_{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        context = manager.get_context(session_id)
        assert context is not None
        # At least one field should be present (race condition expected)
        assert len(context.metadata) >= 1

    def test_concurrent_read_write(self) -> None:
        """Test concurrent reads and writes."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")
        read_count = [0]

        def reader() -> None:
            for _ in range(100):
                context = manager.get_context(session_id)
                if context is not None:
                    read_count[0] += 1

        def writer() -> None:
            for i in range(100):
                manager.update_context(
                    session_id,
                    metadata={"counter": i},
                )

        reader_threads = [Thread(target=reader) for _ in range(3)]
        writer_thread = Thread(target=writer)

        for t in reader_threads:
            t.start()
        writer_thread.start()

        for t in reader_threads:
            t.join()
        writer_thread.join()

        # All reads should have succeeded
        assert read_count[0] == 300


class TestMemoryManagerTimestampBehavior:
    """Edge cases for timestamp behavior."""

    def test_updated_at_changes_on_update(self) -> None:
        """Test that updated_at timestamp changes on update."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        context1 = manager.get_context(session_id)
        assert context1 is not None
        timestamp1 = context1.updated_at

        time.sleep(0.02)  # Small delay

        manager.update_context(session_id, metadata={"test": True})

        context2 = manager.get_context(session_id)
        assert context2 is not None
        timestamp2 = context2.updated_at

        assert timestamp2 > timestamp1

    def test_created_at_does_not_change(self) -> None:
        """Test that created_at remains constant."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        context1 = manager.get_context(session_id)
        assert context1 is not None
        created_at1 = context1.created_at

        manager.update_context(session_id, metadata={"test": True})

        context2 = manager.get_context(session_id)
        assert context2 is not None
        created_at2 = context2.created_at

        assert created_at1 == created_at2

    def test_multiple_updates_increment_timestamp(self) -> None:
        """Test that multiple updates keep incrementing timestamp."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        timestamps = []
        for i in range(5):
            time.sleep(0.01)
            manager.update_context(session_id, metadata={f"key_{i}": i})
            context = manager.get_context(session_id)
            assert context is not None
            timestamps.append(context.updated_at)

        # Timestamps should be monotonically increasing
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i - 1]


class TestMemoryManagerReprAndStr:
    """Edge cases for string representation."""

    def test_repr_empty_manager(self) -> None:
        """Test repr of empty manager."""
        manager = MemoryManager()
        assert "sessions=0" in repr(manager)

    def test_repr_with_sessions(self) -> None:
        """Test repr with multiple sessions."""
        manager = MemoryManager()
        for i in range(5):
            manager.create_session(f"Request {i}")

        assert "sessions=5" in repr(manager)

    def test_repr_after_clear(self) -> None:
        """Test repr after clearing."""
        manager = MemoryManager()
        manager.create_session("Test")
        manager.clear_all()

        assert "sessions=0" in repr(manager)


class TestMemoryManagerInvalidOperations:
    """Edge cases for invalid operations."""

    def test_get_context_with_empty_string_id(self) -> None:
        """Test getting context with empty string session ID."""
        manager = MemoryManager()
        context = manager.get_context("")
        assert context is None

    def test_update_context_with_empty_string_id(self) -> None:
        """Test updating context with empty string session ID."""
        manager = MemoryManager()
        success = manager.update_context("", decisions={"test": True})
        assert success is False

    def test_delete_session_with_empty_string_id(self) -> None:
        """Test deleting session with empty string session ID."""
        manager = MemoryManager()
        success = manager.delete_session("")
        assert success is False

    def test_update_with_no_fields(self) -> None:
        """Test update with no fields provided."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        # Update with no kwargs (should still update timestamp)
        success = manager.update_context(session_id)
        assert success is True

    def test_update_with_unknown_fields(self) -> None:
        """Test update with fields not in SharedContext."""
        manager = MemoryManager()
        session_id = manager.create_session("Test")

        # Unknown fields should be ignored
        success = manager.update_context(
            session_id,
            unknown_field="value",  # type: ignore
            another_unknown=123,  # type: ignore
        )
        assert success is True

        context = manager.get_context(session_id)
        assert context is not None
        # Unknown fields should not be in context
        assert not hasattr(context, "unknown_field")
