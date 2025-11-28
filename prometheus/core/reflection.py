"""
Reflection Engine - Self-Critique and Improvement.

References:
- Reflexion (arXiv:2303.11366): Dynamic memory + self-reflection loop
- Self-Refine: Generate → Critique → Improve loop
- Agent-R: Iterative self-training framework

The Reflection Engine enables the agent to:
1. Evaluate its own actions and results
2. Identify errors and areas for improvement
3. Generate improved versions
4. Learn from the reflection process
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime
import json
import re


class ReflectionType(Enum):
    """Types of reflection."""
    ACTION_CRITIQUE = "action_critique"
    OUTPUT_CRITIQUE = "output_critique"
    STRATEGY_CRITIQUE = "strategy_critique"
    SELF_ASSESSMENT = "self_assessment"
    ERROR_ANALYSIS = "error_analysis"


class CritiqueAspect(Enum):
    """Aspects to critique."""
    CORRECTNESS = "correctness"
    EFFICIENCY = "efficiency"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    SAFETY = "safety"
    RELEVANCE = "relevance"


@dataclass
class Reflection:
    """A reflection entry."""
    id: str
    type: ReflectionType
    subject: str  # What is being evaluated
    critique: str  # The critique text
    score: float  # 0-1 overall score
    aspect_scores: Dict[str, float] = field(default_factory=dict)
    improvements: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    root_cause: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "subject": self.subject[:100] + "..." if len(self.subject) > 100 else self.subject,
            "score": self.score,
            "improvements": self.improvements,
            "lessons": self.lessons_learned,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ImprovementCycle:
    """A complete Generate → Critique → Improve cycle."""
    original: str
    critiques: List[Reflection]
    iterations: List[str]  # Each improved version
    final_version: str
    improvement_score: float  # How much it improved
    converged: bool  # Whether improvement converged

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "iterations": len(self.iterations),
            "improvement_score": self.improvement_score,
            "converged": self.converged,
            "final_score": self.critiques[-1].score if self.critiques else 0,
        }


class ReflectionEngine:
    """
    Self-Reflection and Improvement Engine.

    Implements the loop: Generate → Critique → Improve → Learn
    """

    def __init__(self, llm_client, memory_system):
        self.llm = llm_client
        self.memory = memory_system
        self.reflection_history: List[Reflection] = []
        self._reflection_count = 0

    async def critique_action(
        self,
        action: str,
        result: str,
        context: Optional[dict] = None,
        aspects: Optional[List[CritiqueAspect]] = None,
    ) -> Reflection:
        """
        Critique an action and its result.

        Evaluates:
        - Was the action appropriate?
        - Was the result as expected?
        - Were there negative side effects?
        - What could have been done better?
        """
        context = context or {}
        aspects = aspects or [
            CritiqueAspect.CORRECTNESS,
            CritiqueAspect.EFFICIENCY,
            CritiqueAspect.COMPLETENESS,
        ]

        aspects_str = ", ".join(a.value for a in aspects)

        prompt = f"""You are a critical evaluator. Analyze this action and its result.

ACTION TAKEN:
{action}

RESULT:
{result}

CONTEXT:
{json.dumps(context, indent=2, default=str)}

Evaluate the following aspects: {aspects_str}

Provide your analysis in JSON format:
{{
    "appropriateness_score": 0.0-1.0,
    "effectiveness_score": 0.0-1.0,
    "aspect_scores": {{
        "correctness": 0.0-1.0,
        "efficiency": 0.0-1.0,
        "completeness": 0.0-1.0
    }},
    "critique": "detailed critique of what went well and what didn't",
    "side_effects": ["any unintended consequences"],
    "improvements": ["specific improvement 1", "specific improvement 2"],
    "lessons": ["lesson learned 1", "lesson learned 2"],
    "root_cause": "if there was an issue, what was the root cause"
}}

Be specific, constructive, and actionable in your feedback."""

        response = await self.llm.generate(prompt)
        data = self._parse_json_response(response)

        # Calculate overall score
        score = (
            data.get("appropriateness_score", 0.5) * 0.4 +
            data.get("effectiveness_score", 0.5) * 0.6
        )

        reflection = Reflection(
            id=self._generate_id(),
            type=ReflectionType.ACTION_CRITIQUE,
            subject=action[:200],
            critique=data.get("critique", "No critique provided"),
            score=score,
            aspect_scores=data.get("aspect_scores", {}),
            improvements=data.get("improvements", []),
            lessons_learned=data.get("lessons", []),
            root_cause=data.get("root_cause"),
        )

        self._store_reflection(reflection)
        return reflection

    async def critique_output(
        self,
        output: str,
        task: str,
        criteria: List[str],
        reference: Optional[str] = None,
    ) -> Reflection:
        """
        Critique a generated output against specific criteria.
        """
        criteria_str = "\n".join(f"- {c}" for c in criteria)
        reference_section = f"\nREFERENCE (ideal output):\n{reference}" if reference else ""

        prompt = f"""Evaluate this output against the given criteria.

TASK: {task}

