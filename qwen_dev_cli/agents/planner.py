"""
PlannerAgent v6.0: "Espetacular" Edition (Nov 2025)

Revolutionary features based on Claude/Anthropic's 2025 best practices:
    ✓ GOAP (Goal-Oriented Action Planning) - Used in F.E.A.R. AI
    ✓ Multi-Agent Swarm Orchestration (Queen-Led Coordination)
    ✓ Dependency Graph with Parallel Execution Detection
    ✓ Context Isolation per Sub-Agent (Anthropic SDK Pattern)
    ✓ Checkpoint/Rollback Strategy (Production Safety)
    ✓ Cost-Based Path Optimization (Dijkstra's Algorithm)
    ✓ Fork-Join Patterns for Scalability
    ✓ Observability Hooks (OpenTelemetry Ready)

NEW in v6.0 (Inspired by Claude Code, Cursor, Devin):
    ✓ Interactive Clarifying Questions (Cursor 2.1 pattern)
    ✓ plan.md Artifact Generation (Claude Code pattern)
    ✓ Confidence Ratings per Step (Devin pattern)
    ✓ Read-Only Exploration Mode (Claude Plan Mode)

NEW in v6.1 (Verbalized Sampling - Zhang et al. 2025):
    ✓ Multi-Plan Generation (Standard/Accelerator/Lateral)
    ✓ Verbalized Probabilities (P(Success), P(Friction), P(Quality))
    ✓ Risk/Reward Scoring with automatic recommendation
    ✓ Comparison Matrix for plan selection

Architecture inspired by:
- Anthropic Claude SDK Best Practices (2025)
- Claude-Flow v2.7 Hive-Mind Intelligence
- GOAP Planning Systems (F.E.A.R., STRIPS)
- Multi-Agent Orchestration Patterns
- Cursor AI Plan Mode (Nov 2025)
- Devin AI Planning System (2025)

References:
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview
- Claude Code: Best practices for agentic coding (2025)
- Building agents with the Claude Agent SDK (2025)
- Zhang et al. (2025): Verbalized Sampling for Planning
"""

import asyncio
import json
import re
import heapq
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ValidationError, field_validator

from .base import (
    AgentCapability,
    AgentResponse,
    AgentRole,
    AgentTask,
    BaseAgent,
)

# ============================================================================
# ENHANCED DATA MODELS - Enterprise Grade
# ============================================================================

class ExecutionStrategy(str, Enum):
    """Execution patterns for multi-agent coordination"""
    SEQUENTIAL = "sequential"      # One after another (dependencies)
    PARALLEL = "parallel"          # All at once (no dependencies)
    FORK_JOIN = "fork-join"        # Parallel + merge at end
    PIPELINE = "pipeline"          # Stream output between agents
    CONDITIONAL = "conditional"    # Based on runtime conditions

class AgentPriority(str, Enum):
    CRITICAL = "critical"  # Must complete for success
    HIGH = "high"          # Important but can continue
    MEDIUM = "medium"      # Nice to have
    LOW = "low"            # Optional enhancement

class CheckpointType(str, Enum):
    VALIDATION = "validation"      # Validate before continuing
    ROLLBACK = "rollback"          # Can rollback to here
    DECISION = "decision"          # Decision point for branching


# ============================================================================
# NEW v6.0: CLARIFYING QUESTIONS (Cursor 2.1 Pattern)
# ============================================================================

class ClarifyingQuestion(BaseModel):
    """
    Interactive question to gather user context before planning.

    Inspired by Cursor 2.1's clarifying questions feature that asks
    2-3 targeted questions before generating a plan.
    """
    id: str = Field(default_factory=lambda: f"q-{uuid.uuid4().hex[:8]}")
    question: str = Field(..., description="The question to ask the user")
    category: str = Field(default="general", description="scope|approach|constraints|preferences")
    options: List[str] = Field(default_factory=list, description="Suggested answers (optional)")
    required: bool = Field(default=False, description="Must be answered before planning")
    default: Optional[str] = Field(default=None, description="Default if user skips")


class ClarificationResponse(BaseModel):
    """User's response to clarifying questions"""
    question_id: str
    answer: str
    skipped: bool = False


class PlanningMode(str, Enum):
    """
    Planning modes inspired by Claude Code Plan Mode.

    EXPLORATION: Read-only, gather context, no modifications
    PLANNING: Generate plan, await approval
    EXECUTION: Execute approved plan
    """
    EXPLORATION = "exploration"  # Read-only exploration (Claude Plan Mode)
    PLANNING = "planning"        # Generate plan
    EXECUTION = "execution"      # Execute plan


# ============================================================================
# NEW v6.0: CONFIDENCE RATINGS (Devin Pattern)
# ============================================================================

class ConfidenceLevel(str, Enum):
    """Confidence levels for plan steps (Devin-inspired)"""
    CERTAIN = "certain"      # 0.9-1.0: Well-understood, low risk
    CONFIDENT = "confident"  # 0.7-0.9: Good understanding, manageable risk
    MODERATE = "moderate"    # 0.5-0.7: Some uncertainty, may need adjustment
    LOW = "low"              # 0.3-0.5: Significant uncertainty
    SPECULATIVE = "speculative"  # 0.0-0.3: Best guess, high risk


@dataclass
class StepConfidence:
    """
    Confidence rating for a planning step.

    Inspired by Devin's confidence ratings that help users
    understand which parts of a plan are more reliable.
    """
    score: float  # 0.0 to 1.0
    level: ConfidenceLevel
    reasoning: str  # Why this confidence level
    risk_factors: List[str] = field(default_factory=list)

    @classmethod
    def from_score(cls, score: float, reasoning: str = "", risks: List[str] = None) -> 'StepConfidence':
        """Create confidence from numeric score"""
        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

        if score >= 0.9:
            level = ConfidenceLevel.CERTAIN
        elif score >= 0.7:
            level = ConfidenceLevel.CONFIDENT
        elif score >= 0.5:
            level = ConfidenceLevel.MODERATE
        elif score >= 0.3:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.SPECULATIVE

        return cls(
            score=score,
            level=level,
            reasoning=reasoning or f"Confidence score: {score:.2f}",
            risk_factors=risks or []
        )


# ============================================================================
# NEW v6.1: MULTI-PLAN GENERATION (Zhang et al. Verbalized Sampling)
# ============================================================================

class PlanStrategy(str, Enum):
    """
    Plan generation strategies based on Verbalized Sampling.

    Instead of collapsing to a single "average" plan, we explore
    the latent space of possibilities with distinct approaches.
    """
    STANDARD = "standard"      # Plan A: Conventional, low risk path
    ACCELERATOR = "accelerator"  # Plan B: High speed, higher risk
    LATERAL = "lateral"        # Plan C: Creative/unconventional approach


