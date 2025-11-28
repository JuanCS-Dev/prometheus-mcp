"""
Tests for MemoryManager and SharedContext.

Tests cover:
    - Session creation and retrieval
    - Context updates
    - Session cleanup
    - Thread safety (future)
"""

from datetime import datetime

from jdev_cli.orchestration.memory import (
    MemoryManager,
    SharedContext,
)


class TestSharedContext:
    """Test SharedContext Pydantic model."""

    def test_context_creation_minimal(self) -> None:
        """Test context creation with minimal required fields."""
        context = SharedContext(user_request="Add authentication")

        assert context.user_request == "Add authentication"
        assert context.session_id  # Auto-generated UUID
        assert isinstance(context.decisions, dict)
        assert isinstance(context.context_files, list)
        assert isinstance(context.execution_plan, dict)
        assert isinstance(context.execution_results, dict)
        assert isinstance(context.review_feedback, dict)
        assert isinstance(context.metadata, dict)
        assert isinstance(context.created_at, datetime)
        assert isinstance(context.updated_at, datetime)

    def test_context_with_data(self) -> None:
        """Test context creation with full data."""
        context = SharedContext(
            user_request="Migrate to FastAPI",
            decisions={"approved": True, "architecture": "microservices"},
            context_files=[{"path": "app.py", "symbols": ["main", "router"]}],
            metadata={"priority": "high"},
        )

        assert context.decisions["approved"] is True
        assert len(context.context_files) == 1
        assert context.metadata["priority"] == "high"


class TestMemoryManager:
    """Test MemoryManager session management."""

    def test_create_session(self) -> None:
        """Test session creation returns unique ID."""
        manager = MemoryManager()

        session_id = manager.create_session("Test request")

        assert session_id is not None
        assert len(session_id) > 0

    def test_create_multiple_sessions(self) -> None:
        """Test multiple sessions have unique IDs."""
        manager = MemoryManager()

        session_id1 = manager.create_session("Request 1")
        session_id2 = manager.create_session("Request 2")

        assert session_id1 != session_id2
        assert manager.get_session_count() == 2

    def test_get_context_existing_session(self) -> None:
        """Test retrieving context for existing session."""
        manager = MemoryManager()
        session_id = manager.create_session("Test request")

        context = manager.get_context(session_id)

        assert context is not None
        assert context.session_id == session_id
        assert context.user_request == "Test request"

    def test_get_context_nonexistent_session(self) -> None:
        """Test retrieving context for nonexistent session returns None."""
        manager = MemoryManager()

        context = manager.get_context("nonexistent-session-id")

        assert context is None

    def test_update_context_decisions(self) -> None:
        """Test updating decisions field."""
        manager = MemoryManager()
        session_id = manager.create_session("Test request")

        success = manager.update_context(
            session_id,
            decisions={"approved": True, "risks": ["migration downtime"]},
        )

        assert success is True
        context = manager.get_context(session_id)
        assert context is not None
        assert context.decisions["approved"] is True
        assert "migration downtime" in context.decisions["risks"]

    def test_update_context_multiple_fields(self) -> None:
        """Test updating multiple fields at once."""
        manager = MemoryManager()
        session_id = manager.create_session("Test request")

        success = manager.update_context(
            session_id,
            decisions={"approved": True},
            context_files=[{"path": "main.py"}],
            metadata={"tokens": 1234},
        )

        assert success is True
        context = manager.get_context(session_id)
        assert context is not None
        assert context.decisions["approved"] is True
        assert len(context.context_files) == 1
        assert context.metadata["tokens"] == 1234

    def test_update_context_updates_timestamp(self) -> None:
        """Test that update_context updates the updated_at timestamp."""
        manager = MemoryManager()
        session_id = manager.create_session("Test request")

        original_context = manager.get_context(session_id)
        assert original_context is not None
        original_timestamp = original_context.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        manager.update_context(session_id, metadata={"test": "value"})

        updated_context = manager.get_context(session_id)
        assert updated_context is not None
        assert updated_context.updated_at > original_timestamp

    def test_update_context_nonexistent_session(self) -> None:
        """Test updating nonexistent session returns False."""
        manager = MemoryManager()

        success = manager.update_context(
            "nonexistent-session",
            decisions={"approved": False},
        )

        assert success is False

    def test_delete_session_existing(self) -> None:
        """Test deleting existing session."""
        manager = MemoryManager()
        session_id = manager.create_session("Test request")

        success = manager.delete_session(session_id)

        assert success is True
        assert manager.get_context(session_id) is None
        assert manager.get_session_count() == 0

    def test_delete_session_nonexistent(self) -> None:
        """Test deleting nonexistent session returns False."""
        manager = MemoryManager()

        success = manager.delete_session("nonexistent-session")

        assert success is False

    def test_list_sessions(self) -> None:
        """Test listing all active sessions."""
        manager = MemoryManager()

        session_id1 = manager.create_session("Request 1")
        session_id2 = manager.create_session("Request 2")

        sessions = manager.list_sessions()

        assert len(sessions) == 2
        assert session_id1 in sessions
        assert session_id2 in sessions

    def test_get_session_count(self) -> None:
        """Test getting session count."""
        manager = MemoryManager()

        assert manager.get_session_count() == 0

        manager.create_session("Request 1")
        assert manager.get_session_count() == 1

        manager.create_session("Request 2")
        assert manager.get_session_count() == 2

    def test_clear_all(self) -> None:
        """Test clearing all sessions."""
        manager = MemoryManager()

        manager.create_session("Request 1")
        manager.create_session("Request 2")
        assert manager.get_session_count() == 2

        manager.clear_all()

        assert manager.get_session_count() == 0
        assert manager.list_sessions() == []

    def test_manager_repr(self) -> None:
        """Test manager string representation."""
        manager = MemoryManager()
        manager.create_session("Test request")

        repr_str = repr(manager)

        assert "MemoryManager" in repr_str
        assert "sessions=1" in repr_str
