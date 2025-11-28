"""Tests for Consolidated Context Manager - Week 4 Day 1"""
from jdev_cli.core.context_manager_consolidated import ConsolidatedContextManager

class TestConsolidatedManager:
    def test_init(self):
        mgr = ConsolidatedContextManager(max_tokens=1000)
        assert mgr.engine is not None

    def test_get_stats(self):
        mgr = ConsolidatedContextManager(max_tokens=1000)
        stats = mgr.get_optimization_stats()
        assert 'total_tokens' in stats
        assert 'usage_percent' in stats

    def test_recommendations(self):
        mgr = ConsolidatedContextManager(max_tokens=1000)
        recs = mgr.get_optimization_recommendations()
        assert isinstance(recs, list)

    def test_rendering_delegate(self):
        mgr = ConsolidatedContextManager(max_tokens=1000)
        panel = mgr.render_token_usage_realtime()
        assert panel is not None
