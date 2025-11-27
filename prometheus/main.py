"""
🔥 PROMETHEUS: Self-Evolving Meta-Agent

Entry point for Blaxel deployment and standalone usage.

Deploy to Blaxel:
    bl deploy --name prometheus

Run locally:
    python -m prometheus "your task here"

Features:
- Self-Evolution (Agent0) - Improves through practice
- World Model (SimuRA) - Simulates before acting
- 6-Type Memory (MIRIX) - Persistent learning
- Tool Factory (AutoTools) - Creates tools on-demand
- Reflection Engine (Reflexion) - Self-critique and improvement
- Multi-Agent Orchestration - Coordinates all subsystems

References:
- Agent0: arXiv:2511.16043
- SimuRA: arXiv:2507.23773
- MIRIX: arXiv:2507.07957
- AutoTools: arXiv:2405.16533
- Reflexion: arXiv:2303.11366
"""

import os
import sys
import asyncio
from typing import AsyncIterator, Optional

# Try to import Blaxel SDK
try:
    from blaxel.core import Agent, tool
    BLAXEL_AVAILABLE = True
except ImportError:
    BLAXEL_AVAILABLE = False

    # Mock decorators for standalone use
    def tool(func):
        return func

    class Agent:
        name = ""
        description = ""

        def __init__(self):
            pass


# Import PROMETHEUS components
from .core.llm_client import GeminiClient
from .core.orchestrator import PrometheusOrchestrator


class PrometheusAgent(Agent if BLAXEL_AVAILABLE else object):
    """
    🔥 PROMETHEUS: The Agent That Builds Itself

    A self-evolving meta-agent combining 6 cutting-edge research
    breakthroughs from November 2025.

    Capabilities:
    - Execute complex tasks with planning and reflection
    - Learn and improve from every interaction
    - Create new tools on-demand
    - Simulate actions before execution
    - Maintain persistent memory across sessions
    """

    name = "prometheus"
    description = """
🔥 PROMETHEUS: Self-Evolving Meta-Agent

Combines cutting-edge AI research (Nov 2025):
• World Model - Simulates before acting (+124% task completion)
• 6-Type Memory - Persistent learning system
• Tool Factory - Creates tools automatically
• Reflection Engine - Self-critique and improvement
• Co-Evolution - Continuous self-improvement

Use for complex tasks requiring planning, code generation,
analysis, and multi-step reasoning.
"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize PROMETHEUS agent."""
        if BLAXEL_AVAILABLE:
            super().__init__()

        # Get API key
        self.api_key = (
            api_key or
            os.environ.get("GOOGLE_API_KEY") or
            os.environ.get("GEMINI_API_KEY")
        )

        # Lazy initialization
        self._llm: Optional[GeminiClient] = None
        self._orchestrator: Optional[PrometheusOrchestrator] = None

    async def _ensure_initialized(self):
        """Ensure all components are initialized."""
        if self._orchestrator is None:
            self._llm = GeminiClient(api_key=self.api_key)
            self._orchestrator = PrometheusOrchestrator(
                llm_client=self._llm,
                agent_name="Prometheus",
            )

    @tool
    async def execute_task(self, task: str) -> str:
        """
        Execute a complex task with full PROMETHEUS capabilities.

        Uses world model simulation, memory context, reflection,
        and all available tools to complete the task.

        Args:
            task: The task to execute

        Returns:
            Complete execution output with results
        """
        await self._ensure_initialized()

        result_parts = []
        async for chunk in self._orchestrator.execute(task, stream=True):
            result_parts.append(chunk)

        return "".join(result_parts)

    @tool
    async def evolve(self, iterations: int = 5, domain: str = "general") -> str:
        """
        Run evolution cycle to improve capabilities.

        The agent practices generated tasks to improve its skills.

        Args:
            iterations: Number of practice iterations
            domain: Focus domain (general, code, reasoning, math)

        Returns:
            Evolution summary with improvement metrics
        """
        await self._ensure_initialized()

        summary = await self._orchestrator.evolve_capabilities(
            iterations=iterations,
            domain=domain,
        )

        import json
        return f"Evolution Complete:\n{json.dumps(summary, indent=2, default=str)}"

    @tool
    async def remember(self, topic: str, content: str) -> str:
        """
        Store information in persistent memory.

        Args:
            topic: Topic/key for the memory
            content: Content to remember

        Returns:
            Confirmation message
        """
        await self._ensure_initialized()
        self._orchestrator.memory.learn_fact(topic, content, source="user")
        return f"Remembered: {topic}"

    @tool
    async def recall(self, query: str) -> str:
        """
        Search and recall from memory.

        Args:
            query: Search query

        Returns:
            Relevant memories
        """
        await self._ensure_initialized()
        results = self._orchestrator.memory.search_knowledge(query, top_k=5)

        if not results:
            return "No relevant memories found."

        output = ["Found memories:"]
        for r in results:
            output.append(f"- [{r['topic']}]: {r['content']}")

        return "\n".join(output)

    @tool
    async def get_status(self) -> str:
        """
        Get current system status.

        Returns:
            Complete status of all PROMETHEUS subsystems
        """
        await self._ensure_initialized()

        import json
        status = self._orchestrator.get_status()
        return json.dumps(status, indent=2, default=str)

    @tool
    async def benchmark(self) -> str:
        """
        Run capability benchmark.

        Tests the agent across all difficulty levels.

        Returns:
            Benchmark results with performance breakdown
        """
        await self._ensure_initialized()

        import json
        results = await self._orchestrator.benchmark_capabilities()
        return f"Benchmark Results:\n{json.dumps(results, indent=2, default=str)}"

    async def run(self, prompt: str) -> AsyncIterator[str]:
        """
        Main entry point for Blaxel.

        Streams execution output.
        """
        await self._ensure_initialized()

        async for chunk in self._orchestrator.execute(prompt, stream=True):
            yield chunk

    async def chat(self, message: str) -> str:
        """
        Simple chat interface.

        For quick interactions without full orchestration.
        """
        await self._ensure_initialized()
        return await self._llm.generate(message)


