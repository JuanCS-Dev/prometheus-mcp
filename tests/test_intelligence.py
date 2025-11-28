"""Tests for intelligence layer.

Boris Cherny: Tests are documentation. They show how the code should be used.
"""

import pytest
from jdev_cli.intelligence.types import (
    Suggestion,
    SuggestionType,
    SuggestionConfidence,
    Context,
    SuggestionPattern,
    SuggestionResult
)
from jdev_cli.intelligence.engine import SuggestionEngine
from jdev_cli.intelligence.patterns import register_builtin_patterns


class TestTypes:
    """Test type definitions."""

    def test_suggestion_immutable(self):
        """Suggestions should be immutable."""
        suggestion = Suggestion(
            type=SuggestionType.NEXT_STEP,
            content="git push",
            confidence=SuggestionConfidence.HIGH,
            reasoning="After commit"
        )

        # Should not be able to modify
        with pytest.raises(AttributeError):
            suggestion.content = "modified"  # type: ignore

    def test_context_immutable(self):
        """Context should be immutable."""
        context = Context(current_command="git commit")

        with pytest.raises(AttributeError):
            context.current_command = "modified"  # type: ignore

    def test_context_with_command(self):
        """Context.with_command should return new instance."""
        ctx1 = Context(command_history=["ls"])
        ctx2 = ctx1.with_command("pwd")

        assert ctx1.current_command is None
        assert ctx2.current_command == "pwd"
        assert ctx2.command_history == ["ls"]  # Preserved

    def test_suggestion_str(self):
        """Suggestion should have readable string representation."""
        suggestion = Suggestion(
            type=SuggestionType.NEXT_STEP,
            content="test",
            confidence=SuggestionConfidence.HIGH,
            reasoning="reason"
        )

        assert "🎯" in str(suggestion)
        assert "test" in str(suggestion)

    def test_suggestion_result_best(self):
        """SuggestionResult should return highest confidence suggestion."""
        suggestions = [
            Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="low",
                confidence=SuggestionConfidence.LOW,
                reasoning="r"
            ),
            Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="high",
                confidence=SuggestionConfidence.HIGH,
                reasoning="r"
            ),
            Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="medium",
                confidence=SuggestionConfidence.MEDIUM,
                reasoning="r"
            ),
        ]

        result = SuggestionResult(
            suggestions=suggestions,
            context=Context(),
            generation_time_ms=1.0,
            patterns_evaluated=3
        )

        assert result.best_suggestion.content == "high"


