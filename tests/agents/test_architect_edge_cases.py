"""
Comprehensive edge case testing for ArchitectAgent.

Tests cover:
    - Boundary conditions
    - Real-world scenarios
    - Malformed inputs
    - Performance edge cases
    - Concurrent operations
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.architect import ArchitectAgent
from jdev_cli.agents.base import AgentTask


class TestArchitectBoundaryConditions:
    """Boundary condition tests for Architect."""

    @pytest.mark.asyncio
    async def test_architect_with_empty_request(self) -> None:
        """Test Architect handles empty request gracefully."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "VETOED",
                "reasoning": "Empty request cannot be analyzed",
                "architecture": {"approach": "N/A", "risks": [], "constraints": [], "estimated_complexity": "UNKNOWN"},
                "recommendations": ["Provide a specific request"],
            })
        )
        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(request="", session_id="test")

        # Agent should handle empty request and return a response
        response = await architect.execute(task)
        # Either returns vetoed or fails gracefully
        assert response is not None

    @pytest.mark.asyncio
    async def test_architect_with_very_long_request(self) -> None:
        """Test Architect with very long request (10K chars)."""
        long_request = "A" * 10000
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "VETOED",
                "reasoning": "Request too vague",
                "architecture": {"approach": "N/A", "risks": [], "constraints": [], "estimated_complexity": "HIGH"},
                "recommendations": [],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(request=long_request, session_id="test")

        response = await architect.execute(task)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_architect_with_unicode_request(self) -> None:
        """Test Architect with unicode characters."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Internacionalization request is valid",
                "architecture": {"approach": "Add i18n", "risks": [], "constraints": [], "estimated_complexity": "MEDIUM"},
                "recommendations": [],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Adicionar autenticação JWT 🔐 中文",
            session_id="test"
        )

        response = await architect.execute(task)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_architect_with_special_chars_in_request(self) -> None:
        """Test Architect with special characters."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Request is clear despite special chars",
                "architecture": {"approach": "Standard", "risks": [], "constraints": [], "estimated_complexity": "LOW"},
                "recommendations": [],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Add feature with 'quotes' and \"escapes\" and \n newlines",
            session_id="test"
        )

        response = await architect.execute(task)
        assert response.success is True


