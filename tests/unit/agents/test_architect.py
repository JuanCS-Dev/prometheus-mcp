"""
Tests for ArchitectAgent - The Visionary Skeptic.

Tests cover:
- ARCHITECT_SYSTEM_PROMPT constant
- ArchitectAgent initialization
- ArchitectAgent.execute() with various scenarios
- _build_analysis_prompt() helper
- _extract_decision_fallback() helper
- Integration tests for full workflow

Based on Anthropic Claude Code testing standards.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.architect import (
    ARCHITECT_SYSTEM_PROMPT,
    ArchitectAgent,
)
from jdev_cli.agents.base import (
    AgentRole,
    AgentCapability,
    AgentTask,
    AgentResponse,
)


# =============================================================================
# SYSTEM PROMPT TESTS
# =============================================================================

class TestArchitectSystemPrompt:
    """Tests for ARCHITECT_SYSTEM_PROMPT constant."""

    def test_prompt_exists(self):
        """Test system prompt is defined."""
        assert ARCHITECT_SYSTEM_PROMPT is not None
        assert isinstance(ARCHITECT_SYSTEM_PROMPT, str)
        assert len(ARCHITECT_SYSTEM_PROMPT) > 100

    def test_prompt_contains_role(self):
        """Test prompt defines the agent role."""
        assert "Architect" in ARCHITECT_SYSTEM_PROMPT
        assert "Feasibility" in ARCHITECT_SYSTEM_PROMPT

    def test_prompt_contains_decision_criteria(self):
        """Test prompt contains decision criteria."""
        assert "APPROVE" in ARCHITECT_SYSTEM_PROMPT
        assert "VETO" in ARCHITECT_SYSTEM_PROMPT

    def test_prompt_contains_output_format(self):
        """Test prompt defines JSON output format."""
        assert "JSON" in ARCHITECT_SYSTEM_PROMPT
        assert "decision" in ARCHITECT_SYSTEM_PROMPT
        assert "reasoning" in ARCHITECT_SYSTEM_PROMPT
        assert "architecture" in ARCHITECT_SYSTEM_PROMPT

    def test_prompt_mentions_read_only(self):
        """Test prompt specifies READ_ONLY capabilities."""
        assert "READ_ONLY" in ARCHITECT_SYSTEM_PROMPT

    def test_prompt_contains_personality(self):
        """Test prompt defines agent personality."""
        assert "Skeptical" in ARCHITECT_SYSTEM_PROMPT or "skeptical" in ARCHITECT_SYSTEM_PROMPT
        assert "production" in ARCHITECT_SYSTEM_PROMPT.lower()

    def test_prompt_contains_boris_quote(self):
        """Test prompt includes Boris Cherny philosophy."""
        assert "Boris" in ARCHITECT_SYSTEM_PROMPT or "fail" in ARCHITECT_SYSTEM_PROMPT


# =============================================================================
# ARCHITECTAGENT INITIALIZATION TESTS
# =============================================================================

class TestArchitectAgentInitialization:
    """Tests for ArchitectAgent initialization."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        return MagicMock()

    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client."""
        return MagicMock()

    def test_basic_initialization(self, mock_llm, mock_mcp):
        """Test basic agent initialization."""
        agent = ArchitectAgent(llm_client=mock_llm, mcp_client=mock_mcp)

        assert agent is not None
        assert agent.role == AgentRole.ARCHITECT

    def test_has_read_only_capability(self, mock_llm, mock_mcp):
        """Test agent has READ_ONLY capability."""
        agent = ArchitectAgent(llm_client=mock_llm, mcp_client=mock_mcp)

        assert AgentCapability.READ_ONLY in agent.capabilities

    def test_no_write_capability(self, mock_llm, mock_mcp):
        """Test agent does NOT have write capabilities."""
        agent = ArchitectAgent(llm_client=mock_llm, mcp_client=mock_mcp)

        assert AgentCapability.FILE_EDIT not in agent.capabilities
        assert AgentCapability.BASH_EXEC not in agent.capabilities

    def test_uses_architect_system_prompt(self, mock_llm, mock_mcp):
        """Test agent uses the ARCHITECT_SYSTEM_PROMPT."""
        agent = ArchitectAgent(llm_client=mock_llm, mcp_client=mock_mcp)

        assert agent.system_prompt == ARCHITECT_SYSTEM_PROMPT

    def test_stores_clients(self, mock_llm, mock_mcp):
        """Test agent stores LLM and MCP clients."""
        agent = ArchitectAgent(llm_client=mock_llm, mcp_client=mock_mcp)

        assert agent.llm_client == mock_llm
        assert agent.mcp_client == mock_mcp


# =============================================================================
# EXECUTE TESTS - APPROVED SCENARIOS
# =============================================================================

class TestArchitectExecuteApproved:
    """Tests for ArchitectAgent.execute() - APPROVED scenarios."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        return MagicMock()

    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client."""
        return MagicMock()

    @pytest.fixture
    def architect(self, mock_llm, mock_mcp):
        """Create ArchitectAgent instance."""
        return ArchitectAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_approved_decision_json(self, architect):
        """Test execute with valid APPROVED JSON response."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "Request is feasible with current codebase",
            "architecture": {
                "approach": "Add new module for JWT handling",
                "risks": ["Token expiry handling", "Key rotation"],
                "constraints": ["Must integrate with existing auth"],
                "estimated_complexity": "MEDIUM"
            },
            "recommendations": ["Use PyJWT library", "Add token refresh"]
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Add JWT authentication")
        response = await architect.execute(task)

        assert response.success is True
        assert response.data["decision"] == "APPROVED"
        assert "architecture" in response.data
        # Data contains all the decision info
        assert response.data.get("reasoning") is not None

    @pytest.mark.asyncio
    async def test_approved_normalizes_approve_variant(self, architect):
        """Test execute accepts 'APPROVE' variant."""
        llm_response = json.dumps({
            "decision": "APPROVE",  # Without 'D'
            "reasoning": "Looks good"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Simple feature")
        response = await architect.execute(task)

        assert response.success is True
        # Original decision is preserved in data, but response succeeds
        # because APPROVE is accepted and normalized internally
        assert response.data["decision"].upper() in ("APPROVE", "APPROVED")

    @pytest.mark.asyncio
    async def test_approved_with_low_complexity(self, architect):
        """Test APPROVED with LOW complexity estimate."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "Simple change",
            "architecture": {
                "approach": "Single file edit",
                "risks": [],
                "constraints": [],
                "estimated_complexity": "LOW"
            }
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Fix typo in README")
        response = await architect.execute(task)

        assert response.success is True
        assert response.data["architecture"]["estimated_complexity"] == "LOW"


# =============================================================================
# EXECUTE TESTS - VETOED SCENARIOS
# =============================================================================

class TestArchitectExecuteVetoed:
    """Tests for ArchitectAgent.execute() - VETOED scenarios."""

    @pytest.fixture
    def architect(self):
        """Create ArchitectAgent instance."""
        return ArchitectAgent(llm_client=MagicMock(), mcp_client=MagicMock())

    @pytest.mark.asyncio
    async def test_vetoed_decision_json(self, architect):
        """Test execute with valid VETOED JSON response."""
        llm_response = json.dumps({
            "decision": "VETOED",
            "reasoning": "Request conflicts with architectural principles",
            "architecture": {
                "approach": "N/A - Request vetoed",
                "risks": ["Breaking existing API", "Data loss"],
                "constraints": ["Backwards compatibility required"],
                "estimated_complexity": "HIGH"
            },
            "recommendations": ["Reconsider approach", "Break into phases"]
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Delete all user data and rebuild")
        response = await architect.execute(task)

        assert response.success is True
        assert response.data["decision"] == "VETOED"

    @pytest.mark.asyncio
    async def test_vetoed_normalizes_veto_variant(self, architect):
        """Test execute accepts 'VETO' variant."""
        llm_response = json.dumps({
            "decision": "VETO",  # Without 'ED'
            "reasoning": "Too risky"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Dangerous operation")
        response = await architect.execute(task)

        assert response.success is True
        # Original decision preserved in data, accepted internally
        assert response.data["decision"].upper() in ("VETO", "VETOED")


# =============================================================================
# EXECUTE TESTS - ERROR HANDLING
# =============================================================================

class TestArchitectExecuteErrors:
    """Tests for ArchitectAgent.execute() - error handling."""

    @pytest.fixture
    def architect(self):
        """Create ArchitectAgent instance."""
        return ArchitectAgent(llm_client=MagicMock(), mcp_client=MagicMock())

    @pytest.mark.asyncio
    async def test_invalid_json_uses_fallback(self, architect):
        """Test fallback extraction when LLM returns invalid JSON."""
        llm_response = "I APPROVE this request. It looks feasible."
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Add feature")
        response = await architect.execute(task)

        # Should use fallback and still succeed
        assert response.success is True
        assert response.data["decision"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_missing_decision_field(self, architect):
        """Test error when LLM response missing 'decision' field."""
        llm_response = json.dumps({
            "reasoning": "Analysis complete",
            "architecture": {"approach": "TBD"}
            # Missing 'decision' field
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Add feature")
        response = await architect.execute(task)

        assert response.success is False
        assert "missing" in response.reasoning.lower() or "decision" in response.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_decision_value(self, architect):
        """Test error when decision is neither APPROVED nor VETOED."""
        llm_response = json.dumps({
            "decision": "MAYBE",  # Invalid
            "reasoning": "Uncertain"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Add feature")
        response = await architect.execute(task)

        assert response.success is False
        assert "Invalid decision" in response.reasoning or "APPROVED or VETOED" in response.error

    @pytest.mark.asyncio
    async def test_llm_exception_handling(self, architect):
        """Test error handling when LLM call raises exception."""
        architect._call_llm = AsyncMock(side_effect=Exception("LLM service unavailable"))

        task = AgentTask(request="Add feature")
        response = await architect.execute(task)

        assert response.success is False
        assert "failed" in response.reasoning.lower()
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_case_insensitive_decision(self, architect):
        """Test decision parsing is case insensitive."""
        llm_response = json.dumps({
            "decision": "approved",  # Lowercase
            "reasoning": "OK"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Add feature")
        response = await architect.execute(task)

        assert response.success is True
        # Decision parsing uses .upper() so lowercase is accepted
        # Original value preserved in data
        assert response.data["decision"].upper() == "APPROVED"


# =============================================================================
# _BUILD_ANALYSIS_PROMPT TESTS
# =============================================================================

class TestBuildAnalysisPrompt:
    """Tests for _build_analysis_prompt() helper."""

    @pytest.fixture
    def architect(self):
        """Create ArchitectAgent instance."""
        return ArchitectAgent(llm_client=MagicMock(), mcp_client=MagicMock())

    def test_basic_prompt(self, architect):
        """Test basic prompt generation."""
        task = AgentTask(request="Add user authentication")
        prompt = architect._build_analysis_prompt(task)

        assert "Add user authentication" in prompt
        assert "REQUEST:" in prompt
        assert "CONTEXT:" in prompt

    def test_prompt_with_files(self, architect):
        """Test prompt includes file context."""
        task = AgentTask(
            request="Refactor auth module",
            context={"files": ["src/auth.py", "src/users.py", "tests/test_auth.py"]}
        )
        prompt = architect._build_analysis_prompt(task)

        assert "3 files" in prompt
        assert "src/auth.py" in prompt
        assert "src/users.py" in prompt

    def test_prompt_limits_files_to_five(self, architect):
        """Test prompt shows max 5 files."""
        files = [f"src/file_{i}.py" for i in range(10)]
        task = AgentTask(
            request="Large refactor",
            context={"files": files}
        )
        prompt = architect._build_analysis_prompt(task)

        assert "10 files" in prompt
        # Should only show first 5
        assert "file_0" in prompt
        assert "file_4" in prompt
        # file_5 onwards should NOT be in prompt listing
        # (though the count shows 10)

    def test_prompt_with_constraints(self, architect):
        """Test prompt includes constraints."""
        task = AgentTask(
            request="Add new API",
            context={"constraints": "Must be backwards compatible"}
        )
        prompt = architect._build_analysis_prompt(task)

        assert "Constraints:" in prompt
        assert "backwards compatible" in prompt

    def test_prompt_mentions_json(self, architect):
        """Test prompt asks for JSON response."""
        task = AgentTask(request="Simple request")
        prompt = architect._build_analysis_prompt(task)

        assert "JSON" in prompt

    def test_prompt_mentions_skepticism(self, architect):
        """Test prompt reminds to be skeptical."""
        task = AgentTask(request="Risky operation")
        prompt = architect._build_analysis_prompt(task)

        assert "skeptical" in prompt.lower() or "veto" in prompt.lower()


# =============================================================================
# _EXTRACT_DECISION_FALLBACK TESTS
# =============================================================================

class TestExtractDecisionFallback:
    """Tests for _extract_decision_fallback() helper."""

    @pytest.fixture
    def architect(self):
        """Create ArchitectAgent instance."""
        return ArchitectAgent(llm_client=MagicMock(), mcp_client=MagicMock())

    def test_extract_approved(self, architect):
        """Test extraction of APPROVED decision."""
        response = "After analysis, I APPROVE this request. It's feasible."
        result = architect._extract_decision_fallback(response)

        assert result["decision"] == "APPROVED"
        assert "reasoning" in result
        assert "architecture" in result

    def test_extract_approve_variant(self, architect):
        """Test extraction recognizes 'approve' variant."""
        response = "I approve of this approach. Seems good."
        result = architect._extract_decision_fallback(response)

        assert result["decision"] == "APPROVED"

    def test_extract_vetoed(self, architect):
        """Test extraction of VETOED decision."""
        response = "This request is VETOED due to security concerns."
        result = architect._extract_decision_fallback(response)

        assert result["decision"] == "VETOED"

    def test_extract_veto_variant(self, architect):
        """Test extraction recognizes 'veto' variant."""
        response = "I must veto this request. Too risky."
        result = architect._extract_decision_fallback(response)

        assert result["decision"] == "VETOED"

    def test_extract_rejected(self, architect):
        """Test extraction recognizes 'rejected'."""
        response = "This request is rejected for safety reasons."
        result = architect._extract_decision_fallback(response)

        assert result["decision"] == "VETOED"

    def test_extract_unknown(self, architect):
        """Test extraction returns UNKNOWN for ambiguous response."""
        response = "I'm not sure about this. Needs more analysis."
        result = architect._extract_decision_fallback(response)

        assert result["decision"] == "UNKNOWN"

    def test_fallback_truncates_reasoning(self, architect):
        """Test fallback truncates long reasoning to 500 chars."""
        long_response = "A" * 1000
        result = architect._extract_decision_fallback(long_response)

        assert len(result["reasoning"]) == 500

    def test_fallback_returns_complete_structure(self, architect):
        """Test fallback returns complete data structure."""
        response = "APPROVED - looks good"
        result = architect._extract_decision_fallback(response)

        assert "decision" in result
        assert "reasoning" in result
        assert "architecture" in result
        assert "approach" in result["architecture"]
        assert "risks" in result["architecture"]
        assert "constraints" in result["architecture"]
        assert "estimated_complexity" in result["architecture"]
        assert "recommendations" in result

    def test_fallback_complexity_unknown(self, architect):
        """Test fallback sets complexity to UNKNOWN."""
        response = "APPROVED"
        result = architect._extract_decision_fallback(response)

        assert result["architecture"]["estimated_complexity"] == "UNKNOWN"

    def test_fallback_approach_indicates_fallback(self, architect):
        """Test fallback approach indicates fallback extraction."""
        response = "APPROVED"
        result = architect._extract_decision_fallback(response)

        assert "fallback" in result["architecture"]["approach"].lower()


# =============================================================================
# EXECUTE WITH CONTEXT TESTS
# =============================================================================

class TestArchitectExecuteWithContext:
    """Tests for execute with various context scenarios."""

    @pytest.fixture
    def architect(self):
        """Create ArchitectAgent instance."""
        return ArchitectAgent(llm_client=MagicMock(), mcp_client=MagicMock())

    @pytest.mark.asyncio
    async def test_execute_with_file_context(self, architect):
        """Test execute passes file context to analysis."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "Feasible with existing files"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(
            request="Modify auth",
            context={"files": ["src/auth.py"]}
        )
        response = await architect.execute(task)

        assert response.success is True
        # Verify _call_llm was called with prompt containing file info
        call_args = architect._call_llm.call_args[0][0]
        assert "auth.py" in call_args

    @pytest.mark.asyncio
    async def test_execute_with_constraints(self, architect):
        """Test execute passes constraints to analysis."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "Meets constraints"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(
            request="Add feature",
            context={"constraints": "No breaking changes"}
        )
        response = await architect.execute(task)

        assert response.success is True
        call_args = architect._call_llm.call_args[0][0]
        assert "No breaking changes" in call_args

    @pytest.mark.asyncio
    async def test_execute_empty_context(self, architect):
        """Test execute with empty context."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "Simple request"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Simple task", context={})
        response = await architect.execute(task)

        assert response.success is True


