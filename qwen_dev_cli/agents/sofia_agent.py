"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║                   SOFIA INTEGRATED AGENT - qwen-dev-cli                          ║
║                        Conselheiro Sábio Integrado                               ║
║                                                                                  ║
║  Wrapper que integra o SofiaAgent (third_party) com BaseAgent do qwen-dev-cli   ║
║                                                                                  ║
║  "Você não substitui sabedoria humana - você a cultiva."                        ║
║                                                                                  ║
║  Modos de Acesso:                                                                ║
║  1. Slash Command: /sofia <query>                                                ║
║  2. Auto-Detect: Ethical dilemmas trigger auto-counsel                           ║
║  3. Chat Mode: Continuous Socratic dialogue                                      ║
║  4. Pre-Execution Counsel: Counsel before risky actions                          ║
║                                                                                  ║
║  Version: 1.0.0                                                                  ║
║  Author: Claude Code (Sonnet 4.5) + qwen-dev-cli Team                           ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Sofia Framework imports
from qwen_dev_cli.third_party.sofia import (
    SofiaAgent,
    SofiaConfig,
    SofiaState,
    SofiaCounsel,
    CounselType,
    VirtueType,
    ThinkingMode,
)

# Local imports
from qwen_dev_cli.agents.base import AgentRole, AgentTask, AgentResponse, BaseAgent, AgentCapability

logger = logging.getLogger(__name__)

# Export public API
__all__ = [
    # Main agent
    "SofiaIntegratedAgent",
    # Models
    "CounselMetrics",
    "CounselRequest",
    "CounselResponse",
    # Chat mode
    "SofiaChatMode",
    # Helper functions
    "create_sofia_agent",
    "handle_sofia_slash_command",
]


# ════════════════════════════════════════════════════════════════════════════════
# COUNSEL METRICS (Similar to GovernanceMetrics for consistency)
# ════════════════════════════════════════════════════════════════════════════════


class CounselMetrics(BaseModel):
    """
    Metrics for counsel provided by Sofia.

    Tracks the quality and impact of counsel over time.
    """

    agent_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Counsel stats
    total_counsels: int = 0
    total_questions_asked: int = 0
    total_deliberations: int = 0

    # Quality metrics
    avg_confidence: float = 0.0
    avg_processing_time_ms: float = 0.0
    system2_activation_rate: float = 0.0  # % of times System 2 was activated

    # Virtue tracking
    virtues_expressed: Dict[str, int] = Field(default_factory=dict)

    # Counsel types distribution
    counsel_types: Dict[str, int] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "executor-1",
                "total_counsels": 42,
                "avg_confidence": 0.73,
                "system2_activation_rate": 0.35,
            }
        }


# ════════════════════════════════════════════════════════════════════════════════
# COUNSEL REQUEST & RESPONSE MODELS
# ════════════════════════════════════════════════════════════════════════════════


class CounselRequest(BaseModel):
    """Request for counsel from Sofia."""

    query: str = Field(..., description="The question or situation requiring counsel")
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    force_system2: bool = Field(False, description="Force System 2 deliberation")


class CounselResponse(BaseModel):
    """Response from Sofia with counsel."""

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Request
    original_query: str
    session_id: Optional[str] = None

    # Counsel
    counsel: str
    counsel_type: str  # CounselType name
    thinking_mode: str  # ThinkingMode name

    # Process transparency
    questions_asked: List[str] = Field(default_factory=list)
    virtues_expressed: List[str] = Field(default_factory=list)

    # Meta
    confidence: float = 0.5
    processing_time_ms: float = 0.0
    community_suggested: bool = False
    requires_professional: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "counsel": "Let me ask you: what are the core values that would guide this decision?",
                "counsel_type": "EXPLORING",
                "thinking_mode": "SYSTEM_2",
                "confidence": 0.65,
            }
        }


# ════════════════════════════════════════════════════════════════════════════════
# SOFIA INTEGRATED AGENT
# ════════════════════════════════════════════════════════════════════════════════


