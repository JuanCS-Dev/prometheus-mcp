"""
Executor Agent - Learns to solve tasks.

Reference: Agent0 (arXiv:2511.16043)
- Co-evolution with Curriculum Agent
- Learns from both successes and failures
- Develops skills progressively

The Executor Agent is responsible for:
1. Attempting to solve generated tasks
2. Learning from successes and failures
3. Developing and improving skills
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import json
import re

from .curriculum_agent import EvolutionTask, TaskDifficulty, TaskDomain


@dataclass
class ExecutionResult:
    """Result of executing a task."""
    task: EvolutionTask
    solution: str
    success: bool
    score: float  # 0-1
    time_taken: float  # seconds
    skills_demonstrated: List[str]
    errors_made: List[str]
    reflection: str = ""
    improvement_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_id": self.task.id,
            "success": self.success,
            "score": self.score,
            "time_taken": self.time_taken,
            "skills": self.skills_demonstrated,
            "errors": self.errors_made,
        }


@dataclass
class SkillProfile:
    """Profile of a learned skill."""
    name: str
    proficiency: float  # 0-1
    practice_count: int = 0
    last_practiced: Optional[datetime] = None
    success_history: List[bool] = field(default_factory=list)

    def update(self, success: bool):
        """Update skill based on practice result."""
        self.practice_count += 1
        self.last_practiced = datetime.now()
        self.success_history.append(success)

        # Keep last 20 results
        if len(self.success_history) > 20:
            self.success_history = self.success_history[-20:]

        # Update proficiency with exponential moving average
        alpha = 0.2 if self.practice_count > 5 else 0.5
        self.proficiency = (1 - alpha) * self.proficiency + alpha * (1.0 if success else 0.0)


class ExecutorAgent:
    """
    Learns to solve tasks through practice.

    Develops skills progressively through the co-evolution loop.
    """

    def __init__(
        self,
        llm_client,
        tool_factory,
        memory_system,
        reflection_engine,
        sandbox_executor,
    ):
        self.llm = llm_client
        self.tools = tool_factory
        self.memory = memory_system
        self.reflection = reflection_engine
        self.sandbox = sandbox_executor

        self.skills: Dict[str, SkillProfile] = {}
        self.execution_history: List[ExecutionResult] = []

        # Performance tracking
        self._total_attempts = 0
        self._total_successes = 0

    async def attempt_task(
        self,
        task: EvolutionTask,
        use_hints: bool = False,
        max_retries: int = 2,
    ) -> ExecutionResult:
        """
        Attempt to solve a task.

        Process:
        1. Plan approach
        2. Execute with available tools
        3. Evaluate result
        4. Learn from experience
        """
        start_time = datetime.now()

        # Get relevant context from memory
        context = self.memory.get_context_for_task(task.description)

        # Add hints if requested and available
        hints_section = ""
        if use_hints and task.hints:
            hints_section = f"\nHINTS:\n" + "\n".join(f"- {h}" for h in task.hints)

        # Plan and execute
        solution = await self._generate_solution(task, context, hints_section)

        # Evaluate the solution
        score, errors = await self._evaluate_solution(task, solution)

        # Retry if failed and retries available
        retry_count = 0
        while score < 0.7 and retry_count < max_retries:
            retry_count += 1
            # Get feedback and try again
            improved_solution = await self._improve_solution(task, solution, errors, context)
            solution = improved_solution
            score, errors = await self._evaluate_solution(task, solution)

        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds()

        # Identify skills demonstrated
        skills_demonstrated = self._identify_skills(solution, task)

        # Create result
        result = ExecutionResult(
            task=task,
            solution=solution,
            success=score >= 0.7,
            score=score,
            time_taken=time_taken,
            skills_demonstrated=skills_demonstrated,
            errors_made=errors,
        )

        # Learn from the attempt
        await self._learn_from_result(result)

        # Store in history
        self.execution_history.append(result)
        self._total_attempts += 1
        if result.success:
            self._total_successes += 1

        return result

    async def _generate_solution(
        self,
        task: EvolutionTask,
        context: dict,
        hints_section: str = "",
    ) -> str:
        """Generate a solution for the task."""
        # Format relevant experiences
        experiences_section = ""
        if context.get("relevant_experiences"):
            exp_list = [
                f"- {e.get('content', '')[:100]}"
                for e in context["relevant_experiences"][:3]
            ]
            experiences_section = "\nRELEVANT EXPERIENCES:\n" + "\n".join(exp_list)

        # Format relevant procedures
        procedures_section = ""
        if context.get("relevant_procedures"):
            proc_list = [
                f"- {p.get('skill', '')}: {p.get('steps', [])[:2]}"
                for p in context["relevant_procedures"][:3]
            ]
            procedures_section = "\nRELEVANT PROCEDURES:\n" + "\n".join(proc_list)

        # Available tools
        tools_list = self.tools.list_tools()
        tools_section = "\nAVAILABLE TOOLS:\n" + "\n".join(
            f"- {t['name']}: {t.get('description', 'No description')[:50]}"
            for t in tools_list[:10]
        )

        prompt = f"""Solve this task step by step.