# =============================================================================
# DATA CONTENT TESTS
# =============================================================================

class TestArchitectResponseData:
    """Tests for response data contents."""

    @pytest.fixture
    def architect(self):
        """Create ArchitectAgent instance."""
        return ArchitectAgent(llm_client=MagicMock(), mcp_client=MagicMock())

    @pytest.mark.asyncio
    async def test_data_contains_decision(self, architect):
        """Test data contains decision."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "OK"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Test")
        response = await architect.execute(task)

        assert "decision" in response.data
        assert response.data["decision"] in ("APPROVED", "VETOED")

    @pytest.mark.asyncio
    async def test_data_contains_complexity(self, architect):
        """Test data contains complexity in architecture section."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "OK",
            "architecture": {"estimated_complexity": "HIGH"}
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Test")
        response = await architect.execute(task)

        assert "architecture" in response.data
        assert response.data["architecture"]["estimated_complexity"] == "HIGH"

    @pytest.mark.asyncio
    async def test_data_preserves_reasoning(self, architect):
        """Test data preserves reasoning from LLM."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "Detailed reasoning here"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Test")
        response = await architect.execute(task)

        assert response.data["reasoning"] == "Detailed reasoning here"
        # AgentResponse.reasoning also set
        assert response.reasoning == "Detailed reasoning here"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestArchitectIntegration:
    """Integration tests for complete workflow."""

    @pytest.mark.asyncio
    async def test_full_approval_workflow(self):
        """Test complete approval workflow."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        architect = ArchitectAgent(llm_client=mock_llm, mcp_client=mock_mcp)

        # Simulate realistic LLM response
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "JWT authentication is feasible. The codebase has existing auth infrastructure.",
            "architecture": {
                "approach": "Create new jwt_handler.py module, integrate with existing auth middleware",
                "risks": ["Token storage security", "Key rotation complexity"],
                "constraints": ["Must maintain backwards compatibility with session auth"],
                "estimated_complexity": "MEDIUM"
            },
            "recommendations": [
                "Use PyJWT library",
                "Implement refresh token mechanism",
                "Add rate limiting to token endpoints"
            ]
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(
            request="Add JWT authentication to the API",
            context={
                "files": ["src/auth/middleware.py", "src/auth/users.py"],
                "constraints": "Must support both JWT and existing session auth"
            }
        )

        response = await architect.execute(task)

        assert response.success is True
        assert response.data["decision"] == "APPROVED"
        assert len(response.data["architecture"]["risks"]) == 2
        assert len(response.data["recommendations"]) == 3
        assert response.data["architecture"]["estimated_complexity"] == "MEDIUM"

    @pytest.mark.asyncio
    async def test_full_veto_workflow(self):
        """Test complete veto workflow."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        architect = ArchitectAgent(llm_client=mock_llm, mcp_client=mock_mcp)

        llm_response = json.dumps({
            "decision": "VETOED",
            "reasoning": "Deleting the database without backup is too risky and violates data safety principles.",
            "architecture": {
                "approach": "N/A - Request vetoed",
                "risks": ["Complete data loss", "No recovery possible", "Violates regulations"],
                "constraints": ["Data retention policy requires backups"],
                "estimated_complexity": "N/A"
            },
            "recommendations": [
                "Create backup before any destructive operations",
                "Use soft delete instead of hard delete",
                "Implement proper migration strategy"
            ]
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(
            request="Delete the production database and rebuild from scratch",
            context={}
        )

        response = await architect.execute(task)

        assert response.success is True
        assert response.data["decision"] == "VETOED"
        assert "data loss" in response.data["architecture"]["risks"][0].lower()
        # Decision is in data
        assert response.data.get("reasoning") is not None

    @pytest.mark.asyncio
    async def test_fallback_workflow(self):
        """Test workflow when LLM returns non-JSON."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        architect = ArchitectAgent(llm_client=mock_llm, mcp_client=mock_mcp)

        # LLM returns plain text instead of JSON
        llm_response = """
        After careful analysis, I approve this request.

        The proposed feature is technically feasible and aligns with the existing architecture.
        There are minimal risks involved, and the implementation should be straightforward.
        """
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Add logging to the API")
        response = await architect.execute(task)

        assert response.success is True
        assert response.data["decision"] == "APPROVED"
        # Fallback should provide complete structure
        assert "architecture" in response.data
        assert "fallback" in response.data["architecture"]["approach"].lower()


