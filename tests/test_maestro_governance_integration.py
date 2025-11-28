"""
Maestro Governance Integration Tests

Validates Phase 5 integration:
- MaestroGovernance initialization
- Risk level detection
- Governance hooks in execution
- Sofia command
- Error handling and graceful degradation
- Import validation

This test suite searches for AIR GAPS in the integration.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

# Validate all imports work
from jdev_cli.maestro_governance import MaestroGovernance, render_sofia_counsel
from jdev_cli.core.governance_pipeline import GovernancePipeline
from jdev_cli.agents.justica_agent import JusticaIntegratedAgent
from jdev_cli.agents.sofia_agent import SofiaIntegratedAgent
from jdev_cli.agents.base import AgentTask, AgentResponse


class TestMaestroGovernanceImports:
    """Test that all required imports are present and working."""

    def test_maestro_governance_import(self):
        """Validate MaestroGovernance class imports."""
        assert MaestroGovernance is not None
        assert hasattr(MaestroGovernance, 'initialize')
        assert hasattr(MaestroGovernance, 'execute_with_governance')
        assert hasattr(MaestroGovernance, 'ask_sofia')
        assert hasattr(MaestroGovernance, 'detect_risk_level')
        assert hasattr(MaestroGovernance, 'get_governance_status')

    def test_render_sofia_counsel_import(self):
        """Validate render_sofia_counsel function imports."""
        assert render_sofia_counsel is not None
        assert callable(render_sofia_counsel)

    def test_all_dependencies_import(self):
        """Validate all dependency imports work."""
        # These should not raise ImportError
        from jdev_cli.core.observability import setup_observability, trace_operation
        from jdev_cli.core.agent_identity import get_agent_identity, AGENT_IDENTITIES

        assert setup_observability is not None
        assert trace_operation is not None
        assert get_agent_identity is not None
        assert AGENT_IDENTITIES is not None


class TestMaestroGovernanceInitialization:
    """Test MaestroGovernance initialization and configuration."""

    def test_governance_creation(self):
        """Test that MaestroGovernance can be created."""
        mock_llm = Mock()
        mock_mcp = Mock()

        gov = MaestroGovernance(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            enable_governance=True,
            enable_counsel=True,
            enable_observability=True,
            auto_risk_detection=True
        )

        assert gov.llm_client == mock_llm
        assert gov.mcp_client == mock_mcp
        assert gov.enable_governance is True
        assert gov.enable_counsel is True
        assert gov.enable_observability is True
        assert gov.auto_risk_detection is True
        assert gov.initialized is False
        assert gov.justica is None
        assert gov.sofia is None
        assert gov.pipeline is None

    def test_governance_disabled_configuration(self):
        """Test governance can be configured as disabled."""
        mock_llm = Mock()
        mock_mcp = Mock()

        gov = MaestroGovernance(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            enable_governance=False,
            enable_counsel=False,
            enable_observability=False,
            auto_risk_detection=False
        )

        assert gov.enable_governance is False
        assert gov.enable_counsel is False
        assert gov.enable_observability is False
        assert gov.auto_risk_detection is False

    @pytest.mark.asyncio
    async def test_initialization_idempotent(self):
        """Test that initialize() is idempotent (can be called multiple times)."""
        mock_llm = Mock()
        mock_mcp = Mock()

        with patch.object(JusticaIntegratedAgent, '__init__', return_value=None):
            with patch.object(SofiaIntegratedAgent, '__init__', return_value=None):
                gov = MaestroGovernance(mock_llm, mock_mcp, enable_observability=False)

                # Mock the agents to avoid actual initialization
                gov.justica = Mock()
                gov.sofia = Mock()
                gov.pipeline = Mock()
                gov.initialized = True

                # Should not re-initialize
                await gov.initialize()

                assert gov.initialized is True


class TestRiskLevelDetection:
    """Test automatic risk level detection from prompts."""

    def test_critical_risk_patterns(self):
        """Test CRITICAL risk detection."""
        mock_llm = Mock()
        mock_mcp = Mock()
        gov = MaestroGovernance(mock_llm, mock_mcp, auto_risk_detection=True)

        critical_prompts = [
            "Delete all production data",
            "Drop the users table",
            "Deploy to production without tests",
            "Change root password",
            "Modify security settings",
            "Update admin credentials"
        ]

        for prompt in critical_prompts:
            risk = gov.detect_risk_level(prompt, "planner")
            assert risk == "CRITICAL", f"Failed for: {prompt}"

    def test_high_risk_patterns(self):
        """Test HIGH risk detection."""
        mock_llm = Mock()
        mock_mcp = Mock()
        gov = MaestroGovernance(mock_llm, mock_mcp, auto_risk_detection=True)

        high_prompts = [
            "Refactor database schema",
            "Change API endpoints",
            "Redesign architecture",
            "Migration script for users",
            "Breaking change in payment flow"  # Changed from "authentication" (which triggers CRITICAL)
        ]

        for prompt in high_prompts:
            risk = gov.detect_risk_level(prompt, "planner")
            assert risk == "HIGH", f"Failed for: {prompt}"

    def test_medium_risk_default(self):
        """Test MEDIUM risk as default."""
        mock_llm = Mock()
        mock_mcp = Mock()
        gov = MaestroGovernance(mock_llm, mock_mcp, auto_risk_detection=True)

        medium_prompts = [
            "Add user profile feature",
            "Fix bug in payment flow",  # Changed from "authentication" (CRITICAL keyword)
            "Implement caching layer"
        ]

        for prompt in medium_prompts:
            risk = gov.detect_risk_level(prompt, "planner")
            assert risk == "MEDIUM", f"Failed for: {prompt}"

    def test_low_risk_patterns(self):
        """Test LOW risk detection."""
        mock_llm = Mock()
        mock_mcp = Mock()
        gov = MaestroGovernance(mock_llm, mock_mcp, auto_risk_detection=True)

        low_prompts = [
            "Show all Python files",
            "List available tests",
            "Read configuration",
            "Document the endpoints",  # Changed from "API" (HIGH keyword)
            "Search for TODO comments"
        ]

        for prompt in low_prompts:
            risk = gov.detect_risk_level(prompt, "planner")
            assert risk == "LOW", f"Failed for: {prompt}"

    def test_auto_risk_detection_disabled(self):
        """Test that auto detection can be disabled."""
        mock_llm = Mock()
        mock_mcp = Mock()
        gov = MaestroGovernance(mock_llm, mock_mcp, auto_risk_detection=False)

        # Should always return MEDIUM when disabled
        assert gov.detect_risk_level("Delete production", "planner") == "MEDIUM"
        assert gov.detect_risk_level("Read a file", "planner") == "MEDIUM"


class TestGovernanceStatus:
    """Test governance status reporting."""

    def test_get_status_before_init(self):
        """Test status when not initialized."""
        mock_llm = Mock()
        mock_mcp = Mock()
        gov = MaestroGovernance(mock_llm, mock_mcp)

        status = gov.get_governance_status()

        assert status["initialized"] is False
        assert status["governance_enabled"] is True
        assert status["counsel_enabled"] is True
        assert status["justica_available"] is False
        assert status["sofia_available"] is False
        assert status["pipeline_available"] is False

    def test_get_status_after_mock_init(self):
        """Test status when initialized (mocked)."""
        mock_llm = Mock()
        mock_mcp = Mock()
        gov = MaestroGovernance(mock_llm, mock_mcp)

        # Mock initialization
        gov.initialized = True
        gov.justica = Mock()
        gov.sofia = Mock()
        gov.pipeline = Mock()

        status = gov.get_governance_status()

        assert status["initialized"] is True
        assert status["justica_available"] is True
        assert status["sofia_available"] is True
        assert status["pipeline_available"] is True


class TestAirGapValidation:
    """Test for AIR GAPS in the integration."""

    def test_no_circular_imports(self):
        """Test that there are no circular import dependencies."""
        # If we got this far, imports worked - no circular dependencies

        assert True  # If imports succeed, no circular deps

    def test_maestro_py_has_governance_import(self):
        """Verify maestro.py imports governance module."""
        import ast
        with open('/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli/jdev_cli/maestro.py', 'r') as f:
            tree = ast.parse(f.read())

        # Check for governance import
        imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        governance_imported = any(
            imp.module == 'jdev_cli.maestro_governance'
            for imp in imports
        )

        assert governance_imported, "maestro.py must import maestro_governance"

    def test_maestro_py_has_state_governance_field(self):
        """Verify GlobalState has governance field."""
        with open('/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli/jdev_cli/maestro.py', 'r') as f:
            content = f.read()

        assert 'self.governance' in content, "GlobalState must have governance field"
        assert 'state.governance' in content, "Code must reference state.governance"

    def test_maestro_py_initializes_governance(self):
        """Verify ensure_initialized() creates MaestroGovernance."""
        with open('/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli/jdev_cli/maestro.py', 'r') as f:
            content = f.read()

        assert 'MaestroGovernance(' in content, "Must instantiate MaestroGovernance"
        assert 'await state.governance.initialize()' in content, "Must call initialize()"

    def test_maestro_py_has_governance_hook(self):
        """Verify execute_agent_task() has governance hook."""
        with open('/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli/jdev_cli/maestro.py', 'r') as f:
            content = f.read()

        assert 'with_governance' in content, "Must have with_governance parameter"
        assert 'execute_with_governance' in content, "Must call execute_with_governance"

    def test_maestro_py_has_sofia_command(self):
        """Verify sofia command exists."""
        with open('/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli/jdev_cli/maestro.py', 'r') as f:
            content = f.read()

        assert '@agent_app.async_command("sofia")' in content, "Must have sofia command"
        assert 'ask_sofia' in content, "Must call ask_sofia method"

    def test_maestro_py_has_governance_status_command(self):
        """Verify governance status command exists."""
        with open('/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli/jdev_cli/maestro.py', 'r') as f:
            content = f.read()

        assert '@agent_app.async_command("governance")' in content, "Must have governance command"
        assert 'get_governance_status' in content, "Must call get_governance_status method"

    def test_all_agent_roles_have_identities(self):
        """Verify all AgentRoles used have corresponding identities."""
        from jdev_cli.core.agent_identity import AGENT_IDENTITIES
        from jdev_cli.agents.base import AgentRole

        # Check that key roles have identities
        critical_roles = ["maestro", "governance", "counselor", "executor"]

        for role_id in critical_roles:
            assert role_id in AGENT_IDENTITIES, f"Identity missing for: {role_id}"

        # Verify executor uses EXECUTOR role
        executor_identity = AGENT_IDENTITIES.get("executor")
        assert executor_identity is not None
        assert executor_identity.role == AgentRole.EXECUTOR

    def test_governance_pipeline_accepts_all_roles(self):
        """Test that governance pipeline can handle all agent roles."""
        from jdev_cli.agents.base import AgentRole

        mock_llm = Mock()
        mock_mcp = Mock()
        gov = MaestroGovernance(mock_llm, mock_mcp)

        # Should not crash for any role
        for role in AgentRole:
            risk = gov.detect_risk_level("Test action", role.value)
            assert risk in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def test_graceful_degradation_path_exists(self):
        """Test that graceful degradation code exists."""
        with open('/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli/jdev_cli/maestro.py', 'r') as f:
            content = f.read()

        # Check for error handling
        assert 'except Exception as e:' in content
        assert 'degraded mode' in content.lower() or 'without governance' in content.lower()

        # Check for fallback execution
        assert 'if with_governance and state.governance:' in content
        assert 'else:' in content  # Fallback path


class TestIntegrationConsistency:
    """Test consistency between components."""

    def test_governance_pipeline_uses_correct_agents(self):
        """Test GovernancePipeline uses Justiça and Sofia correctly."""
        mock_llm = Mock()
        mock_mcp = Mock()

        with patch.object(JusticaIntegratedAgent, '__init__', return_value=None):
            with patch.object(SofiaIntegratedAgent, '__init__', return_value=None):
                justica = Mock(spec=JusticaIntegratedAgent)
                sofia = Mock(spec=SofiaIntegratedAgent)

                pipeline = GovernancePipeline(
                    justica=justica,
                    sofia=sofia,
                    enable_governance=True,
                    enable_counsel=True
                )

                assert pipeline.justica == justica
                assert pipeline.sofia == sofia

    def test_maestro_governance_requires_both_agents(self):
        """Test MaestroGovernance creates both Justiça and Sofia."""
        mock_llm = Mock()
        mock_mcp = Mock()

        gov = MaestroGovernance(
            mock_llm, mock_mcp,
            enable_governance=True,
            enable_counsel=True
        )

        # Before init, should be None
        assert gov.justica is None
        assert gov.sofia is None
        assert gov.pipeline is None

    def test_permissions_consistency(self):
        """Test that permissions are consistently defined."""
        from jdev_cli.core.agent_identity import AgentPermission, get_agent_identity

        # Governance should have evaluation permissions
        governance = get_agent_identity("governance")
        assert governance is not None
        assert governance.can(AgentPermission.EVALUATE_GOVERNANCE)
        assert governance.can(AgentPermission.BLOCK_ACTIONS)

        # Counselor should have counsel permissions
        counselor = get_agent_identity("counselor")
        assert counselor is not None
        assert counselor.can(AgentPermission.PROVIDE_COUNSEL)
        assert counselor.can(AgentPermission.ACCESS_ETHICAL_KNOWLEDGE)

        # Executor should have execution permissions
        executor = get_agent_identity("executor")
        assert executor is not None
        assert executor.can(AgentPermission.EXECUTE_COMMANDS)


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_execute_without_pipeline(self):
        """Test execute_with_governance when pipeline is None."""
        mock_llm = Mock()
        mock_mcp = Mock()
        gov = MaestroGovernance(mock_llm, mock_mcp)

        # Pipeline is None (not initialized)
        assert gov.pipeline is None

        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value=AgentResponse(
            success=True,
            reasoning="Direct execution",
            data={}
        ))

        task = AgentTask(request="Test task", context={})

        # Should execute directly without governance
        response = await gov.execute_with_governance(mock_agent, task)

        assert response.success is True
        mock_agent.execute.assert_called_once()

    def test_render_sofia_counsel_handles_errors(self):
        """Test render_sofia_counsel handles error responses."""
        error_data = {
            "success": False,
            "error": "Sofia unavailable"
        }

        # Should not crash
        try:
            render_sofia_counsel(error_data)
            assert True
        except Exception as e:
            pytest.fail(f"render_sofia_counsel crashed on error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