@dataclass
class PlanProbabilities:
    """
    Verbalized probability estimates for a plan.

    Based on Zhang et al. (2025) - explicit probability reasoning
    helps LLMs make better decisions under uncertainty.
    """
    success: float  # P(Success): Probability of achieving the goal
    friction: float  # P(Friction): Probability of encountering blockers
    time_overrun: float  # P(TimeOverrun): Probability of taking longer than estimated
    quality: float  # P(Quality): Probability of high-quality output

    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio for plan comparison."""
        reward = self.success * self.quality
        risk = self.friction + self.time_overrun
        if risk == 0:
            return float('inf')
        return reward / risk

    @property
    def overall_score(self) -> float:
        """Weighted overall score (0-1)."""
        return (
            self.success * 0.4 +
            (1 - self.friction) * 0.25 +
            (1 - self.time_overrun) * 0.15 +
            self.quality * 0.2
        )

    def to_display(self) -> str:
        """Format for display."""
        return (
            f"P(Success)={self.success:.2f} | "
            f"P(Friction)={self.friction:.2f} | "
            f"P(Quality)={self.quality:.2f}"
        )


class AlternativePlan(BaseModel):
    """
    A single alternative plan with its strategy and probabilities.

    Part of the Multi-Plan Generation system inspired by
    Verbalized Sampling (Zhang et al. 2025).
    """
    strategy: PlanStrategy
    name: str  # Human-readable name
    description: str  # Brief description of the approach
    plan: Dict[str, Any]  # The actual ExecutionPlan data

    # Verbalized probabilities
    p_success: float = Field(ge=0.0, le=1.0, description="P(Success)")
    p_friction: float = Field(ge=0.0, le=1.0, description="P(Friction)")
    p_time_overrun: float = Field(default=0.3, ge=0.0, le=1.0)
    p_quality: float = Field(default=0.7, ge=0.0, le=1.0)

    # Analysis
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    best_for: str = ""  # When to choose this plan

    @property
    def probabilities(self) -> PlanProbabilities:
        return PlanProbabilities(
            success=self.p_success,
            friction=self.p_friction,
            time_overrun=self.p_time_overrun,
            quality=self.p_quality
        )

    @property
    def risk_reward_ratio(self) -> float:
        return self.probabilities.risk_reward_ratio

    @property
    def overall_score(self) -> float:
        return self.probabilities.overall_score


class MultiPlanResult(BaseModel):
    """
    Result of multi-plan generation.

    Contains 3 alternative plans and a recommendation.
    """
    task_summary: str
    plans: List[AlternativePlan] = Field(min_length=1, max_length=5)
    recommended_plan: PlanStrategy
    recommendation_reasoning: str

    # Comparison matrix
    comparison_summary: str = ""

    # Metadata
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    generation_time_ms: Optional[int] = None

    def get_plan(self, strategy: PlanStrategy) -> Optional[AlternativePlan]:
        """Get plan by strategy."""
        for plan in self.plans:
            if plan.strategy == strategy:
                return plan
        return None

    def get_recommended(self) -> Optional[AlternativePlan]:
        """Get the recommended plan."""
        return self.get_plan(self.recommended_plan)

    def to_markdown(self) -> str:
        """Format as markdown for display."""
        lines = [
            "# 🎯 Multi-Plan Analysis (Verbalized Sampling)",
            "",
            f"**Task:** {self.task_summary}",
            "",
            "---",
            "",
        ]

        for plan in self.plans:
            emoji = {"standard": "📋", "accelerator": "🚀", "lateral": "💡"}.get(
                plan.strategy.value, "📌"
            )
            lines.extend([
                f"## {emoji} Plan {plan.strategy.value.upper()}: {plan.name}",
                "",
                f"*{plan.description}*",
                "",
                f"**Probabilities:** {plan.probabilities.to_display()}",
                "",
                f"**Overall Score:** {plan.overall_score:.2f}",
                "",
            ])

            if plan.pros:
                lines.append("**Pros:**")
                for pro in plan.pros:
                    lines.append(f"- ✅ {pro}")
                lines.append("")

            if plan.cons:
                lines.append("**Cons:**")
                for con in plan.cons:
                    lines.append(f"- ⚠️ {con}")
                lines.append("")

            if plan.best_for:
                lines.append(f"**Best for:** {plan.best_for}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # Recommendation
        rec = self.get_recommended()
        lines.extend([
            "## 🎯 RECOMMENDATION",
            "",
            f"**Selected:** Plan {self.recommended_plan.value.upper()}" +
            (f" - {rec.name}" if rec else ""),
            "",
            f"**Reasoning:** {self.recommendation_reasoning}",
            "",
        ])

        return "\n".join(lines)


@dataclass
class WorldState:
    """
    GOAP-inspired world state tracking.
    Represents the current state of the development environment.
    """
    facts: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, int] = field(default_factory=dict)  # tokens, time, etc.
    
    def satisfies(self, goal: 'GoalState') -> bool:
        """Check if current state satisfies goal"""
        for key, value in goal.desired_facts.items():
            if key not in self.facts or self.facts[key] != value:
                return False
        return True
    
    def distance_to(self, goal: 'GoalState') -> float:
        """Calculate heuristic distance to goal (for A*)"""
        distance = 0.0
        for key, value in goal.desired_facts.items():
            if key not in self.facts:
                distance += 1.0
            elif self.facts[key] != value:
                distance += 0.5
        return distance

@dataclass
class GoalState:
    """Desired end state for GOAP planning"""
    name: str
    desired_facts: Dict[str, Any]
    priority: float = 1.0  # Weight for multi-goal scenarios
    
@dataclass
class Action:
    """
    GOAP Action with preconditions and effects.
    Atomic unit of work for an agent.
    """
    id: str
    agent_role: str
    description: str
    preconditions: Dict[str, Any]  # Required world state
    effects: Dict[str, Any]        # Changes to world state
    cost: float = 1.0              # For path optimization
    duration_estimate: str = "5m"
    
    def can_execute(self, state: WorldState) -> bool:
        """Check if preconditions are met"""
        for key, value in self.preconditions.items():
            if key not in state.facts or state.facts[key] != value:
                return False
        return True
    
    def apply(self, state: WorldState) -> WorldState:
        """Apply effects to world state"""
        new_state = WorldState(
            facts=state.facts.copy(),
            resources=state.resources.copy()
        )
        new_state.facts.update(self.effects)
        return new_state

class SOPStep(BaseModel):
    """Enhanced SOP with GOAP integration and v6.0 Confidence Ratings"""
    id: str
    role: str
    action: str
    objective: str
    definition_of_done: str

    # GOAP fields
    preconditions: Dict[str, Any] = Field(default_factory=dict)
    effects: Dict[str, Any] = Field(default_factory=dict)
    cost: float = Field(default=1.0, description="Execution cost (time/tokens/complexity)")

    # Orchestration fields
    dependencies: List[str] = Field(default_factory=list)
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    priority: AgentPriority = AgentPriority.MEDIUM

    # Context isolation (Anthropic best practice)
    context_isolation: bool = Field(default=True, description="Isolate agent context")
    max_tokens: int = Field(default=4000, description="Token budget for this step")

    # Safety
    checkpoint: Optional[CheckpointType] = None
    rollback_on_error: bool = False
    retry_count: int = 0

    # Observability
    correlation_id: Optional[str] = None
    telemetry_tags: Dict[str, str] = Field(default_factory=dict)

    # NEW v6.0: Confidence Rating (Devin pattern)
    confidence_score: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence in successful execution (0.0-1.0)"
    )
    confidence_reasoning: str = Field(
        default="",
        description="Explanation for confidence level"
    )
    risk_factors: List[str] = Field(
        default_factory=list,
        description="Known risks that affect confidence"
    )

class ExecutionStage(BaseModel):
    """
    Stage in the workflow - groups related steps.
    Inspired by Claude-Flow's stage system.
    """
    name: str
    description: str
    steps: List[SOPStep]
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    checkpoint: bool = False
    required: bool = True  # Must succeed for plan to continue

class ExecutionPlan(BaseModel):
    """Comprehensive execution plan with enterprise features + v6.0 enhancements"""
    plan_id: str
    goal: str
    strategy_overview: str

    # GOAP fields
    initial_state: Dict[str, Any] = Field(default_factory=dict)
    goal_state: Dict[str, Any] = Field(default_factory=dict)
    estimated_cost: float = 0.0

    # Multi-stage execution
    stages: List[ExecutionStage] = Field(default_factory=list)

    # Legacy SOPs (for backward compatibility)
    sops: List[SOPStep] = Field(default_factory=list)

    # Safety & Recovery
    rollback_strategy: str = "Restore from last checkpoint"
    checkpoints: List[str] = Field(default_factory=list)
    risk_assessment: str = "MEDIUM"

    # Coordination
    parallel_execution_opportunities: List[List[str]] = Field(
        default_factory=list,
        description="Groups of steps that can run in parallel"
    )
    critical_path: List[str] = Field(
        default_factory=list,
        description="Longest dependency chain"
    )

    # Resource planning
    estimated_duration: str = "30-60 minutes"
    token_budget: int = 50000
    max_parallel_agents: int = 4

    # Observability
    plan_version: str = "6.0"
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # NEW v6.0: Planning Mode (Claude Code pattern)
    mode: PlanningMode = Field(
        default=PlanningMode.PLANNING,
        description="Current planning mode (exploration/planning/execution)"
    )

    # NEW v6.0: Clarifying Questions (Cursor 2.1 pattern)
    clarifying_questions: List[ClarifyingQuestion] = Field(
        default_factory=list,
        description="Questions asked before planning"
    )
    clarification_responses: List[ClarificationResponse] = Field(
        default_factory=list,
        description="User's answers to clarifying questions"
    )

    # NEW v6.0: Overall Confidence (Devin pattern)
    overall_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weighted average confidence across all steps"
    )
    confidence_summary: str = Field(
        default="",
        description="Human-readable confidence assessment"
    )

    # NEW v6.0: Plan Artifact Path (Claude Code pattern)
    plan_artifact_path: Optional[str] = Field(
        default=None,
        description="Path to generated plan.md file"
    )

# ============================================================================
# GOAP PLANNER - The Brain
# ============================================================================

class GOAPPlanner:
    """
    Goal-Oriented Action Planner using A* pathfinding.
    Finds optimal sequence of actions to reach goal state.
    
    Based on F.E.A.R. AI system by Jeff Orkin (2006).
    """
    
    def __init__(self, actions: List[Action]):
        self.actions = actions
    
    def plan(
        self, 
        initial_state: WorldState, 
        goal: GoalState,
        max_depth: int = 20
    ) -> Optional[List[Action]]:
        """
        Find optimal action sequence using A* algorithm.
        
        Returns:
            List of actions to execute, or None if no plan found
        """
        # Priority queue: (f_score, g_score, state, path)
        frontier = [(0.0, 0.0, initial_state, [])]
        explored: Set[str] = set()
        
        while frontier:
            f_score, g_score, current_state, path = heapq.heappop(frontier)
            
            # Check if we've reached the goal
            if current_state.satisfies(goal):
                return path
            
            # Depth limit
            if len(path) >= max_depth:
                continue
            
            # Skip if already explored
            state_hash = self._hash_state(current_state)
            if state_hash in explored:
                continue
            explored.add(state_hash)
            
            # Explore neighbors (applicable actions)
            for action in self.actions:
                if not action.can_execute(current_state):
                    continue
                
                # Apply action
                new_state = action.apply(current_state)
                new_path = path + [action]
                
                # Calculate scores
                new_g_score = g_score + action.cost
                h_score = new_state.distance_to(goal)
                new_f_score = new_g_score + h_score
                
                heapq.heappush(
                    frontier,
                    (new_f_score, new_g_score, new_state, new_path)
                )
        
        return None  # No plan found
    
    def _hash_state(self, state: WorldState) -> str:
        """Create hashable representation of state"""
        return json.dumps(state.facts, sort_keys=True)

# ============================================================================
# DEPENDENCY GRAPH ANALYZER
# ============================================================================

class DependencyAnalyzer:
    """
    Analyzes step dependencies to find:
    - Parallel execution opportunities
    - Critical path (longest chain)
    - Circular dependencies
    - Optimal execution order
    """
    
    @staticmethod
    def build_graph(steps: List[SOPStep]) -> Dict[str, List[str]]:
        """Build adjacency list from dependencies"""
        graph = {step.id: step.dependencies for step in steps}
        return graph
    
    @staticmethod
    def find_parallel_groups(steps: List[SOPStep]) -> List[List[str]]:
        """
        Find groups of steps that can execute in parallel.
        Steps with no dependencies on each other can run together.
        """
        graph = DependencyAnalyzer.build_graph(steps)
        step_map = {s.id: s for s in steps}
        
        # Topological sort to get execution levels
        in_degree = {step.id: len(step.dependencies) for step in steps}
        levels = []
        
        while any(d == 0 for d in in_degree.values()):
            # Current level: nodes with no dependencies
            current_level = [
                sid for sid, degree in in_degree.items() 
                if degree == 0
            ]
            levels.append(current_level)
            
            # Remove current level nodes
            for sid in current_level:
                in_degree[sid] = -1  # Mark as processed
                # Decrease in-degree of dependent nodes
                for other_sid, deps in graph.items():
                    if sid in deps:
                        in_degree[other_sid] -= 1
        
        return levels
    
    @staticmethod
    def find_critical_path(steps: List[SOPStep]) -> List[str]:
        """
        Find critical path: longest dependency chain.
        This determines minimum execution time.
        """
        graph = DependencyAnalyzer.build_graph(steps)
        step_map = {s.id: s for s in steps}
        
        # Calculate longest path using dynamic programming
        memo = {}
        
        def longest_path(step_id: str) -> Tuple[float, List[str]]:
            if step_id in memo:
                return memo[step_id]
            
            step = step_map[step_id]
            
            if not step.dependencies:
                result = (step.cost, [step_id])
            else:
                # Find longest path through dependencies
                max_cost = 0.0
                max_path = []
                
                for dep_id in step.dependencies:
                    dep_cost, dep_path = longest_path(dep_id)
                    if dep_cost > max_cost:
                        max_cost = dep_cost
                        max_path = dep_path
                
                result = (max_cost + step.cost, max_path + [step_id])
            
            memo[step_id] = result
            return result
        
        # Find overall longest path
        max_cost = 0.0
        critical_path = []
        
        for step in steps:
            cost, path = longest_path(step.id)
            if cost > max_cost:
                max_cost = cost
                critical_path = path
        
        return critical_path
    
    @staticmethod
    def detect_cycles(steps: List[SOPStep]) -> List[List[str]]:
        """Detect circular dependencies"""
        graph = DependencyAnalyzer.build_graph(steps)
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
            
            rec_stack.remove(node)
        
        for step in steps:
            if step.id not in visited:
                dfs(step.id, [])
        
        return cycles

# ============================================================================
# PLANNER AGENT - The Orchestrator Queen 👑
# ============================================================================

class PlannerAgent(BaseAgent):
    """
    Enterprise-Grade Planning & Orchestration Agent v6.0 "Espetacular"

    The "Queen" of the multi-agent swarm (Claude-Flow pattern).
    Responsible for:
    - High-level strategic planning (GOAP)
    - Agent coordination & delegation
    - Resource allocation
    - Risk assessment
    - Observability

    NEW in v6.0 (Inspired by Claude Code, Cursor 2.1, Devin):
    - Interactive Clarifying Questions before planning
    - plan.md Artifact Generation for user tracking
    - Confidence Ratings per step
    - Read-Only Exploration Mode

    Keep tool permissions narrow: "read and route" (Anthropic best practice).
    """

    def __init__(
        self,
        llm_client: Any,
        mcp_client: Any,
        plan_artifact_dir: Optional[str] = None,
        ask_clarifying_questions: bool = True,
    ):
        super().__init__(
            role=AgentRole.PLANNER,
            capabilities=[
                AgentCapability.DESIGN,
                AgentCapability.READ_ONLY  # Narrow permissions!
            ],
            llm_client=llm_client,
            mcp_client=mcp_client,
            system_prompt=self._build_system_prompt()
        )

        # Initialize analyzers
        self.dependency_analyzer = DependencyAnalyzer()
        self.goap_planner: Optional[GOAPPlanner] = None

        # NEW v6.0: Configuration
        self.plan_artifact_dir = plan_artifact_dir or ".qwen/plans"
        self.ask_clarifying_questions = ask_clarifying_questions
        self.current_mode: PlanningMode = PlanningMode.PLANNING

        # NEW v6.0: Callbacks for interactive features
        self._question_callback: Optional[Callable] = None
        self._approval_callback: Optional[Callable] = None

    def _build_system_prompt(self) -> str:
        return """
