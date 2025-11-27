"""
PROMETHEUS Agents Module.

Agent0-inspired co-evolution agents (arXiv:2511.16043):
- Curriculum Agent - Generates progressively harder tasks
- Executor Agent - Learns to solve tasks
- Critic Agent - Evaluates and critiques
- Research Agent - Gathers information
"""

from .curriculum_agent import CurriculumAgent
from .executor_agent import ExecutorAgent

__all__ = [
    "CurriculumAgent",
    "ExecutorAgent",
]