TASK: {task.description}
DIFFICULTY: {task.difficulty.name}
DOMAIN: {task.domain.value}

SUCCESS CRITERIA:
{chr(10).join(f'- {c}' for c in task.success_criteria)}

{experiences_section}
{procedures_section}
{tools_section}
{hints_section}

Think through the problem carefully and provide a complete solution.
If this is a coding task, provide working code.
If this is a reasoning task, show your reasoning step by step.

SOLUTION:"""

        return await self.llm.generate(prompt)

    async def _evaluate_solution(
        self,
        task: EvolutionTask,
        solution: str,
    ) -> Tuple[float, List[str]]:
        """Evaluate a solution against task criteria."""
        errors = []

        # If there are test cases, run them
        if task.test_cases and task.domain == TaskDomain.CODE:
            test_score, test_errors = await self._run_test_cases(task, solution)
            errors.extend(test_errors)
            if test_score is not None:
                return test_score, errors

        # LLM-based evaluation
        prompt = f"""Evaluate this solution against the success criteria.

TASK: {task.description}

SUCCESS CRITERIA:
{chr(10).join(f'- {c}' for c in task.success_criteria)}

SOLUTION:
{solution}

Evaluate each criterion and provide scores in JSON:
{{
    "criterion_scores": {{"criterion": 0.8, ...}},
    "overall_score": 0.0-1.0,
    "errors": ["error 1", "error 2"],
    "what_worked": ["thing that worked"],
    "what_failed": ["thing that failed"]
}}"""

        response = await self.llm.generate(prompt)
        data = self._parse_json_response(response)

        errors.extend(data.get("errors", []))
        errors.extend(data.get("what_failed", []))

        return data.get("overall_score", 0.5), errors

    async def _run_test_cases(
        self,
        task: EvolutionTask,
        solution: str,
    ) -> Tuple[Optional[float], List[str]]:
        """Run test cases for code solutions."""
        if not task.test_cases:
            return None, []

        # Extract code from solution
        code = self._extract_code(solution)
        if not code:
            return 0.0, ["No code found in solution"]

        passed = 0
        errors = []

        for i, test in enumerate(task.test_cases):
            test_input = test.get("input", "")
            expected = test.get("expected_output", test.get("expected", ""))

            test_code = f"""
{code}

# Test case {i + 1}
try:
    result = main({repr(test_input)}) if 'main' in dir() else None
    if result is None:
        # Try to find the main function
        import sys
        for name, obj in list(globals().items()):
            if callable(obj) and not name.startswith('_'):
                try:
                    result = obj({repr(test_input)})
                    break
                except:
                    pass

    expected = {repr(expected)}
    passed = result == expected
    print(f"RESULT: {{result}}")
    print(f"EXPECTED: {{expected}}")
    print(f"PASSED: {{passed}}")
except Exception as e:
    print(f"ERROR: {{e}}")
    print("PASSED: False")
"""

            result = await self.sandbox.execute(test_code, timeout=10)

            if result.success and "PASSED: True" in result.stdout:
                passed += 1
            else:
                error_msg = f"Test {i+1} failed"
                if result.stderr:
                    error_msg += f": {result.stderr[:100]}"
                errors.append(error_msg)

        score = passed / len(task.test_cases) if task.test_cases else 0
        return score, errors

    async def _improve_solution(
        self,
        task: EvolutionTask,
        current_solution: str,
        errors: List[str],
        context: dict,
    ) -> str:
        """Improve a failed solution."""
        prompt = f"""Your previous solution had errors. Fix them.

TASK: {task.description}

PREVIOUS SOLUTION:
{current_solution}

ERRORS:
{chr(10).join(f'- {e}' for e in errors)}

Analyze what went wrong and provide a corrected solution.
Focus on fixing the specific errors mentioned.

