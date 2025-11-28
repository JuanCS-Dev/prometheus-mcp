"""
Tests for Phase 2.3: Multi-Turn Conversation Manager

Tests conversation state machine, context management, and error recovery.
"""

import pytest
import time
from pathlib import Path
import tempfile

from jdev_cli.core.conversation import (
    ConversationManager,
    ConversationState,
    ConversationTurn,
    ContextWindow,
)


class TestContextWindow:
    """Test context window management."""

    def test_token_estimation(self):
        """Test token count estimation."""
        window = ContextWindow(max_tokens=100)

        # Short text
        text = "Hello world"
        tokens = window.estimate_tokens(text)
        assert tokens > 0
        assert tokens < 20  # Should be reasonable

        # Longer text
        long_text = "The quick brown fox jumps over the lazy dog. " * 10
        long_tokens = window.estimate_tokens(long_text)
        assert long_tokens > tokens
        assert long_tokens > 50

    def test_usage_percentage(self):
        """Test usage percentage calculation."""
        window = ContextWindow(max_tokens=1000)
        window.current_tokens = 0
        assert window.get_usage_percentage() == 0.0

        window.current_tokens = 500
        assert window.get_usage_percentage() == 0.5

        window.current_tokens = 1000
        assert window.get_usage_percentage() == 1.0

    def test_compaction_triggers(self):
        """Test compaction trigger thresholds."""
        window = ContextWindow(max_tokens=100, soft_limit=0.6, hard_limit=0.8)

        # Below soft limit
        window.current_tokens = 50
        needs_compact, reason = window.needs_compaction()
        assert not needs_compact
        assert reason == "ok"

        # At soft limit
        window.current_tokens = 60
        needs_compact, reason = window.needs_compaction()
        assert needs_compact
        assert "soft_limit" in reason

        # At hard limit
        window.current_tokens = 80
        needs_compact, reason = window.needs_compaction()
        assert needs_compact
        assert "hard_limit" in reason

    def test_sliding_window_compaction(self):
        """Test sliding window compaction strategy."""
        window = ContextWindow(max_tokens=1000)

        # Create 20 turns
        turns = []
        for i in range(20):
            turn = ConversationTurn(
                turn_id=i,
                timestamp=time.time(),
                state=ConversationState.IDLE,
                user_input=f"Query {i}",
            )
            turns.append(turn)

        # Compact with sliding window
        compacted = window.compact(turns, strategy="sliding_window")

        # Should keep last 10
        assert len(compacted) == 10
        assert compacted[0].turn_id == 10
        assert compacted[-1].turn_id == 19

    def test_aggressive_compaction(self):
        """Test aggressive compaction strategy."""
        window = ContextWindow(max_tokens=1000)

        # Create 20 turns (some with errors)
        turns = []
        for i in range(20):
            turn = ConversationTurn(
                turn_id=i,
                timestamp=time.time(),
                state=ConversationState.IDLE,
                user_input=f"Query {i}",
            )

            # Add errors to some turns
            if i in [5, 10, 15]:
                turn.error = f"Error at turn {i}"
                turn.error_category = "test_error"

            turns.append(turn)

        # Compact aggressively
        compacted = window.compact(turns, strategy="aggressive")

        # Should keep last 2 + up to 3 error turns
        assert len(compacted) <= 5
        assert compacted[-1].turn_id == 19  # Last turn
        assert compacted[-2].turn_id == 18  # Second to last

        # Should include error turn 15
        error_turns = [t for t in compacted if t.error]
        assert len(error_turns) > 0


class TestConversationTurn:
    """Test individual conversation turn."""

    def test_turn_creation(self):
        """Test creating conversation turn."""
        turn = ConversationTurn(
            turn_id=1,
            timestamp=time.time(),
            state=ConversationState.THINKING,
            user_input="Test query",
        )

        assert turn.turn_id == 1
        assert turn.state == ConversationState.THINKING
        assert turn.user_input == "Test query"
        assert turn.llm_response is None
        assert len(turn.tool_calls) == 0

    def test_turn_serialization(self):
        """Test turn to_dict and from_dict."""
        turn = ConversationTurn(
            turn_id=1,
            timestamp=time.time(),
            state=ConversationState.EXECUTING,
            user_input="Test",
            llm_response="Response",
            tool_calls=[{"tool": "read_file", "args": {"path": "test.py"}}],
        )

        # Serialize
        data = turn.to_dict()
        assert data["turn_id"] == 1
        assert data["state"] == "executing"
        assert data["user_input"] == "Test"

        # Deserialize
        restored = ConversationTurn.from_dict(data)
        assert restored.turn_id == turn.turn_id
        assert restored.state == turn.state
        assert restored.user_input == turn.user_input