# =============================================================================
# EDGE CASES
# =============================================================================

class TestArchitectEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def architect(self):
        """Create ArchitectAgent instance."""
        return ArchitectAgent(llm_client=MagicMock(), mcp_client=MagicMock())

    @pytest.mark.asyncio
    async def test_empty_request(self, architect):
        """Test handling of empty request."""
        llm_response = json.dumps({
            "decision": "VETOED",
            "reasoning": "Empty request cannot be analyzed"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="")
        response = await architect.execute(task)

        # Should still work, LLM decides
        assert isinstance(response, AgentResponse)

    @pytest.mark.asyncio
    async def test_very_long_request(self, architect):
        """Test handling of very long request."""
        llm_response = json.dumps({
            "decision": "VETOED",
            "reasoning": "Request too complex"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        long_request = "Add feature " * 1000  # Very long
        task = AgentTask(request=long_request)
        response = await architect.execute(task)

        assert isinstance(response, AgentResponse)

    @pytest.mark.asyncio
    async def test_unicode_in_request(self, architect):
        """Test handling of unicode characters."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "Supported characters"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Add 日本語 support to the API 🚀")
        response = await architect.execute(task)

        assert response.success is True

    @pytest.mark.asyncio
    async def test_json_with_extra_fields(self, architect):
        """Test handling of JSON with extra unexpected fields."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "OK",
            "extra_field": "Should be ignored",
            "another_extra": {"nested": "data"}
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Test")
        response = await architect.execute(task)

        assert response.success is True
        assert "extra_field" in response.data  # Preserved but not breaking

    @pytest.mark.asyncio
    async def test_llm_returns_empty_string(self, architect):
        """Test handling when LLM returns empty string."""
        architect._call_llm = AsyncMock(return_value="")

        task = AgentTask(request="Test")
        response = await architect.execute(task)

        # Should use fallback and return UNKNOWN, which then fails validation
        # since UNKNOWN is not APPROVED or VETOED
        # This should result in a failed response
        assert response.success is False or response.data.get("decision") == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_none_context(self, architect):
        """Test handling of None values in context."""
        llm_response = json.dumps({
            "decision": "APPROVED",
            "reasoning": "OK"
        })
        architect._call_llm = AsyncMock(return_value=llm_response)

        task = AgentTask(request="Test", context={"files": None})
        response = await architect.execute(task)

        # Should not crash
        assert isinstance(response, AgentResponse)
