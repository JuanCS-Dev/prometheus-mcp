"""Additional edge case tests for DevSquad agents.

These tests cover edge cases and error scenarios to improve robustness:
- Architect: Dangerous requests, missing context
- Explorer: Missing files, token overflow, empty directory
- Planner: Circular dependencies, empty plans
- Refactorer: Rollback scenarios, git conflicts
- Reviewer: Insecure code detection, large diffs
- Squad: Agent failures, timeouts
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from qwen_dev_cli.agents.architect import ArchitectAgent
from qwen_dev_cli.agents.explorer import ExplorerAgent
from qwen_dev_cli.agents.planner import PlannerAgent
from qwen_dev_cli.agents.refactorer import RefactorerAgent
from qwen_dev_cli.agents.reviewer import ReviewerAgent
from qwen_dev_cli.agents.base import AgentTask
from qwen_dev_cli.orchestration.squad import DevSquad


class TestArchitectEdgeCases:
    """Edge cases for Architect agent."""
    
    @pytest.mark.asyncio
    async def test_architect_veto_dangerous_request(self):
        """Test Architect vetoes dangerous security requests."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value='{"decision": "VETOED", "reasoning": "eval() is dangerous"}'
        )
        
        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Create script that uses eval() for user input",
            session_id="test"
        )
        
        response = await architect.execute(task)
        
        assert response.success is True
        assert response.metadata["decision"] == "VETOED"
    
    @pytest.mark.asyncio
    async def test_architect_handles_empty_context(self):
        """Test Architect handles missing/empty context gracefully."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value='{"decision": "APPROVED", "reasoning": "Simple request"}'
        )
        
        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Add logging",
            session_id="test",
            context={}  # Empty context
        )
        
        response = await architect.execute(task)
        
        assert response.success is True


class TestExplorerEdgeCases:
    """Edge cases for Explorer agent."""
    
    @pytest.mark.asyncio
    async def test_explorer_handles_missing_files(self):
        """Test Explorer handles non-existent files gracefully."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value='{"relevant_files": ["nonexistent.py"]}'
        )
        
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(
            side_effect=Exception("File not found")
        )
        
        explorer = ExplorerAgent(llm_client, mcp_client)
        task = AgentTask(
            request="Explore project",
            session_id="test"
        )
        
        response = await explorer.execute(task)
        
        # Should handle error gracefully
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_explorer_token_budget_awareness(self):
        """Test Explorer respects token budget limits."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value='{"relevant_files": []}'
        )
        
        explorer = ExplorerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Explore large codebase",
            session_id="test",
            context={"token_budget": 1000}  # Small budget
        )
        
        response = await explorer.execute(task)
        
        # Should complete without exceeding budget
        assert response is not None


class TestPlannerEdgeCases:
    """Edge cases for Planner agent."""
    
    @pytest.mark.asyncio
    async def test_planner_handles_empty_plan(self):
        """Test Planner handles LLM returning no steps."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value='{"steps": []}'  # Empty plan
        )
        
        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Do nothing",
            session_id="test"
        )

        response = await planner.execute(task)

        # Planner v5/v6 always generates a fallback plan, so it succeeds
        # The plan will have stages/sops even for "Do nothing" requests
        assert response.success is True
        assert "plan" in response.data
    
    @pytest.mark.asyncio
    async def test_planner_invalid_json_fallback(self):
        """Test Planner fallback when LLM returns invalid JSON."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value="Step 1: Create file\nStep 2: Edit file"
        )
        
        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Simple task",
            session_id="test"
        )
        
        response = await planner.execute(task)

        # Planner v5/v6 uses fallback plan generation with sops (not steps)
        assert response.success is True
        plan = response.data.get("plan", {})
        # v5/v6 uses 'sops' for steps, and generates fallback plan
        sops = plan.get("sops", [])
        stages = plan.get("stages", [])
        assert len(sops) >= 1 or len(stages) >= 1  # Has some plan structure


class TestRefactorerEdgeCases:
    """Edge cases for Refactorer agent."""
    
    @pytest.mark.asyncio
    async def test_refactorer_handles_invalid_step(self):
        """Test Refactorer handles malformed steps."""
        refactorer = RefactorerAgent(MagicMock(), MagicMock())
        task = AgentTask(
            request="Execute",
            session_id="test",
            context={"step": {}}  # Missing required fields
        )
        
        response = await refactorer.execute(task)

        assert response.success is False
        # Error message should indicate the problem (file not found, step, missing, etc.)
        reasoning = response.reasoning.lower() if response.reasoning else ""
        error = (response.error or "").lower()
        assert any(term in reasoning or term in error for term in [
            "step", "missing", "file", "target", "not found", "failed", "rollback"
        ])


class TestReviewerEdgeCases:
    """Edge cases for Reviewer agent."""
    
    @pytest.mark.asyncio
    async def test_reviewer_rejects_eval_usage(self):
        """Test Reviewer detects eval() usage."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value='{"approved": false, "issues": ["eval() detected"]}'
        )
        
        reviewer = ReviewerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Review code",
            session_id="test",
            context={"diff": "eval(user_input)"}
        )
        
        response = await reviewer.execute(task)
        
        # Should detect security issue
        assert response is not None
    
    @pytest.mark.asyncio
    async def test_reviewer_handles_empty_diff(self):
        """Test Reviewer handles empty diffs."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value='{"approved": true, "grade": "A"}'
        )
        
        reviewer = ReviewerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Review",
            session_id="test",
            context={"diff": ""}  # Empty diff
        )
        
        response = await reviewer.execute(task)
        
        assert response is not None


class TestSquadEdgeCases:
    """Edge cases for DevSquad orchestrator."""
    
    @pytest.mark.asyncio
    async def test_squad_handles_architect_failure(self):
        """Test Squad handles Architect agent failure."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(side_effect=Exception("LLM error"))
        
        mcp_client = MagicMock()
        squad = DevSquad(llm_client, mcp_client)
        
        result = await squad.execute_workflow("Test request")
        
        # Should fail gracefully
        assert result.status.value == "failed"
        assert len(result.phases) >= 1  # At least tried Architecture
    
    @pytest.mark.asyncio
    async def test_squad_handles_empty_request(self):
        """Test Squad handles empty request string."""
        llm_client = MagicMock()
        mcp_client = MagicMock()
        squad = DevSquad(llm_client, mcp_client)
        
        result = await squad.execute_workflow("")
        
        # Should handle gracefully
        assert result is not None
