"""
PROMETHEUS Client for TUI - Streaming integration.

Provides the same interface as GeminiClient but routes through
PROMETHEUS for enhanced capabilities.
"""

from typing import AsyncIterator, Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from jdev_cli.core.providers.prometheus_provider import PrometheusProvider, PrometheusConfig


@dataclass
class PrometheusStreamConfig:
    """Streaming configuration."""
    temperature: float = 1.0
    max_output_tokens: int = 8192
    enable_world_model: bool = True
    enable_memory: bool = True
    enable_reflection: bool = True
    init_timeout: float = 15.0
    stream_timeout: float = 120.0
    chunk_timeout: float = 45.0


class PrometheusClient:
    """
    PROMETHEUS Client with streaming support.

    Drop-in replacement for GeminiClient that adds:
    - World model simulation (preview actions)
    - Persistent memory (learn from interactions)
    - Self-reflection (improve over time)
    - Automatic tool creation
    """

    def __init__(
        self,
        config: Optional[PrometheusStreamConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        self.config = config or PrometheusStreamConfig()
        self._tools = tools or []
        self._provider: Optional[PrometheusProvider] = None
        self._initialized = False

        # Metrics
        self._total_requests = 0
        self._total_tokens = 0
        self._avg_response_time = 0.0

    async def _ensure_provider(self):
        """Lazy initialization."""
        if not self._initialized:
            prometheus_config = PrometheusConfig(
                enable_world_model=self.config.enable_world_model,
                enable_memory=self.config.enable_memory,
                enable_reflection=self.config.enable_reflection,
            )
            self._provider = PrometheusProvider(config=prometheus_config)
            self._initialized = True

    def set_tools(self, tools: List[Dict[str, Any]]):
        """Set available tools."""
        self._tools = tools

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]:
        """
        Stream response from PROMETHEUS.

        Yields chunks as they arrive, with full PROMETHEUS pipeline:
        1. Memory retrieval (relevant past experiences)
        2. World model simulation (plan before act)
        3. Execution (with tool calling)
        4. Reflection (learn from result)
        """
        await self._ensure_provider()

        start_time = datetime.now()
        self._total_requests += 1

        try:
            if self._provider:
                async for chunk in self._provider.stream(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    tools=tools or self._tools
                ):
                    yield chunk
        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            if self._total_requests > 0:
                self._avg_response_time = (
                    self._avg_response_time * (self._total_requests - 1) + elapsed
                ) / self._total_requests

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status."""
        base_status = {
            "provider": "prometheus",
            "initialized": self._initialized,
            "total_requests": self._total_requests,
            "avg_response_time": self._avg_response_time,
        }

        if self._initialized and self._provider:
            base_status["prometheus_status"] = self._provider.get_status()

        return base_status

    async def evolve(self, iterations: int = 5) -> Dict[str, Any]:
        """Run evolution cycle."""
        await self._ensure_provider()
        if self._provider:
            return await self._provider.evolve(iterations)
        return {"error": "Provider not initialized"}
