"""
Curriculum Agent - Generates progressively harder tasks.

Reference: Agent0 (arXiv:2511.16043)
- Curriculum Agent vs Executor Agent co-evolution
- +18% math reasoning, +24% general reasoning
- Zero external data needed

The Curriculum Agent is responsible for:
1. Assessing the Executor's current level
2. Generating tasks at the "frontier" of difficulty
3. Adapting curriculum based on performance
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import hashlib
import json
import re
import random


class TaskDifficulty(Enum):
    """Task difficulty levels."""
    TRIVIAL = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    EXPERT = 5


class TaskDomain(Enum):
    """Domains of tasks."""
    CODE = "code"
    MATH = "math"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    WRITING = "writing"
    GENERAL = "general"


@dataclass
class EvolutionTask:
    """A task generated for evolution training."""
    id: str
    description: str
    difficulty: TaskDifficulty
    domain: TaskDomain
    expected_skills: List[str]
    success_criteria: List[str]
    test_cases: List[dict] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    time_limit: int = 300  # seconds
    created_at: datetime = field(default_factory=datetime.now)
    solved: bool = False
    attempts: int = 0
    best_score: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "difficulty": self.difficulty.name,
            "domain": self.domain.value,
            "skills": self.expected_skills,
            "criteria": self.success_criteria,
            "solved": self.solved,
            "best_score": self.best_score,
        }


@dataclass
class CurriculumStats:
    """Statistics about curriculum generation."""
    total_tasks: int = 0
    tasks_by_difficulty: Dict[str, int] = field(default_factory=dict)
    tasks_by_domain: Dict[str, int] = field(default_factory=dict)
    avg_solve_rate: float = 0.0
    frontier_difficulty: TaskDifficulty = TaskDifficulty.EASY


class CurriculumAgent:
    """
    Generates progressively harder tasks for the Executor.

    Implements adaptive curriculum learning where task difficulty
    is adjusted based on the Executor's performance.
    """

    # Task templates by domain
    TASK_TEMPLATES = {
        TaskDomain.CODE: [
            "Implement a function that {action} for {input_type}",
            "Write a {complexity} algorithm to {goal}",
            "Create a data structure that {capability}",
            "Debug and fix the issue in this code: {code_snippet}",
            "Optimize this code for {metric}: {code_snippet}",
        ],
        TaskDomain.MATH: [
            "Solve this mathematical problem: {problem}",
            "Prove that {statement}",
            "Find the {operation} of {expression}",
            "Calculate {calculation} given {constraints}",
        ],
        TaskDomain.REASONING: [
            "Given {premises}, deduce {conclusion_type}",
            "Analyze the logical structure of: {argument}",
            "Identify the fallacy in: {statement}",
            "Complete this pattern: {pattern}",
        ],
        TaskDomain.ANALYSIS: [
            "Analyze this {artifact_type} and identify {aspects}",
            "Compare and contrast {item_a} with {item_b}",
            "Evaluate the {quality} of {subject}",
            "Summarize the key points of {content}",
        ],
        TaskDomain.WRITING: [
            "Write a {document_type} about {topic}",
            "Explain {concept} to {audience}",
            "Create documentation for {subject}",
            "Rewrite this for {purpose}: {text}",
        ],
    }

    def __init__(self, llm_client):
        self.llm = llm_client
        self.task_history: List[EvolutionTask] = []
        self.stats = CurriculumStats()

        # Difficulty distribution (probability weights)
        self.difficulty_distribution: Dict[TaskDifficulty, float] = {
            TaskDifficulty.TRIVIAL: 0.05,
            TaskDifficulty.EASY: 0.30,
            TaskDifficulty.MEDIUM: 0.40,
            TaskDifficulty.HARD: 0.20,
            TaskDifficulty.EXPERT: 0.05,
        }

        # Skills discovered through evolution
        self.discovered_skills: Dict[str, float] = {}  # skill -> mastery level

    async def generate_task(
        self,
        executor_stats: Dict[str, Any],
        domain: TaskDomain = TaskDomain.GENERAL,
        specific_skill: Optional[str] = None,
    ) -> EvolutionTask:
        """
        Generate a task at the frontier of difficulty.

        The frontier is the level where the executor has ~50% success.
        """
        # Determine target difficulty
        target_difficulty = self._select_difficulty(executor_stats)

        # Get skills to practice
        skills_to_target = self._select_target_skills(executor_stats, specific_skill)

        # Generate task using LLM
        task = await self._generate_task_with_llm(
            target_difficulty,
            domain,
            skills_to_target,
            executor_stats
        )

        self.task_history.append(task)
        self._update_stats(task)

        return task

    async def generate_task_batch(
        self,
        executor_stats: Dict[str, Any],
        batch_size: int = 5,
        domains: Optional[List[TaskDomain]] = None,
    ) -> List[EvolutionTask]:
        """Generate a batch of tasks across different domains."""
        domains = domains or list(TaskDomain)
        tasks = []

        for i in range(batch_size):
            domain = domains[i % len(domains)]
            task = await self.generate_task(executor_stats, domain)
            tasks.append(task)

        return tasks

    async def _generate_task_with_llm(
        self,
        difficulty: TaskDifficulty,
        domain: TaskDomain,
        target_skills: List[str],
        executor_stats: Dict[str, Any],
    ) -> EvolutionTask:
        """Generate a task using the LLM."""
        mastered_skills = executor_stats.get("skills_mastered", [])
        weak_skills = executor_stats.get("skills_to_improve", [])

        prompt = f"""Generate a {difficulty.name} difficulty task for AI agent training.

