"""Consolidated Context Tests - Week 4 Day 1"""
import pytest
from qwen_dev_cli.tui.components.context_awareness import ContextAwarenessEngine, ContentType

class TestConsolidation:
    def test_lru_features(self):
        engine = ContextAwarenessEngine(max_context_tokens=1000)
        engine.add_item("t1", "C", ContentType.FILE_CONTENT, 100)
        assert "t1" in engine.items
        assert engine.window.total_tokens == 100
    
    def test_auto_optimize(self):
        engine = ContextAwarenessEngine(max_context_tokens=1000)
        for i in range(10):
            engine.add_item(f"i{i}", "C", ContentType.FILE_CONTENT, 100)
        metrics = engine.auto_optimize(target_usage=0.5)
        assert metrics.tokens_after < 600
    
    def test_backwards_compat(self):
        engine = ContextAwarenessEngine(max_context_tokens=1000)
        panel = engine.render_token_usage_realtime()
        assert panel is not None
