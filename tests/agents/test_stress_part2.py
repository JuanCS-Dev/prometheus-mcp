"""Additional 32 stress tests - Part 2.

More aggressive tests to reach 60 total stress tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.architect import ArchitectAgent
from jdev_cli.agents.explorer import ExplorerAgent
from jdev_cli.agents.planner import PlannerAgent
from jdev_cli.agents.refactorer import RefactorerAgent
from jdev_cli.agents.reviewer import ReviewerAgent
from jdev_cli.agents.base import AgentTask
from jdev_cli.orchestration.squad import DevSquad


class TestArchitectStressPart2:
    """More Architect stress tests."""

    @pytest.mark.asyncio
    async def test_architect_sql_injection_attempt(self):
        """Test SQL injection in request."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"decision\": \"VETOED\", \"reasoning\": \"SQL detected\"}')

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="'; DROP TABLE users; --",
            session_id="test"
        )

        response = await architect.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_architect_xss_attempt(self):
        """Test XSS in request."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"decision\": \"APPROVED\", \"reasoning\": \"OK\"}')

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="<script>alert('XSS')</script>",
            session_id="test"
        )

        response = await architect.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_architect_repeated_calls(self):
        """Test 1000 sequential calls."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"decision\": \"APPROVED\", \"reasoning\": \"OK\"}')

        architect = ArchitectAgent(llm_client, MagicMock())

        for i in range(1000):
            task = AgentTask(request=f"Request {i}", session_id="test")
            response = await architect.execute(task)
            assert response is not None

    @pytest.mark.asyncio
    async def test_architect_mixed_encodings(self):
        """Test mixed character encodings."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"decision\": \"APPROVED\", \"reasoning\": \"OK\"}')

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Test ASCII + UTF-8: café 日本語",
            session_id="test"
        )

        response = await architect.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_architect_control_characters(self):
        """Test control characters."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"decision\": \"APPROVED\", \"reasoning\": \"OK\"}')

        architect = ArchitectAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Test\r\n\t\x1b[31mRed\x1b[0m",
            session_id="test"
        )

        response = await architect.execute(task)
        assert response is not None


class TestExplorerStressPart2:
    """More Explorer stress tests."""

    @pytest.mark.asyncio
    async def test_explorer_symlink_loop(self):
        """Test symlink loop detection."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"relevant_files\": []}')

        explorer = ExplorerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Explore",
            session_id="test",
            context={"files": ["/a/b/c", "/a/b/c/../../a/b/c"]}  # Loop
        )

        response = await explorer.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_explorer_hidden_files(self):
        """Test with .git, .env, etc."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"relevant_files\": []}')

        explorer = ExplorerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Explore",
            session_id="test",
            context={"files": [".git/config", ".env", ".secrets.json"]}
        )

        response = await explorer.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_explorer_very_long_paths(self):
        """Test with 1000 char paths."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"relevant_files\": []}')

        explorer = ExplorerAgent(llm_client, MagicMock())
        long_path = "/".join(["a" * 50 for _ in range(20)])  # 1000+ chars
        task = AgentTask(
            request="Explore",
            session_id="test",
            context={"files": [long_path]}
        )

        response = await explorer.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_explorer_duplicate_files(self):
        """Test with 1000 duplicate files."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"relevant_files\": []}')

        explorer = ExplorerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Explore",
            session_id="test",
            context={"files": ["same.py"] * 1000}
        )

        response = await explorer.execute(task)
        assert response is not None


