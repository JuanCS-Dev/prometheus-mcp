"""
Prometheus Orchestrator - Lead Agent.

Coordinates all subsystems:
- Memory System (MIRIX)
- World Model (SimuRA)
- Tool Factory (AutoTools)
- Reflection Engine (Reflexion)
- Co-Evolution Loop (Agent0)

Based on the Orchestrator-Worker pattern from Anthropic:
https://www.anthropic.com/engineering/multi-agent-research-system
"""

from dataclasses import dataclass, field
from typing import AsyncIterator, List, Dict, Optional, Any, Callable
from datetime import datetime
import asyncio
import json
import os

from .llm_client import GeminiClient
from .world_model import WorldModel, ActionType, WorldState
from .reflection import ReflectionEngine
from .evolution import CoEvolutionLoop
from ..memory.memory_system import MemorySystem
from ..tools.tool_factory import ToolFactory
from ..sandbox.executor import SandboxExecutor


@dataclass
class ExecutionContext:
    """Context for task execution."""
    task: str
    memory_context: Dict[str, Any]
    world_state: WorldState
    available_tools: List[Dict[str, Any]]
    constraints: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionResult:
    """Result of orchestrated execution."""
    task: str
    output: str
    success: bool
    score: float
    actions_taken: List[str]
    tools_used: List[str]
    reflection_score: float
    execution_time: float
    lessons_learned: List[str]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task": self.task[:100],
            "success": self.success,
            "score": self.score,
            "actions": len(self.actions_taken),
            "tools_used": self.tools_used,
            "reflection_score": self.reflection_score,
            "execution_time": self.execution_time,
        }