class TestConversationManager:
    """Test conversation manager."""

    def test_manager_initialization(self):
        """Test creating conversation manager."""
        manager = ConversationManager(
            session_id="test_session",
            max_context_tokens=2000,
        )

        assert manager.session_id == "test_session"
        assert manager.current_state == ConversationState.IDLE
        assert len(manager.turns) == 0
        assert manager.turn_counter == 0

    def test_state_transitions(self):
        """Test state machine transitions."""
        manager = ConversationManager(session_id="test")

        assert manager.current_state == ConversationState.IDLE

        # Start turn
        turn = manager.start_turn("Test query")
        assert manager.current_state == ConversationState.THINKING

        # Add LLM response
        manager.add_llm_response(turn, "Response", tokens_used=10)
        assert manager.current_state == ConversationState.EXECUTING

        # Add tool calls
        manager.add_tool_calls(turn, [{"tool": "read_file", "args": {}}])
        assert manager.current_state == ConversationState.EXECUTING

        # Add successful tool result
        manager.add_tool_result(turn, "read_file", {}, "success", True)
        assert manager.current_state == ConversationState.IDLE

    def test_multi_turn_conversation(self):
        """Test multiple conversation turns."""
        manager = ConversationManager(session_id="test")

        # Turn 1
        turn1 = manager.start_turn("Query 1")
        manager.add_llm_response(turn1, "Response 1")
        manager.transition_state(ConversationState.IDLE, "manual_complete")

        # Turn 2
        turn2 = manager.start_turn("Query 2")
        manager.add_llm_response(turn2, "Response 2")
        manager.transition_state(ConversationState.IDLE, "manual_complete")

        # Turn 3
        turn3 = manager.start_turn("Query 3")
        manager.add_llm_response(turn3, "Response 3")
        manager.transition_state(ConversationState.IDLE, "manual_complete")

        assert len(manager.turns) == 3
        assert manager.turn_counter == 3

    def test_error_tracking(self):
        """Test error tracking and categorization."""
        manager = ConversationManager(session_id="test", enable_auto_recovery=True)

        turn = manager.start_turn("Bad query")
        manager.add_llm_response(turn, "Trying...")
        manager.add_tool_calls(turn, [{"tool": "bad_tool", "args": {}}])

        # Simulate tool error
        manager.add_tool_result(
            turn, "bad_tool", {}, None, False,
            error="File not found: missing.txt"
        )

        # State should be RECOVERING (auto-recovery enabled)
        assert manager.current_state == ConversationState.RECOVERING
        assert turn.error is not None
        assert turn.error_category == "not_found"
        assert turn.recovery_attempted

    def test_error_categorization(self):
        """Test error category detection."""
        manager = ConversationManager(session_id="test")

        assert manager._categorize_error("SyntaxError: invalid syntax") == "syntax"
        assert manager._categorize_error("Permission denied") == "permission"
        assert manager._categorize_error("File not found") == "not_found"
        # "command not found" contains "not found", so categorized as "not_found"
        assert manager._categorize_error("bash: command not found: xyz") == "command_not_found"
        assert manager._categorize_error("Timeout after 30s") == "timeout"
        assert manager._categorize_error("Unknown error") == "unknown"

    def test_context_for_llm(self):
        """Test generating context for LLM."""
        manager = ConversationManager(session_id="test")

        # Add 3 turns
        for i in range(3):
            turn = manager.start_turn(f"Query {i}")
            manager.add_llm_response(turn, f"Response {i}")
            manager.transition_state(ConversationState.IDLE, "complete")

        # Get context
        context = manager.get_context_for_llm(include_last_n=2)

        # Should have 4 messages (2 turns × 2 messages each: user + assistant)
        assert len(context) >= 4
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"

    def test_recovery_context(self):
        """Test generating recovery context."""
        manager = ConversationManager(session_id="test")

        turn = manager.start_turn("Failing query")
        manager.add_llm_response(turn, "Attempting...")
        manager.add_tool_calls(turn, [{"tool": "bad_tool", "args": {}}])
        manager.add_tool_result(turn, "bad_tool", {}, None, False, error="Test error")

        recovery_ctx = manager.get_recovery_context(turn)

        assert recovery_ctx["turn_id"] == turn.turn_id
        assert recovery_ctx["error"] == "Test error"
        assert recovery_ctx["error_category"] == "unknown"
        assert len(recovery_ctx["failed_tool_calls"]) == 1
        assert recovery_ctx["max_attempts"] == 2

    def test_session_persistence(self):
        """Test saving and restoring session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_session.json"

            # Create manager with conversation
            manager = ConversationManager(session_id="persist_test")

            for i in range(3):
                turn = manager.start_turn(f"Query {i}")
                manager.add_llm_response(turn, f"Response {i}", tokens_used=10)
                manager.transition_state(ConversationState.IDLE, "done")

            # Save
            saved_path = manager.save_session(save_path)
            assert saved_path.exists()

            # Restore
            restored = ConversationManager.restore_session(saved_path)

            assert restored.session_id == "persist_test"
            assert len(restored.turns) == 3
            assert restored.turn_counter == 3
            assert restored.context_window.current_tokens == 30  # 3 turns × 10 tokens

    def test_conversation_summary(self):
        """Test conversation summary generation."""
        manager = ConversationManager(session_id="test")

        # Add successful turns
        for i in range(5):
            turn = manager.start_turn(f"Query {i}")
            manager.add_llm_response(turn, f"Response {i}")
            manager.add_tool_calls(turn, [{"tool": "test_tool", "args": {}}])
            manager.add_tool_result(turn, "test_tool", {}, "success", True)

        # Add error turn
        error_turn = manager.start_turn("Bad query")
        manager.add_llm_response(error_turn, "Trying...")
        manager.add_tool_calls(error_turn, [{"tool": "bad_tool", "args": {}}])
        manager.add_tool_result(error_turn, "bad_tool", {}, None, False, error="Error")

        # Get summary
        summary = manager.get_summary()

        assert summary["session_id"] == "test"
        assert summary["total_turns"] == 6
        assert summary["total_tool_calls"] == 6
        assert summary["successful_tools"] == 5
        assert summary["failed_tools"] == 1
        assert summary["error_turns"] == 1

    def test_context_compaction_automatic(self):
        """Test automatic context compaction when limit reached."""
        # Create manager with small context window
        manager = ConversationManager(
            session_id="test",
            max_context_tokens=200,  # Very small for testing
        )

        # Add many turns to trigger compaction
        for i in range(20):
            turn = manager.start_turn(f"This is a longer query number {i} to increase token count")
            manager.add_llm_response(
                turn,
                f"This is a detailed response number {i} with more tokens",
                tokens_used=20
            )
            manager.transition_state(ConversationState.IDLE, "done")

        # Context should have been compacted
        assert len(manager.turns) < 20  # Should be compacted
        assert manager.context_window.get_usage_percentage() < 0.8  # Below hard limit


# Test integration with Phase 2.3 requirements
class TestConstitutionalCompliance:
    """Test compliance with Constitutional requirements."""

    def test_layer2_auto_critique(self):
        """Test Layer 2 (Deliberation): Auto-critique via error tracking."""
        manager = ConversationManager(session_id="test", enable_auto_recovery=True)

        turn = manager.start_turn("Test")
        manager.add_tool_calls(turn, [{"tool": "test", "args": {}}])
        manager.add_tool_result(turn, "test", {}, None, False, error="Test error")

        # Should mark for recovery (auto-critique)
        assert turn.recovery_attempted
        assert manager.current_state == ConversationState.RECOVERING

    def test_layer3_context_compaction(self):
        """Test Layer 3 (State Management): Context compaction."""
        manager = ConversationManager(session_id="test", max_context_tokens=100)

        # Fill context
        for i in range(15):
            turn = manager.start_turn(f"Query {i}")
            manager.add_llm_response(turn, f"Response {i}", tokens_used=10)

        # Should have triggered compaction
        assert len(manager.turns) < 15

    def test_p6_max_recovery_attempts(self):
        """Test P6 (Eficiência de Token): Max 2 recovery attempts."""
        manager = ConversationManager(session_id="test", max_recovery_attempts=2)

        assert manager.max_recovery_attempts == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