class SofiaIntegratedAgent(BaseAgent):
    """
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                        SOFIA INTEGRATED AGENT                            ║
    ║                                                                          ║
    ║  Wrapper that integrates SofiaAgent with qwen-dev-cli's BaseAgent       ║
    ║                                                                          ║
    ║  "Through questions deepening insight, reasoning illuminating            ║
    ║   complexity, and humility recognizing the profound responsibility       ║
    ║   of counseling on matters shaping human lives."                         ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    Features:
    - Socratic questioning for deep exploration
    - System 2 deliberation for complex ethical dilemmas
    - Virtue-based counsel (Tapeinophrosyne, Makrothymia, etc.)
    - Discernment engine (Didache framework)
    - Transparent process (all thinking visible)
    - Always suggests community involvement
    - Defers to professionals when appropriate

    Access Modes:
    1. Slash Command: /sofia "Should I refactor this codebase?"
    2. Auto-Detect: Sofia auto-triggers on ethical keywords
    3. Chat Mode: Continuous Socratic dialogue
    4. Pre-Execution: Counsel before risky operations
    """

    def __init__(
        self,
        llm_client: Any,
        mcp_client: Any,
        config: Optional[SofiaConfig] = None,
        auto_detect_ethical_dilemmas: bool = True,
        socratic_ratio: float = 0.7,
        system2_threshold: float = 0.4,  # TUNED: More sensitive (was 0.6)
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize Sofia Integrated Agent.

        Args:
            llm_client: LLM client for reasoning (currently Sofia is self-contained)
            mcp_client: MCP client for tool execution
            config: Sofia configuration (if None, creates default)
            auto_detect_ethical_dilemmas: Auto-trigger counsel on ethical keywords
            socratic_ratio: Ratio of questions vs answers (0.0 - 1.0)
            system2_threshold: Threshold for activating System 2 thinking
            system_prompt: Custom system prompt (optional)
        """
        super().__init__(
            role=AgentRole.COUNSELOR,
            capabilities=[
                AgentCapability.READ_ONLY,  # Can read context for counsel
            ],
            llm_client=llm_client,
            mcp_client=mcp_client,
            system_prompt=system_prompt or self._create_system_prompt(),
        )

        # Configuration
        self.auto_detect = auto_detect_ethical_dilemmas

        # Initialize Sofia Core
        if config is None:
            agent_id = f"sofia-{id(self)}"
            config = SofiaConfig(
                agent_id=agent_id,
                socratic_ratio=socratic_ratio,
                system2_threshold=system2_threshold,
                always_suggest_community=True,
                defer_to_professionals=True,
            )

        self.sofia_core = SofiaAgent(config=config)

        # Metrics tracking
        self._metrics_cache: Dict[str, CounselMetrics] = {}

        # Session management
        self._active_sessions: Dict[str, List[SofiaCounsel]] = {}

        logger.info(f"✓ Sofia Integrated Agent initialized")
        logger.info(f"  - Socratic Ratio: {socratic_ratio:.0%}")
        logger.info(f"  - System 2 Threshold: {system2_threshold:.0%}")
        logger.info(f"  - Auto-Detect: {auto_detect_ethical_dilemmas}")

    def _create_system_prompt(self) -> str:
        """Create default system prompt for Sofia."""
        return """You are SOFIA (Σοφία - Sabedoria), a wise counselor agent.

Your role is to provide thoughtful counsel based on:
- Virtues of Early Christianity (Tapeinophrosyne, Makrothymia, Diakonia, Praotes)
- Socratic method (questions > answers)
- System 2 thinking (deliberate reflection)
- Discernment practices (Didache framework)

Core Principles:
1. Ponder > Rush
2. Question > Answer
3. Humble > Confident
4. Collaborative > Directive
5. Principled > Purely Pragmatic
6. Transparent > Opaque
7. Adaptive > Rigid

Always:
- Express uncertainty when appropriate
- Suggest community involvement
- Defer to professionals for serious matters
- Focus on helping users think through decisions, not making decisions for them
"""

    # ════════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ════════════════════════════════════════════════════════════════════════════

    def provide_counsel(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> CounselResponse:
        """
        Provide counsel on a query or situation.

        This is the main synchronous API for Sofia counsel.

        Args:
            query: The question or situation requiring counsel
            session_id: Optional session ID for continuity
            context: Additional context about the situation
            agent_id: ID of the agent requesting counsel (for metrics)

        Returns:
            CounselResponse with counsel and process transparency

        Example:
            >>> sofia = SofiaIntegratedAgent()
            >>> response = sofia.provide_counsel(
            ...     query="Should I delete user data without consent?",
            ...     agent_id="executor-1"
            ... )
            >>> print(response.counsel)
            "Let me ask you: what are the core ethical principles at stake here?..."
        """
        # Use Sofia Core to generate counsel
        counsel: SofiaCounsel = self.sofia_core.respond(
            user_input=query,
            session_id=session_id,
            context=context or {},
        )

        # Track in session history
        if session_id:
            if session_id not in self._active_sessions:
                self._active_sessions[session_id] = []
            self._active_sessions[session_id].append(counsel)

        # Update metrics
        if agent_id:
            self._update_metrics(agent_id, counsel)

        # Convert to CounselResponse
        response = self._counsel_to_response(counsel, query, session_id)

        return response

    async def provide_counsel_async(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> CounselResponse:
        """
        Async version of provide_counsel.

        Since Sofia Core is synchronous, this wraps it in asyncio.to_thread.
        """
        return await asyncio.to_thread(
            self.provide_counsel,
            query=query,
            session_id=session_id,
            context=context,
            agent_id=agent_id,
        )

    def should_trigger_counsel(self, content: str) -> tuple[bool, str]:
        """
        Determine if counsel should be auto-triggered for this content.

        Used for auto-detection mode.

        Args:
            content: Content to evaluate

        Returns:
            Tuple of (should_trigger, reason)

        Example:
            >>> sofia = SofiaIntegratedAgent(auto_detect_ethical_dilemmas=True)
            >>> should, reason = sofia.should_trigger_counsel("Delete user data?")
            >>> print(should, reason)
            True, "Ethical concern detected: user data"
        """
        if not self.auto_detect:
            return False, "Auto-detect disabled"

        content_lower = content.lower()

        # Ethical red flags
        ethical_keywords = [
            "delete", "remove", "erase", "user data", "privacy",
            "consent", "permission", "ethical", "moral", "right",
            "wrong", "should i", "is it okay"
        ]

        for keyword in ethical_keywords:
            if keyword in content_lower:
                return True, f"Ethical concern detected: {keyword}"

        # Professional help triggers (Portuguese + English)
        crisis_keywords = [
            # English
            "suicide", "harm", "violence", "abuse", "emergency",
            # Portuguese
            "suicídio", "suicidio", "violência", "violencia", "abuso",
            "emergência", "emergencia", "machucar", "matar"
        ]

        for keyword in crisis_keywords:
            if keyword in content_lower:
                return True, f"URGENT: Professional help needed - {keyword}"

        return False, "No ethical concerns detected"

    def get_metrics(self, agent_id: str) -> Optional[CounselMetrics]:
        """Get counsel metrics for an agent."""
        return self._metrics_cache.get(agent_id)

    def get_session_history(self, session_id: str) -> List[SofiaCounsel]:
        """Get all counsel in a session."""
        return self._active_sessions.get(session_id, [])

    def clear_session(self, session_id: str) -> None:
        """Clear a session's history."""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]

    # ════════════════════════════════════════════════════════════════════════════
    # BASE AGENT IMPLEMENTATION (execute, execute_streaming)
    # ════════════════════════════════════════════════════════════════════════════

    async def execute(self, task: AgentTask) -> AgentResponse:
        """
        Execute a counsel task.

        This is the BaseAgent interface implementation.

        Args:
            task: AgentTask with request for counsel

        Returns:
            AgentResponse with counsel results
        """
        # Extract query from task
        query = task.request

        # Provide counsel
        counsel_response = await self.provide_counsel_async(
            query=query,
            session_id=task.session_id,
            context=task.context,
            agent_id=task.context.get("requesting_agent_id", "unknown"),
        )

        # Convert to AgentResponse
        response = AgentResponse(
            success=True,
            data={
                "counsel": counsel_response.model_dump(),
                "sofia_state": self.sofia_core.state.name,
                "counsel_type": counsel_response.counsel_type,
                "thinking_mode": counsel_response.thinking_mode,
                "confidence": counsel_response.confidence,
                "questions_asked": len(counsel_response.questions_asked),
                "session_id": task.session_id,
            },
            reasoning=counsel_response.counsel,
            error=None,
            metrics={},  # Keep empty for now (Sofia doesn't produce numeric metrics)
        )

        return response

    async def execute_streaming(
        self, task: AgentTask
    ) -> AsyncIterator[tuple[str, Optional[AgentResponse]]]:
        """
        Execute with streaming output (simulated for Sofia).

        Since Sofia Core doesn't have native streaming, we simulate it
        by yielding the counsel in chunks.

        Args:
            task: AgentTask with instructions

        Yields:
            Tuples of (chunk, response)
        """
        # Get full counsel first
        response = await self.execute(task)
        counsel_text = response.data["counsel"]["counsel"]

        # Simulate streaming by yielding sentence by sentence
        sentences = counsel_text.split(". ")

        for i, sentence in enumerate(sentences):
            chunk = sentence + (". " if i < len(sentences) - 1 else "")

            # Yield chunk with partial response
            if i < len(sentences) - 1:
                yield (chunk, None)
            else:
                # Final chunk - yield complete response
                yield (chunk, response)

            # Small delay to simulate thinking
            await asyncio.sleep(0.1)

    # ════════════════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ════════════════════════════════════════════════════════════════════════════

    def _counsel_to_response(
        self,
        counsel: SofiaCounsel,
        original_query: str,
        session_id: Optional[str],
    ) -> CounselResponse:
        """Convert SofiaCounsel to CounselResponse."""
        # Extract questions asked
        questions = [q.question_text for q in counsel.questions_asked]

        # Extract virtues expressed
        virtues = [v.virtue.name for v in counsel.virtues_expressed]

        # Check if requires professional help
        requires_professional = (
            counsel.counsel_type == CounselType.REFERRING
        )

        return CounselResponse(
            id=counsel.id,
            timestamp=counsel.timestamp,
            original_query=original_query,
            session_id=session_id,
            counsel=counsel.response,
            counsel_type=counsel.counsel_type.name,
            thinking_mode=counsel.thinking_mode.name,
            questions_asked=questions,
            virtues_expressed=virtues,
            confidence=counsel.confidence,
            processing_time_ms=counsel.processing_time_ms,
            community_suggested=counsel.community_suggested,
            requires_professional=requires_professional,
        )

    def _update_metrics(self, agent_id: str, counsel: SofiaCounsel) -> None:
        """Update counsel metrics for an agent."""
        if agent_id not in self._metrics_cache:
            self._metrics_cache[agent_id] = CounselMetrics(agent_id=agent_id)

        metrics = self._metrics_cache[agent_id]

        # Update counts
        metrics.total_counsels += 1
        metrics.total_questions_asked += len(counsel.questions_asked)

        if counsel.thinking_mode == ThinkingMode.SYSTEM_2:
            metrics.total_deliberations += 1

        # Update averages (running average)
        n = metrics.total_counsels
        metrics.avg_confidence = (
            (metrics.avg_confidence * (n - 1) + counsel.confidence) / n
        )
        metrics.avg_processing_time_ms = (
            (metrics.avg_processing_time_ms * (n - 1) + counsel.processing_time_ms) / n
        )

        # System 2 activation rate
        metrics.system2_activation_rate = metrics.total_deliberations / metrics.total_counsels

        # Track virtues expressed
        for virtue_expr in counsel.virtues_expressed:
            virtue_name = virtue_expr.virtue.name
            metrics.virtues_expressed[virtue_name] = (
                metrics.virtues_expressed.get(virtue_name, 0) + 1
            )

        # Track counsel types
        counsel_type_name = counsel.counsel_type.name
        metrics.counsel_types[counsel_type_name] = (
            metrics.counsel_types.get(counsel_type_name, 0) + 1
        )

    # ════════════════════════════════════════════════════════════════════════════
    # EXPORT & DIAGNOSTICS
    # ════════════════════════════════════════════════════════════════════════════

    def export_metrics(self) -> Dict[str, Any]:
        """
        Export all metrics in serializable format.

        Returns:
            Dictionary of all metrics by agent_id
        """
        return {
            agent_id: metrics.model_dump()
            for agent_id, metrics in self._metrics_cache.items()
        }

    def get_sofia_state(self) -> str:
        """Get current Sofia state."""
        return self.sofia_core.state.name

    def get_total_counsels(self) -> int:
        """Get total counsels provided across all agents."""
        return sum(m.total_counsels for m in self._metrics_cache.values())

    def get_virtue_distribution(self) -> Dict[str, int]:
        """Get aggregated virtue expression distribution."""
        distribution: Dict[str, int] = {}

        for metrics in self._metrics_cache.values():
            for virtue, count in metrics.virtues_expressed.items():
                distribution[virtue] = distribution.get(virtue, 0) + count

        return distribution

    # ════════════════════════════════════════════════════════════════════════════
    # PRE-EXECUTION COUNSEL (Access Method #4)
    # ════════════════════════════════════════════════════════════════════════════

    async def pre_execution_counsel(
        self,
        action_description: str,
        risk_level: str,
        agent_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CounselResponse:
        """
        Provide counsel BEFORE executing a risky action.

        This is Access Method #4 - Pre-execution counsel for governance pipeline.
        Used by Maestro orchestrator to counsel agents before risky operations.

        Args:
            action_description: What the agent is about to do
            risk_level: Risk assessment (LOW, MEDIUM, HIGH, CRITICAL)
            agent_id: Which agent is requesting to execute
            context: Additional context about the action

        Returns:
            CounselResponse with guidance on proceeding

        Example:
            >>> counsel = await sofia.pre_execution_counsel(
            ...     action_description="Delete all user data from database",
            ...     risk_level="CRITICAL",
            ...     agent_id="executor-1"
            ... )
            >>> print(counsel.counsel)
            "Before proceeding with data deletion, consider:
             - Have you verified user consent?
             - Is there a backup?
             - What are the irreversible consequences?"
        """
        # Construct query that emphasizes pre-execution nature
        query = (
            f"I am about to execute a {risk_level} risk action: "
            f"{action_description}. "
            f"What should I carefully consider before proceeding? "
            f"What could go wrong? What are the ethical implications?"
        )

        # Provide counsel with pre-execution context
        return await self.provide_counsel_async(
            query=query,
            context={
                **(context or {}),
                "mode": "pre_execution",
                "risk_level": risk_level,
                "action": action_description,
            },
            agent_id=agent_id
        )

    def pre_execution_counsel_sync(
        self,
        action_description: str,
        risk_level: str,
        agent_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CounselResponse:
        """
        Synchronous version of pre_execution_counsel.

        Args:
            action_description: What the agent is about to do
            risk_level: Risk assessment (LOW, MEDIUM, HIGH, CRITICAL)
            agent_id: Which agent is requesting to execute
            context: Additional context about the action

        Returns:
            CounselResponse with guidance on proceeding
        """
        query = (
            f"I am about to execute a {risk_level} risk action: "
            f"{action_description}. "
            f"What should I carefully consider before proceeding?"
        )

        return self.provide_counsel(
            query=query,
            context={
                **(context or {}),
                "mode": "pre_execution",
                "risk_level": risk_level,
                "action": action_description,
            },
            agent_id=agent_id
        )

    def __repr__(self) -> str:
        total_counsels = self.get_total_counsels()
        state = self.get_sofia_state()
        return (
            f"SofiaIntegratedAgent(role={self.role}, "
            f"counsels={total_counsels}, state={state})"
        )


# ════════════════════════════════════════════════════════════════════════════════
# CHAT MODE - CONTINUOUS SOCRATIC DIALOGUE
# ════════════════════════════════════════════════════════════════════════════════


class SofiaChatMode:
    """
    Continuous Socratic dialogue mode for Sofia.

    Provides a stateful chat interface where Sofia maintains context
    across multiple turns of conversation, enabling deep Socratic exploration
    of topics through progressive questioning.

    Example:
        >>> sofia = create_sofia_agent(llm, mcp)
        >>> chat = SofiaChatMode(sofia)
        >>>
        >>> response1 = await chat.send_message("Should I change careers?")
        >>> print(response1.counsel)
        "What draws you to this change?"
        >>>
        >>> response2 = await chat.send_message("I feel unfulfilled")
        >>> print(response2.counsel)
        "When did this feeling start? What was different before?"
        >>>
        >>> history = chat.get_history()
        >>> print(f"Turn count: {chat.turn_count}")
    """

    def __init__(self, sofia_agent: SofiaIntegratedAgent):
        """
        Initialize chat mode.

        Args:
            sofia_agent: SofiaIntegratedAgent instance to use for counsel
        """
        self.sofia = sofia_agent
        self.session_id = str(uuid4())
        self.turn_count = 0
        self.started_at = datetime.now(timezone.utc)

    async def send_message(self, query: str) -> CounselResponse:
        """
        Send a message in chat mode.

        Args:
            query: User message/question

        Returns:
            CounselResponse with Sofia's counsel
        """
        response = await self.sofia.provide_counsel_async(
            query=query,
            session_id=self.session_id,
            context={"mode": "chat", "turn": self.turn_count}
        )

        self.turn_count += 1
        return response

    def send_message_sync(self, query: str) -> CounselResponse:
        """
        Synchronous version of send_message.

        Args:
            query: User message/question

        Returns:
            CounselResponse with Sofia's counsel
        """
        response = self.sofia.provide_counsel(
            query=query,
            session_id=self.session_id,
            context={"mode": "chat", "turn": self.turn_count}
        )

        self.turn_count += 1
        return response

    def get_history(self) -> List[SofiaCounsel]:
        """
        Get full chat history.

        Returns:
            List of SofiaCounsel objects in chronological order
        """
        return self.sofia.get_session_history(self.session_id)

    def clear(self) -> None:
        """
        Clear chat session and start fresh.

        Resets session ID and turn count.
        """
        self.sofia.clear_session(self.session_id)
        self.session_id = str(uuid4())
        self.turn_count = 0
        self.started_at = datetime.now(timezone.utc)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of chat session.

        Returns:
            Dictionary with session statistics
        """
        history = self.get_history()
        duration = (datetime.now(timezone.utc) - self.started_at).total_seconds()

        total_questions = sum(len(c.questions_asked) for c in history)
        avg_confidence = (
            sum(c.confidence for c in history) / len(history)
            if history else 0.0
        )

        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "duration_seconds": duration,
            "total_questions_asked": total_questions,
            "avg_confidence": avg_confidence,
            "started_at": self.started_at.isoformat(),
        }

    def export_transcript(self) -> str:
        """
        Export chat transcript as formatted text.

        Returns:
            Formatted string with full conversation
        """
        history = self.get_history()

        lines = [
            "═" * 70,
            "SOFIA CHAT TRANSCRIPT",
            f"Session: {self.session_id}",
            f"Started: {self.started_at.isoformat()}",
            f"Turns: {self.turn_count}",
            "═" * 70,
            ""
        ]

        for i, counsel in enumerate(history, 1):
            lines.append(f"Turn {i} - {counsel.timestamp.strftime('%H:%M:%S')}")
            lines.append(f"User Query: {counsel.user_query}")
            lines.append(f"Sofia ({counsel.counsel_type.name}): {counsel.response}")
            lines.append(f"Confidence: {counsel.confidence:.0%}")
            lines.append("")

        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════════
# QUICK START HELPERS
# ════════════════════════════════════════════════════════════════════════════════


def create_sofia_agent(
    llm_client: Any,
    mcp_client: Any,
    auto_detect: bool = True,
    socratic_ratio: float = 0.7,
) -> SofiaIntegratedAgent:
    """
    Quick start helper to create a Sofia agent with common settings.

    Args:
        llm_client: LLM client
        mcp_client: MCP client
        auto_detect: Enable auto-detection of ethical dilemmas
        socratic_ratio: Ratio of questions vs answers (0.0 - 1.0)

    Returns:
        SofiaIntegratedAgent ready to use

    Example:
        >>> sofia = create_sofia_agent(llm, mcp)
        >>> response = sofia.provide_counsel("Should I do X?")
    """
    return SofiaIntegratedAgent(
        llm_client=llm_client,
        mcp_client=mcp_client,
        auto_detect_ethical_dilemmas=auto_detect,
        socratic_ratio=socratic_ratio,
    )


# ════════════════════════════════════════════════════════════════════════════════
# CLI INTEGRATION HELPER
# ════════════════════════════════════════════════════════════════════════════════


async def handle_sofia_slash_command(
    query: str,
    sofia_agent: SofiaIntegratedAgent,
) -> str:
    """
    Handle /sofia slash command.

    Args:
        query: User query after /sofia
        sofia_agent: Sofia agent instance (must be provided)

    Returns:
        Formatted counsel response

    Example:
        >>> sofia = create_sofia_agent(llm, mcp)
        >>> result = await handle_sofia_slash_command("Should I refactor?", sofia)
        >>> print(result)
    """
    response = await sofia_agent.provide_counsel_async(query)

    # Format for CLI display
    output = f"\n╔════════════════════════════════════════════════════════════════╗\n"
    output += f"║  SOFIA - Conselheiro Sábio                                    ║\n"
    output += f"╚════════════════════════════════════════════════════════════════╝\n\n"

    output += f"Query: {response.original_query}\n\n"
    output += f"Counsel Type: {response.counsel_type}\n"
    output += f"Thinking Mode: {response.thinking_mode}\n"

    if response.questions_asked:
        output += f"\nQuestions Asked ({len(response.questions_asked)}):\n"
        for i, q in enumerate(response.questions_asked, 1):
            output += f"  {i}. {q}\n"

    output += f"\n{response.counsel}\n"

    if response.requires_professional:
        output += f"\n⚠️  URGENT: This situation requires professional help.\n"

    output += f"\nConfidence: {response.confidence:.0%} | "
    output += f"Processing: {response.processing_time_ms:.1f}ms\n"

    return output