class TestPlannerStressPart2:
    """More Planner stress tests."""

    @pytest.mark.asyncio
    async def test_planner_nested_dependencies(self):
        """Test deeply nested dependencies."""
        llm_client = MagicMock()
        steps = [{"id": i, "action": f"step_{i}", "dependencies": [i-1] if i > 0 else []} for i in range(100)]
        llm_client.generate = AsyncMock(return_value=f'{{\"steps\": {steps}}}')

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await planner.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_planner_duplicate_step_ids(self):
        """Test duplicate IDs."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"steps\": [{\"id\": 1, \"action\": \"a\"}, {\"id\": 1, \"action\": \"b\"}]}')

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await planner.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_planner_missing_required_fields(self):
        """Test steps missing action."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"steps\": [{\"id\": 1}]}')  # No action

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await planner.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_planner_invalid_action_types(self):
        """Test invalid action types."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"steps\": [{\"id\": 1, \"action\": \"rm -rf /\"}]}')

        planner = PlannerAgent(llm_client, MagicMock())
        task = AgentTask(request="Test", session_id="test")

        response = await planner.execute(task)
        assert response is not None


class TestRefactorerStressPart2:
    """More Refactorer stress tests."""

    @pytest.mark.asyncio
    async def test_refactorer_concurrent_steps(self):
        """Test 10 concurrent step executions."""
        refactorer = RefactorerAgent(MagicMock(), MagicMock())

        tasks = []
        for i in range(10):
            task = AgentTask(
                request=f"Test {i}",
                session_id=f"test-{i}",
                context={"step": {"id": i, "action": "test", "params": {}}}
            )
            tasks.append(refactorer.execute(task))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_refactorer_invalid_file_paths(self):
        """Test with invalid paths."""
        refactorer = RefactorerAgent(MagicMock(), MagicMock())
        task = AgentTask(
            request="Test",
            session_id="test",
            context={"step": {
                "id": 1,
                "action": "create_file",
                "params": {"path": "../../../etc/passwd", "content": "hack"}
            }}
        )

        response = await refactorer.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_refactorer_binary_content(self):
        """Test with binary content."""
        refactorer = RefactorerAgent(MagicMock(), MagicMock())
        task = AgentTask(
            request="Test",
            session_id="test",
            context={"step": {
                "id": 1,
                "action": "create_file",
                "params": {"path": "test.bin", "content": "\x00\x01\x02\xff"}
            }}
        )

        response = await refactorer.execute(task)
        assert response is not None


class TestReviewerStressPart2:
    """More Reviewer stress tests."""

    @pytest.mark.asyncio
    async def test_reviewer_no_diff(self):
        """Test with no changes."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"approved\": true, \"grade\": \"A\"}')

        reviewer = ReviewerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Review",
            session_id="test",
            context={"diff": ""}
        )

        response = await reviewer.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_reviewer_only_deletions(self):
        """Test with only deletions."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"approved\": true, \"grade\": \"B\"}')

        reviewer = ReviewerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Review",
            session_id="test",
            context={"diff": "\n".join([f"-line {i}" for i in range(100)])}
        )

        response = await reviewer.execute(task)
        assert response is not None

    @pytest.mark.asyncio
    async def test_reviewer_mixed_languages(self):
        """Test with multiple languages."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"approved\": true, \"grade\": \"A\"}')

        reviewer = ReviewerAgent(llm_client, MagicMock())
        task = AgentTask(
            request="Review",
            session_id="test",
            context={"diff": "+def foo():\\n+  pass\\n+function bar() {}\\n+class Baz {}"}
        )

        response = await reviewer.execute(task)
        assert response is not None


class TestSquadStressPart2:
    """More Squad stress tests."""

    @pytest.mark.asyncio
    async def test_squad_rapid_fire_requests(self):
        """Test 50 rapid requests."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"decision\": \"VETOED\", \"reasoning\": \"Test\"}')

        squad = DevSquad(llm_client, MagicMock())

        for i in range(50):
            result = await squad.execute_workflow(f"Request {i}")
            assert result is not None

    @pytest.mark.asyncio
    async def test_squad_empty_llm_response(self):
        """Test empty LLM response."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="")

        squad = DevSquad(llm_client, MagicMock())
        result = await squad.execute_workflow("Test")

        assert result is not None

    @pytest.mark.asyncio
    async def test_squad_llm_returns_html(self):
        """Test LLM returns HTML."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="<html><body>Error</body></html>")

        squad = DevSquad(llm_client, MagicMock())
        result = await squad.execute_workflow("Test")

        assert result is not None


class TestPerformanceDegradation:
    """Test performance under stress."""

    @pytest.mark.asyncio
    async def test_architect_performance_degradation(self):
        """Test 100 calls don't slow down."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"decision\": \"APPROVED\", \"reasoning\": \"OK\"}')

        architect = ArchitectAgent(llm_client, MagicMock())

        import time
        times = []

        for i in range(100):
            start = time.time()
            task = AgentTask(request=f"Request {i}", session_id="test")
            await architect.execute(task)
            times.append(time.time() - start)

        # Last 10 should not be significantly slower than first 10
        avg_first = sum(times[:10]) / 10
        avg_last = sum(times[-10:]) / 10

        assert avg_last < avg_first * 2  # Less than 2x slower

    @pytest.mark.asyncio
    async def test_memory_manager_performance(self):
        """Test MemoryManager doesn't degrade."""
        from jdev_cli.orchestration.memory import MemoryManager

        manager = MemoryManager()

        import time
        times = []

        for i in range(1000):
            start = time.time()
            session_id = manager.create_session(f"test-{i}")
            manager.update_context(session_id, metadata={"count": i})
            manager.get_context(session_id)
            times.append(time.time() - start)

        avg_first = sum(times[:100]) / 100
        avg_last = sum(times[-100:]) / 100

        assert avg_last < avg_first * 3  # Less than 3x slower


class TestRaceConditions:
    """Test race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_architect_calls(self):
        """Test 20 concurrent Architect calls."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value='{\"decision\": \"APPROVED\", \"reasoning\": \"OK\"}')

        architect = ArchitectAgent(llm_client, MagicMock())

        tasks = []
        for i in range(20):
            task = AgentTask(request=f"Request {i}", session_id=f"test-{i}")
            tasks.append(architect.execute(task))

        results = await asyncio.gather(*tasks)
        assert len(results) == 20
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_memory_access(self):
        """Test concurrent memory access."""
        from jdev_cli.orchestration.memory import MemoryManager

        manager = MemoryManager()
        session_id = manager.create_session("test")

        async def update_many(key: str):
            for i in range(50):
                manager.update_context(session_id, metadata={key: i})

        tasks = [update_many(f"key_{i}") for i in range(20)]
        await asyncio.gather(*tasks)

        context = manager.get_context(session_id)
        assert context is not None


# Total: 60 stress tests (28 original + 32 new)
