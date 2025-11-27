"""
🔥 PROMETHEUS: Self-Evolving Meta-Agent

The Agent That Builds Itself.

Combining 6 cutting-edge breakthroughs from Nov 2025:
1. Self-Evolution (Agent0) - arXiv:2511.16043
2. World Model (SimuRA) - arXiv:2507.23773
3. 6-Type Memory (MIRIX) - arXiv:2507.07957
4. Tool Factory (AutoTools) - arXiv:2405.16533
5. Reflection Engine (Reflexion) - arXiv:2303.11366
6. Multi-Agent Orchestration (Anthropic)

Author: JuanCS Dev
Date: 2025-11-27
Hackathon: Blaxel Choice Award - $2,500
"""

__version__ = "1.0.0"
__author__ = "JuanCS Dev"
__codename__ = "PROMETHEUS"

from .core.orchestrator import PrometheusOrchestrator
from .core.llm_client import GeminiClient

__all__ = [
    "PrometheusOrchestrator",
    "GeminiClient",
    "__version__",
    "__codename__",
]
