"""
Co-Evolution Loop - Agent0-inspired Self-Improvement.

Reference: Agent0 (arXiv:2511.16043)
- Curriculum Agent vs Executor Agent co-evolution
- +18% math reasoning, +24% general reasoning
- Zero external data needed

The co-evolution loop enables the agent to:
1. Generate progressively harder tasks (Curriculum Agent)
2. Learn to solve them (Executor Agent)
3. Improve continuously without external data
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, AsyncIterator
from datetime import datetime
import asyncio

from ..agents.curriculum_agent import (
    CurriculumAgent,
    EvolutionTask,
    TaskDifficulty,
    TaskDomain,
)
from ..agents.executor_agent import ExecutorAgent, ExecutionResult


@dataclass
class EvolutionStats:
    """Overall evolution statistics."""
    total_iterations: int = 0
    total_tasks: int = 0
    tasks_solved: int = 0
    success_rate: float = 0.0
    avg_difficulty: float = 2.0
    skills_mastered: List[str] = field(default_factory=list)
    current_frontier: TaskDifficulty = TaskDifficulty.EASY
    improvement_curve: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_iterations": self.total_iterations,
            "total_tasks": self.total_tasks,
            "tasks_solved": self.tasks_solved,
            "success_rate": self.success_rate,
            "avg_difficulty": self.avg_difficulty,
            "skills_mastered": self.skills_mastered,
            "current_frontier": self.current_frontier.name,
            "improvement_curve": self.improvement_curve[-20:],  # Last 20
        }


@dataclass
class EvolutionIteration:
    """A single iteration of evolution."""
    iteration: int
    task: EvolutionTask
    result: ExecutionResult
    executor_stats_before: Dict[str, Any]
    executor_stats_after: Dict[str, Any]
    improvement: float  # Change in overall success rate

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "iteration": self.iteration,
            "task": self.task.to_dict(),
            "success": self.result.success,
            "score": self.result.score,
            "improvement": self.improvement,
        }


class CoEvolutionLoop:
    """
    Co-Evolution Loop Coordinator.

    Manages the interplay between Curriculum Agent and Executor Agent
    for continuous self-improvement.
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
        self.curriculum = CurriculumAgent(llm_client)
        self.executor = ExecutorAgent(
            llm_client,
            tool_factory,
            memory_system,
            reflection_engine,
            sandbox_executor,
        )

        self.evolution_history: List[EvolutionIteration] = []
        self.stats = EvolutionStats()
        self._is_evolving = False

    async def evolve(
        self,
        num_iterations: int = 10,
        domain: TaskDomain = TaskDomain.GENERAL,
    ) -> EvolutionStats:
        """
        Run the evolution loop.

        For each iteration:
        1. Curriculum generates task at frontier
        2. Executor attempts to solve
        3. Curriculum adjusts based on result
        4. Executor learns from experience
        """
        async for _ in self.evolve_with_progress(num_iterations, domain):
            pass
        return self.stats

    async def evolve_with_progress(
        self,
        num_iterations: int = 10,
        domain: TaskDomain = TaskDomain.GENERAL,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Run evolution loop with progress updates.

        Yields progress dict after each iteration.
        """
        self._is_evolving = True

        try:
            for i in range(num_iterations):
                # Get current stats
                stats_before = self.executor.get_stats()

                # Generate task at frontier
                task = await self.curriculum.generate_task(stats_before, domain)

                # Executor attempts task
                result = await self.executor.attempt_task(task)

                # Curriculum updates based on result
                self.curriculum.update_curriculum(task, {
                    "success": result.success,
                    "score": result.score,
                    "skills_demonstrated": result.skills_demonstrated,
                })

                # Get updated stats
                stats_after = self.executor.get_stats()

                # Calculate improvement
                improvement = (
                    stats_after.get("success_rate", 0) -
                    stats_before.get("success_rate", 0)
                )

                # Store iteration
                iteration = EvolutionIteration(
                    iteration=i + 1,
                    task=task,
                    result=result,
                    executor_stats_before=stats_before,
                    executor_stats_after=stats_after,
                    improvement=improvement,
                )
                self.evolution_history.append(iteration)

                # Update overall stats
                self._update_stats(result, stats_after)

                # Yield progress
                yield {
                    "iteration": i + 1,
                    "total": num_iterations,
                    "task_difficulty": task.difficulty.name,
                    "success": result.success,
                    "score": result.score,
                    "current_success_rate": self.stats.success_rate,
                    "frontier": self.stats.current_frontier.name,
                }

                # Small delay between iterations
                await asyncio.sleep(0.1)

        finally:
            self._is_evolving = False

    async def evolve_targeted(
        self,
        target_skill: str,
        num_iterations: int = 5,
    ) -> EvolutionStats:
        """
        Evolve with focus on a specific skill.
        """
        for i in range(num_iterations):
            stats = self.executor.get_stats()

            # Generate task targeting specific skill
            task = await self.curriculum.generate_task(
                stats,
                domain=TaskDomain.GENERAL,
                specific_skill=target_skill,
            )

            result = await self.executor.attempt_task(task)

            self.curriculum.update_curriculum(task, {
                "success": result.success,
                "score": result.score,
                "skills_demonstrated": result.skills_demonstrated,
            })

            self._update_stats(result, self.executor.get_stats())

        return self.stats

    async def evolve_multi_domain(
        self,
        iterations_per_domain: int = 3,
        domains: Optional[List[TaskDomain]] = None,
    ) -> EvolutionStats:
        """
        Evolve across multiple domains.
        """
        domains = domains or [
            TaskDomain.CODE,
            TaskDomain.REASONING,
            TaskDomain.ANALYSIS,
        ]

        for domain in domains:
            async for _ in self.evolve_with_progress(
                num_iterations=iterations_per_domain,
                domain=domain,
            ):
                pass  # Consume generator

        return self.stats

    async def benchmark(
        self,
        num_tasks_per_level: int = 3,
    ) -> Dict[str, Any]:
        """
        Run a benchmark across all difficulty levels.

        Returns detailed performance breakdown.
        """
        results = {
            "by_difficulty": {},
            "overall": {},
            "skills_tested": set(),
        }

        for difficulty in TaskDifficulty:
            level_results = []

            for _ in range(num_tasks_per_level):
                stats = self.executor.get_stats()

                # Force specific difficulty
                task = await self._generate_task_at_difficulty(
                    difficulty,
                    TaskDomain.GENERAL,
                    stats,
                )

                result = await self.executor.attempt_task(task, use_hints=False)
                level_results.append(result)
                results["skills_tested"].update(result.skills_demonstrated)

            # Aggregate level results
            successes = sum(1 for r in level_results if r.success)
            avg_score = sum(r.score for r in level_results) / len(level_results)

            results["by_difficulty"][difficulty.name] = {
                "success_rate": successes / num_tasks_per_level,
                "avg_score": avg_score,
                "attempts": num_tasks_per_level,
            }

        # Overall metrics
        all_results = [
            r for level in results["by_difficulty"].values()
            for r in [level]
        ]
        results["overall"] = {
            "weighted_success_rate": sum(
                r["success_rate"] * (i + 1)
                for i, r in enumerate(results["by_difficulty"].values())
            ) / sum(range(1, len(TaskDifficulty) + 1)),
            "skills_count": len(results["skills_tested"]),
        }
        results["skills_tested"] = list(results["skills_tested"])

        return results

    async def _generate_task_at_difficulty(
        self,
        difficulty: TaskDifficulty,
        domain: TaskDomain,
        executor_stats: Dict[str, Any],
    ) -> EvolutionTask:
        """Generate a task at exact difficulty level."""
        # Temporarily override curriculum distribution
        original_dist = self.curriculum.difficulty_distribution.copy()

        # Set all weight to target difficulty
        for d in TaskDifficulty:
            self.curriculum.difficulty_distribution[d] = 1.0 if d == difficulty else 0.0

        task = await self.curriculum.generate_task(executor_stats, domain)

        # Restore distribution
        self.curriculum.difficulty_distribution = original_dist

        return task

    def _update_stats(
        self,
        result: ExecutionResult,
        executor_stats: Dict[str, Any],
    ):
        """Update overall evolution stats."""
        self.stats.total_iterations += 1
        self.stats.total_tasks += 1

        if result.success:
            self.stats.tasks_solved += 1

        self.stats.success_rate = (
            self.stats.tasks_solved / self.stats.total_tasks
        )

        # Update difficulty tracking
        difficulties = [
            it.task.difficulty.value
            for it in self.evolution_history[-20:]
        ]
        if difficulties:
            self.stats.avg_difficulty = sum(difficulties) / len(difficulties)

        # Update frontier
        frontier_name = executor_stats.get("current_frontier", "EASY")
        if isinstance(frontier_name, str):
            self.stats.current_frontier = TaskDifficulty[frontier_name]
        else:
            self.stats.current_frontier = frontier_name

        # Update skills
        self.stats.skills_mastered = executor_stats.get("skills_mastered", [])

        # Track improvement curve
        self.stats.improvement_curve.append(self.stats.success_rate)

    def get_evolution_summary(self) -> Dict[str, Any]:
        """Get comprehensive evolution summary."""
        return {
            "stats": self.stats.to_dict(),
            "curriculum": self.curriculum.get_stats(),
            "executor": self.executor.get_stats(),
            "recent_iterations": [
                it.to_dict() for it in self.evolution_history[-10:]
            ],
            "improvement_analysis": self._analyze_improvement(),
        }

    def _analyze_improvement(self) -> Dict[str, Any]:
        """Analyze improvement patterns."""
        if len(self.stats.improvement_curve) < 5:
            return {"trend": "insufficient_data"}

        curve = self.stats.improvement_curve

        # Calculate moving averages
        window = 5
        if len(curve) >= window * 2:
            recent_avg = sum(curve[-window:]) / window
            older_avg = sum(curve[-window*2:-window]) / window

            if recent_avg > older_avg + 0.1:
                trend = "improving"
            elif recent_avg < older_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "early_stage"

        return {
            "trend": trend,
            "latest_rate": curve[-1] if curve else 0,
            "best_rate": max(curve) if curve else 0,
            "total_improvement": curve[-1] - curve[0] if len(curve) > 1 else 0,
        }

    def get_recommendations(self) -> List[str]:
        """Get recommendations for improvement."""
        recommendations = []
        stats = self.executor.get_stats()

        # Based on success rate
        if stats["success_rate"] < 0.3:
            recommendations.append(
                "Consider practicing more EASY tasks to build foundations"
            )
        elif stats["success_rate"] > 0.8:
            recommendations.append(
                "Ready to tackle harder challenges - increase difficulty"
            )

        # Based on skills
        weak_skills = stats.get("skills_to_improve", [])
        if weak_skills:
            recommendations.append(
                f"Focus on improving: {', '.join(weak_skills[:3])}"
            )

        # Based on curriculum
        curriculum_stats = self.curriculum.get_stats()
        if curriculum_stats["solve_rate"] < 0.4:
            recommendations.append(
                "Task difficulty may be too high - curriculum will auto-adjust"
            )

        return recommendations

    def reset(self):
        """Reset evolution state."""
        self.evolution_history = []
        self.stats = EvolutionStats()
        self.curriculum = CurriculumAgent(self.llm)
        # Note: executor keeps learned skills

    def export_state(self) -> Dict[str, Any]:
        """Export complete evolution state."""
        return {
            "stats": self.stats.to_dict(),
            "curriculum": self.curriculum.export_curriculum(),
            "executor": self.executor.export_state(),
            "history_size": len(self.evolution_history),
        }

    @property
    def is_evolving(self) -> bool:
        """Check if evolution is currently running."""
        return self._is_evolving