IMPROVED SOLUTION:"""

        return await self.llm.generate(prompt)

    def _identify_skills(
        self,
        solution: str,
        task: EvolutionTask,
    ) -> List[str]:
        """Identify skills demonstrated in the solution."""
        demonstrated = set()
        solution_lower = solution.lower()

        # Skill detection patterns
        skill_patterns = {
            "planning": ["step", "plan", "first", "then", "finally", "approach"],
            "code_generation": ["def ", "class ", "import ", "function", "```python"],
            "analysis": ["analyze", "evaluate", "compare", "examine", "observe"],
            "problem_solving": ["solve", "solution", "approach", "method", "strategy"],
            "debugging": ["fix", "bug", "error", "issue", "debug"],
            "optimization": ["optimize", "improve", "efficient", "performance"],
            "reasoning": ["because", "therefore", "thus", "hence", "conclude"],
            "math": ["calculate", "compute", "formula", "equation", "="],
            "tool_use": ["tool", "use", "execute", "run", "call"],
        }

        for skill, keywords in skill_patterns.items():
            if any(kw in solution_lower for kw in keywords):
                demonstrated.add(skill)

        # Add expected skills from task
        demonstrated.update(task.expected_skills)

        return list(demonstrated)

    async def _learn_from_result(self, result: ExecutionResult):
        """Learn from task execution result."""
        # Update skill profiles
        for skill in result.skills_demonstrated:
            if skill not in self.skills:
                self.skills[skill] = SkillProfile(name=skill, proficiency=0.5)
            self.skills[skill].update(result.success)

        # Store experience in memory
        outcome = "SUCCESS" if result.success else "FAILURE"
        self.memory.remember_experience(
            experience=f"Task: {result.task.description[:100]}",
            outcome=f"{outcome} (score: {result.score:.2f})",
            context={
                "errors": result.errors_made,
                "skills": result.skills_demonstrated,
                "difficulty": result.task.difficulty.name,
            },
            importance=result.score if result.success else 1 - result.score,
        )

        # If failed, do deeper reflection
        if not result.success and result.errors_made:
            reflection_result = await self.reflection.critique_action(
                action=f"Attempted task: {result.task.description[:100]}",
                result=f"Failed with score {result.score:.2f}. Errors: {result.errors_made}",
                context={"solution": result.solution[:500]},
            )
            result.reflection = reflection_result.critique
            result.improvement_notes = reflection_result.improvements

            # Learn procedure from reflection
            if reflection_result.lessons_learned:
                self.memory.learn_procedure(
                    skill_name=f"avoid_error_{result.task.domain.value}",
                    steps=reflection_result.lessons_learned,
                )

    def _extract_code(self, text: str) -> str:
        """Extract code from solution text."""
        # Try to find code block
        code_match = re.search(r'```(?:python)?\n(.*?)```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Look for function definitions
        func_match = re.search(r'(def \w+.*?)(?=\n\n|\Z)', text, re.DOTALL)
        if func_match:
            return func_match.group(1).strip()

        return text

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response."""
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {}

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        if not self.execution_history:
            return {
                "total_attempts": 0,
                "success_rate": 0.0,
                "current_frontier": TaskDifficulty.EASY.name,
                "skills_mastered": [],
                "skills_to_improve": [],
            }

        # Calculate success rates by difficulty
        by_difficulty = {}
        for result in self.execution_history:
            diff = result.task.difficulty.name
            if diff not in by_difficulty:
                by_difficulty[diff] = {"attempts": 0, "successes": 0}
            by_difficulty[diff]["attempts"] += 1
            if result.success:
                by_difficulty[diff]["successes"] += 1

        # Determine current frontier (highest difficulty with >40% success)
        current_frontier = TaskDifficulty.EASY
        for d in TaskDifficulty:
            if d.name in by_difficulty:
                data = by_difficulty[d.name]
                rate = data["successes"] / data["attempts"]
                if rate > 0.4:
                    current_frontier = d

        # Categorize skills
        mastered = [
            s for s, p in self.skills.items()
            if p.proficiency > 0.8
        ]
        to_improve = [
            s for s, p in self.skills.items()
            if 0.3 < p.proficiency < 0.7
        ]

        return {
            "total_attempts": self._total_attempts,
            "total_successes": self._total_successes,
            "success_rate": self._total_successes / max(self._total_attempts, 1),
            "current_frontier": current_frontier.name,
            "current_level": current_frontier.name,
            "skills_mastered": mastered,
            "skills_to_improve": to_improve,
            "skill_count": len(self.skills),
            "by_difficulty": {
                d: {
                    "rate": data["successes"] / data["attempts"],
                    "attempts": data["attempts"]
                }
                for d, data in by_difficulty.items()
            },
        }

    def get_skill_report(self) -> Dict[str, Any]:
        """Get detailed skill report."""
        return {
            skill: {
                "proficiency": round(profile.proficiency, 3),
                "practice_count": profile.practice_count,
                "last_practiced": profile.last_practiced.isoformat() if profile.last_practiced else None,
                "recent_success_rate": sum(profile.success_history[-10:]) / max(len(profile.success_history[-10:]), 1),
            }
            for skill, profile in self.skills.items()
        }

    def export_state(self) -> dict:
        """Export executor state."""
        return {
            "stats": self.get_stats(),
            "skills": self.get_skill_report(),
            "history_size": len(self.execution_history),
        }
