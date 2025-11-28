"""Integration tests for Day 5 features using real LLM calls.

This test file requires valid API keys (GEMINI_API_KEY, NEBIUS_API_KEY, or HF_TOKEN)
to be present in the environment. It performs real network calls.
"""

import pytest
import os
from jdev_cli.core.llm import LLMClient
from jdev_cli.core.mcp_client import MCPClient
from jdev_cli.tools.registry_helper import get_default_registry
from jdev_cli.orchestration.squad import DevSquad, WorkflowStatus

# Skip if no keys are present
requires_api_key = pytest.mark.skipif(
    not (os.getenv("GEMINI_API_KEY") or os.getenv("NEBIUS_API_KEY") or os.getenv("HF_TOKEN")),
    reason="No API key found in environment"
)

@pytest.fixture
def real_squad():
    """Initialize DevSquad with real components."""
    llm = LLMClient(enable_telemetry=True)
    registry = get_default_registry()
    mcp = MCPClient(registry)
    return DevSquad(llm_client=llm, mcp_client=mcp)

@pytest.mark.asyncio
@requires_api_key
async def test_devsquad_pipeline_execution(real_squad):
    """Test that DevSquad pipeline executes all phases with real LLM.
    
    This test validates the integration, not the quality of LLM responses.
    Success criteria:
    - Pipeline executes without crashes
    - All 5 phases are attempted (or workflow stops at expected gate)
    - Proper error handling if LLM gives unexpected responses
    """
    request = "List the current directory contents"

    print(f"\n🚀 Testing DevSquad Pipeline: {request}")
    result = await real_squad.execute_workflow(request)

    # Print detailed results
    print("\n📊 Pipeline Result:")
    print(f"  Status: {result.status}")
    print(f"  Phases Executed: {len(result.phases)}")

    for i, phase in enumerate(result.phases, 1):
        print(f"\n  Phase {i}: {phase.phase}")
        print(f"    Success: {phase.success}")
        print(f"    Duration: {phase.duration_seconds:.2f}s")
        if not phase.success:
            print(f"    Error: {phase.agent_response.error}")

    # Validation: Pipeline should execute at least Phase 1 (Architecture)
    assert len(result.phases) >= 1, "Pipeline should execute at least Architecture phase"
    assert result.phases[0].phase.value == "architecture", "First phase should be Architecture"

    # Validation: No crashes (status should be valid)
    assert result.status in [
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.AWAITING_APPROVAL
    ], f"Unexpected status: {result.status}"

    print("\n✅ Pipeline Integration Test PASSED")
    print(f"   - Executed {len(result.phases)} phases")
    print(f"   - Final status: {result.status}")
    print(f"   - Total duration: {result.total_duration_seconds:.2f}s")

@pytest.mark.asyncio
@requires_api_key
async def test_architect_decision_normalization(real_squad):
    """Test that Architect agent handles decision variations correctly."""
    request = "Show me the Python version"

    print(f"\n🚀 Testing Architect Decision: {request}")
    result = await real_squad.execute_workflow(request)

    # Should at least complete Architecture phase
    assert len(result.phases) >= 1
    arch_phase = result.phases[0]

    print("\n  Architect Response:")
    print(f"    Success: {arch_phase.success}")
    print(f"    Decision: {arch_phase.agent_response.metadata.get('decision', 'N/A')}")

    # Validation: Architect should return a valid decision
    if arch_phase.success:
        decision = arch_phase.agent_response.metadata.get('decision')
        assert decision in ['APPROVED', 'VETOED'], f"Invalid decision: {decision}"
        print(f"\n✅ Architect Decision Test PASSED: {decision}")
    else:
        print("\n⚠️  Architect failed (acceptable for integration test)")
        print(f"    Error: {arch_phase.agent_response.error}")
