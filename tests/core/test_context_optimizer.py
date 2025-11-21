"""Tests for Context Optimizer - Boris Cherny Week 4 Day 1 Phase 2"""
import pytest
from qwen_dev_cli.core.context_optimizer import ContextOptimizer, ContentType

class TestContextOptimizer:
    def test_add_and_usage(self):
        opt = ContextOptimizer(max_tokens=1000)
        opt.add_item("t1", "Content", ContentType.FILE_CONTENT, 500)
        assert opt.get_usage_percent() == 50.0
    
    def test_auto_optimize(self):
        opt = ContextOptimizer(max_tokens=1000)
        for i in range(10):
            opt.add_item(f"i{i}", "C", ContentType.FILE_CONTENT, 100)
        metrics = opt.auto_optimize(target_usage=0.5)
        assert metrics.tokens_after < 600
        assert metrics.items_removed > 0
    
    def test_pinned_not_removed(self):
        opt = ContextOptimizer(max_tokens=1000)
        opt.add_item("pin", "P", ContentType.CONVERSATION, 500, pinned=True)
        for i in range(5):
            opt.add_item(f"i{i}", "C", ContentType.FILE_CONTENT, 100)
        opt.auto_optimize(target_usage=0.4)
        assert "pin" in opt.items
