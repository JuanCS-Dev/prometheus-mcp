"""
Scientific test suite for Undo/Redo and Timeline Replay features
Constitutional compliance: P2 (Validação), P3 (Correção)
"""

import pytest
from jdev_cli.tui.components.preview import UndoRedoStack
from jdev_cli.tui.components.execution_timeline import (
    ExecutionTimeline,
    TimelinePlayback
)


class TestUndoRedoStack:
    """Test undo/redo functionality"""

    def test_push_state(self):
        """Test pushing states to undo stack"""
        stack = UndoRedoStack()

        stack.push("content1", "First change", [0, 1])
        assert len(stack.undo_stack) == 1
        assert stack.current_state.content == "content1"
        assert stack.current_state.description == "First change"

    def test_undo_operation(self):
        """Test undo functionality"""
        stack = UndoRedoStack()

        stack.push("content1", "Change 1")
        stack.push("content2", "Change 2")
        stack.push("content3", "Change 3")

        # Undo once
        state = stack.undo()
        assert state.content == "content2"
        assert len(stack.undo_stack) == 2
        assert len(stack.redo_stack) == 1

    def test_redo_operation(self):
        """Test redo functionality"""
        stack = UndoRedoStack()

        stack.push("content1", "Change 1")
        stack.push("content2", "Change 2")

        # Undo then redo
        stack.undo()
        state = stack.redo()

        assert state.content == "content2"
        assert len(stack.redo_stack) == 0

    def test_redo_cleared_on_new_push(self):
        """Test that redo stack is cleared when new state is pushed"""
        stack = UndoRedoStack()

        stack.push("content1", "Change 1")
        stack.push("content2", "Change 2")
        stack.undo()

        assert stack.can_redo()

        # New push should clear redo stack
        stack.push("content3", "Change 3")
        assert not stack.can_redo()
        assert len(stack.redo_stack) == 0

    def test_max_history_limit(self):
        """Test that history is limited to max_history"""
        stack = UndoRedoStack(max_history=5)

        # Push 10 states
        for i in range(10):
            stack.push(f"content{i}", f"Change {i}")

        # Should only keep last 5
        assert len(stack.undo_stack) == 5
        assert stack.undo_stack[0].content == "content5"

    def test_can_undo_redo(self):
        """Test can_undo and can_redo flags"""
        stack = UndoRedoStack()

        assert not stack.can_undo()
        assert not stack.can_redo()

        stack.push("content1", "Change 1")
        assert stack.can_undo()
        assert not stack.can_redo()

        stack.undo()
        assert not stack.can_undo()
        assert stack.can_redo()

    def test_get_history(self):
        """Test getting full history"""
        stack = UndoRedoStack()

        stack.push("content1", "Change 1")
        stack.push("content2", "Change 2")
        stack.push("content3", "Change 3")

        history = stack.get_history()
        assert len(history) == 3
        assert history[0].content == "content1"
        assert history[2].content == "content3"