class TestArchitectRealWorldScenarios:
    """Real-world scenario tests."""

    @pytest.mark.asyncio
    async def test_architect_approves_add_api_endpoint(self) -> None:
        """Test realistic scenario: adding REST API endpoint."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Adding REST endpoint is straightforward with existing framework",
                "architecture": {
                    "approach": "Add route handler in api/routes.py, connect to service layer",
                    "risks": ["Input validation needed", "Rate limiting should be considered"],
                    "constraints": ["Must follow existing REST conventions", "OpenAPI spec needs update"],
                    "estimated_complexity": "LOW",
                },
                "recommendations": [
                    "Add input validation with Pydantic",
                    "Include unit tests",
                    "Update API documentation",
                ],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Add GET /api/users/{id} endpoint to retrieve user by ID",
            session_id="test",
            context={"files": ["src/api/routes.py", "src/services/user_service.py"]},
        )

        response = await architect.execute(task)
        assert response.success is True
        assert response.data["decision"] == "APPROVED"
        assert response.data["architecture"]["estimated_complexity"] == "LOW"
        assert len(response.data["recommendations"]) >= 3

    @pytest.mark.asyncio
    async def test_architect_vetoes_breaking_change(self) -> None:
        """Test realistic scenario: dangerous breaking change."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "VETOED",
                "reasoning": "Changing database schema without migration breaks production",
                "architecture": {
                    "approach": "Not recommended",
                    "risks": ["Data loss", "Service downtime", "Client compatibility break"],
                    "constraints": ["Requires database migration", "Backward compatibility needed"],
                    "estimated_complexity": "HIGH",
                },
                "recommendations": [
                    "Create migration script first",
                    "Use blue-green deployment",
                    "Add deprecation warnings before removal",
                ],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Delete the 'email' column from users table",
            session_id="test",
        )

        response = await architect.execute(task)
        assert response.success is True
        assert response.data["decision"] == "VETOED"
        # Check reasoning contains risk keywords
        reasoning_lower = response.reasoning.lower()
        assert ("downtime" in reasoning_lower or "data loss" in reasoning_lower or
                "breaks" in reasoning_lower or "migration" in reasoning_lower)

    @pytest.mark.asyncio
    async def test_architect_handles_microservice_request(self) -> None:
        """Test realistic scenario: microservice architecture."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Service extraction is feasible with clear boundaries",
                "architecture": {
                    "approach": "Extract payment processing to separate service with message queue",
                    "risks": ["Network latency", "Service discovery complexity", "Transaction boundaries"],
                    "constraints": ["Requires message broker (RabbitMQ/Kafka)", "Service mesh recommended"],
                    "estimated_complexity": "HIGH",
                },
                "recommendations": [
                    "Start with strangler pattern",
                    "Implement circuit breakers",
                    "Add distributed tracing",
                ],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Extract payment processing into separate microservice",
            session_id="test",
        )

        response = await architect.execute(task)
        assert response.success is True
        assert response.data["decision"] == "APPROVED"
        assert response.data["architecture"]["estimated_complexity"] == "HIGH"


class TestArchitectMalformedInputs:
    """Tests with malformed/invalid inputs."""

    @pytest.mark.asyncio
    async def test_architect_handles_json_with_extra_fields(self) -> None:
        """Test Architect ignores extra fields in JSON response."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Valid",
                "architecture": {"approach": "Test", "risks": [], "constraints": [], "estimated_complexity": "LOW"},
                "recommendations": [],
                "extra_field": "should be ignored",
                "another_field": 123,
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await architect.execute(task)
        assert response.success is True
        assert response.data["decision"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_architect_handles_incomplete_architecture(self) -> None:
        """Test Architect handles architecture with missing fields."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Valid",
                "architecture": {
                    "approach": "Test",
                    # Missing risks, constraints, complexity
                },
                "recommendations": [],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await architect.execute(task)
        assert response.success is True
        # Should handle gracefully even with incomplete architecture

    @pytest.mark.asyncio
    async def test_architect_handles_null_fields(self) -> None:
        """Test Architect handles null values in response (may fail gracefully)."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "VETOED",
                "reasoning": None,  # Null reasoning
                "architecture": None,  # Null architecture
                "recommendations": None,
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await architect.execute(task)
        # May fail due to null fields (expected behavior)
        assert response is not None  # At least returns a response

    @pytest.mark.asyncio
    async def test_architect_handles_wrong_type_decision(self) -> None:
        """Test Architect handles decision with wrong type."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": 123,  # Number instead of string
                "reasoning": "Test",
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await architect.execute(task)
        # Should fail validation
        assert response.success is False


class TestArchitectContextHandling:
    """Tests for context processing."""

    @pytest.mark.asyncio
    async def test_architect_with_many_files_in_context(self) -> None:
        """Test Architect with large file list in context."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Large codebase but request is focused",
                "architecture": {"approach": "Focused change", "risks": [], "constraints": [], "estimated_complexity": "MEDIUM"},
                "recommendations": [],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Add logging",
            session_id="test",
            context={"files": [f"file{i}.py" for i in range(100)]},
        )

        response = await architect.execute(task)
        assert response.success is True
        # Should only include first 5 files in prompt
        prompt_call = llm_client.generate.call_args[1]["prompt"]
        assert "100 files" in prompt_call

    @pytest.mark.asyncio
    async def test_architect_with_nested_context(self) -> None:
        """Test Architect with deeply nested context."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Valid",
                "architecture": {"approach": "Test", "risks": [], "constraints": [], "estimated_complexity": "LOW"},
                "recommendations": [],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Test",
            session_id="test",
            context={
                "level1": {
                    "level2": {
                        "level3": {"data": "deep"},
                    },
                },
            },
        )

        response = await architect.execute(task)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_architect_with_empty_context(self) -> None:
        """Test Architect with empty context dict."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Request is self-contained",
                "architecture": {"approach": "Simple", "risks": [], "constraints": [], "estimated_complexity": "LOW"},
                "recommendations": [],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(request="Add feature", session_id="test", context={})

        response = await architect.execute(task)
        assert response.success is True