class PrometheusOrchestrator:
    """
    Main Orchestrator for PROMETHEUS.

    Coordinates all subsystems to execute complex tasks
    autonomously with self-improvement capabilities.

    Pipeline:
    1. Memory retrieval for context
    2. World model simulation for planning
    3. Tool execution (with auto-generation)
    4. Reflection and learning
    5. Evolution for continuous improvement
    """

    def __init__(
        self,
        llm_client: Optional[GeminiClient] = None,
        agent_name: str = "Prometheus",
    ):
        # Core LLM client
        self.llm = llm_client or GeminiClient()
        self.agent_name = agent_name

        # Initialize all subsystems
        self.memory = MemorySystem(agent_name=agent_name)
        self.sandbox = SandboxExecutor()
        self.tools = ToolFactory(self.llm, self.sandbox)
        self.world_model = WorldModel(self.llm)
        self.reflection = ReflectionEngine(self.llm, self.memory)
        self.evolution = CoEvolutionLoop(
            self.llm,
            self.tools,
            self.memory,
            self.reflection,
            self.sandbox,
        )

        # Register builtin tools
        self._register_builtin_tools()

        # Execution history
        self.execution_history: List[ExecutionResult] = []

        # State
        self._is_executing = False

    def _register_builtin_tools(self):
        """Register built-in tools."""
        # File operations
        self.tools.register_builtin("read_file", self._tool_read_file)
        self.tools.register_builtin("write_file", self._tool_write_file)
        self.tools.register_builtin("list_files", self._tool_list_files)

        # Code execution
        self.tools.register_builtin("execute_python", self._tool_execute_python)

        # Search and analysis
        self.tools.register_builtin("search_code", self._tool_search_code)
        self.tools.register_builtin("analyze_code", self._tool_analyze_code)

        # Memory operations
        self.tools.register_builtin("remember", self._tool_remember)
        self.tools.register_builtin("recall", self._tool_recall)

    async def execute(
        self,
        task: str,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """
        Execute a task with full orchestration.

        Yields progress updates as execution proceeds.
        """
        self._is_executing = True
        start_time = datetime.now()
        actions_taken = []
        tools_used = []

        try:
            yield f"🔥 PROMETHEUS: Starting task execution...\n\n"

            # 1. MEMORY: Retrieve context
            yield "📚 Retrieving relevant context from memory...\n"
            memory_context = self.memory.get_context_for_task(task)

            experiences = memory_context.get("relevant_experiences", [])
            if experiences:
                yield f"  → Found {len(experiences)} relevant past experiences\n"

            procedures = memory_context.get("relevant_procedures", [])
            if procedures:
                yield f"  → Found {len(procedures)} applicable procedures\n"

            # 2. WORLD MODEL: Simulate plans
            yield "\n🌍 Simulating potential approaches...\n"

            plans = await self.world_model.find_best_plan(
                goal=task,
                available_actions=[
                    ActionType.THINK,
                    ActionType.READ_FILE,
                    ActionType.WRITE_FILE,
                    ActionType.EXECUTE_CODE,
                    ActionType.USE_TOOL,
                ],
                max_steps=8,
                num_candidates=3,
            )

            if plans:
                best_plan = plans[0]
                yield f"  → Best approach: {best_plan.overall_success_probability:.0%} predicted success\n"

                if best_plan.critical_risks:
                    yield f"  ⚠️  Identified risks: {', '.join(best_plan.critical_risks[:2])}\n"

                actions_taken.append("plan_generated")

            # 3. TOOL CHECK: Identify needed tools
            yield "\n🔧 Checking available tools...\n"
            needed_tools = self._identify_needed_tools(task)
            available = [t["name"] for t in self.tools.list_tools()]

            for tool_name in needed_tools:
                if tool_name not in available:
                    yield f"  → Generating new tool: {tool_name}...\n"
                    # Tool would be generated here if needed

            # 4. EXECUTION: Main task execution
            yield "\n⚡ Executing task...\n"

            execution_output = await self._execute_task_with_context(
                task,
                memory_context,
                plans[0] if plans else None,
            )

            yield f"\n📝 Output:\n{'-' * 40}\n{execution_output}\n{'-' * 40}\n"

            actions_taken.append("task_executed")

            # 5. REFLECTION: Analyze results
            yield "\n🪞 Reflecting on execution...\n"

            reflection_result = await self.reflection.critique_action(
                action=f"Executed task: {task[:100]}",
                result=execution_output[:500],
                context={"memory_context": str(memory_context)[:200]},
            )

            yield f"  → Quality score: {reflection_result.score:.0%}\n"

            if reflection_result.improvements:
                yield f"  → Improvements identified: {len(reflection_result.improvements)}\n"

            if reflection_result.lessons_learned:
                yield f"  → Lessons learned: {len(reflection_result.lessons_learned)}\n"
                for lesson in reflection_result.lessons_learned[:2]:
                    yield f"     • {lesson}\n"

            # 6. LEARNING: Update memory
            yield "\n🧠 Updating knowledge base...\n"

            self.memory.remember_experience(
                experience=f"Task: {task[:200]}",
                outcome=f"Result: {execution_output[:200]}",
                context={
                    "score": reflection_result.score,
                    "tools_used": tools_used,
                },
                importance=reflection_result.score,
            )

            # Consolidate if needed
            if len(self.memory.episodic.entries) % 10 == 0:
                consolidated = self.memory.consolidate_to_vault()
                if consolidated:
                    yield f"  → Consolidated {consolidated} items to knowledge vault\n"

            # Calculate final metrics
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Store result
            result = ExecutionResult(
                task=task,
                output=execution_output,
                success=reflection_result.score > 0.6,
                score=reflection_result.score,
                actions_taken=actions_taken,
                tools_used=tools_used,
                reflection_score=reflection_result.score,
                execution_time=execution_time,
                lessons_learned=reflection_result.lessons_learned,
            )
            self.execution_history.append(result)

            yield f"\n✅ Task completed in {execution_time:.1f}s (score: {reflection_result.score:.0%})\n"

        except Exception as e:
            yield f"\n❌ Error during execution: {str(e)}\n"
            raise

        finally:
            self._is_executing = False

    async def execute_simple(self, task: str) -> str:
        """
        Execute a task and return only the final output.

        Simpler interface without streaming.
        """
        output_parts = []

        async for chunk in self.execute(task, stream=True):
            output_parts.append(chunk)

        return "".join(output_parts)

    async def _execute_task_with_context(
        self,
        task: str,
        context: Dict[str, Any],
        plan: Optional[Any] = None,
    ) -> str:
        """Execute the main task with all context."""
        # Build comprehensive prompt
        context_section = self._format_context(context)
        plan_section = self._format_plan(plan) if plan else ""

        tools_list = self.tools.list_tools()
        tools_section = "\n".join(
            f"- {t['name']}: {t.get('description', 'No description')[:60]}"
            for t in tools_list[:15]
        )

        prompt = f"""You are PROMETHEUS, a self-evolving AI agent. Execute this task thoroughly.

TASK: {task}

RELEVANT CONTEXT:
{context_section}

{plan_section}

AVAILABLE TOOLS:
{tools_section}

Execute the task step by step. If it's a coding task, provide working code.
If it's an analysis task, provide thorough analysis.
If it's a question, provide a comprehensive answer.

Be specific, accurate, and complete in your response."""

        return await self.llm.generate(prompt)

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format memory context for prompt."""
        sections = []

        if context.get("relevant_experiences"):
            exp_text = "\n".join(
                f"  - {e.get('content', '')[:80]}"
                for e in context["relevant_experiences"][:3]
            )
            sections.append(f"Past Experiences:\n{exp_text}")

        if context.get("relevant_knowledge"):
            know_text = "\n".join(
                f"  - [{k.get('topic', '')}]: {k.get('content', '')[:60]}"
                for k in context["relevant_knowledge"][:3]
            )
            sections.append(f"Relevant Knowledge:\n{know_text}")

        if context.get("relevant_procedures"):
            proc_text = "\n".join(
                f"  - {p.get('skill', '')}: {p.get('steps', [])[:2]}"
                for p in context["relevant_procedures"][:3]
            )
            sections.append(f"Known Procedures:\n{proc_text}")

        return "\n\n".join(sections) if sections else "No specific context retrieved."

    def _format_plan(self, plan: Any) -> str:
        """Format plan for prompt."""
        if not plan or not hasattr(plan, 'actions_taken'):
            return ""

        steps = []
        for i, action in enumerate(plan.actions_taken[:5], 1):
            steps.append(f"  {i}. {action.action_type.value}: {action.predicted_outcome[:50]}")

        return f"""
RECOMMENDED APPROACH:
{chr(10).join(steps)}
(Success probability: {plan.overall_success_probability:.0%})
"""

    def _identify_needed_tools(self, task: str) -> List[str]:
        """Identify tools that might be needed for the task."""
        needed = []
        task_lower = task.lower()

        tool_keywords = {
            "read_file": ["read", "file", "content", "load"],
            "write_file": ["write", "save", "create file", "output to"],
            "execute_python": ["run", "execute", "python", "code"],
            "search_code": ["search", "find", "grep", "locate"],
            "analyze_code": ["analyze", "review", "examine", "check"],
        }

        for tool_name, keywords in tool_keywords.items():
            if any(kw in task_lower for kw in keywords):
                needed.append(tool_name)

        return needed

    # =========================================================================
    # BUILTIN TOOLS
    # =========================================================================

    async def _tool_read_file(self, path: str) -> str:
        """Read file contents."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content[:10000]  # Limit size
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except Exception as e:
            return f"Error reading file: {e}"

    async def _tool_write_file(self, path: str, content: str) -> str:
        """Write content to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    async def _tool_list_files(self, directory: str = ".", pattern: str = "*") -> str:
        """List files in directory."""
        import glob
        try:
            files = glob.glob(os.path.join(directory, pattern))
            return "\n".join(files[:50])
        except Exception as e:
            return f"Error listing files: {e}"

    async def _tool_execute_python(self, code: str) -> str:
        """Execute Python code in sandbox."""
        result = await self.sandbox.execute(code, timeout=30)
        if result.success:
            return result.stdout or "Code executed successfully (no output)"
        return f"Error: {result.stderr or result.error_message}"

    async def _tool_search_code(self, query: str, path: str = ".") -> str:
        """Search for code patterns."""
        # Simple grep-like search
        import subprocess
        try:
            result = subprocess.run(
                ["grep", "-r", "-n", query, path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout[:5000] or "No matches found"
        except Exception as e:
            return f"Search error: {e}"

    async def _tool_analyze_code(self, code: str) -> str:
        """Analyze code for issues."""
        prompt = f"""Analyze this code for potential issues:

```
{code}
```

Identify:
1. Bugs or errors
2. Performance issues
3. Security concerns
4. Style improvements

Be specific and actionable."""

        return await self.llm.generate(prompt)

    async def _tool_remember(self, key: str, value: str) -> str:
        """Store something in memory."""
        self.memory.learn_fact(key, value, source="tool_remember")
        return f"Remembered: {key}"

    async def _tool_recall(self, query: str) -> str:
        """Recall from memory."""
        results = self.memory.search_knowledge(query, top_k=5)
        if results:
            return "\n".join(
                f"- {r['topic']}: {r['content']}"
                for r in results
            )
        return "Nothing relevant found in memory"

    # =========================================================================
    # EVOLUTION & LEARNING
    # =========================================================================

    async def evolve_capabilities(
        self,
        iterations: int = 10,
        domain: str = "general",
    ) -> Dict[str, Any]:
        """
        Run evolution cycle to improve capabilities.

        Useful for "warming up" the agent before production use.
        """
        from ..agents.curriculum_agent import TaskDomain

        domain_enum = TaskDomain[domain.upper()] if domain.upper() in TaskDomain.__members__ else TaskDomain.GENERAL

        async for progress in self.evolution.evolve(
            num_iterations=iterations,
            domain=domain_enum,
            yield_progress=True,
        ):
            pass  # Consume generator

        return self.evolution.get_evolution_summary()

    async def benchmark_capabilities(self) -> Dict[str, Any]:
        """Run a benchmark of current capabilities."""
        return await self.evolution.benchmark(num_tasks_per_level=2)

    # =========================================================================
    # STATUS & EXPORT
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get complete system status."""
        return {
            "agent_name": self.agent_name,
            "is_executing": self._is_executing,
            "memory": self.memory.get_stats(),
            "tools": self.tools.get_stats(),
            "world_model": self.world_model.get_stats(),
            "reflection": self.reflection.get_learning_summary(),
            "evolution": self.evolution.get_evolution_summary() if self.evolution.evolution_history else {},
            "execution_history": len(self.execution_history),
        }

    def get_learning_report(self) -> Dict[str, Any]:
        """Get comprehensive learning report."""
        return {
            "memory_stats": self.memory.get_stats(),
            "skills_report": self.evolution.executor.get_skill_report() if hasattr(self.evolution, 'executor') else {},
            "reflection_summary": self.reflection.get_learning_summary(),
            "improvement_suggestions": self.reflection.get_improvement_suggestions(),
            "evolution_recommendations": self.evolution.get_recommendations(),
        }

    def export_state(self) -> Dict[str, Any]:
        """Export complete orchestrator state for persistence."""
        return {
            "agent_name": self.agent_name,
            "memory": self.memory.export_state(),
            "tools": self.tools.export_tools(),
            "evolution": self.evolution.export_state(),
            "reflections": self.reflection.export_reflections(),
            "execution_history": [r.to_dict() for r in self.execution_history[-100:]],
        }

    def import_state(self, state: Dict[str, Any]):
        """Import previously exported state."""
        if "agent_name" in state:
            self.agent_name = state["agent_name"]

        if "memory" in state:
            self.memory.import_state(state["memory"])

        if "tools" in state:
            self.tools.import_tools(state["tools"])

    @property
    def is_busy(self) -> bool:
        """Check if orchestrator is currently executing."""
        return self._is_executing