OUTPUT TO EVALUATE:
{output}

CRITERIA:
{criteria_str}
{reference_section}

Score each criterion 0-1 and provide your assessment in JSON:
{{
    "criterion_scores": {{"criterion_name": 0.8, ...}},
    "overall_score": 0.0-1.0,
    "strengths": ["strength 1", "strength 2"],
    "weaknesses": ["weakness 1", "weakness 2"],
    "specific_improvements": ["improvement 1", "improvement 2"],
    "missing_elements": ["what's missing"],
    "quality_summary": "brief summary of overall quality"
}}"""

        response = await self.llm.generate(prompt)
        data = self._parse_json_response(response)

        critique_text = (
            f"Strengths: {data.get('strengths', [])}\n"
            f"Weaknesses: {data.get('weaknesses', [])}\n"
            f"Summary: {data.get('quality_summary', 'N/A')}"
        )

        reflection = Reflection(
            id=self._generate_id(),
            type=ReflectionType.OUTPUT_CRITIQUE,
            subject=output[:200] + "..." if len(output) > 200 else output,
            critique=critique_text,
            score=data.get("overall_score", 0.5),
            aspect_scores=data.get("criterion_scores", {}),
            improvements=data.get("specific_improvements", []),
            lessons_learned=data.get("missing_elements", []),
        )

        self._store_reflection(reflection)
        return reflection

    async def improve_output(
        self,
        original: str,
        task: str,
        criteria: List[str],
        max_iterations: int = 3,
        target_score: float = 0.9,
    ) -> ImprovementCycle:
        """
        Iteratively improve an output based on critiques.

        Loop: Critique → Improve → Re-critique until converged.
        """
        current = original
        critiques = []
        iterations = []

        # Initial critique
        critique = await self.critique_output(current, task, criteria)
        critiques.append(critique)

        for i in range(max_iterations):
            if critique.score >= target_score:
                break  # Good enough

            # Generate improved version
            improved = await self._generate_improvement(
                current,
                task,
                critique,
                criteria
            )
            iterations.append(improved)

            # Re-critique
            new_critique = await self.critique_output(improved, task, criteria)
            critiques.append(new_critique)

            # Check if actually improved
            if new_critique.score <= critique.score:
                # Not improving, stop
                break

            current = improved
            critique = new_critique

        improvement_score = critiques[-1].score - critiques[0].score
        converged = critique.score >= target_score

        return ImprovementCycle(
            original=original,
            critiques=critiques,
            iterations=iterations,
            final_version=current,
            improvement_score=improvement_score,
            converged=converged,
        )

    async def analyze_error(
        self,
        error_message: str,
        context: dict,
        code_snippet: Optional[str] = None,
    ) -> Reflection:
        """
        Deep analysis of an error.

        Identifies root cause and suggests fixes.
        """
        code_section = f"\nCODE:\n```\n{code_snippet}\n```" if code_snippet else ""

        prompt = f"""Analyze this error in depth.

ERROR MESSAGE:
{error_message}

CONTEXT:
{json.dumps(context, indent=2, default=str)}
{code_section}

Provide thorough analysis in JSON:
{{
    "error_type": "type of error (syntax, logic, runtime, etc.)",
    "root_cause": "the fundamental cause of this error",
    "contributing_factors": ["factor 1", "factor 2"],
    "fix_steps": ["step 1 to fix", "step 2 to fix"],
    "prevention_strategies": ["how to prevent in future"],
    "severity": 0.0-1.0,
    "related_errors": ["similar errors to watch for"]
}}"""

        response = await self.llm.generate(prompt)
        data = self._parse_json_response(response)

        reflection = Reflection(
            id=self._generate_id(),
            type=ReflectionType.ERROR_ANALYSIS,
            subject=error_message[:200],
            critique=f"Error Type: {data.get('error_type', 'Unknown')}\n"
                     f"Root Cause: {data.get('root_cause', 'Unknown')}",
            score=1.0 - data.get("severity", 0.5),  # Invert severity
            improvements=data.get("fix_steps", []),
            lessons_learned=data.get("prevention_strategies", []),
            root_cause=data.get("root_cause"),
        )

        self._store_reflection(reflection)
        return reflection

    async def self_assess(
        self,
        task_completed: str,
        performance_metrics: dict,
    ) -> Reflection:
        """
        Self-assessment of overall performance on a task.
        """
        # Get recent reflection history for context
        recent_reflections = self.reflection_history[-10:]
        recent_scores = [r.score for r in recent_reflections]
        avg_score = sum(recent_scores) / max(len(recent_scores), 1)

        prompt = f"""Perform a self-assessment of your performance.

TASK COMPLETED:
{task_completed}

PERFORMANCE METRICS:
{json.dumps(performance_metrics, indent=2, default=str)}

RECENT REFLECTION SCORES: {recent_scores}
AVERAGE SCORE: {avg_score:.2f}

