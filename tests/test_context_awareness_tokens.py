"""
Tests for Context Awareness Token Tracking - DAY 8 Phase 4
Real-time token usage and optimization tests
"""

import pytest
from datetime import datetime
from jdev_cli.tui.components.context_awareness import (
    ContextAwarenessEngine,
    TokenUsageSnapshot
)


class TestTokenTracking:
    """Test suite for real-time token tracking"""

    def setup_method(self):
        """Setup test environment"""
        self.engine = ContextAwarenessEngine(max_context_tokens=10000)

    def test_token_snapshot_creation(self):
        """Test: Token snapshots are created correctly"""
        snapshot = TokenUsageSnapshot(
            timestamp=datetime.now(),
            total_tokens=1500,
            input_tokens=1000,
            output_tokens=500,
            cost_estimate_usd=0.0025
        )

        assert snapshot.input_tokens == 1000
        assert snapshot.output_tokens == 500
        assert snapshot.total_tokens == 1500
        assert snapshot.cost_estimate_usd == 0.0025

    def test_add_token_snapshot_to_window(self):
        """Test: Snapshots are added to context window history"""
        # Add snapshot
        self.engine.window.add_token_snapshot(
            input_tokens=1000,
            output_tokens=500,
            cost_estimate=0.002
        )

        # Verify
        assert len(self.engine.window.usage_history) == 1
        assert self.engine.window.current_input_tokens == 1000
        assert self.engine.window.current_output_tokens == 500

        snapshot = self.engine.window.usage_history[0]
        assert snapshot.input_tokens == 1000
        assert snapshot.output_tokens == 500
        assert snapshot.cost_estimate_usd == 0.002

    def test_streaming_token_counter(self):
        """Test: Streaming tokens are tracked in real-time"""
        # Start streaming
        assert self.engine.window.streaming_tokens == 0

        # Update during streaming
        self.engine.update_streaming_tokens(10)
        assert self.engine.window.streaming_tokens == 10

        self.engine.update_streaming_tokens(5)
        assert self.engine.window.streaming_tokens == 15

        # Finalize (resets streaming counter)
        self.engine.finalize_streaming_session(
            final_input_tokens=1000,
            final_output_tokens=15,
            cost_estimate=0.001
        )

        assert self.engine.window.streaming_tokens == 0
        assert self.engine.window.current_output_tokens == 15
        assert len(self.engine.window.usage_history) == 1

    def test_usage_history_limit(self):
        """Test: Usage history is limited to 100 snapshots"""
        # Add 150 snapshots
        for i in range(150):
            self.engine.window.add_token_snapshot(
                input_tokens=100 * i,
                output_tokens=50 * i,
                cost_estimate=0.001 * i
            )

        # Should only keep last 100
        assert len(self.engine.window.usage_history) == 100

        # Verify it's the LAST 100 (most recent)
        first_snapshot = self.engine.window.usage_history[0]
        last_snapshot = self.engine.window.usage_history[-1]

        # First should be snapshot #50 (150 - 100)
        assert first_snapshot.input_tokens == 100 * 50
        # Last should be snapshot #149
        assert last_snapshot.input_tokens == 100 * 149

    def test_context_window_warnings(self):
        """Test: Warning and critical thresholds work correctly"""
        # Fresh window
        assert not self.engine.window.is_warning
        assert not self.engine.window.is_critical

        # Fill to 85% (warning)
        self.engine.window.total_tokens = 8500
        assert self.engine.window.is_warning
        assert not self.engine.window.is_critical
        assert self.engine.window.utilization == pytest.approx(0.85)

        # Fill to 95% (critical)
        self.engine.window.total_tokens = 9500
        assert self.engine.window.is_warning
        assert self.engine.window.is_critical
        assert self.engine.window.utilization == pytest.approx(0.95)

    def test_render_token_usage_realtime(self):
        """Test: Real-time token usage panel renders correctly"""
        # Add some usage data
        self.engine.window.add_token_snapshot(1000, 500, 0.002)
        self.engine.window.add_token_snapshot(1200, 600, 0.0025)
        self.engine.window.streaming_tokens = 50

        # Render
        panel = self.engine.render_token_usage_realtime()

        # Verify panel is created
        assert panel is not None
        assert "Token Usage" in panel.title or "Real-Time" in panel.title

    def test_cost_estimation_accumulation(self):
        """Test: Cost estimates accumulate correctly"""
        # Add multiple sessions
        costs = [0.001, 0.002, 0.0015, 0.003]

        for cost in costs:
            self.engine.window.add_token_snapshot(
                input_tokens=1000,
                output_tokens=500,
                cost_estimate=cost
            )

        # Calculate total cost
        total_cost = sum(s.cost_estimate_usd for s in self.engine.window.usage_history)

        expected_total = sum(costs)
        assert total_cost == pytest.approx(expected_total)

    def test_token_tracking_integration_workflow(self):
        """
        Test: Complete workflow simulation
        Simulates real LLM interaction with token tracking
        """
        # Phase 1: User sends prompt (input tokens)
        input_tokens = 500

        # Phase 2: LLM starts streaming (output tokens)
        self.engine.update_streaming_tokens(10)
        assert self.engine.window.streaming_tokens == 10

        self.engine.update_streaming_tokens(20)
        assert self.engine.window.streaming_tokens == 30

        self.engine.update_streaming_tokens(15)
        assert self.engine.window.streaming_tokens == 45

        # Phase 3: Streaming completes
        final_output_tokens = 45
        cost = 0.0015

        self.engine.finalize_streaming_session(
            final_input_tokens=input_tokens,
            final_output_tokens=final_output_tokens,
            cost_estimate=cost
        )

        # Verify final state
        assert self.engine.window.streaming_tokens == 0
        assert self.engine.window.current_input_tokens == 500
        assert self.engine.window.current_output_tokens == 45
        assert len(self.engine.window.usage_history) == 1

        snapshot = self.engine.window.usage_history[0]
        assert snapshot.total_tokens == 545
        assert snapshot.cost_estimate_usd == 0.0015

        print("\n✅ Token Tracking Workflow:")
        print(f"   Input:  {input_tokens} tokens")
        print(f"   Output: {final_output_tokens} tokens")
        print(f"   Cost:   ${cost:.4f}")
        print(f"   Total:  {snapshot.total_tokens} tokens")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