You are PlannerAgent v6.0 "Espetacular" - Enterprise Orchestration Queen 👑

MISSION: Convert high-level goals into optimal, executable multi-agent workflows.

CORE PRINCIPLES (Anthropic 2025 Best Practices):
1. **Context Isolation**: Each sub-agent gets isolated context (no drift)
2. **Atomic Actions**: Each step must be completable by ONE agent in ONE turn
3. **Verifiable Outcomes**: Every step has a "definition_of_done"
4. **Graceful Degradation**: Non-critical steps can fail without breaking the plan
5. **Observability**: Include correlation IDs for distributed tracing

PLANNING METHODOLOGY (GOAP):
- Define clear GOAL STATE (what success looks like)
- Identify INITIAL STATE (current reality)
- Generate ACTIONS with preconditions & effects
- Use A* to find optimal path
- Consider COST (time, tokens, complexity)

ORCHESTRATION PATTERNS:
- **Sequential**: Dependencies require ordering (analyst → architect → coder)
- **Parallel**: Independent tasks run together (UI, API, DB teams)
- **Fork-Join**: Parallel work with merge point (multi-region deployment)
- **Pipeline**: Stream output between agents (preprocessor → analyzer → formatter)
- **Conditional**: Runtime branching based on results

OUTPUT FORMAT:
Pure JSON matching ExecutionPlan schema.
NO preamble, NO markdown blocks, JUST valid JSON.