Provide honest self-assessment in JSON:
{{
    "overall_performance": 0.0-1.0,
    "strengths_demonstrated": ["strength 1", "strength 2"],
    "areas_for_improvement": ["area 1", "area 2"],
    "strategy_adjustments": ["adjustment 1"],
    "confidence_level": 0.0-1.0,
    "key_learnings": ["learning 1", "learning 2"],
    "next_focus_areas": ["what to focus on next"]
}}"""

        response = await self.llm.generate(prompt)
        data = self._parse_json_response(response)

        reflection = Reflection(
            id=self._generate_id(),
            type=ReflectionType.SELF_ASSESSMENT,
            subject=task_completed,
            critique=(
                f"Performance: {data.get('overall_performance', 0.5):.0%}\n"
                f"Confidence: {data.get('confidence_level', 0.5):.0%}\n"
                f"Strengths: {data.get('strengths_demonstrated', [])}"
            ),
            score=data.get("overall_performance", 0.5),
            aspect_scores={
                "confidence": data.get("confidence_level", 0.5),
            },
            improvements=data.get("strategy_adjustments", []),
            lessons_learned=data.get("key_learnings", []),
        )

        self._store_reflection(reflection)

        # Update memory with learnings
        for lesson in data.get("key_learnings", []):
            self.memory.learn_fact(
                f"self_learning_{self._reflection_count}",
                lesson,
                source="self_assessment"
            )

        return reflection

    async def _generate_improvement(
        self,
        current: str,
        task: str,
        critique: Reflection,
        criteria: List[str],
    ) -> str:
        """Generate an improved version based on critique."""
        prompt = f"""Improve this output based on the critique.

TASK: {task}

CURRENT VERSION:
{current}

CRITIQUE:
{critique.critique}

IMPROVEMENTS NEEDED:
{chr(10).join(f'- {i}' for i in critique.improvements)}

CRITERIA TO SATISFY:
{chr(10).join(f'- {c}' for c in criteria)}

Generate an improved version that addresses all the issues.
Output ONLY the improved version, no explanations."""

        return await self.llm.generate(prompt)

    def get_learning_summary(self) -> dict:
        """Get summary of what has been learned from reflections."""
        if not self.reflection_history:
            return {
                "total_reflections": 0,
                "avg_score": 0,
                "lessons": [],
                "trend": "insufficient_data",
            }

        all_lessons = []
        all_improvements = []
        scores = []

        for r in self.reflection_history:
            all_lessons.extend(r.lessons_learned)
            all_improvements.extend(r.improvements)
            scores.append(r.score)

        # Calculate trend
        if len(scores) >= 5:
            recent = scores[-5:]
            older = scores[-10:-5] if len(scores) >= 10 else scores[:5]
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)

            if recent_avg > older_avg + 0.1:
                trend = "improving"
            elif recent_avg < older_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "total_reflections": len(self.reflection_history),
            "avg_score": sum(scores) / len(scores),
            "unique_lessons": list(set(all_lessons)),
            "common_improvements": self._get_common_items(all_improvements, 5),
            "trend": trend,
            "by_type": self._group_by_type(),
        }

    def get_recent_critiques(self, n: int = 5) -> List[dict]:
        """Get recent critiques."""
        return [r.to_dict() for r in self.reflection_history[-n:]]

    def get_improvement_suggestions(self) -> List[str]:
        """Get aggregated improvement suggestions."""
        all_improvements = []
        for r in self.reflection_history[-20:]:
            all_improvements.extend(r.improvements)
        return self._get_common_items(all_improvements, 10)

    def _store_reflection(self, reflection: Reflection):
        """Store reflection and update memory."""
        self.reflection_history.append(reflection)
        self._reflection_count += 1

        # Store lessons in memory
        for lesson in reflection.lessons_learned:
            self.memory.remember_experience(
                experience=f"Reflection: {reflection.subject[:100]}",
                outcome=lesson,
                context={"type": reflection.type.value, "score": reflection.score},
                importance=reflection.score,
            )

    def _generate_id(self) -> str:
        """Generate unique reflection ID."""
        import hashlib
        self._reflection_count += 1
        return hashlib.md5(
            f"reflection_{self._reflection_count}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response."""
        # Try to find JSON block
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

    def _get_common_items(self, items: List[str], n: int) -> List[str]:
        """Get most common items from a list."""
        from collections import Counter
        counter = Counter(items)
        return [item for item, _ in counter.most_common(n)]

    def _group_by_type(self) -> dict:
        """Group reflection stats by type."""
        by_type = {}
        for r in self.reflection_history:
            type_name = r.type.value
            if type_name not in by_type:
                by_type[type_name] = {"count": 0, "avg_score": 0, "scores": []}
            by_type[type_name]["count"] += 1
            by_type[type_name]["scores"].append(r.score)

        for type_name, data in by_type.items():
            data["avg_score"] = sum(data["scores"]) / len(data["scores"])
            del data["scores"]

        return by_type

    def clear_history(self):
        """Clear reflection history."""
        self.reflection_history = []

    def export_reflections(self) -> List[dict]:
        """Export all reflections."""
        return [r.to_dict() for r in self.reflection_history]
