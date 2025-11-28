"""Tests for explanation engine.

Boris Cherny: Test all public APIs, edge cases, and integrations.
"""

import pytest
from jdev_cli.explainer import (
    ExplanationEngine,
    explain_command,
    Explanation,
    ExplanationLevel
)
from jdev_cli.intelligence.context_enhanced import (
    RichContext,
    ExpertiseLevel
)


class TestExplanationTypes:
    """Test explanation types."""

    def test_explanation_immutable(self):
        """Explanations should be immutable."""
        exp = Explanation(
            command="ls",
            summary="List files"
        )

        with pytest.raises(AttributeError):
            exp.command = "modified"  # type: ignore

    def test_explanation_format(self):
        """Explanations should format correctly."""
        exp = Explanation(
            command="git add .",
            summary="Stage all files",
            warnings=["Warning 1"],
            level=ExplanationLevel.DETAILED
        )

        formatted = exp.format()
        assert "git add ." in formatted
        assert "Stage all files" in formatted
        assert "Warning 1" in formatted


class TestExplanationEngine:
    """Test explanation engine."""

    def test_engine_initialization(self):
        """Engine should initialize with built-in explainers."""
        engine = ExplanationEngine()
        assert engine._explainers  # Should have registered explainers

    def test_generic_explanation(self):
        """Should handle unknown commands."""
        engine = ExplanationEngine()
        exp = engine.explain("unknown-command arg1 arg2")

        assert exp.command == "unknown-command arg1 arg2"
        assert "unknown-command" in exp.summary

    def test_git_explanation(self):
        """Should explain git commands."""
        engine = ExplanationEngine()
        exp = engine.explain("git add file.txt")

        assert "git" in exp.command.lower()
        assert "add" in exp.command
        assert len(exp.summary) > 0

    def test_rm_explanation_with_warnings(self):
        """rm -rf should have warnings."""
        engine = ExplanationEngine()
        exp = engine.explain("rm -rf directory/")

        assert len(exp.warnings) > 0
        assert any("DESTRUCTIVE" in w or "danger" in w.lower() for w in exp.warnings)

    def test_chmod_777_warning(self):
        """chmod 777 should warn about security."""
        engine = ExplanationEngine()
        exp = engine.explain("chmod 777 file.txt")

        assert len(exp.warnings) > 0
        assert any("777" in w for w in exp.warnings)


class TestAdaptiveDetail:
    """Test adaptive detail level."""

    def test_expert_gets_concise(self):
        """Experts should get concise explanations."""
        engine = ExplanationEngine()
        context = RichContext(user_expertise=ExpertiseLevel.EXPERT)

        exp = engine.explain("git add .", context)

        assert exp.level in [ExplanationLevel.CONCISE, ExplanationLevel.BALANCED]

    def test_beginner_gets_detailed(self):
        """Beginners should get detailed explanations."""
        engine = ExplanationEngine()
        context = RichContext(user_expertise=ExpertiseLevel.BEGINNER)

        exp = engine.explain("git add .", context)

        assert exp.level == ExplanationLevel.DETAILED

    def test_risky_command_upgrades_detail(self):
        """Risky commands should get more detail."""
        engine = ExplanationEngine()

        # Expert normally gets concise
        context = RichContext(user_expertise=ExpertiseLevel.EXPERT)
        exp = engine.explain("rm -rf /tmp/*", context)

        # But risky command should upgrade to at least balanced
        assert exp.level in [ExplanationLevel.BALANCED, ExplanationLevel.DETAILED]


class TestSpecificCommands:
    """Test specific command explanations."""

    def test_git_push_force_warning(self):
        """git push -f should warn."""
        engine = ExplanationEngine()
        exp = engine.explain("git push -f origin main")

        assert any("force" in w.lower() for w in exp.warnings)

    def test_git_commit_explanation(self):
        """git commit should be well explained."""
        engine = ExplanationEngine()
        exp = engine.explain("git commit -m 'message'")

        assert ("commit" in exp.summary.lower() or "record" in exp.summary.lower())
        assert len(exp.summary) > 0

    def test_docker_run_explanation(self):
        """docker run should be explained."""
        engine = ExplanationEngine()
        exp = engine.explain("docker run nginx")

        assert "docker" in exp.command.lower()
        assert "container" in exp.summary.lower() or "run" in exp.summary.lower()

    def test_npm_install_explanation(self):
        """npm install should be explained."""
        engine = ExplanationEngine()
        exp = engine.explain("npm install react")

        assert "install" in exp.summary.lower()


class TestConvenienceFunction:
    """Test convenience function."""

    def test_explain_command_function(self):
        """explain_command should work without engine."""
        exp = explain_command("ls -la")

        assert isinstance(exp, Explanation)
        assert exp.command == "ls -la"

    def test_explain_with_context(self):
        """explain_command should accept context."""
        context = RichContext(user_expertise=ExpertiseLevel.BEGINNER)
        exp = explain_command("git status", context)

        assert exp.level == ExplanationLevel.DETAILED


class TestIntegration:
    """Integration tests."""

    def test_full_explanation_workflow(self):
        """Test complete explanation workflow."""
        engine = ExplanationEngine()
        context = RichContext(
            user_expertise=ExpertiseLevel.INTERMEDIATE,
            current_command="git push -f origin main"
        )

        exp = engine.explain(context.current_command, context)

        # Should have all components
        assert exp.command
        assert exp.summary
        # Risky command correctly upgrades detail level
        assert exp.level in [ExplanationLevel.BALANCED, ExplanationLevel.DETAILED]

        # Should warn about force push
        assert len(exp.warnings) > 0

        # Should format correctly
        formatted = exp.format()
        assert len(formatted) > 0