CRITICAL:
- Detect parallel execution opportunities (save time!)
- Calculate critical path (longest dependency chain)
- Include checkpoints for rollback
- Assess risks and provide mitigation
- Keep token budgets realistic per agent
        """

    async def execute(self, task: AgentTask) -> AgentResponse:
        """
        Main planning workflow:
        1. Analyze task & context
        2. Define goal state (GOAP)
        3. Generate action space
        4. Run GOAP planner (A* pathfinding)
        5. Optimize execution order
        6. Detect parallel opportunities
        7. Add safety measures (checkpoints, rollback)
        8. Return comprehensive plan
        """
        try:
            # Phase 1: Context gathering
            context = await self._gather_context(task)
            
            # Phase 2: Define GOAP goal
            goal_state = self._define_goal_state(task, context)
            initial_state = self._define_initial_state(context)
            
            # Phase 3: Generate action space from available agents
            available_agents = self._get_available_agents(task)
            actions = self._generate_action_space(
                task, 
                available_agents, 
                context
            )
            
            # Phase 4: Run GOAP planner
            self.goap_planner = GOAPPlanner(actions)
            
            # Try GOAP first, fallback to LLM if needed
            goap_plan = self.goap_planner.plan(
                initial_state,
                goal_state,
                max_depth=20
            )
            
            if goap_plan:
                # Convert GOAP actions to SOPs
                sops = self._actions_to_sops(goap_plan)
            else:
                # GOAP failed, use LLM planning
                sops = await self._llm_planning_fallback(
                    task, context, available_agents
                )
            
            # Phase 5: Dependency analysis
            parallel_groups = self.dependency_analyzer.find_parallel_groups(sops)
            critical_path = self.dependency_analyzer.find_critical_path(sops)
            cycles = self.dependency_analyzer.detect_cycles(sops)
            
            # Fail if circular dependencies detected
            if cycles:
                return AgentResponse(
                    success=False,
                    error=f"Circular dependencies detected: {cycles}",
                    reasoning="Plan has dependency cycles that would cause deadlock."
                )
            
            # Phase 6: Build stages from parallel groups
            stages = self._build_stages(sops, parallel_groups)
            
            # Phase 7: Risk assessment & rollback strategy
            risk_level = self._assess_risk(sops)
            rollback_strategy = self._generate_rollback_strategy(stages, sops)
            
            # Phase 8: Resource estimation
            estimated_duration = self._estimate_duration(sops, parallel_groups)
            token_budget = sum(step.max_tokens for step in sops)
            
            # Phase 9: Build final plan
            plan = ExecutionPlan(
                plan_id=f"plan-{task.task_id}",
                goal=task.request,
                strategy_overview=self._generate_strategy_overview(stages),
                initial_state=initial_state.facts,
                goal_state=goal_state.desired_facts,
                estimated_cost=sum(s.cost for s in sops),
                stages=stages,
                sops=sops,
                rollback_strategy=rollback_strategy,
                checkpoints=self._identify_checkpoints(stages),
                risk_assessment=risk_level,
                parallel_execution_opportunities=parallel_groups,
                critical_path=critical_path,
                estimated_duration=estimated_duration,
                token_budget=token_budget,
                max_parallel_agents=self._calculate_max_parallel(parallel_groups),
                plan_version="5.0",
                metadata={
                    "goap_used": goap_plan is not None,
                    "stages_count": len(stages),
                    "total_steps": len(sops),
                    "parallelism_factor": len(parallel_groups)
                }
            )
            
            return AgentResponse(
                success=True,
                data={"plan": plan.model_dump()},
                reasoning=self._generate_reasoning(plan)
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                error=str(e),
                reasoning="Planning execution failed. See error for details."
            )

    async def _gather_context(self, task: AgentTask) -> Dict[str, Any]:
        """Gather all relevant context for planning"""
        context = {
            "architecture": task.context.get("architecture", {}),
            "files": task.context.get("files", []),
            "constraints": task.context.get("constraints", {}),
            "team_standards": await self._load_team_standards(),
            "available_tools": await self._discover_available_tools()
        }
        return context
    
    async def _load_team_standards(self) -> Dict[str, Any]:
        """Load team standards from CLAUDE.md or similar.

        CLAUDE.md is optional. Falls back to empty standards if not found.

        Compliance: Vértice Constitution v3.0 - P3 (fail gracefully)
        """
        # Try to read CLAUDE.md (Anthropic best practice)
        try:
            result = await self._execute_tool("read_file", {"path": "CLAUDE.md"})
            if result.get("success"):
                self.logger.info("Loaded team standards from CLAUDE.md")
                return {"claude_md": result.get("content", "")}
        except FileNotFoundError:
            self.logger.debug(
                "CLAUDE.md not found (optional). "
                "Using default standards. "
                "Create CLAUDE.md for project-specific guidelines."
            )
        except Exception as e:
            self.logger.warning(f"Failed to load CLAUDE.md: {e}")

        # Fallback: Empty standards (agent uses defaults)
        return {}
    
    async def _discover_available_tools(self) -> List[str]:
        """Discover available MCP tools"""
        # In production: Query MCP for available tools
        return ["read_file", "write_file", "exec_command", "git_operations"]

    def _define_goal_state(self, task: AgentTask, context: Dict) -> GoalState:
        """Define desired end state (GOAP)"""
        # Parse task to extract goal facts
        # For now, simple heuristic
        goal_facts = {
            "task_complete": True,
            "tests_passing": True,
            "code_reviewed": True,
            "documented": True
        }
        
        return GoalState(
            name=f"goal-{task.task_id}",
            desired_facts=goal_facts,
            priority=1.0
        )
    
    def _define_initial_state(self, context: Dict) -> WorldState:
        """Define current state"""
        initial_facts = {
            "task_complete": False,
            "tests_passing": False,
            "code_reviewed": False,
            "documented": False,
            "has_codebase": len(context.get("files", [])) > 0
        }
        
        return WorldState(
            facts=initial_facts,
            resources={"tokens": 100000, "time_minutes": 120}
        )
    
    def _get_available_agents(self, task: AgentTask) -> List[str]:
        """Get list of available agents for delegation"""
        # Could query registry or configuration
        return [
            "architect",
            "coder",
            "refactorer",
            "reviewer",
            "security",
            "tester",
            "documenter"
        ]
    
    def _generate_action_space(
        self,
        task: AgentTask,
        agents: List[str],
        context: Dict
    ) -> List[Action]:
        """
        Generate available actions from agent capabilities.
        Each action represents what an agent can do.
        """
        actions = []
        
        # Architect actions
        actions.append(Action(
            id="design_architecture",
            agent_role="architect",
            description="Design system architecture",
            preconditions={"has_codebase": True},
            effects={"architecture_defined": True},
            cost=3.0,
            duration_estimate="15m"
        ))
        
        # Coder actions
        actions.append(Action(
            id="implement_features",
            agent_role="coder",
            description="Implement features based on design",
            preconditions={"architecture_defined": True},
            effects={"code_written": True},
            cost=5.0,
            duration_estimate="30m"
        ))
        
        # Tester actions
        actions.append(Action(
            id="write_tests",
            agent_role="tester",
            description="Write automated tests",
            preconditions={"code_written": True},
            effects={"tests_passing": True},
            cost=3.0,
            duration_estimate="20m"
        ))
        
        # Reviewer actions
        actions.append(Action(
            id="code_review",
            agent_role="reviewer",
            description="Perform code review",
            preconditions={"code_written": True, "tests_passing": True},
            effects={"code_reviewed": True},
            cost=2.0,
            duration_estimate="15m"
        ))
        
        # Documenter actions
        actions.append(Action(
            id="write_docs",
            agent_role="documenter",
            description="Write documentation",
            preconditions={"code_written": True},
            effects={"documented": True, "task_complete": True},
            cost=2.0,
            duration_estimate="10m"
        ))
        
        return actions
    
    def _actions_to_sops(self, actions: List[Action]) -> List[SOPStep]:
        """Convert GOAP actions to SOP steps"""
        sops = []
        
        for idx, action in enumerate(actions):
            # Find dependencies (actions whose effects match our preconditions)
            deps = []
            for prev_idx, prev_action in enumerate(actions[:idx]):
                # Check if previous action's effects satisfy our preconditions
                if any(
                    key in prev_action.effects and 
                    prev_action.effects[key] == value
                    for key, value in action.preconditions.items()
                ):
                    deps.append(f"step-{prev_idx}")
            
            sop = SOPStep(
                id=f"step-{idx}",
                role=action.agent_role,
                action=action.description,
                objective=f"Execute {action.id}",
                definition_of_done=f"Action {action.id} completed successfully",
                preconditions=action.preconditions,
                effects=action.effects,
                cost=action.cost,
                dependencies=deps,
                context_isolation=True,
                max_tokens=4000,
                correlation_id=f"action-{action.id}"
            )
            sops.append(sop)
        
        return sops
    
    async def _llm_planning_fallback(
        self,
        task: AgentTask,
        context: Dict,
        agents: List[str]
    ) -> List[SOPStep]:
        """Fallback to LLM planning if GOAP fails"""
        prompt = self._build_llm_planning_prompt(task, context, agents)
        raw_response = await self._call_llm(prompt)
        
        # Parse and validate
        plan_data = self._robust_json_parse(raw_response)
        
        if plan_data and "sops" in plan_data:
            return [SOPStep(**sop) for sop in plan_data["sops"]]
        
        # Emergency fallback: basic sequential plan
        return self._generate_basic_plan(task, agents)
    
    def _build_llm_planning_prompt(
        self,
        task: AgentTask,
        context: Dict,
        agents: List[str]
    ) -> str:
        """Build comprehensive planning prompt for LLM"""
        return f"""
Generate a detailed execution plan for this task:

TASK: {task.request}

CONTEXT:
{json.dumps(context, indent=2)}

AVAILABLE AGENTS: {', '.join(agents)}

REQUIREMENTS:
1. Break into atomic steps (one agent, one action)
2. Each step must have clear "definition_of_done"
3. Specify dependencies between steps
4. Mark which steps can run in parallel
5. Add checkpoints for critical transitions
6. Include rollback strategy

OUTPUT SCHEMA:
{{
  "sops": [
    {{
      "id": "step-1",
      "role": "agent_name",
      "action": "What to do",
      "objective": "Why",
      "definition_of_done": "Success criteria",
      "dependencies": [],
      "cost": 1.0,
      "priority": "high",
      "checkpoint": "validation"
    }}
  ]
}}

