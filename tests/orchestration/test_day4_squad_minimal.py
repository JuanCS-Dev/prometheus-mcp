"""
Minimal test suite for DevSquad orchestrator (Day 4).

Focus: Core functionality validation with real agent integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.base import AgentResponse
from jdev_cli.orchestration.squad import DevSquad, WorkflowStatus


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = MagicMock()
    client.generate_content = AsyncMock(return_value=MagicMock(
        text='{"approved": true, "reasoning": "Feasible"}'
    ))
    return client


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client."""
    client = MagicMock()
    client.call_tool = AsyncMock(return_value={"success": True, "content": ""})
    return client


@pytest.fixture
def dev_squad(mock_llm_client, mock_mcp_client):
    """Create DevSquad instance without approval gate."""
    return DevSquad(
        llm_client=mock_llm_client,
        mcp_client=mock_mcp_client,
        require_human_approval=False
    )


class TestDevSquadCore:
    """Core DevSquad functionality tests."""

    def test_initialization(self, dev_squad):
        """Test squad initializes with all 5 agents."""
        assert dev_squad.architect is not None
        assert dev_squad.explorer is not None
        assert dev_squad.planner is not None
        assert dev_squad.refactorer is not None
        assert dev_squad.reviewer is not None
        assert dev_squad.require_human_approval is False

    @pytest.mark.asyncio
    async def test_workflow_stops_on_architect_veto(self, dev_squad):
        """Test workflow stops if architect vetoes."""
        dev_squad.architect.execute = AsyncMock(return_value=AgentResponse(
            success=True,
            data={"approved": False, "reasoning": "Not feasible"},
            reasoning="Vetoed"
        ))

        result = await dev_squad.execute_workflow("Impossible task")

        assert result.status == WorkflowStatus.FAILED
        assert len(result.phases) == 1

    @pytest.mark.asyncio
    async def test_workflow_complete_success(self, dev_squad):
        """Test complete successful workflow."""
        # Mock all agents to succeed
        dev_squad.architect.execute = AsyncMock(return_value=AgentResponse(
            success=True,
            data={"approved": True, "architecture": {}},
            reasoning="Approved"
        ))

        dev_squad.explorer.execute = AsyncMock(return_value=AgentResponse(
            success=True,
            data={"context": {}, "files": []},
            reasoning="Context gathered"
        ))

        dev_squad.planner.execute = AsyncMock(return_value=AgentResponse(
            success=True,
            data={"plan": {"steps": []}},
            reasoning="Plan created"
        ))

        dev_squad.refactorer.execute = AsyncMock(return_value=AgentResponse(
            success=True,
            data={"modified_files": []},
            reasoning="Changes applied"
        ))

        dev_squad.reviewer.execute = AsyncMock(return_value=AgentResponse(
            success=True,
            data={"report": {"approved": True, "grade": "A+"}},
            reasoning="Review passed"
        ))

        result = await dev_squad.execute_workflow("Add new feature")

        assert result.status == WorkflowStatus.COMPLETED
        assert len(result.phases) == 5