# Create singleton instance for Blaxel
agent = PrometheusAgent()


# ============================================================================
# CLI INTERFACE
# ============================================================================

def print_banner():
    """Print PROMETHEUS banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🔥 PROMETHEUS: Self-Evolving Meta-Agent                         ║
║                                                                   ║
║   "The Agent That Builds Itself"                                  ║
║                                                                   ║
║   Combining 6 Breakthroughs from Nov 2025:                        ║
║   • Self-Evolution (Agent0)    • World Model (SimuRA)             ║
║   • 6-Type Memory (MIRIX)      • Tool Factory (AutoTools)         ║
║   • Reflection (Reflexion)     • Multi-Agent Orchestration        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="PROMETHEUS: Self-Evolving Meta-Agent"
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task to execute"
    )
    parser.add_argument(
        "--evolve",
        type=int,
        default=0,
        help="Run N evolution iterations before task"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run capability benchmark"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show system status"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode"
    )

    args = parser.parse_args()

    print_banner()

    agent = PrometheusAgent()

    # Warm up
    if args.evolve > 0:
        print(f"\n🧬 Running {args.evolve} evolution iterations...\n")
        result = await agent.evolve(iterations=args.evolve)
        print(result)

    # Benchmark
    if args.benchmark:
        print("\n📊 Running benchmark...\n")
        result = await agent.benchmark()
        print(result)
        return

    # Status
    if args.status:
        result = await agent.get_status()
        print(result)
        return

    # Interactive mode
    if args.interactive:
        print("\n🔥 Interactive Mode (type 'exit' to quit)\n")
        while True:
            try:
                task = input("\n> ")
                if task.lower() in ['exit', 'quit', 'q']:
                    print("Goodbye!")
                    break
                if task.strip():
                    result = await agent.execute_task(task)
                    print(result)
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
        return

    # Execute task
    if args.task:
        print(f"\n📋 Task: {args.task}\n")
        async for chunk in agent.run(args.task):
            print(chunk, end="", flush=True)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
