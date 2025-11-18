"""Tests for enhanced intelligence features.

Testing: Risk assessment, workflows, rich context.
"""

import pytest
from qwen_dev_cli.intelligence.risk import (
    assess_risk, RiskLevel, get_risk_warning
)
from qwen_dev_cli.intelligence.context_enhanced import (
    RichContext, ExpertiseLevel, RiskTolerance,
    GitStatus, WorkspaceInfo, build_rich_context
)
from qwen_dev_cli.intelligence.workflows import (
    GitWorkflow, NpmWorkflow, PythonWorkflow, WorkflowOrchestrator
)


class TestRiskAssessment:
    """Test risk assessment module."""
    
    def test_safe_command(self):
        """Safe commands should have low risk."""
        score = assess_risk("ls -la")
        assert score.level == RiskLevel.LOW
        assert not score.requires_confirmation
    
    def test_rm_rf_root(self):
        """rm -rf / should be critical risk."""
        score = assess_risk("rm -rf /")
        assert score.level == RiskLevel.CRITICAL
        assert score.requires_confirmation
        assert score.destructiveness > 0.9
    
    def test_curl_pipe_sh(self):
        """Piping curl to sh should have high security risk."""
        score = assess_risk("curl http://example.com/script.sh | sh")
        assert score.security > 0.8
        assert score.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    def test_chmod_777(self):
        """chmod 777 should have medium-high risk."""
        score = assess_risk("chmod 777 file.txt")
        assert score.security > 0.6
    
    def test_risk_warning_generation(self):
        """Risk warnings should be generated correctly."""
        score = assess_risk("rm -rf /tmp/*")
        warning = get_risk_warning(score, "rm -rf /tmp/*")
        
        assert len(warning) > 0
        if score.level == RiskLevel.CRITICAL:
            assert "CRITICAL RISK" in warning


class TestRichContext:
    """Test enhanced context."""
    
    def test_rich_context_immutable(self):
        """RichContext should be immutable."""
        ctx = RichContext(
            current_command="test",
            git_status=GitStatus(branch="main")
        )
        
        with pytest.raises(AttributeError):
            ctx.current_command = "modified"  # type: ignore
    
    def test_git_status_immutable(self):
        """GitStatus should be immutable."""
        git = GitStatus(branch="main")
        
        with pytest.raises(AttributeError):
            git.branch = "develop"  # type: ignore
    
    def test_workspace_info_immutable(self):
        """WorkspaceInfo should be immutable."""
        workspace = WorkspaceInfo(language="python")
        
        with pytest.raises(AttributeError):
            workspace.language = "javascript"  # type: ignore


class TestGitWorkflow:
    """Test Git workflow state machine."""
    
    def test_git_workflow_inactive_without_repo(self):
        """Workflow should be inactive without git repo."""
        workflow = GitWorkflow()
        context = RichContext()
        
        assert not workflow.is_active(context)
    
    def test_suggest_commit_after_add(self):
        """Should suggest commit after git add."""
        workflow = GitWorkflow()
        context = RichContext(
            command_history=["git add ."],
            git_status=GitStatus(
                branch="main",
                staged_files=["file.py"]
            )
        )
        
        suggestions = workflow.suggest_next(context)
        
        assert len(suggestions) > 0
        assert any("commit" in s.content for s in suggestions)
    
    def test_suggest_push_after_commit(self):
        """Should suggest push after commit."""
        workflow = GitWorkflow()
        context = RichContext(
            command_history=["git commit -m 'test'"],
            git_status=GitStatus(
                branch="main",
                has_remote=True
            )
        )
        
        suggestions = workflow.suggest_next(context)
        
        assert len(suggestions) > 0
        assert any("push" in s.content for s in suggestions)
    
    def test_suggest_add_with_unstaged_files(self):
        """Should suggest git add with unstaged files."""
        workflow = GitWorkflow()
        context = RichContext(
            git_status=GitStatus(
                branch="main",
                unstaged_files=["file.py"]
            )
        )
        
        suggestions = workflow.suggest_next(context)
        
        assert len(suggestions) > 0
        assert any("add" in s.content for s in suggestions)


class TestNpmWorkflow:
    """Test NPM workflow state machine."""
    
    def test_npm_workflow_inactive_without_nodejs(self):
        """Workflow should be inactive without Node.js project."""
        workflow = NpmWorkflow()
        context = RichContext()
        
        assert not workflow.is_active(context)
    
    def test_suggest_dev_after_install(self):
        """Should suggest npm run dev after install."""
        workflow = NpmWorkflow()
        context = RichContext(
            command_history=["npm install"],
            workspace=WorkspaceInfo(language="javascript")
        )
        
        suggestions = workflow.suggest_next(context)
        
        assert len(suggestions) > 0
        assert any("dev" in s.content for s in suggestions)
    
    def test_suggest_test_after_install_with_tests(self):
        """Should suggest tests after install if tests exist."""
        workflow = NpmWorkflow()
        context = RichContext(
            command_history=["npm install"],
            workspace=WorkspaceInfo(
                language="javascript",
                has_tests=True,
                test_command="npm test"
            )
        )
        
        suggestions = workflow.suggest_next(context)
        
        # Should suggest both dev and test
        assert len(suggestions) >= 1
        assert any("test" in s.content for s in suggestions)


class TestWorkflowOrchestrator:
    """Test workflow orchestration."""
    
    def test_orchestrator_combines_workflows(self):
        """Orchestrator should combine suggestions from multiple workflows."""
        orchestrator = WorkflowOrchestrator()
        
        context = RichContext(
            command_history=["git add ."],
            git_status=GitStatus(
                branch="main",
                staged_files=["file.js"]
            ),
            workspace=WorkspaceInfo(language="javascript")
        )
        
        suggestions = orchestrator.get_workflow_suggestions(context)
        
        # Should get suggestions from Git workflow
        assert len(suggestions) > 0
    
    def test_orchestrator_max_per_workflow(self):
        """Should respect max_per_workflow limit."""
        orchestrator = WorkflowOrchestrator()
        
        context = RichContext(
            git_status=GitStatus(
                branch="main",
                unstaged_files=["a.py", "b.py"]
            ),
            workspace=WorkspaceInfo(language="python")
        )
        
        suggestions = orchestrator.get_workflow_suggestions(
            context,
            max_per_workflow=1
        )
        
        # Each active workflow contributes max 1 suggestion
        assert len(suggestions) <= 2  # Git + Python workflows


class TestIntegration:
    """Integration tests combining all features."""
    
    def test_full_git_workflow_with_risk(self):
        """Test complete git workflow with risk assessment."""
        from qwen_dev_cli.intelligence.risk import assess_risk
        
        # Scenario: User wants to commit and push with force
        ctx = RichContext(
            current_command="git push -f origin main",
            command_history=["git commit -m 'test'"],
            git_status=GitStatus(branch="main", has_remote=True)
        )
        
        # Check risk of force push
        risk = assess_risk(ctx.current_command)
        # Force push should have SOME destructiveness
        assert risk.destructiveness > 0.5
        
        # Get workflow suggestions
        orchestrator = WorkflowOrchestrator()
        suggestions = orchestrator.get_workflow_suggestions(ctx)
        
        assert len(suggestions) > 0