class TestTimelinePlayback:
    """Test timeline playback functionality"""

    def test_playback_initialization(self):
        """Test playback initialization"""
        timeline = ExecutionTimeline()
        playback = TimelinePlayback(timeline)

        assert playback.current_step == 0
        assert not playback.is_playing
        assert playback.playback_speed == 1.0

    def test_play_pause(self):
        """Test play/pause controls"""
        timeline = ExecutionTimeline()
        playback = TimelinePlayback(timeline)

        playback.play()
        assert playback.is_playing

        playback.pause()
        assert not playback.is_playing

    def test_rewind(self):
        """Test rewind functionality"""
        timeline = ExecutionTimeline()
        timeline.record_event("step1", "start", {"name": "Step 1"})
        timeline.record_event("step2", "start", {"name": "Step 2"})

        playback = TimelinePlayback(timeline)
        playback.current_step = 1

        playback.rewind()
        assert playback.current_step == 0
        assert not playback.is_playing

    def test_step_navigation(self):
        """Test step forward/backward"""
        timeline = ExecutionTimeline()
        timeline.record_event("step1", "start")
        timeline.record_event("step2", "start")
        timeline.record_event("step3", "start")

        playback = TimelinePlayback(timeline)

        # Step forward
        result = playback.step_forward()
        assert result
        assert playback.current_step == 1

        # Step forward again
        playback.step_forward()
        assert playback.current_step == 2

        # Can't step forward beyond end
        result = playback.step_forward()
        assert not result
        assert playback.current_step == 2

        # Step backward
        result = playback.step_backward()
        assert result
        assert playback.current_step == 1

    def test_jump_to_step(self):
        """Test jumping to specific step"""
        timeline = ExecutionTimeline()
        for i in range(5):
            timeline.record_event(f"step{i}", "start")

        playback = TimelinePlayback(timeline)

        # Valid jump
        result = playback.jump_to(3)
        assert result
        assert playback.current_step == 3

        # Invalid jump
        result = playback.jump_to(10)
        assert not result
        assert playback.current_step == 3  # Should stay at current

    def test_speed_control(self):
        """Test playback speed control"""
        timeline = ExecutionTimeline()
        playback = TimelinePlayback(timeline)

        playback.set_speed(2.0)
        assert playback.playback_speed == 2.0

        playback.set_speed(5.0)
        assert playback.playback_speed == 5.0

        # Speed is clamped
        playback.set_speed(20.0)
        assert playback.playback_speed == 10.0  # Max speed

        playback.set_speed(0.01)
        assert playback.playback_speed == 0.1  # Min speed

    def test_get_progress(self):
        """Test progress calculation"""
        timeline = ExecutionTimeline()
        for i in range(10):
            timeline.record_event(f"step{i}", "start")

        playback = TimelinePlayback(timeline)

        assert playback.get_progress() == 0.0

        playback.current_step = 5
        assert playback.get_progress() == 0.5

        playback.current_step = 9
        assert playback.get_progress() == 0.9

    def test_get_current_event(self):
        """Test getting current event"""
        timeline = ExecutionTimeline()
        timeline.record_event("step1", "start", {"name": "Step 1"})
        timeline.record_event("step2", "start", {"name": "Step 2"})

        playback = TimelinePlayback(timeline)

        event = playback.get_current_event()
        assert event is not None
        assert event.step_id == "step1"

        playback.step_forward()
        event = playback.get_current_event()
        assert event.step_id == "step2"


class TestIntegration:
    """Integration tests for combined features"""

    def test_undo_with_timeline(self):
        """Test undo stack integrated with timeline"""
        stack = UndoRedoStack()
        timeline = ExecutionTimeline()

        # Simulate workflow with undo points
        timeline.record_event("edit1", "start", {"name": "Edit file"})
        stack.push("version1", "Initial edit", [0])
        timeline.record_event("edit1", "end")

        timeline.record_event("edit2", "start", {"name": "Second edit"})
        stack.push("version2", "Additional changes", [1, 2])
        timeline.record_event("edit2", "end")

        # Verify both systems are tracking correctly
        assert len(stack.undo_stack) == 2
        assert len(timeline.events) == 4

        # Undo and verify
        state = stack.undo()
        assert state.content == "version1"

    def test_timeline_replay_edge_cases(self):
        """Test timeline replay with edge cases"""
        timeline = ExecutionTimeline()

        # Empty timeline
        playback = TimelinePlayback(timeline)
        assert playback.get_current_event() is None
        assert playback.get_progress() == 0.0

        # Single event
        timeline.record_event("single", "start")
        playback2 = TimelinePlayback(timeline)
        assert playback2.get_current_event() is not None

    def test_performance_undo_operations(self):
        """Test performance of undo operations with many states"""
        import time

        stack = UndoRedoStack(max_history=1000)

        # Push 1000 states
        start = time.time()
        for i in range(1000):
            stack.push(f"content{i}", f"Change {i}")
        push_time = time.time() - start

        # Undo 100 times
        start = time.time()
        for _ in range(100):
            if stack.can_undo():
                stack.undo()
        undo_time = time.time() - start

        # Should be fast (<100ms total)
        assert push_time < 0.1
        assert undo_time < 0.01

    def test_timeline_playback_performance(self):
        """Test performance of timeline playback"""
        import time

        timeline = ExecutionTimeline()

        # Create large timeline
        start = time.time()
        for i in range(1000):
            timeline.record_event(f"step{i}", "start")
        record_time = time.time() - start

        playback = TimelinePlayback(timeline)

        # Test navigation performance
        start = time.time()
        for _ in range(100):
            playback.step_forward()
        nav_time = time.time() - start

        # Should be very fast (<10ms)
        assert record_time < 0.1
        assert nav_time < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