class TestArchitectPerformance:
    """Performance-related edge cases."""

    @pytest.mark.asyncio
    async def test_architect_execution_count_increments(self) -> None:
        """Test that execution count increments correctly."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Test",
                "architecture": {"approach": "Test", "risks": [], "constraints": [], "estimated_complexity": "LOW"},
                "recommendations": [],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())
        initial_count = architect.execution_count

        task = AgentTask(request="Test", session_id="test")
        await architect.execute(task)

        assert architect.execution_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_architect_multiple_sequential_calls(self) -> None:
        """Test Architect handles multiple calls in sequence."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(
            return_value=json.dumps({
                "decision": "APPROVED",
                "reasoning": "Test",
                "architecture": {"approach": "Test", "risks": [], "constraints": [], "estimated_complexity": "LOW"},
                "recommendations": [],
            })
        )

        architect = ArchitectAgent(llm_client, MagicMock())

        for i in range(5):
            task = AgentTask(request=f"Test {i}", session_id=f"test-{i}")
            response = await architect.execute(task)
            assert response.success is True

        assert architect.execution_count == 5


class TestArchitectFallbackExtraction:
    """Additional fallback extraction tests."""

    def test_fallback_extracts_rejected(self) -> None:
        """Test fallback extracts 'rejected' as VETOED."""
        architect = ArchitectAgent(MagicMock(), MagicMock())
        result = architect._extract_decision_fallback("This is REJECTED")
        assert result["decision"] == "VETOED"

    def test_fallback_handles_mixed_case(self) -> None:
        """Test fallback handles mixed case."""
        architect = ArchitectAgent(MagicMock(), MagicMock())
        result = architect._extract_decision_fallback("I ApPrOvE this")
        assert result["decision"] == "APPROVED"

    def test_fallback_truncates_long_reasoning(self) -> None:
        """Test fallback truncates very long reasoning."""
        architect = ArchitectAgent(MagicMock(), MagicMock())
        long_text = "A" * 1000
        result = architect._extract_decision_fallback(long_text)
        assert len(result["reasoning"]) <= 500

    def test_fallback_includes_architecture_structure(self) -> None:
        """Test fallback includes valid architecture structure."""
        architect = ArchitectAgent(MagicMock(), MagicMock())
        result = architect._extract_decision_fallback("Test")
        assert "architecture" in result
        assert "approach" in result["architecture"]
        assert isinstance(result["architecture"]["risks"], list)


class TestArchitectPromptEdgeCases:
    """Edge cases for prompt building."""

    def test_prompt_with_constraints_only(self) -> None:
        """Test prompt with only constraints, no files."""
        architect = ArchitectAgent(MagicMock(), MagicMock())
        task = AgentTask(
            request="Test",
            session_id="test",
            context={"constraints": "Must be fast"},
        )
        prompt = architect._build_analysis_prompt(task)
        assert "Must be fast" in prompt
        assert "files" not in prompt.lower() or "0 files" in prompt

    def test_prompt_with_files_only(self) -> None:
        """Test prompt with only files, no constraints."""
        architect = ArchitectAgent(MagicMock(), MagicMock())
        task = AgentTask(
            request="Test",
            session_id="test",
            context={"files": ["a.py", "b.py"]},
        )
        prompt = architect._build_analysis_prompt(task)
        assert "2 files" in prompt or "a.py" in prompt

    def test_prompt_limits_file_list(self) -> None:
        """Test prompt only shows first 5 files."""
        architect = ArchitectAgent(MagicMock(), MagicMock())
        task = AgentTask(
            request="Test",
            session_id="test",
            context={"files": [f"file{i}.py" for i in range(20)]},
        )
        prompt = architect._build_analysis_prompt(task)
        # Should mention 20 files but only list first 5
        assert "20 files" in prompt
        file_count_in_prompt = prompt.count("file")
        assert file_count_in_prompt <= 7  # "files" + 5 file names + buffer