class TestEngine:
    """Test suggestion engine."""

    def test_engine_initialization(self):
        """Engine should initialize empty."""
        engine = SuggestionEngine()

        assert engine.pattern_count == 0
        assert engine.enabled_pattern_count == 0

    def test_register_pattern(self):
        """Should register patterns in priority order."""
        engine = SuggestionEngine()

        def dummy_fn(ctx):
            return None

        p1 = SuggestionPattern("p1", "test", dummy_fn, priority=50)
        p2 = SuggestionPattern("p2", "test", dummy_fn, priority=100)
        p3 = SuggestionPattern("p3", "test", dummy_fn, priority=75)

        engine.register_pattern(p1)
        engine.register_pattern(p2)
        engine.register_pattern(p3)

        assert engine.pattern_count == 3
        # Should be ordered by priority: p2(100), p3(75), p1(50)

    def test_unregister_pattern(self):
        """Should unregister patterns by name."""
        engine = SuggestionEngine()

        def dummy_fn(ctx):
            return None

        pattern = SuggestionPattern("test", "pattern", dummy_fn)
        engine.register_pattern(pattern)

        assert engine.pattern_count == 1
        assert engine.unregister_pattern("test")
        assert engine.pattern_count == 0
        assert not engine.unregister_pattern("nonexistent")

    def test_generate_suggestions_empty(self):
        """Should return empty result with no patterns."""
        engine = SuggestionEngine()
        context = Context(current_command="test")

        result = engine.generate_suggestions(context)

        assert len(result.suggestions) == 0
        assert result.patterns_evaluated == 0
        assert result.generation_time_ms >= 0

    def test_generate_suggestions_with_pattern(self):
        """Should generate suggestions from matching patterns."""
        engine = SuggestionEngine()

        def suggest_test(ctx):
            if ctx.current_command and "test" in ctx.current_command:
                return Suggestion(
                    type=SuggestionType.NEXT_STEP,
                    content="pytest",
                    confidence=SuggestionConfidence.HIGH,
                    reasoning="Testing"
                )
            return None

        pattern = SuggestionPattern("test_pattern", "test", suggest_test)
        engine.register_pattern(pattern)

        context = Context(current_command="test something")
        result = engine.generate_suggestions(context)

        assert len(result.suggestions) == 1
        assert result.suggestions[0].content == "pytest"

    def test_max_suggestions_limit(self):
        """Should respect max_suggestions limit."""
        engine = SuggestionEngine()

        # Register 5 patterns that all match
        for i in range(5):
            def suggest(ctx):
                return Suggestion(
                    type=SuggestionType.NEXT_STEP,
                    content=f"suggestion_{i}",
                    confidence=SuggestionConfidence.MEDIUM,
                    reasoning="test"
                )

            pattern = SuggestionPattern(f"p{i}", "", suggest)
            engine.register_pattern(pattern)

        context = Context()
        result = engine.generate_suggestions(context, max_suggestions=3)

        assert len(result.suggestions) == 3

    def test_engine_enable_disable(self):
        """Should respect enabled/disabled state."""
        engine = SuggestionEngine()

        def suggest(ctx):
            return Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="test",
                confidence=SuggestionConfidence.HIGH,
                reasoning="r"
            )

        pattern = SuggestionPattern("test", "", suggest)
        engine.register_pattern(pattern)

        # Enabled by default
        result = engine.generate_suggestions(Context())
        assert len(result.suggestions) == 1

        # Disable engine
        engine.disable()
        result = engine.generate_suggestions(Context())
        assert len(result.suggestions) == 0

        # Re-enable
        engine.enable()
        result = engine.generate_suggestions(Context())
        assert len(result.suggestions) == 1

    def test_pattern_exception_handling(self):
        """Should handle pattern exceptions gracefully."""
        engine = SuggestionEngine()

        def bad_pattern(ctx):
            raise ValueError("Intentional error")

        def good_pattern(ctx):
            return Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="works",
                confidence=SuggestionConfidence.HIGH,
                reasoning="r"
            )

        engine.register_pattern(SuggestionPattern("bad", "", bad_pattern))
        engine.register_pattern(SuggestionPattern("good", "", good_pattern))

        # Should not crash, should return good suggestion
        result = engine.generate_suggestions(Context())
        assert len(result.suggestions) == 1
        assert result.suggestions[0].content == "works"


class TestBuiltinPatterns:
    """Test built-in patterns."""

    def test_git_push_after_commit(self):
        """Should suggest git push after commit."""
        engine = SuggestionEngine()
        register_builtin_patterns(engine)

        context = Context(
            command_history=["git commit -m 'test'"],
            git_branch="main"
        )

        result = engine.generate_suggestions(context)

        # Should suggest git push
        assert any("git push" in s.content for s in result.suggestions)

    def test_git_add_before_commit(self):
        """Should suggest git add before commit."""
        engine = SuggestionEngine()
        register_builtin_patterns(engine)

        context = Context(current_command="git commit -m 'test'")

        result = engine.generate_suggestions(context)

        # Should suggest git add
        assert any("git add" in s.content for s in result.suggestions)

    def test_safer_rm_detection(self):
        """Should detect dangerous rm commands."""
        engine = SuggestionEngine()
        register_builtin_patterns(engine)

        context = Context(current_command="rm -rf /tmp/test")

        result = engine.generate_suggestions(context)

        # Should have safety suggestion
        assert any(
            s.type == SuggestionType.ERROR_PREVENTION
            for s in result.suggestions
        )

    def test_test_after_changes(self):
        """Should suggest tests after code changes."""
        engine = SuggestionEngine()
        register_builtin_patterns(engine)

        context = Context(recent_files=["src/main.py", "tests/test_main.py"])

        result = engine.generate_suggestions(context)

        # Should suggest running tests
        assert any("test" in s.content.lower() for s in result.suggestions)


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test complete suggestion workflow."""
        engine = SuggestionEngine()
        register_builtin_patterns(engine)

        # Scenario: User commits code
        context = Context(
            current_command="git commit -m 'Added feature'",
            command_history=["git add .", "git status"],
            git_branch="feature/new-feature",
            recent_files=["src/feature.py"]
        )

        result = engine.generate_suggestions(context)

        assert len(result.suggestions) > 0
        assert result.generation_time_ms > 0
        assert result.patterns_evaluated > 0

        best = result.best_suggestion
        assert best is not None
        assert best.confidence in [
            SuggestionConfidence.HIGH,
            SuggestionConfidence.MEDIUM,
            SuggestionConfidence.LOW
        ]
