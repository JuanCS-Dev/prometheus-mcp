"""
World Model - SimuRA-inspired Simulation Engine.

References:
- SimuRA (arXiv:2507.23773): +124% task completion with world model planning
- Dyna-Think (arXiv:2506.00320): 2x fewer tokens with internal simulation

The World Model enables the agent to:
1. Simulate consequences before acting
2. Plan action sequences
3. Avoid predictable errors
4. Learn from simulations (not just real executions)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import json
import re


class ActionType(Enum):
    """Types of actions the agent can take."""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    EXECUTE_CODE = "execute_code"
    SEARCH = "search"
    API_CALL = "api_call"
    THINK = "think"
    ASK_USER = "ask_user"
    CREATE_TOOL = "create_tool"
    USE_TOOL = "use_tool"


@dataclass
class WorldState:
    """State of the world at a point in time."""
    files: Dict[str, str] = field(default_factory=dict)  # path -> content/status
    variables: Dict[str, Any] = field(default_factory=dict)
    executed_actions: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    resources_used: Dict[str, float] = field(default_factory=lambda: {
        "tokens": 0,
        "api_calls": 0,
        "time_seconds": 0,
    })
    success_probability: float = 1.0
    confidence: float = 1.0

    def clone(self) -> "WorldState":
        """Create a deep copy of the state."""
        return WorldState(
            files=self.files.copy(),
            variables=self.variables.copy(),
            executed_actions=self.executed_actions.copy(),
            errors_encountered=self.errors_encountered.copy(),
            resources_used=self.resources_used.copy(),
            success_probability=self.success_probability,
            confidence=self.confidence,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "files_known": list(self.files.keys()),
            "variables": self.variables,
            "actions_taken": len(self.executed_actions),
            "errors": len(self.errors_encountered),
            "success_probability": self.success_probability,
        }


@dataclass
class SimulatedAction:
    """An action with its predicted consequences."""
    action_type: ActionType
    parameters: Dict[str, Any]
    predicted_outcome: str
    success_probability: float
    side_effects: List[str]
    risks: List[str]
    estimated_tokens: int = 0
    estimated_time: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "action": self.action_type.value,
            "parameters": self.parameters,
            "outcome": self.predicted_outcome,
            "success_prob": self.success_probability,
            "risks": self.risks,
        }


@dataclass
class SimulationResult:
    """Result of a complete simulation."""
    initial_state: WorldState
    final_state: WorldState
    actions_taken: List[SimulatedAction]
    overall_success_probability: float
    total_estimated_tokens: int
    total_estimated_time: float
    critical_risks: List[str]
    plan_summary: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success_probability": self.overall_success_probability,
            "actions_count": len(self.actions_taken),
            "estimated_tokens": self.total_estimated_tokens,
            "critical_risks": self.critical_risks,
            "summary": self.plan_summary,
        }


class WorldModel:
    """
    Internal Simulation Engine.

    Allows the agent to "imagine" consequences of actions
    before executing them in the real world.
    """

    # Token estimates per action type
    TOKEN_ESTIMATES = {
        ActionType.READ_FILE: 500,
        ActionType.WRITE_FILE: 200,
        ActionType.EDIT_FILE: 300,
        ActionType.EXECUTE_CODE: 400,
        ActionType.SEARCH: 600,
        ActionType.API_CALL: 800,
        ActionType.THINK: 1000,
        ActionType.ASK_USER: 100,
        ActionType.CREATE_TOOL: 1500,
        ActionType.USE_TOOL: 400,
    }

    # Time estimates per action type (seconds)
    TIME_ESTIMATES = {
        ActionType.READ_FILE: 0.5,
        ActionType.WRITE_FILE: 0.3,
        ActionType.EDIT_FILE: 0.5,
        ActionType.EXECUTE_CODE: 5.0,
        ActionType.SEARCH: 2.0,
        ActionType.API_CALL: 3.0,
        ActionType.THINK: 2.0,
        ActionType.ASK_USER: 30.0,
        ActionType.CREATE_TOOL: 10.0,
        ActionType.USE_TOOL: 3.0,
    }

    def __init__(self, llm_client):
        self.llm = llm_client
        self.state_history: List[WorldState] = []
        self.learned_patterns: Dict[str, float] = {}  # pattern -> success_rate
        self.simulation_cache: Dict[str, SimulatedAction] = {}

    async def simulate_action(
        self,
        action: ActionType,
        parameters: dict,
        current_state: WorldState,
    ) -> Tuple[SimulatedAction, WorldState]:
        """
        Simulate a single action and predict its outcome.

        Uses LLM to predict:
        1. Likely outcome
        2. Success probability
        3. Side effects
        4. Potential risks
        """
        # Check cache
        cache_key = f"{action.value}:{json.dumps(parameters, sort_keys=True)}"
        if cache_key in self.simulation_cache:
            cached = self.simulation_cache[cache_key]
            new_state = self._apply_simulated_action(current_state, cached)
            return cached, new_state

        # Build simulation prompt
        simulation_prompt = f"""You are a world model simulator. Given an action and current state, predict the outcome.

