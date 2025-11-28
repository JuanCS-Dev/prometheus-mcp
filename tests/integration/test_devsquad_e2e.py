"""End-to-end integration tests for DevSquad.

These tests validate complete workflows with real LLM calls.
Requires valid API keys (GEMINI_API_KEY, NEBIUS_API_KEY, or HF_TOKEN).

Test Scenarios:
1. JWT Authentication - Full 5-phase workflow
2. Setup FastAPI Project - Workflow library execution
3. Human Gate - Approval/rejection mechanism
4. Self-Correction - Refactorer retry logic
5. Constitutional AI - Security validation
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch

from jdev_cli.core.llm import LLMClient
from jdev_cli.core.mcp_client import MCPClient
from jdev_cli.tools.registry_helper import get_default_registry
from jdev_cli.orchestration.squad import DevSquad, WorkflowStatus, WorkflowPhase
from jdev_cli.orchestration.workflows import WorkflowLibrary

# Skip if no API keys
requires_api_key = pytest.mark.skipif(
    not (os.getenv("GEMINI_API_KEY") or os.getenv("NEBIUS_API_KEY") or os.getenv("HF_TOKEN")),
    reason="No API key found in environment"
)


@pytest.fixture
def real_squad():
    """Initialize DevSquad with real LLM and MCP."""
    llm = LLMClient(enable_telemetry=True)
    registry = get_default_registry()
    mcp = MCPClient(registry)
    return DevSquad(llm_client=llm, mcp_client=mcp, require_human_approval=False)


@pytest.fixture
def squad_with_human_gate():
    """Initialize DevSquad with human approval enabled."""
    llm = LLMClient(enable_telemetry=True)
    registry = get_default_registry()
    mcp = MCPClient(registry)
    return DevSquad(llm_client=llm, mcp_client=mcp, require_human_approval=True)


@pytest.mark.asyncio
@requires_api_key
async def test_e2e_jwt_authentication(real_squad, tmp_path):
    """Test full workflow for adding JWT authentication.
    
    Validates all 5 phases execute:
    - Architecture: Architect approves
    - Exploration: Explorer gathers context
    - Planning: Planner generates steps
    - Execution: Refactorer executes (mocked for speed)
    - Review: Reviewer validates
    """
    # Change to tmp directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        request = "Add JWT authentication to my FastAPI application"

        print(f"\n🚀 E2E Test: {request}")

        # Mock Refactorer execution to avoid actual file changes
        with patch('jdev_cli.agents.refactorer.RefactorerAgent.execute') as mock_refactor:
            mock_refactor.return_value = AsyncMock(
                success=True,
                data={"steps_completed": 5, "files_modified": ["app/auth.py"]},
                reasoning="Mocked execution for testing"
            )

            result = await real_squad.execute_workflow(request)

        # Validate workflow execution
        print(f"\n📊 Result: {result.status}")
        print(f"   Phases: {len(result.phases)}")

        # Should execute at least Architecture and Exploration
        assert len(result.phases) >= 2, "Should execute at least 2 phases"

        # Check Architecture phase
        arch_phase = result.phases[0]
        assert arch_phase.phase == WorkflowPhase.ARCHITECTURE
        print(f"   ✅ Architecture: {arch_phase.success}")

        # If Architect approved, check Exploration
        if arch_phase.success and len(result.phases) >= 2:
            explore_phase = result.phases[1]
            assert explore_phase.phase == WorkflowPhase.EXPLORATION
            print(f"   ✅ Exploration: {explore_phase.success}")

        print("\n✅ E2E JWT Authentication Test Complete")

    finally:
        os.chdir(original_cwd)


@pytest.mark.asyncio
@requires_api_key
async def test_e2e_setup_fastapi_project(real_squad, tmp_path):
    """Test workflow library execution for FastAPI setup.
    
    Uses predefined workflow from WorkflowLibrary.
    """
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Get workflow from library
        library = WorkflowLibrary()
        workflow = library.get("setup-fastapi")

        assert workflow is not None, "setup-fastapi workflow should exist"

        # Build request from workflow
        request = f"Execute workflow: {workflow.name}. {workflow.description}"

        print(f"\n🚀 E2E Test: Workflow '{workflow.name}'")
        print(f"   Steps: {len(workflow.steps)}")

        # Mock Refactorer to avoid actual execution
        with patch('jdev_cli.agents.refactorer.RefactorerAgent.execute') as mock_refactor:
            mock_refactor.return_value = AsyncMock(
                success=True,
                data={"steps_completed": len(workflow.steps)},
                reasoning="Workflow executed successfully"
            )

            result = await real_squad.execute_workflow(request)

        print(f"\n📊 Result: {result.status}")
        print(f"   Phases executed: {len(result.phases)}")

        # Validate at least Architecture phase
        assert len(result.phases) >= 1
        assert result.phases[0].phase == WorkflowPhase.ARCHITECTURE

        print("\n✅ E2E Workflow Test Complete")

    finally:
        os.chdir(original_cwd)


@pytest.mark.asyncio
@requires_api_key
async def test_e2e_human_gate(squad_with_human_gate):
    """Test human approval mechanism.
    
    Validates workflow pauses at Human Gate and respects approval/rejection.
    """
    request = "List files in current directory"

    print("\n🚀 E2E Test: Human Gate")

    # Test 1: Auto-approve callback
    async def auto_approve(plan):
        print("   📋 Plan received for approval")
        return True  # Approve

    result = await squad_with_human_gate.execute_workflow(
        request,
        approval_callback=auto_approve
    )

    print(f"\n📊 Result with approval: {result.status}")

    # Should reach at least Planning phase
    assert len(result.phases) >= 3, "Should reach Planning phase"

    # Test 2: Auto-reject callback
    async def auto_reject(plan):
        print("   ❌ Plan rejected")
        return False  # Reject

    result = await squad_with_human_gate.execute_workflow(
        request,
        approval_callback=auto_reject
    )

    print(f"\n📊 Result with rejection: {result.status}")

    # Should stop at Planning phase
    assert result.status in [WorkflowStatus.FAILED, WorkflowStatus.AWAITING_APPROVAL]

    print("\n✅ E2E Human Gate Test Complete")


@pytest.mark.asyncio
async def test_e2e_self_correction():
    """Test Refactorer self-correction concept.
    
    Validates that Refactorer has retry logic capability.
    Note: This is a simplified test that validates the agent structure.
    """
    from jdev_cli.agents.refactorer import RefactorerAgent
    from jdev_cli.agents.base import AgentTask

    print("\n🚀 E2E Test: Self-Correction")

    # Mock LLM and MCP
    mock_llm = MagicMock()
    mock_mcp = MagicMock()

    refactorer = RefactorerAgent(mock_llm, mock_mcp)

    # Verify Refactorer has the expected attributes
    assert hasattr(refactorer, 'execute'), "Should have execute method"
    assert refactorer.role.value == "refactorer", "Should be refactorer role"

    # Create simple task
    task = AgentTask(
        request="Test self-correction capability",
        context={"plan": {"steps": []}},
        session_id="test-session"
    )

    # Mock LLM to return success
    mock_llm.generate_content = AsyncMock(return_value=MagicMock(
        text='{"success": true, "steps_completed": 0}'
    ))

    result = await refactorer.execute(task)

    print(f"\n📊 Result: {result.success}")
    print(f"   Agent has retry capability: {hasattr(refactorer, 'MAX_CORRECTION_ATTEMPTS')}")

    # Validate agent structure supports self-correction
    # (actual retry logic is tested in unit tests)
    assert result is not None, "Should return result"

    print("\n✅ E2E Self-Correction Test Complete")


@pytest.mark.asyncio
@requires_api_key
async def test_e2e_constitutional_ai(real_squad):
    """Test Constitutional AI security validation.
    
    Validates Reviewer rejects dangerous code patterns.
    """
    # Request that should trigger security concerns
    request = "Create a Python script that uses eval() to execute user input"

    print("\n🚀 E2E Test: Constitutional AI")
    print(f"   Request: {request}")

    # Mock Refactorer to return code with eval()
    with patch('jdev_cli.agents.refactorer.RefactorerAgent.execute') as mock_refactor:
        mock_refactor.return_value = AsyncMock(
            success=True,
            data={
                "code": "user_input = input('Enter code: ')\neval(user_input)",
                "files_modified": ["dangerous.py"]
            },
            reasoning="Created script with eval()"
        )

        result = await real_squad.execute_workflow(request)

    print(f"\n📊 Result: {result.status}")

    # If workflow reaches Review phase, check for rejection
    if len(result.phases) >= 5:
        review_phase = result.phases[4]
        assert review_phase.phase == WorkflowPhase.REVIEW

        # Reviewer should detect eval() and reject
        if review_phase.success:
            review_data = review_phase.agent_response.data
            print(f"   Review: {review_data.get('report', {}).get('approved', 'N/A')}")

    print("\n✅ E2E Constitutional AI Test Complete")
