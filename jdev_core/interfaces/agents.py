"""
Agent Interfaces.

SCALE & SUSTAIN Phase 2.2 - Interface Extraction.

Defines interfaces for agent system:
- IAgent: Individual agent interface
- IAgentRouter: Request routing to agents

Author: JuanCS Dev
Date: 2025-11-26
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Any, List, Optional

from jdev_core.types import AgentRole


@dataclass
class AgentRouteResult:
    """Result of routing a query to an agent."""
    agent_name: str
    agent_role: AgentRole
    confidence: float  # 0.0 to 1.0
    reasoning: str
    fallback_agents: List[str] = field(default_factory=list)


@dataclass
class AgentContext:
    """Context provided to agents."""
    session_id: str
    user_message: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    tools_available: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IAgent(ABC):
    """
    Interface for individual agents.

    Agents are specialized AI personas that handle specific tasks.

    Example:
        class PlannerAgent(IAgent):
            @property
            def role(self) -> AgentRole:
                return AgentRole.PLANNER

            async def execute(self, context):
                async for chunk in self._plan(context):
                    yield chunk
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        pass

    @property
    @abstractmethod
    def role(self) -> AgentRole:
        """Agent role."""
        pass

    @property
    def description(self) -> str:
        """Agent description."""
        return f"{self.role.value} agent"

    @property
    def capabilities(self) -> List[str]:
        """List of capabilities this agent provides."""
        return []

    @abstractmethod
    async def execute(
        self,
        context: AgentContext
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute agent task.

        Args:
            context: Execution context

        Yields:
            Streaming chunks (type, data)
        """
        pass

    async def can_handle(self, query: str) -> float:
        """
        Check if agent can handle a query.

        Args:
            query: User query

        Returns:
            Confidence score 0.0 to 1.0
        """
        return 0.0

    async def initialize(self) -> None:
        """Initialize agent (optional)."""
        pass

    async def cleanup(self) -> None:
        """Cleanup agent resources (optional)."""
        pass


class IAgentRouter(ABC):
    """
    Interface for agent routing.

    Routes queries to appropriate agents based on intent.

    Example:
        router = MyAgentRouter(agents)
        result = await router.route("plan a feature for user auth")
        agent = router.get_agent(result.agent_name)
    """

    @abstractmethod
    async def route(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentRouteResult:
        """
        Route query to appropriate agent.

        Args:
            query: User query
            context: Optional context information

        Returns:
            Routing result with selected agent
        """
        pass

    @abstractmethod
    def register_agent(self, agent: IAgent) -> None:
        """Register an agent."""
        pass

    @abstractmethod
    def get_agent(self, name: str) -> Optional[IAgent]:
        """Get agent by name."""
        pass

    @abstractmethod
    def get_agents_by_role(self, role: AgentRole) -> List[IAgent]:
        """Get all agents with a role."""
        pass

    @abstractmethod
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        pass


class IAgentOrchestrator(ABC):
    """
    Interface for multi-agent orchestration.

    Coordinates execution across multiple agents.
    """

    @abstractmethod
    async def execute_workflow(
        self,
        request: str,
        agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a multi-agent workflow.

        Args:
            request: Workflow request
            agents: Optional list of agents to use

        Returns:
            Workflow execution result
        """
        pass

    @abstractmethod
    async def execute_parallel(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple agent tasks in parallel.

        Args:
            tasks: List of task definitions

        Returns:
            List of results
        """
        pass


__all__ = [
    'IAgent',
    'IAgentRouter',
    'IAgentOrchestrator',
    'AgentRouteResult',
    'AgentContext',
]