CURRENT STATE:
- Files known: {list(current_state.files.keys())[:10]}
- Variables: {dict(list(current_state.variables.items())[:5])}
- Previous actions: {current_state.executed_actions[-5:]}
- Errors so far: {current_state.errors_encountered[-3:]}
- Current success probability: {current_state.success_probability:.2f}

ACTION TO SIMULATE:
- Type: {action.value}
- Parameters: {json.dumps(parameters, indent=2)}

Based on the action type and parameters, predict:
1. What will likely happen
2. Probability of success (0.0-1.0)
3. Any side effects
4. Potential risks

Respond in JSON format:
{{
    "predicted_outcome": "description of what will happen",
    "success_probability": 0.85,
    "side_effects": ["effect1", "effect2"],
    "risks": ["risk1", "risk2"],
    "state_changes": {{
        "files_modified": ["path1"],
        "variables_changed": {{"var": "value"}},
        "errors_possible": ["error1"]
    }}
}}"""

        try:
            response = await self.llm.generate(simulation_prompt)
            prediction = self._parse_json_response(response)
        except Exception as e:
            # Fallback to conservative prediction
            prediction = {
                "predicted_outcome": f"Execute {action.value} with uncertain outcome",
                "success_probability": 0.5,
                "side_effects": [],
                "risks": [f"Simulation error: {str(e)}"],
                "state_changes": {}
            }

        # Create simulated action
        simulated = SimulatedAction(
            action_type=action,
            parameters=parameters,
            predicted_outcome=prediction.get("predicted_outcome", "Unknown"),
            success_probability=prediction.get("success_probability", 0.5),
            side_effects=prediction.get("side_effects", []),
            risks=prediction.get("risks", []),
            estimated_tokens=self.TOKEN_ESTIMATES.get(action, 500),
            estimated_time=self.TIME_ESTIMATES.get(action, 1.0),
        )

        # Cache the simulation
        self.simulation_cache[cache_key] = simulated

        # Apply state changes
        new_state = self._apply_simulated_action(current_state, simulated, prediction.get("state_changes", {}))

        return simulated, new_state

    async def simulate_plan(
        self,
        plan: List[Tuple[ActionType, dict]],
        initial_state: Optional[WorldState] = None,
    ) -> SimulationResult:
        """
        Simulate a complete plan of actions.

        Returns comprehensive result with probabilities and risks.
        """
        if initial_state is None:
            initial_state = WorldState()

        current_state = initial_state.clone()
        actions_taken = []
        critical_risks = []
        total_tokens = 0
        total_time = 0.0

        for action_type, params in plan:
            simulated, new_state = await self.simulate_action(
                action_type, params, current_state
            )
            actions_taken.append(simulated)
            total_tokens += simulated.estimated_tokens
            total_time += simulated.estimated_time

            # Collect critical risks
            for risk in simulated.risks:
                if any(kw in risk.lower() for kw in ["critical", "fatal", "data loss", "security"]):
                    critical_risks.append(risk)

            current_state = new_state

            # Early stop if probability too low
            if current_state.success_probability < 0.1:
                break

        # Generate plan summary
        summary = self._generate_plan_summary(actions_taken)

        return SimulationResult(
            initial_state=initial_state,
            final_state=current_state,
            actions_taken=actions_taken,
            overall_success_probability=current_state.success_probability,
            total_estimated_tokens=total_tokens,
            total_estimated_time=total_time,
            critical_risks=critical_risks,
            plan_summary=summary,
        )

    async def find_best_plan(
        self,
        goal: str,
        available_actions: Optional[List[ActionType]] = None,
        initial_state: Optional[WorldState] = None,
        max_steps: int = 10,
        num_candidates: int = 3,
    ) -> List[SimulationResult]:
        """
        Use Tree of Thoughts to find best plans.

        Generates multiple candidate plans and simulates each.
        Returns top plans sorted by success probability.
        """
        if available_actions is None:
            available_actions = list(ActionType)

        if initial_state is None:
            initial_state = WorldState()

        # Generate candidate plans using LLM
        planning_prompt = f"""Generate {num_candidates} different plans to achieve this goal.