DOMAIN: {domain.value}
TARGET DIFFICULTY: {difficulty.name} (level {difficulty.value}/5)
TARGET SKILLS: {target_skills}

EXECUTOR CONTEXT:
- Current level: {executor_stats.get('current_level', 'UNKNOWN')}
- Mastered skills: {mastered_skills[:5]}
- Weak areas: {weak_skills[:3]}
- Success rate: {executor_stats.get('success_rate', 0.5):.1%}

REQUIREMENTS:
1. Task should be challenging but achievable at {difficulty.name} level
2. Should require the target skills
3. Must have clear, measurable success criteria
4. Include test cases if applicable

Generate the task in JSON format:
{{
    "description": "clear and detailed task description",
    "domain": "{domain.value}",
    "expected_skills": ["skill1", "skill2"],
    "success_criteria": ["criterion 1", "criterion 2"],
    "test_cases": [
        {{"input": "...", "expected_output": "...", "explanation": "..."}}
    ],
    "hints": ["hint for if stuck"],
    "estimated_time_minutes": 5-30
}}

Make the task specific and actionable, not vague."""

        response = await self.llm.generate(prompt)
        data = self._parse_json_response(response)

        # Create task
        task = EvolutionTask(
            id=self._generate_id(data.get("description", "")),
            description=data.get("description", f"Complete a {difficulty.name} {domain.value} task"),
            difficulty=difficulty,
            domain=domain,
            expected_skills=data.get("expected_skills", target_skills),
            success_criteria=data.get("success_criteria", ["Task completed"]),
            test_cases=data.get("test_cases", []),
            hints=data.get("hints", []),
            time_limit=data.get("estimated_time_minutes", 10) * 60,
        )

        return task

    def _select_difficulty(self, executor_stats: Dict[str, Any]) -> TaskDifficulty:
        """Select appropriate difficulty based on executor performance."""
        success_rate = executor_stats.get("success_rate", 0.5)
        current_frontier = executor_stats.get("current_frontier", TaskDifficulty.EASY)

        if isinstance(current_frontier, str):
            current_frontier = TaskDifficulty[current_frontier]

        # Adjust frontier based on success rate
        if success_rate > 0.8:
            # Doing great, increase difficulty
            new_level = min(current_frontier.value + 1, 5)
            target = TaskDifficulty(new_level)
            self.stats.frontier_difficulty = target
        elif success_rate < 0.3:
            # Struggling, decrease difficulty
            new_level = max(current_frontier.value - 1, 1)
            target = TaskDifficulty(new_level)
            self.stats.frontier_difficulty = target
        else:
            # At frontier, stay here
            target = current_frontier

        # Add some randomness around the target
        weights = []
        for d in TaskDifficulty:
            # Higher weight for target and adjacent difficulties
            distance = abs(d.value - target.value)
            weight = max(0.1, 1.0 - distance * 0.3)
            weights.append(weight)

        # Normalize
        total = sum(weights)
        weights = [w / total for w in weights]

        return random.choices(list(TaskDifficulty), weights=weights)[0]

    def _select_target_skills(
        self,
        executor_stats: Dict[str, Any],
        specific_skill: Optional[str] = None,
    ) -> List[str]:
        """Select skills to target in the task."""
        if specific_skill:
            return [specific_skill]

        weak_skills = executor_stats.get("skills_to_improve", [])
        mastered_skills = executor_stats.get("skills_mastered", [])

        # Prioritize weak skills for practice
        target_skills = []

        if weak_skills:
            # Pick 1-2 weak skills
            target_skills.extend(random.sample(weak_skills, min(2, len(weak_skills))))

        if mastered_skills and random.random() < 0.3:
            # Occasionally reinforce mastered skills
            target_skills.append(random.choice(mastered_skills))

        if not target_skills:
            # Default skills
            target_skills = ["problem_solving", "code_generation"]

        return target_skills[:3]

    def update_curriculum(self, task: EvolutionTask, result: Dict[str, Any]):
        """Update curriculum based on task result."""
        task.attempts += 1
        task.best_score = max(task.best_score, result.get("score", 0))
        task.solved = result.get("success", False) or task.best_score > 0.7

        # Update difficulty distribution based on result
        if result.get("success"):
            # Success: shift weight to harder tasks
            self._adjust_distribution_up(task.difficulty)
        else:
            # Failure: shift weight to easier tasks
            self._adjust_distribution_down(task.difficulty)

        # Update skill discoveries
        for skill in result.get("skills_demonstrated", []):
            if skill not in self.discovered_skills:
                self.discovered_skills[skill] = 0.5
            # Update mastery estimate
            current = self.discovered_skills[skill]
            self.discovered_skills[skill] = 0.9 * current + 0.1 * result.get("score", 0.5)

    def _adjust_distribution_up(self, current_difficulty: TaskDifficulty):
        """Shift distribution toward harder tasks."""
        for d in TaskDifficulty:
            if d.value > current_difficulty.value:
                self.difficulty_distribution[d] = min(
                    0.5,
                    self.difficulty_distribution[d] + 0.02
                )
            elif d.value < current_difficulty.value:
                self.difficulty_distribution[d] = max(
                    0.05,
                    self.difficulty_distribution[d] - 0.01
                )
        self._normalize_distribution()

    def _adjust_distribution_down(self, current_difficulty: TaskDifficulty):
        """Shift distribution toward easier tasks."""
        for d in TaskDifficulty:
            if d.value <= current_difficulty.value:
                self.difficulty_distribution[d] = min(
                    0.5,
                    self.difficulty_distribution[d] + 0.02
                )
            elif d.value > current_difficulty.value:
                self.difficulty_distribution[d] = max(
                    0.05,
                    self.difficulty_distribution[d] - 0.01
                )
        self._normalize_distribution()

    def _normalize_distribution(self):
        """Normalize difficulty distribution to sum to 1."""
        total = sum(self.difficulty_distribution.values())
        for d in self.difficulty_distribution:
            self.difficulty_distribution[d] /= total

    def _update_stats(self, task: EvolutionTask):
        """Update curriculum statistics."""
        self.stats.total_tasks += 1

        # By difficulty
        diff_name = task.difficulty.name
        self.stats.tasks_by_difficulty[diff_name] = (
            self.stats.tasks_by_difficulty.get(diff_name, 0) + 1
        )

        # By domain
        domain_name = task.domain.value
        self.stats.tasks_by_domain[domain_name] = (
            self.stats.tasks_by_domain.get(domain_name, 0) + 1
        )

        # Update solve rate
        solved = sum(1 for t in self.task_history if t.solved)
        self.stats.avg_solve_rate = solved / max(len(self.task_history), 1)

    def _generate_id(self, description: str) -> str:
        """Generate unique task ID."""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{description}{timestamp}".encode()).hexdigest()[:12]

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response."""
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def get_unsolved_tasks(self, limit: int = 10) -> List[EvolutionTask]:
        """Get unsolved tasks for retry."""
        unsolved = [t for t in self.task_history if not t.solved]
        unsolved.sort(key=lambda t: t.best_score, reverse=True)  # Closest to solving first
        return unsolved[:limit]

    def get_stats(self) -> dict:
        """Get curriculum statistics."""
        return {
            "total_tasks": self.stats.total_tasks,
            "by_difficulty": self.stats.tasks_by_difficulty,
            "by_domain": self.stats.tasks_by_domain,
            "solve_rate": self.stats.avg_solve_rate,
            "frontier": self.stats.frontier_difficulty.name,
            "difficulty_distribution": {
                d.name: round(w, 3)
                for d, w in self.difficulty_distribution.items()
            },
            "discovered_skills": len(self.discovered_skills),
        }

    def export_curriculum(self) -> dict:
        """Export curriculum state."""
        return {
            "tasks": [t.to_dict() for t in self.task_history],
            "stats": self.get_stats(),
            "distribution": {
                d.name: w for d, w in self.difficulty_distribution.items()
            },
            "discovered_skills": self.discovered_skills,
        }