RESPOND WITH PURE JSON ONLY.
"""
    
    def _generate_basic_plan(
        self,
        task: AgentTask,
        agents: List[str]
    ) -> List[SOPStep]:
        """Emergency fallback: basic sequential plan"""
        return [
            SOPStep(
                id="step-1",
                role="architect",
                action="Analyze requirements and design solution",
                objective="Create technical plan",
                definition_of_done="Architecture documented",
                cost=2.0
            ),
            SOPStep(
                id="step-2",
                role="coder",
                action="Implement the solution",
                objective="Write working code",
                definition_of_done="Code compiles and runs",
                dependencies=["step-1"],
                cost=5.0
            ),
            SOPStep(
                id="step-3",
                role="tester",
                action="Write and run tests",
                objective="Verify correctness",
                definition_of_done="All tests pass",
                dependencies=["step-2"],
                cost=3.0
            )
        ]
    
    def _build_stages(
        self,
        sops: List[SOPStep],
        parallel_groups: List[List[str]]
    ) -> List[ExecutionStage]:
        """Group SOPs into execution stages"""
        stages = []
        sop_map = {sop.id: sop for sop in sops}
        
        for level_idx, group in enumerate(parallel_groups):
            stage_steps = [sop_map[sid] for sid in group]
            
            # Determine strategy
            strategy = (
                ExecutionStrategy.PARALLEL 
                if len(group) > 1 
                else ExecutionStrategy.SEQUENTIAL
            )
            
            # Check if stage has checkpoint
            has_checkpoint = any(
                step.checkpoint is not None 
                for step in stage_steps
            )
            
            stage = ExecutionStage(
                name=f"Stage {level_idx + 1}: {self._infer_stage_name(stage_steps)}",
                description=self._generate_stage_description(stage_steps),
                steps=stage_steps,
                strategy=strategy,
                checkpoint=has_checkpoint,
                required=all(step.priority in [AgentPriority.CRITICAL, AgentPriority.HIGH] for step in stage_steps)
            )
            stages.append(stage)
        
        return stages
    
    def _infer_stage_name(self, steps: List[SOPStep]) -> str:
        """Infer human-readable stage name from steps"""
        roles = list(set(step.role for step in steps))
        if len(roles) == 1:
            return f"{roles[0].title()} Phase"
        return "Multi-Agent Phase"
    
    def _generate_stage_description(self, steps: List[SOPStep]) -> str:
        """Generate description for stage"""
        if len(steps) == 1:
            return steps[0].objective
        return f"Parallel execution of {len(steps)} tasks: {', '.join(s.action[:30] for s in steps)}"
    
    def _assess_risk(self, sops: List[SOPStep]) -> str:
        """Assess overall plan risk level"""
        critical_count = sum(1 for s in sops if s.priority == AgentPriority.CRITICAL)
        has_security = any("security" in s.role.lower() for s in sops)
        total_cost = sum(s.cost for s in sops)
        
        if critical_count > 5 or not has_security or total_cost > 50:
            return "HIGH"
        elif critical_count > 2 or total_cost > 20:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_rollback_strategy(
        self,
        stages: List[ExecutionStage],
        sops: List[SOPStep]
    ) -> str:
        """Generate comprehensive rollback strategy"""
        checkpoints = [
            stage.name 
            for stage in stages 
            if stage.checkpoint
        ]
        
        if not checkpoints:
            return "Full rollback to initial state if any step fails."
        
        strategy_parts = [
            "Staged rollback strategy:",
            f"- Checkpoints at: {', '.join(checkpoints)}",
            "- On failure: Restore to last successful checkpoint",
            "- Critical steps have automatic retry (max 3 attempts)",
            "- All changes tracked for point-in-time recovery"
        ]
        
        return "\n".join(strategy_parts)
    
    def _identify_checkpoints(self, stages: List[ExecutionStage]) -> List[str]:
        """Identify checkpoint stages"""
        return [
            stage.name 
            for stage in stages 
            if stage.checkpoint
        ]
    
    def _estimate_duration(
        self,
        sops: List[SOPStep],
        parallel_groups: List[List[str]]
    ) -> str:
        """Estimate total execution time accounting for parallelism"""
        # Sum of critical path (longest sequential chain)
        critical_path = self.dependency_analyzer.find_critical_path(sops)
        sop_map = {s.id: s for s in sops}
        
        total_cost = sum(sop_map[sid].cost for sid in critical_path)
        
        # Convert cost to time (rough heuristic: 1 cost = 5 minutes)
        minutes = int(total_cost * 5)
        
        if minutes < 10:
            return "< 10 minutes"
        elif minutes < 30:
            return "10-30 minutes"
        elif minutes < 60:
            return "30-60 minutes"
        elif minutes < 120:
            return "1-2 hours"
        else:
            return f"~{minutes // 60} hours"
    
    def _calculate_max_parallel(
        self,
        parallel_groups: List[List[str]]
    ) -> int:
        """Calculate maximum parallel agents needed"""
        if not parallel_groups:
            return 1
        return max(len(group) for group in parallel_groups)
    
    def _generate_strategy_overview(self, stages: List[ExecutionStage]) -> str:
        """Generate high-level strategy description"""
        parallel_stages = sum(1 for s in stages if s.strategy == ExecutionStrategy.PARALLEL)
        total_stages = len(stages)
        
        overview_parts = [
            f"Multi-stage execution plan with {total_stages} stages.",
        ]
        
        if parallel_stages > 0:
            overview_parts.append(
                f"{parallel_stages} stages use parallel execution for efficiency."
            )
        
        overview_parts.append("Each stage has clear success criteria and rollback capability.")
        
        return " ".join(overview_parts)
    
    def _generate_reasoning(self, plan: ExecutionPlan) -> str:
        """Generate human-readable reasoning about the plan"""
        parts = [
            f"Generated {len(plan.sops)}-step plan across {len(plan.stages)} stages.",
            f"Risk level: {plan.risk_assessment}.",
            f"Estimated duration: {plan.estimated_duration}.",
        ]
        
        if plan.parallel_execution_opportunities:
            max_parallel = max(len(g) for g in plan.parallel_execution_opportunities)
            parts.append(f"Detected {max_parallel}-way parallelism opportunities.")
        
        if plan.metadata.get("goap_used"):
            parts.append("Used GOAP (Goal-Oriented Action Planning) for optimal path finding.")
        else:
            parts.append("Used LLM-based planning (GOAP unavailable).")
        
        return " ".join(parts)

    def _robust_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Enterprise-grade JSON parsing with multiple fallback strategies.
        Handles all common LLM output formats.
        """
        # Strategy 1: Strip markdown blocks
        clean_text = text.strip()
        
        # Remove markdown code blocks
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0]
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0]
        
        clean_text = clean_text.strip()
        
        # Strategy 2: Direct parse
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 3: Find JSON object with regex
        try:
            # Match outermost braces
            match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', clean_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Strategy 4: Fix common issues
        try:
            # Remove trailing commas
            fixed_text = re.sub(r',(\s*[}\]])', r'\1', clean_text)
            return json.loads(fixed_text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 5: Extract JSON array if present
        try:
            match = re.search(r'\[(?:[^\[\]]|(?:\[[^\[\]]*\]))*\]', clean_text, re.DOTALL)
            if match:
                arr = json.loads(match.group(0))
                return {"sops": arr}  # Wrap in expected structure
        except (json.JSONDecodeError, AttributeError):
            pass

        return None

    async def execute_streaming(
        self,
        task: AgentTask
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Streaming execution for PlannerAgent.

        Claude Code Style: Generates plan internally, then streams formatted markdown.
        Does NOT stream raw JSON tokens to UI.

        Yields:
            Dict with format {"type": "status"|"thinking"|"result", "data": ...}
        """
        trace_id = getattr(task, 'trace_id', str(uuid.uuid4()))

        try:
            # PHASE 1: Initial Status
            yield {"type": "status", "data": "📋 Loading project context..."}

            cwd = task.context.get('cwd', '.') if task.context else '.'
            await asyncio.sleep(0.05)

            # PHASE 2: Build Prompt
            yield {"type": "status", "data": "🎯 Generating plan..."}

            # Detect language and add instruction
            try:
                from qwen_core import LanguageDetector
                lang_instruction = LanguageDetector.get_prompt_instruction(task.request)
            except ImportError:
                lang_instruction = None

            prompt = f"""Create an execution plan for the following request:

REQUEST: {task.request}

CONTEXT:
- Working Directory: {cwd}

Generate a comprehensive plan with clear steps. Respond with a valid JSON object using this EXACT format:

{{
  "goal": "Brief description of the goal",
  "strategy_overview": "High-level approach",
  "sops": [
    {{
      "id": "step-1",
      "action": "Description of what to do",
      "role": "executor",
      "confidence_score": 0.8,
      "definition_of_done": "How to verify completion"
    }},
    {{
      "id": "step-2",
      "action": "Next action...",
      "role": "executor",
      "confidence_score": 0.7,
      "definition_of_done": "Verification criteria"
    }}
  ],
  "risk_assessment": "LOW|MEDIUM|HIGH",
  "rollback_strategy": "How to undo if needed",
  "estimated_duration": "Time estimate"
}}

Include 3-7 concrete, actionable steps in the sops array.

{f'IMPORTANT: {lang_instruction}' if lang_instruction else ''}"""

            # PHASE 3: Generate LLM Response (internal - NOT streamed to UI)
            # Claude Code pattern: Generate internally, format, then stream formatted output
            response_buffer = []
            token_count = 0

            async for token in self.llm_client.stream(
                prompt=prompt,
                system_prompt=self._get_system_prompt() if hasattr(self, '_get_system_prompt') else None,
                max_tokens=4096,
                temperature=0.3
            ):
                response_buffer.append(token)
                token_count += 1
                # Show progress indicator every 50 tokens (Claude Code style)
                if token_count % 50 == 0:
                    yield {"type": "status", "data": f"🎯 Generating plan... ({token_count} tokens)"}

            llm_response = ''.join(response_buffer)

            # PHASE 4: Process and Format
            yield {"type": "status", "data": "⚙️ Processing plan..."}

            plan = self._robust_json_parse(llm_response) if hasattr(self, '_robust_json_parse') else {"raw_response": llm_response}

            # PHASE 5: Generate Formatted Markdown (Claude Code style)
            yield {"type": "status", "data": "📝 Formatting plan..."}

            # Use _format_plan_as_markdown to create beautiful output
            formatted_markdown = self._format_plan_as_markdown(plan, task)

            # PHASE 6: Stream the formatted markdown LINE BY LINE
            # CRITICAL: Stream by lines to avoid cutting words in the middle!
            # This also helps the BlockDetector identify markdown blocks properly
            lines = formatted_markdown.split('\n')
            for line in lines:
                yield {"type": "thinking", "data": line + "\n"}
                await asyncio.sleep(0.005)  # 5ms delay for smooth visual

            # PHASE 7: Return Result (NO formatted_markdown - already streamed!)
            yield {"type": "status", "data": "✅ Plan complete!"}

            yield {
                "type": "result",
                "data": AgentResponse(
                    success=True,
                    data={
                        "plan": plan,
                        "sops": plan.get("sops", []) if isinstance(plan, dict) else [],
                        # NOTE: formatted_markdown NOT included to avoid duplication
                    },
                    reasoning=f"Generated plan with {len(plan.get('sops', []) if isinstance(plan, dict) else [])} steps"
                )
            }

        except Exception as e:
            self.logger.exception(f"[{trace_id}] Planning error: {e}")
            yield {"type": "error", "data": {"error": str(e), "trace_id": trace_id}}

    # =========================================================================
    # NEW v6.0: CLARIFYING QUESTIONS (Cursor 2.1 Pattern)
    # =========================================================================

    def set_question_callback(self, callback: Callable[[List[ClarifyingQuestion]], List[ClarificationResponse]]):
        """Set callback for asking clarifying questions to user."""
        self._question_callback = callback

    def set_approval_callback(self, callback: Callable[[ExecutionPlan], bool]):
        """Set callback for getting user approval before execution."""
        self._approval_callback = callback

    async def _generate_clarifying_questions(
        self,
        task: AgentTask
    ) -> List[ClarifyingQuestion]:
        """
        Generate 2-3 targeted clarifying questions based on the task.

        Inspired by Cursor 2.1's approach of asking questions before planning.
        """
        prompt = f"""Analyze this task and generate 2-3 clarifying questions that would help create a better plan.

TASK: {task.request}

CONTEXT: {json.dumps(task.context, indent=2) if task.context else "None provided"}

Generate questions in this JSON format:
{{
  "questions": [
    {{
      "question": "The question text",
      "category": "scope|approach|constraints|preferences",
      "options": ["Option 1", "Option 2", "Option 3"],
      "required": true/false
    }}
  ]
}}

Focus on:
1. SCOPE: What's included/excluded from the task?
2. APPROACH: Which implementation strategy to use?
3. CONSTRAINTS: Any limitations or requirements?
4. PREFERENCES: Code style, testing preferences, etc?

Respond with ONLY the JSON, no explanation."""

        try:
            response = await self._call_llm(prompt)
            data = self._robust_json_parse(response)

            if data and "questions" in data:
                questions = []
                for q in data["questions"][:3]:  # Max 3 questions
                    questions.append(ClarifyingQuestion(
                        question=q.get("question", ""),
                        category=q.get("category", "general"),
                        options=q.get("options", []),
                        required=q.get("required", False)
                    ))
                return questions
        except Exception as e:
            self.logger.warning(f"Failed to generate clarifying questions: {e}")

        # Fallback: Default questions
        return [
            ClarifyingQuestion(
                question="What is the scope of this task? (e.g., single file, module, entire project)",
                category="scope",
                options=["Single file", "Module/directory", "Entire project"],
                required=False
            ),
            ClarifyingQuestion(
                question="Do you want tests written for the changes?",
                category="preferences",
                options=["Yes, with high coverage", "Basic tests only", "No tests needed"],
                required=False
            )
        ]

    async def execute_with_clarification(
        self,
        task: AgentTask,
        responses: Optional[List[ClarificationResponse]] = None
    ) -> AgentResponse:
        """
        Execute planning with optional clarifying questions.

        This is the v6.0 enhanced entry point that:
        1. Generates clarifying questions (if enabled)
        2. Waits for user responses (via callback)
        3. Incorporates responses into planning
        4. Generates plan with confidence ratings
        5. Creates plan.md artifact
        """
        clarifying_questions: List[ClarifyingQuestion] = []
        clarification_responses: List[ClarificationResponse] = responses or []

        # Step 1: Generate and ask clarifying questions
        if self.ask_clarifying_questions and not responses:
            clarifying_questions = await self._generate_clarifying_questions(task)

            if clarifying_questions and self._question_callback:
                try:
                    clarification_responses = self._question_callback(clarifying_questions)
                except Exception as e:
                    self.logger.warning(f"Question callback failed: {e}")

        # Step 2: Enrich task context with clarification responses
        enriched_context = task.context.copy() if task.context else {}
        enriched_context["clarifications"] = {
            r.question_id: r.answer
            for r in clarification_responses
            if not r.skipped
        }

        enriched_task = AgentTask(
            task_id=task.task_id,
            request=task.request,
            context=enriched_context,
            session_id=task.session_id,
            metadata=task.metadata
        )

        # Step 3: Execute standard planning
        response = await self.execute(enriched_task)

        # Step 4: Enhance response with v6.0 features
        if response.success and "plan" in response.data:
            plan_data = response.data["plan"]

            # Add clarifying questions to plan
            if isinstance(plan_data, dict):
                plan_data["clarifying_questions"] = [q.model_dump() for q in clarifying_questions]
                plan_data["clarification_responses"] = [r.model_dump() for r in clarification_responses]

                # Calculate overall confidence
                sops = plan_data.get("sops", [])
                if sops:
                    confidence_scores = [s.get("confidence_score", 0.7) for s in sops]
                    plan_data["overall_confidence"] = sum(confidence_scores) / len(confidence_scores)
                    plan_data["confidence_summary"] = self._generate_confidence_summary(
                        plan_data["overall_confidence"]
                    )

                # Generate plan.md artifact
                artifact_path = await self._generate_plan_artifact(plan_data, task)
                if artifact_path:
                    plan_data["plan_artifact_path"] = artifact_path

        return response

    # =========================================================================
    # NEW v6.0: CONFIDENCE RATINGS (Devin Pattern)
    # =========================================================================

    def _calculate_step_confidence(
        self,
        step: SOPStep,
        context: Dict[str, Any]
    ) -> Tuple[float, str, List[str]]:
        """
        Calculate confidence score for a planning step.

        Factors:
        - Role familiarity (how common is this operation)
        - Dependency complexity (more deps = lower confidence)
        - Cost (higher cost = more complex = lower confidence)
        - Priority (critical steps get extra scrutiny)

        Returns:
            (score, reasoning, risk_factors)
        """
        score = 0.8  # Base confidence
        reasoning_parts = []
        risks = []

        # Factor 1: Role familiarity
        familiar_roles = {"architect", "coder", "tester", "reviewer", "documenter"}
        if step.role.lower() in familiar_roles:
            score += 0.05
            reasoning_parts.append("familiar role")
        else:
            score -= 0.1
            risks.append(f"Unfamiliar role: {step.role}")

        # Factor 2: Dependency complexity
        dep_count = len(step.dependencies)
        if dep_count == 0:
            score += 0.05
            reasoning_parts.append("no dependencies")
        elif dep_count <= 2:
            pass  # Neutral
        else:
            score -= 0.05 * (dep_count - 2)
            risks.append(f"High dependency count: {dep_count}")

        # Factor 3: Cost/complexity
        if step.cost <= 1.0:
            score += 0.05
            reasoning_parts.append("low complexity")
        elif step.cost <= 3.0:
            pass  # Neutral
        else:
            score -= 0.1
            risks.append(f"High complexity (cost={step.cost})")

        # Factor 4: Priority risk
        if step.priority == AgentPriority.CRITICAL:
            score -= 0.05
            risks.append("Critical priority increases risk exposure")

        # Clamp score
        score = max(0.1, min(1.0, score))

        reasoning = f"Confidence {score:.2f}: " + ", ".join(reasoning_parts) if reasoning_parts else f"Base confidence: {score:.2f}"

        return score, reasoning, risks

    def _generate_confidence_summary(self, overall_confidence: float) -> str:
        """Generate human-readable confidence summary."""
        if overall_confidence >= 0.9:
            return "🟢 HIGH CONFIDENCE: This plan is well-understood with low risk."
        elif overall_confidence >= 0.7:
            return "🟡 GOOD CONFIDENCE: Plan is solid with manageable risks."
        elif overall_confidence >= 0.5:
            return "🟠 MODERATE CONFIDENCE: Some uncertainty exists. Review carefully."
        elif overall_confidence >= 0.3:
            return "🔴 LOW CONFIDENCE: Significant uncertainty. Consider breaking into smaller tasks."
        else:
            return "⚫ SPECULATIVE: High uncertainty. Recommend exploration before execution."

    # =========================================================================
    # NEW v6.0: PLAN.MD ARTIFACT (Claude Code Pattern)
    # =========================================================================

    async def _generate_plan_artifact(
        self,
        plan_data: Dict[str, Any],
        task: AgentTask
    ) -> Optional[str]:
        """
        Generate a plan.md file for user tracking.

        Inspired by Claude Code's plan mode that generates a structured
        markdown file with checkboxes for each step.
        """
        try:
            # Ensure directory exists
            artifact_dir = Path(self.plan_artifact_dir)
            artifact_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plan_id = plan_data.get("plan_id", "unknown")[:8]
            filename = f"plan_{timestamp}_{plan_id}.md"
            filepath = artifact_dir / filename

            # Generate markdown content
            content = self._format_plan_as_markdown(plan_data, task)

            # Write file
            filepath.write_text(content, encoding="utf-8")

            self.logger.info(f"Generated plan artifact: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.warning(f"Failed to generate plan artifact: {e}")
            return None

    def _format_plan_as_markdown(
        self,
        plan_data: Dict[str, Any],
        task: AgentTask
    ) -> str:
        """Format plan as structured markdown with checkboxes."""
        lines = [
            f"# 📋 Execution Plan",
            f"",
            f"**Goal:** {plan_data.get('goal', task.request)}",
            f"",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"**Confidence:** {plan_data.get('confidence_summary', 'Not calculated')}",
            f"",
            f"---",
            f"",
            f"## Strategy Overview",
            f"",
            f"{plan_data.get('strategy_overview', 'Sequential execution of planned steps.')}",
            f"",
        ]

        # Add clarifying questions and responses
        questions = plan_data.get("clarifying_questions", [])
        responses = plan_data.get("clarification_responses", [])
        if questions:
            lines.extend([
                f"## Clarifications",
                f"",
            ])
            response_map = {r.get("question_id"): r.get("answer") for r in responses}
            for q in questions:
                answer = response_map.get(q.get("id"), "Not answered")
                lines.append(f"- **Q:** {q.get('question', 'Unknown')}")
                lines.append(f"  - **A:** {answer}")
            lines.append("")

        # Add stages/steps with checkboxes
        lines.extend([
            f"## Execution Steps",
            f"",
        ])

        stages = plan_data.get("stages", [])
        # Fallback: accept multiple common formats for steps
        sops = (
            plan_data.get("sops") or
            plan_data.get("steps") or
            plan_data.get("tasks") or
            plan_data.get("actions") or
            (plan_data.get("plan") if isinstance(plan_data.get("plan"), list) else None) or
            []
        )

        if stages:
            for stage in stages:
                lines.append(f"### {stage.get('name', 'Stage')}")
                lines.append(f"")
                lines.append(f"*{stage.get('description', '')}*")
                lines.append(f"")
                for step in stage.get("steps", []):
                    confidence = step.get("confidence_score", 0.7)
                    conf_emoji = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🔴"
                    lines.append(f"- [ ] **{step.get('id')}** ({step.get('role')}): {step.get('action')}")
                    lines.append(f"  - {conf_emoji} Confidence: {confidence:.0%}")
                    lines.append(f"  - ✅ Done when: {step.get('definition_of_done', 'Completed')}")
                lines.append("")
        elif sops:
            for i, step in enumerate(sops, 1):
                # Handle case where step is just a string
                if isinstance(step, str):
                    action = step
                    step_id = f"step-{i}"
                    role = "executor"
                    confidence = 0.7
                    done_when = "Completed"
                elif isinstance(step, dict):
                    # Robust field extraction with fallbacks
                    step_id = step.get("id") or step.get("step_id") or f"step-{i}"
                    action = (
                        step.get("action") or
                        step.get("description") or
                        step.get("task") or
                        step.get("name") or
                        step.get("title") or
                        "No description"
                    )
                    role = step.get("role") or step.get("agent") or step.get("type") or "executor"
                    raw_conf = step.get("confidence_score") or step.get("confidence") or 0.7
                    try:
                        confidence = float(raw_conf)
                    except (ValueError, TypeError):
                        confidence = 0.7
                    done_when = (
                        step.get("definition_of_done") or
                        step.get("done_when") or
                        step.get("success_criteria") or
                        step.get("criteria") or
                        "Completed"
                    )
                else:
                    # Unknown type, convert to string
                    action = str(step)
                    step_id = f"step-{i}"
                    role = "executor"
                    confidence = 0.7
                    done_when = "Completed"

                conf_emoji = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🔴"
                lines.append(f"- [ ] **{step_id}** ({role}): {action}")
                lines.append(f"  - {conf_emoji} Confidence: {confidence:.0%}")
                lines.append(f"  - ✅ Done when: {done_when}")
            lines.append("")

        # Add risk assessment
        lines.extend([
            f"## Risk Assessment",
            f"",
            f"**Level:** {plan_data.get('risk_assessment', 'MEDIUM')}",
            f"",
            f"**Rollback Strategy:** {plan_data.get('rollback_strategy', 'Restore from last checkpoint')}",
            f"",
        ])

        # Add resource estimates
        lines.extend([
            f"## Resources",
            f"",
            f"- **Estimated Duration:** {plan_data.get('estimated_duration', 'Unknown')}",
            f"- **Token Budget:** {plan_data.get('token_budget', 'Unknown')}",
            f"- **Max Parallel Agents:** {plan_data.get('max_parallel_agents', 1)}",
            f"",
        ])

        # Footer
        lines.extend([
            f"---",
            f"",
            f"*Generated by PlannerAgent v6.0 \"Espetacular\"*",
        ])

        return "\n".join(lines)

    # =========================================================================
    # NEW v6.0: EXPLORATION MODE (Claude Plan Mode Pattern)
    # =========================================================================

    async def explore(self, task: AgentTask) -> AgentResponse:
        """
        Execute in exploration mode - read-only analysis.

        Like Claude Code's Plan Mode, this gathers context and analyzes
        the task without making any modifications.

        Use this before execute() to understand the problem space.
        """
        self.current_mode = PlanningMode.EXPLORATION

        # Restrict to read-only operations
        original_capabilities = self.capabilities.copy()
        self.capabilities = [AgentCapability.READ_ONLY]

        try:
            # Gather context
            context = await self._gather_context(task)

            # Analyze task requirements
            analysis_prompt = f"""Analyze this task in EXPLORATION mode (read-only).

TASK: {task.request}

CONTEXT:
{json.dumps(context, indent=2)}

Provide:
1. UNDERSTANDING: What is being requested?
2. SCOPE: What files/systems are involved?
3. COMPLEXITY: How complex is this task? (Simple/Medium/Complex)
4. RISKS: What could go wrong?
5. QUESTIONS: What clarifications would help?
6. APPROACH: Suggested high-level approach

Respond in JSON format."""

            response = await self._call_llm(analysis_prompt)
            analysis = self._robust_json_parse(response)

            return AgentResponse(
                success=True,
                data={
                    "mode": "exploration",
                    "analysis": analysis or {"raw": response},
                    "context": context
                },
                reasoning="Exploration complete. Ready for planning phase.",
                metadata={"mode": PlanningMode.EXPLORATION.value}
            )

        finally:
            # Restore capabilities
            self.capabilities = original_capabilities
            self.current_mode = PlanningMode.PLANNING

    # =========================================================================
    # NEW v6.1: MULTI-PLAN GENERATION (Verbalized Sampling)
    # =========================================================================

    async def generate_multi_plan(
        self,
        task: AgentTask,
        strategies: Optional[List[PlanStrategy]] = None
    ) -> MultiPlanResult:
        """
        Generate multiple alternative plans using Verbalized Sampling.

        Based on Zhang et al. (2025) - instead of generating one "average" plan,
        we explore the latent space of possibilities with distinct approaches:

        - STANDARD: Conventional, low-risk path
        - ACCELERATOR: High-speed, higher-risk approach
        - LATERAL: Creative/unconventional solution

        Each plan includes verbalized probabilities:
        - P(Success): Probability of achieving the goal
        - P(Friction): Probability of encountering blockers
        - P(Quality): Probability of high-quality output

        Returns:
            MultiPlanResult with all plans and recommendation
        """
        import time
        start_time = time.time()

        strategies = strategies or [
            PlanStrategy.STANDARD,
            PlanStrategy.ACCELERATOR,
            PlanStrategy.LATERAL
        ]

        # Gather context once
        context = await self._gather_context(task)

        # Generate each plan type
        plans: List[AlternativePlan] = []

        for strategy in strategies:
            try:
                plan = await self._generate_plan_variant(task, context, strategy)
                if plan:
                    plans.append(plan)
            except Exception as e:
                self.logger.warning(f"Failed to generate {strategy.value} plan: {e}")

        # If no plans generated, create a basic standard plan
        if not plans:
            basic_plan = self._create_fallback_plan(task, PlanStrategy.STANDARD)
            plans.append(basic_plan)

        # Select best plan
        recommended, reasoning = self._select_best_plan(plans, task)

        # Build comparison summary
        comparison = self._build_comparison_summary(plans)

        generation_time = int((time.time() - start_time) * 1000)

        return MultiPlanResult(
            task_summary=task.request[:200],
            plans=plans,
            recommended_plan=recommended,
            recommendation_reasoning=reasoning,
            comparison_summary=comparison,
            generation_time_ms=generation_time
        )

    async def _generate_plan_variant(
        self,
        task: AgentTask,
        context: Dict[str, Any],
        strategy: PlanStrategy
    ) -> Optional[AlternativePlan]:
        """Generate a single plan variant for a specific strategy."""

        strategy_prompts = {
            PlanStrategy.STANDARD: """
Generate a STANDARD plan - the conventional, low-risk approach.
Focus on:
- Proven patterns and best practices
- Step-by-step sequential execution
- Comprehensive validation at each step
- Prefer stability over speed
""",
            PlanStrategy.ACCELERATOR: """
Generate an ACCELERATOR plan - high-speed, parallel execution approach.
Focus on:
- Maximum parallelization of independent tasks
- Aggressive timelines
- Minimal validation (fail-fast approach)
- Accept higher risk for faster delivery
""",
            PlanStrategy.LATERAL: """
Generate a LATERAL plan - creative, unconventional approach.
Focus on:
- Alternative solutions that others might not consider
- Novel use of tools or patterns
- Potential shortcuts or innovations
- "What if we approached this completely differently?"
"""
        }

        prompt = f"""You are generating a {strategy.value.upper()} execution plan.

TASK: {task.request}

CONTEXT:
{json.dumps(context, indent=2)}

{strategy_prompts.get(strategy, "")}

Generate a plan with VERBALIZED PROBABILITIES. Think explicitly about:
- P(Success): How likely is this approach to succeed? (0.0-1.0)
- P(Friction): How likely are we to hit blockers? (0.0-1.0)
- P(TimeOverrun): How likely to take longer than estimated? (0.0-1.0)
- P(Quality): How likely to produce high-quality output? (0.0-1.0)

OUTPUT JSON FORMAT:
{{
  "name": "Short descriptive name for this plan variant",
  "description": "Brief description of the approach",
  "p_success": 0.XX,
  "p_friction": 0.XX,
  "p_time_overrun": 0.XX,
  "p_quality": 0.XX,
  "pros": ["advantage 1", "advantage 2"],
  "cons": ["disadvantage 1", "disadvantage 2"],
  "best_for": "When this plan is the best choice",
  "sops": [
    {{
      "id": "step-1",
      "role": "agent_role",
      "action": "What to do",
      "objective": "Why",
      "definition_of_done": "Success criteria",
      "dependencies": [],
      "cost": 1.0,
      "confidence_score": 0.XX
    }}
  ]
}}

RESPOND WITH PURE JSON ONLY."""

        try:
            response = await self._call_llm(prompt)
            data = self._robust_json_parse(response)

            if not data:
                return None

            return AlternativePlan(
                strategy=strategy,
                name=data.get("name", f"{strategy.value.title()} Plan"),
                description=data.get("description", ""),
                plan=data,
                p_success=float(data.get("p_success", 0.7)),
                p_friction=float(data.get("p_friction", 0.3)),
                p_time_overrun=float(data.get("p_time_overrun", 0.3)),
                p_quality=float(data.get("p_quality", 0.7)),
                pros=data.get("pros", []),
                cons=data.get("cons", []),
                best_for=data.get("best_for", "")
            )

        except Exception as e:
            self.logger.error(f"Failed to generate {strategy.value} variant: {e}")
            return None

    def _create_fallback_plan(
        self,
        task: AgentTask,
        strategy: PlanStrategy
    ) -> AlternativePlan:
        """Create a basic fallback plan when LLM generation fails."""
        return AlternativePlan(
            strategy=strategy,
            name="Basic Sequential Plan",
            description="Fallback plan with standard sequential execution",
            plan={
                "sops": [
                    {
                        "id": "step-1",
                        "role": "architect",
                        "action": "Analyze and plan",
                        "objective": "Understand requirements",
                        "definition_of_done": "Plan documented",
                        "cost": 2.0
                    },
                    {
                        "id": "step-2",
                        "role": "coder",
                        "action": "Implement solution",
                        "objective": "Write code",
                        "definition_of_done": "Code compiles",
                        "dependencies": ["step-1"],
                        "cost": 5.0
                    },
                    {
                        "id": "step-3",
                        "role": "tester",
                        "action": "Test implementation",
                        "objective": "Verify correctness",
                        "definition_of_done": "Tests pass",
                        "dependencies": ["step-2"],
                        "cost": 3.0
                    }
                ]
            },
            p_success=0.7,
            p_friction=0.3,
            p_time_overrun=0.4,
            p_quality=0.6,
            pros=["Simple and predictable", "Easy to follow"],
            cons=["May not be optimal", "No parallelization"],
            best_for="When other approaches fail or for simple tasks"
        )

    def _select_best_plan(
        self,
        plans: List[AlternativePlan],
        task: AgentTask
    ) -> Tuple[PlanStrategy, str]:
        """
        Select the best plan based on overall score and task characteristics.

        Uses a weighted scoring system that considers:
        - Success probability (most important)
        - Friction probability (risk factor)
        - Quality probability
        - Time overrun probability
        """
        if not plans:
            return PlanStrategy.STANDARD, "No plans available, defaulting to standard"

        # Sort by overall score
        sorted_plans = sorted(plans, key=lambda p: p.overall_score, reverse=True)
        best = sorted_plans[0]

        # Build reasoning
        reasoning_parts = [
            f"Selected {best.strategy.value.upper()} with score {best.overall_score:.2f}.",
        ]

        if best.p_success >= 0.8:
            reasoning_parts.append(f"High success probability ({best.p_success:.0%}).")
        if best.p_friction <= 0.3:
            reasoning_parts.append(f"Low friction risk ({best.p_friction:.0%}).")

        # Compare to alternatives
        if len(sorted_plans) > 1:
            runner_up = sorted_plans[1]
            score_diff = best.overall_score - runner_up.overall_score
            if score_diff < 0.1:
                reasoning_parts.append(
                    f"Close call with {runner_up.strategy.value.upper()} "
                    f"(score diff: {score_diff:.2f})."
                )

        return best.strategy, " ".join(reasoning_parts)

    def _build_comparison_summary(self, plans: List[AlternativePlan]) -> str:
        """Build a comparison summary of all plans."""
        if not plans:
            return "No plans to compare."

        lines = ["Plan Comparison:"]
        for plan in sorted(plans, key=lambda p: p.overall_score, reverse=True):
            lines.append(
                f"  {plan.strategy.value.upper()}: "
                f"Score={plan.overall_score:.2f} | "
                f"Success={plan.p_success:.0%} | "
                f"Friction={plan.p_friction:.0%}"
            )

        return "\n".join(lines)

    async def execute_with_multi_plan(
        self,
        task: AgentTask,
        auto_select: bool = True,
        preferred_strategy: Optional[PlanStrategy] = None
    ) -> AgentResponse:
        """
        Execute planning with multi-plan generation.

        This is the ultimate v6.1 entry point that:
        1. Generates 3 alternative plans (Standard/Accelerator/Lateral)
        2. Calculates probabilities for each
        3. Recommends the best plan
        4. Optionally executes the selected plan

        Args:
            task: The task to plan
            auto_select: If True, automatically use recommended plan
            preferred_strategy: Override recommendation with specific strategy
        """
        # Generate multi-plan
        multi_result = await self.generate_multi_plan(task)

        # Select plan
        if preferred_strategy:
            selected = multi_result.get_plan(preferred_strategy)
            if not selected:
                selected = multi_result.get_recommended()
        elif auto_select:
            selected = multi_result.get_recommended()
        else:
            # Return multi-plan result for user selection
            return AgentResponse(
                success=True,
                data={
                    "multi_plan": multi_result.model_dump(),
                    "requires_selection": True,
                    "markdown": multi_result.to_markdown()
                },
                reasoning=f"Generated {len(multi_result.plans)} alternative plans. "
                          f"Recommended: {multi_result.recommended_plan.value.upper()}",
                metadata={"mode": "multi_plan_selection"}
            )

        # Execute the selected plan
        if selected:
            # Create a task with the selected plan's SOPs
            plan_data = selected.plan
            return AgentResponse(
                success=True,
                data={
                    "plan": plan_data,
                    "selected_strategy": selected.strategy.value,
                    "probabilities": selected.probabilities.to_display(),
                    "multi_plan_summary": multi_result.comparison_summary,
                    "sops": plan_data.get("sops", [])
                },
                reasoning=f"Executing {selected.strategy.value.upper()} plan: {selected.name}. "
                          f"{multi_result.recommendation_reasoning}",
                metadata={
                    "mode": "multi_plan_execution",
                    "strategy": selected.strategy.value,
                    "overall_score": selected.overall_score
                }
            )

        return AgentResponse(
            success=False,
            error="No plan could be generated",
            reasoning="All plan generation attempts failed."
        )


# ============================================================================
# PLAN VALIDATOR - Quality Assurance
# ============================================================================

class PlanValidator:
    """
    Validates execution plans before execution.
    Catches issues early to prevent runtime failures.
    """
    
    @staticmethod
    def validate(plan: ExecutionPlan) -> Tuple[bool, List[str]]:
        """
        Validate plan for common issues.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check 1: No circular dependencies
        sop_map = {sop.id: sop for sop in plan.sops}
        visited = set()
        rec_stack = set()
        
        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = sop_map.get(step_id)
            if not step:
                return False
            
            for dep_id in step.dependencies:
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    errors.append(f"Circular dependency detected involving step {step_id}")
                    return True
            
            rec_stack.remove(step_id)
            return False
        
        for sop in plan.sops:
            if sop.id not in visited:
                has_cycle(sop.id)
        
        # Check 2: All dependencies exist
        all_ids = {sop.id for sop in plan.sops}
        for sop in plan.sops:
            for dep in sop.dependencies:
                if dep not in all_ids:
                    errors.append(f"Step {sop.id} depends on non-existent step {dep}")
        
        # Check 3: At least one step without dependencies (entry point)
        entry_points = [sop for sop in plan.sops if not sop.dependencies]
        if not entry_points:
            errors.append("No entry point found - all steps have dependencies")
        
        # Check 4: Resource budget is reasonable
        if plan.token_budget > 200000:
            errors.append(f"Token budget ({plan.token_budget}) exceeds recommended limit (200k)")
        
        # Check 5: Each stage is reachable
        if plan.stages:
            for stage in plan.stages:
                if not stage.steps:
                    errors.append(f"Empty stage detected: {stage.name}")
        
        # Check 6: Critical steps have checkpoints
        critical_steps = [s for s in plan.sops if s.priority == AgentPriority.CRITICAL]
        critical_with_checkpoints = [s for s in critical_steps if s.checkpoint]
        if critical_steps and not critical_with_checkpoints:
            errors.append("Critical steps found but no checkpoints defined")
        
        return len(errors) == 0, errors

# ============================================================================
# EXECUTION MONITOR - Observability Hook
# ============================================================================

@dataclass
class ExecutionEvent:
    """Event emitted during plan execution for observability"""
    timestamp: str
    event_type: str  # started, completed, failed, checkpoint
    step_id: str
    agent_role: str
    correlation_id: str
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class ExecutionMonitor:
    """
    Observability layer for plan execution.
    Emits events compatible with OpenTelemetry.
    """
    
    def __init__(self):
        self.events: List[ExecutionEvent] = []
    
    def emit(self, event: ExecutionEvent):
        """Emit execution event"""
        self.events.append(event)
        # In production: Send to OpenTelemetry, DataDog, etc.
        print(f"[{event.timestamp}] {event.event_type}: {event.step_id} ({event.agent_role})")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics"""
        completed = [e for e in self.events if e.event_type == "completed"]
        failed = [e for e in self.events if e.event_type == "failed"]
        
        return {
            "total_events": len(self.events),
            "completed_steps": len(completed),
            "failed_steps": len(failed),
            "success_rate": len(completed) / max(len(self.events), 1),
            "avg_duration_ms": sum(e.duration_ms or 0 for e in completed) / max(len(completed), 1)
        }
