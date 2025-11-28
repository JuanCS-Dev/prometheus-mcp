"""
Tests for PlannerAgent - The Project Manager.

Validates plan generation, atomic steps, risk assessment.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.planner import PlannerAgent
from jdev_cli.agents.base import AgentTask, AgentCapability, AgentRole


class TestPlannerBasic:
    """Basic functionality tests for Planner."""

    def test_planner_initialization(self) -> None:
        """Test Planner initializes with DESIGN capability."""
        llm_client = MagicMock()
        mcp_client = MagicMock()

        planner = PlannerAgent(llm_client, mcp_client)

        assert planner.role == AgentRole.PLANNER
        assert AgentCapability.DESIGN in planner.capabilities
        assert len(planner.capabilities) == 1  # Only DESIGN

    @pytest.mark.asyncio
    async def test_planner_generates_plan(self) -> None:
        """Test Planner generates valid execution plan."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "plan_name": "Add JWT Auth",
                "total_steps": 3,
                "estimated_duration": "30 minutes",
                "steps": [
                    {
                        "id": 1,
                        "action": "create_directory",
                        "description": "Create auth folder",
                        "params": {"path": "app/auth"},
                        "risk": "LOW",
                        "requires_approval": False,
                        "dependencies": [],
                        "validation": "Directory exists"
                    },
                    {
                        "id": 2,
                        "action": "create_file",
                        "description": "Create JWT handler",
                        "params": {"path": "app/auth/jwt.py", "content": "# JWT"},
                        "risk": "LOW",
                        "requires_approval": False,
                        "dependencies": [1],
                        "validation": "File exists"
                    },
                    {
                        "id": 3,
                        "action": "bash_command",
                        "description": "Run tests",
                        "params": {"command": "pytest"},
                        "risk": "LOW",
                        "requires_approval": False,
                        "dependencies": [2],
                        "validation": "Tests pass"
                    }
                ],
                "checkpoints": [{"after_step": 3, "description": "Auth complete"}],
                "rollback_strategy": "Delete app/auth if tests fail"
            })
        )

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Add JWT authentication", session_id="test")

        response = await planner.execute(task)

        assert response.success is True
        assert "steps" in response.data
        assert len(response.data["steps"]) == 3
        assert response.metadata["total_steps"] == 3

    @pytest.mark.asyncio
    async def test_planner_includes_architecture_context(self) -> None:
        """Test Planner uses Architect's architecture in planning."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "plan_name": "Implement API",
                "total_steps": 2,
                "steps": [
                    {"id": 1, "action": "create_file", "params": {}, "risk": "LOW", "requires_approval": False, "dependencies": []},
                    {"id": 2, "action": "bash_command", "params": {}, "risk": "LOW", "requires_approval": False, "dependencies": [1]}
                ]
            })
        )

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Build REST API",
            session_id="test",
            context={
                "architecture": {
                    "approach": "FastAPI with SQLAlchemy",
                    "risks": ["Database migration needed"],
                    "constraints": ["Must use existing models"]
                }
            }
        )

        response = await planner.execute(task)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_planner_tracks_high_risk_steps(self) -> None:
        """Test Planner counts high-risk operations."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "plan_name": "Dangerous Plan",
                "total_steps": 3,
                "steps": [
                    {"id": 1, "action": "create_file", "params": {}, "risk": "LOW", "requires_approval": False, "dependencies": []},
                    {"id": 2, "action": "delete_file", "params": {}, "risk": "HIGH", "requires_approval": True, "dependencies": []},
                    {"id": 3, "action": "edit_file", "params": {}, "risk": "MEDIUM", "requires_approval": False, "dependencies": []}
                ]
            })
        )

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Refactor", session_id="test")

        response = await planner.execute(task)

        assert response.success is True
        assert response.metadata["high_risk_count"] == 1
        assert response.metadata["requires_approval_count"] == 1

    @pytest.mark.asyncio
    async def test_planner_validates_plan_structure(self) -> None:
        """Test Planner rejects invalid plans."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "steps": [
                    {"id": 1}  # Missing required fields
                ]
            })
        )

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await planner.execute(task)
        assert response.success is False
        assert "valid" in response.reasoning.lower() or "invalid" in response.error.lower()

    @pytest.mark.asyncio
    async def test_planner_handles_llm_failure(self) -> None:
        """Test Planner handles LLM errors gracefully."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(side_effect=Exception("LLM Error"))

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await planner.execute(task)
        assert response.success is False
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_planner_fallback_extraction(self) -> None:
        """Test Planner extracts plan from non-JSON text."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value="Step 1: Create directory app/auth\nStep 2: Create file jwt.py\nStep 3: Run tests"
        )

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Add auth", session_id="test")

        response = await planner.execute(task)

        # Should extract via fallback
        assert response.success is True
        assert len(response.data["steps"]) == 3

    @pytest.mark.asyncio
    async def test_planner_enforces_high_risk_approval(self) -> None:
        """Test Planner auto-marks HIGH risk for approval."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "plan_name": "Test",
                "steps": [
                    {
                        "id": 1,
                        "action": "delete_file",
                        "params": {},
                        "risk": "HIGH",
                        "requires_approval": False,  # Should be corrected to True
                        "dependencies": []
                    }
                ]
            })
        )

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Delete", session_id="test")

        response = await planner.execute(task)

        assert response.success is True
        # Should auto-correct requires_approval to True
        assert response.data["steps"][0]["requires_approval"] is True

    def test_planner_prompt_includes_context(self) -> None:
        """Test Planner builds prompt with context."""
        planner = PlannerAgent(MagicMock(), MagicMock())

        task = AgentTask(
            request="Add feature",
            session_id="test",
            context={
                "architecture": {"approach": "Use FastAPI"},
                "relevant_files": ["app/main.py", "app/routes.py"],
                "constraints": ["Must maintain backward compatibility"]
            }
        )

        prompt = planner._build_planning_prompt(task)

        assert "Add feature" in prompt
        assert "Use FastAPI" in prompt
        assert "app/main.py" in prompt
        assert "backward compatibility" in prompt

    def test_planner_limits_file_list_in_prompt(self) -> None:
        """Test Planner limits file list to first 10."""
        planner = PlannerAgent(MagicMock(), MagicMock())

        files = [f"file{i}.py" for i in range(50)]
        task = AgentTask(
            request="Test",
            session_id="test",
            context={"relevant_files": files}
        )

        prompt = planner._build_planning_prompt(task)

        # Should show first 10 and mention more
        assert "file0.py" in prompt
        assert "file9.py" in prompt
        assert "40 more" in prompt or "and 40" in prompt

    @pytest.mark.asyncio
    async def test_planner_execution_count_increments(self) -> None:
        """Test Planner tracks execution count."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "plan_name": "Test",
                "steps": [{"id": 1, "action": "create_file", "params": {}, "risk": "LOW", "requires_approval": False, "dependencies": []}]
            })
        )

        planner = PlannerAgent(llm_client, MagicMock())

        # Reset execution count to 0 for test
        planner.execution_count = 0
        initial_count = planner.execution_count

        task = AgentTask(request="Test", session_id="test")
        await planner.execute(task)

        assert planner.execution_count == initial_count + 1

    def test_planner_cannot_use_write_tools(self) -> None:
        """Test Planner cannot use write tools (DESIGN only)."""
        planner = PlannerAgent(MagicMock(), MagicMock())

        assert planner._can_use_tool("write_file") is False
        assert planner._can_use_tool("bash_command") is False
        assert planner._can_use_tool("edit_file") is False