GOAL: {goal}

AVAILABLE ACTIONS: {[a.value for a in available_actions]}

CURRENT STATE:
{json.dumps(initial_state.to_dict(), indent=2)}

For each plan, provide a sequence of actions. Output {num_candidates} plans as JSON arrays:

Plan 1 (Conservative approach):
[
    {{"action": "action_type", "params": {{"key": "value"}}, "reason": "why this step"}}
]

Plan 2 (Balanced approach):
[...]

Plan 3 (Aggressive/fast approach):
[...]

Each plan should be a valid sequence to achieve the goal."""

        try:
            response = await self.llm.generate(planning_prompt)
            candidate_plans = self._parse_plans(response, available_actions)
        except Exception as e:
            # Fallback: single simple plan
            candidate_plans = [
                [(ActionType.THINK, {"goal": goal})]
            ]

        # Simulate each plan
        results = []
        for plan in candidate_plans[:num_candidates]:
            if plan:  # Skip empty plans
                result = await self.simulate_plan(plan, initial_state)
                results.append(result)

        # Sort by success probability
        results.sort(key=lambda r: r.overall_success_probability, reverse=True)

        return results

    async def evaluate_action_risk(
        self,
        action: ActionType,
        parameters: dict,
        current_state: WorldState,
    ) -> Dict[str, Any]:
        """
        Evaluate risk of a specific action.

        Returns detailed risk assessment.
        """
        simulated, _ = await self.simulate_action(action, parameters, current_state)

        # Categorize risks
        risk_levels = {"low": [], "medium": [], "high": [], "critical": []}

        for risk in simulated.risks:
            risk_lower = risk.lower()
            if any(kw in risk_lower for kw in ["critical", "fatal", "irreversible"]):
                risk_levels["critical"].append(risk)
            elif any(kw in risk_lower for kw in ["data loss", "security", "corruption"]):
                risk_levels["high"].append(risk)
            elif any(kw in risk_lower for kw in ["error", "fail", "slow"]):
                risk_levels["medium"].append(risk)
            else:
                risk_levels["low"].append(risk)

        return {
            "action": action.value,
            "success_probability": simulated.success_probability,
            "risk_levels": risk_levels,
            "recommendation": self._get_recommendation(simulated.success_probability, risk_levels),
            "side_effects": simulated.side_effects,
        }

    def _apply_simulated_action(
        self,
        state: WorldState,
        action: SimulatedAction,
        state_changes: Optional[dict] = None,
    ) -> WorldState:
        """Apply simulated action to state."""
        new_state = state.clone()
        state_changes = state_changes or {}

        # Record action
        new_state.executed_actions.append(
            f"{action.action_type.value}({json.dumps(action.parameters)})"
        )

        # Apply file changes
        for path in state_changes.get("files_modified", []):
            new_state.files[path] = "[MODIFIED]"

        # Apply variable changes
        new_state.variables.update(state_changes.get("variables_changed", {}))

        # Add possible errors
        new_state.errors_encountered.extend(state_changes.get("errors_possible", []))

        # Update success probability
        new_state.success_probability *= action.success_probability

        # Update resource usage
        new_state.resources_used["tokens"] += action.estimated_tokens
        new_state.resources_used["time_seconds"] += action.estimated_time
        new_state.resources_used["api_calls"] += 1

        # Decrease confidence slightly with each action
        new_state.confidence *= 0.95

        return new_state

    def _parse_json_response(self, text: str) -> dict:
        """Extract JSON from LLM response."""
        # Try parsing entire response first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON block with balanced braces
        start = text.find('{')
        if start != -1:
            depth = 0
            end = start
            for i, char in enumerate(text[start:], start):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

            if depth == 0:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

        # Try to find code block with JSON
        code_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                pass

        return {}

    def _parse_plans(
        self,
        response: str,
        available_actions: List[ActionType],
    ) -> List[List[Tuple[ActionType, dict]]]:
        """Parse multiple plans from LLM response."""
        plans = []
        action_map = {a.value: a for a in available_actions}

        # Find all JSON arrays in response
        json_arrays = re.findall(r'\[[\s\S]*?\]', response)

        for arr_str in json_arrays:
            try:
                arr = json.loads(arr_str)
                plan = []

                for item in arr:
                    if isinstance(item, dict):
                        action_name = item.get("action", "")
                        if action_name in action_map:
                            plan.append((
                                action_map[action_name],
                                item.get("params", item.get("parameters", {}))
                            ))

                if plan:
                    plans.append(plan)

            except json.JSONDecodeError:
                continue

        return plans

    def _generate_plan_summary(self, actions: List[SimulatedAction]) -> str:
        """Generate human-readable plan summary."""
        if not actions:
            return "Empty plan"

        steps = []
        for i, action in enumerate(actions, 1):
            steps.append(f"{i}. {action.action_type.value}: {action.predicted_outcome[:50]}...")

        return "\n".join(steps)

    def _get_recommendation(
        self,
        success_prob: float,
        risk_levels: Dict[str, List[str]],
    ) -> str:
        """Get action recommendation based on analysis."""
        if risk_levels["critical"]:
            return "AVOID: Critical risks detected"
        elif success_prob < 0.3:
            return "NOT RECOMMENDED: Low success probability"
        elif risk_levels["high"]:
            return "CAUTION: High risks present, consider alternatives"
        elif success_prob < 0.6:
            return "PROCEED WITH CAUTION: Moderate success probability"
        elif risk_levels["medium"]:
            return "ACCEPTABLE: Some risks but manageable"
        else:
            return "RECOMMENDED: Good success probability, low risk"

    def learn_pattern(self, action_pattern: str, actual_success: bool):
        """Learn from actual execution outcomes to improve predictions."""
        current = self.learned_patterns.get(action_pattern, 0.5)
        # Exponential moving average
        self.learned_patterns[action_pattern] = 0.8 * current + 0.2 * (1.0 if actual_success else 0.0)

    def get_pattern_success_rate(self, action_pattern: str) -> float:
        """Get learned success rate for a pattern."""
        return self.learned_patterns.get(action_pattern, 0.5)

    def clear_cache(self):
        """Clear simulation cache."""
        self.simulation_cache = {}

    def get_stats(self) -> dict:
        """Get world model statistics."""
        return {
            "cached_simulations": len(self.simulation_cache),
            "learned_patterns": len(self.learned_patterns),
            "state_history_size": len(self.state_history),
        }
