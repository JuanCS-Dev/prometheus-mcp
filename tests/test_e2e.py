"""End-to-end integration tests for complete workflows."""

from jdev_cli.shell import InteractiveShell
from jdev_cli.core.cache import get_cache
from jdev_cli.intelligence.engine import get_engine
from jdev_cli.explainer import explain_command
from jdev_cli.intelligence.context_enhanced import build_rich_context
from jdev_cli.core.constitutional_metrics import generate_constitutional_report


class TestE2EIntegration:
    """Test complete end-to-end workflows."""

    def test_shell_initialization(self):
        """Shell should initialize with all components."""
        shell = InteractiveShell()

        assert shell is not None
        assert shell.llm is not None
        assert shell.conversation is not None
        assert shell.recovery_engine is not None

    def test_cache_integration(self):
        """Cache should be accessible globally."""
        cache = get_cache()

        # Test basic operations
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

        # Stats should track
        assert cache.stats.hits > 0 or cache.stats.misses > 0

    def test_suggestion_engine(self):
        """Suggestion engine should provide suggestions."""
        engine = get_engine()
        from jdev_cli.intelligence.patterns import register_builtin_patterns

        register_builtin_patterns(engine)

        context = build_rich_context(
            current_command="git commit -m 'test'",
            command_history=["git add ."]
        )

        result = engine.generate_suggestions(context)
        assert result is not None
        assert result.patterns_evaluated > 0

    def test_explainer_integration(self):
        """Explainer should explain commands."""
        context = build_rich_context(current_command="rm -rf test/")

        explanation = explain_command("rm -rf test/", context)

        assert explanation is not None
        assert explanation.command == "rm -rf test/"
        assert len(explanation.warnings) > 0  # Should warn about rm -rf

    def test_constitutional_metrics(self):
        """Constitutional metrics should be calculable."""
        metrics = generate_constitutional_report(
            codebase_path="jdev_cli",
            completeness=0.95,
            precision=0.98,
            recall=0.92
        )

        assert metrics is not None
        assert metrics.lei >= 0.0
        assert metrics.hri >= 0.0
        assert 0.0 <= metrics.cpi <= 1.0

        # LEI should be < 2.0 (reasonable threshold - includes legitimate pass/NotImplemented)
        assert metrics.lei < 2.0, f"LEI too high: {metrics.lei} (details: {metrics.lei_details})"


class TestFeatureIntegration:
    """Test that features are actually integrated."""

    def test_risk_assessment_import(self):
        """Risk assessment should be importable."""
        from jdev_cli.intelligence.risk import assess_risk, RiskLevel

        risk = assess_risk("rm -rf /")
        assert risk.level == RiskLevel.CRITICAL

    def test_workflows_import(self):
        """Workflows should be importable."""
        from jdev_cli.intelligence.workflows import (
            WorkflowOrchestrator
        )

        orchestrator = WorkflowOrchestrator()
        assert len(orchestrator.workflows) > 0

    def test_async_executor_import(self):
        """Async executor should be importable."""
        from jdev_cli.core.async_executor import AsyncExecutor

        executor = AsyncExecutor()
        assert executor._max_parallel == 5

    def test_file_watcher_import(self):
        """File watcher should be importable."""
        from jdev_cli.core.file_watcher import FileWatcher

        watcher = FileWatcher(".")
        assert watcher.root_path is not None
