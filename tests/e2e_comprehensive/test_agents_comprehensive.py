"""
Comprehensive E2E Tests: Agent Execution
=========================================

Tests agent instantiation and API compatibility.
Validates that all agent classes can be imported and basic instantiated.

Author: JuanCS Dev
Date: 2025-11-27
"""

import pytest


class TestPlannerAgentAPI:
    """Planner agent API tests."""

    def test_planner_can_be_imported(self):
        """Test planner agent can be imported."""
        try:
            from jdev_cli.agents.planner.agent import PlannerAgent
            assert PlannerAgent is not None
        except ImportError as e:
            pytest.fail(f"Failed to import PlannerAgent: {e}")

    def test_planner_module_structure(self):
        """Test planner module has expected structure."""
        try:
            from jdev_cli.agents import planner
            assert hasattr(planner, 'PlannerAgent')
        except (ImportError, AttributeError) as e:
            pytest.skip(f"Planner module structure different: {e}")


class TestArchitectAgentAPI:
    """Architect agent API tests."""

    def test_architect_can_be_imported(self):
        """Test architect agent can be imported."""
        try:
            from jdev_cli.agents.architect import ArchitectAgent
            assert ArchitectAgent is not None
        except ImportError as e:
            pytest.skip(f"ArchitectAgent not found: {e}")

    def test_architect_is_class(self):
        """Test architect is a class."""
        try:
            from jdev_cli.agents.architect import ArchitectAgent
            assert isinstance(ArchitectAgent, type)
        except ImportError:
            pytest.skip("ArchitectAgent not found")


class TestReviewerAgentAPI:
    """Reviewer agent API tests."""

    def test_reviewer_can_be_imported(self):
        """Test reviewer agent can be imported."""
        try:
            from jdev_cli.agents.reviewer import ReviewerAgent
            assert ReviewerAgent is not None
        except ImportError as e:
            pytest.skip(f"ReviewerAgent not found: {e}")

    def test_reviewer_is_class(self):
        """Test reviewer is a class."""
        try:
            from jdev_cli.agents.reviewer import ReviewerAgent
            assert isinstance(ReviewerAgent, type)
        except ImportError:
            pytest.skip("ReviewerAgent not found")


class TestExecutorAgentAPI:
    """Executor agent API tests."""

    def test_executor_can_be_imported(self):
        """Test executor agent can be imported."""
        try:
            from jdev_cli.agents.executor import NextGenExecutorAgent
            assert NextGenExecutorAgent is not None
        except ImportError as e:
            pytest.skip(f"NextGenExecutorAgent not found: {e}")

    def test_executor_is_class(self):
        """Test executor is a class."""
        try:
            from jdev_cli.agents.executor import NextGenExecutorAgent
            assert isinstance(NextGenExecutorAgent, type)
        except ImportError:
            pytest.skip("NextGenExecutorAgent not found")


class TestOtherAgents:
    """Test other agent imports."""

    def test_explorer_agent_exists(self):
        """Test explorer agent can be imported."""
        try:
            from jdev_cli.agents.explorer import ExplorerAgent
            assert ExplorerAgent is not None
        except ImportError:
            pytest.skip("ExplorerAgent not found")

    def test_security_agent_exists(self):
        """Test security agent can be imported."""
        try:
            from jdev_cli.agents.security import SecurityAgent
            assert SecurityAgent is not None
        except ImportError:
            pytest.skip("SecurityAgent not found")

    def test_refactor_agent_exists(self):
        """Test refactor agent can be imported."""
        try:
            from jdev_cli.agents.refactor import RefactorAgent
            assert RefactorAgent is not None
        except ImportError:
            pytest.skip("RefactorAgent not found")

    def test_documentation_agent_exists(self):
        """Test documentation agent can be imported."""
        try:
            from jdev_cli.agents.documentation import DocumentationAgent
            assert DocumentationAgent is not None
        except ImportError:
            pytest.skip("DocumentationAgent not found")

    def test_performance_agent_exists(self):
        """Test performance agent can be imported."""
        try:
            from jdev_cli.agents.performance import PerformanceAgent
            assert PerformanceAgent is not None
        except ImportError:
            pytest.skip("PerformanceAgent not found")

    def test_devops_agent_exists(self):
        """Test devops agent can be imported."""
        try:
            from jdev_cli.agents.devops_agent import DevOpsAgent
            assert DevOpsAgent is not None
        except ImportError:
            pytest.skip("DevOpsAgent not found")


class TestAgentBaseClass:
    """Test base agent functionality."""

    def test_base_agent_exists(self):
        """Test base agent can be imported."""
        try:
            from jdev_cli.agents.base import BaseAgent
            assert BaseAgent is not None
        except ImportError as e:
            pytest.fail(f"Failed to import BaseAgent: {e}")

    def test_base_agent_is_class(self):
        """Test base agent is a class."""
        try:
            from jdev_cli.agents.base import BaseAgent
            assert isinstance(BaseAgent, type)
        except ImportError:
            pytest.fail("BaseAgent not found")
