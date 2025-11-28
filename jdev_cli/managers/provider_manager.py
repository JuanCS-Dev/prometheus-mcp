"""
Provider Manager.

SCALE & SUSTAIN Phase 1.1.5 - Provider Manager.

Manages LLM providers with fallback and load balancing.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional
import threading


class ProviderStatus(Enum):
    """Provider health status."""
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    UNKNOWN = auto()


class ProviderType(Enum):
    """LLM provider types."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NEBIUS = "nebius"
    GROQ = "groq"
    LOCAL = "local"
    CUSTOM = "custom"
    PROMETHEUS = "prometheus"
    GEMINI = "gemini"


@dataclass
class ProviderConfig:
    """Provider configuration."""
    name: str
    type: ProviderType
    base_url: str
    api_key: Optional[str] = None
    model: str = ""
    timeout: int = 120
    max_retries: int = 3
    priority: int = 100  # Lower = higher priority
    enabled: bool = True
    rate_limit: Optional[int] = None  # requests per minute
    metadata: Dict[str, Any] = field(default_factory=dict)
    capabilities: Dict[str, bool] = field(default_factory=lambda: {
        "native_code_execution": False,
        "caching": False,
        "grounding": False,
        "system_instruction": True
    })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "priority": self.priority,
            "enabled": self.enabled,
            "rate_limit": self.rate_limit,
            "capabilities": self.capabilities,
        }


@dataclass
class ProviderHealth:
    """Provider health information."""
    status: ProviderStatus
    last_check: float
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    consecutive_failures: int = 0
    success_rate: float = 1.0

    def is_available(self) -> bool:
        """Check if provider is available for use."""
        return self.status in (ProviderStatus.HEALTHY, ProviderStatus.DEGRADED)


class ProviderManager:
    """
    Manages LLM providers with health monitoring and fallback.

    Features:
    - Multiple provider support
    - Health monitoring
    - Automatic failover
    - Load balancing (round-robin, priority, weighted)
    - Rate limiting
    - Request routing

    Example:
        manager = ProviderManager()

        # Add providers
        manager.add_provider(ProviderConfig(
            name="ollama-local",
            type=ProviderType.OLLAMA,
            base_url="http://localhost:11434",
            model="qwen2.5-coder:14b",
            priority=10
        ))

        manager.add_provider(ProviderConfig(
            name="nebius-cloud",
            type=ProviderType.NEBIUS,
            base_url="https://api.nebius.ai",
            api_key="...",
            priority=50  # Fallback
        ))

        # Get best available provider
        provider = manager.get_provider()

        # Or get specific provider
        ollama = manager.get_provider("ollama-local")
    """

    def __init__(self):
        self._providers: Dict[str, ProviderConfig] = {}
        self._health: Dict[str, ProviderHealth] = {}
        self._request_counts: Dict[str, int] = {}
        self._last_requests: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._round_robin_index = 0

    def add_provider(self, config: ProviderConfig) -> None:
        """Add a provider."""
        with self._lock:
            self._providers[config.name] = config
            self._health[config.name] = ProviderHealth(
                status=ProviderStatus.UNKNOWN,
                last_check=0
            )
            self._request_counts[config.name] = 0
            self._last_requests[config.name] = 0

    def remove_provider(self, name: str) -> bool:
        """Remove a provider."""
        with self._lock:
            if name in self._providers:
                del self._providers[name]
                del self._health[name]
                del self._request_counts[name]
                del self._last_requests[name]
                return True
            return False

    def get_provider(
        self,
        name: Optional[str] = None,
        strategy: str = "priority"
    ) -> Optional[ProviderConfig]:
        """
        Get a provider.

        Args:
            name: Specific provider name (optional)
            strategy: Selection strategy ("priority", "round_robin", "least_loaded")

        Returns:
            Provider config or None
        """
        with self._lock:
            if name:
                return self._providers.get(name)

            # Get available providers
            available = [
                (n, c) for n, c in self._providers.items()
                if c.enabled and self._health[n].is_available()
            ]

            if not available:
                # Fallback to any enabled provider
                available = [
                    (n, c) for n, c in self._providers.items()
                    if c.enabled
                ]

            if not available:
                return None

            if strategy == "priority":
                # Sort by priority (lower = higher priority)
                available.sort(key=lambda x: x[1].priority)
                return available[0][1]

            elif strategy == "round_robin":
                self._round_robin_index = (self._round_robin_index + 1) % len(available)
                return available[self._round_robin_index][1]

            elif strategy == "least_loaded":
                # Sort by request count
                available.sort(key=lambda x: self._request_counts[x[0]])
                return available[0][1]

            return available[0][1]

    def list_providers(
        self,
        enabled_only: bool = True,
        provider_type: Optional[ProviderType] = None
    ) -> List[ProviderConfig]:
        """List all providers."""
        providers = list(self._providers.values())

        if enabled_only:
            providers = [p for p in providers if p.enabled]

        if provider_type:
            providers = [p for p in providers if p.type == provider_type]

        return sorted(providers, key=lambda p: p.priority)

    def get_health(self, name: str) -> Optional[ProviderHealth]:
        """Get provider health status."""
        return self._health.get(name)

    def update_health(
        self,
        name: str,
        status: ProviderStatus,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Update provider health status."""
        with self._lock:
            if name not in self._health:
                return

            health = self._health[name]
            health.status = status
            health.last_check = time.time()
            health.latency_ms = latency_ms
            health.error = error

            if status == ProviderStatus.HEALTHY:
                health.consecutive_failures = 0
            elif status == ProviderStatus.UNHEALTHY:
                health.consecutive_failures += 1

    def record_request(
        self,
        name: str,
        success: bool,
        latency_ms: Optional[float] = None
    ) -> None:
        """Record a request for statistics and health."""
        with self._lock:
            if name not in self._providers:
                return

            self._request_counts[name] += 1
            self._last_requests[name] = time.time()

            # Update health based on request success
            health = self._health[name]

            if success:
                health.consecutive_failures = 0
                if health.status == ProviderStatus.UNHEALTHY:
                    health.status = ProviderStatus.DEGRADED
                elif health.status == ProviderStatus.DEGRADED:
                    health.status = ProviderStatus.HEALTHY
                else:
                    health.status = ProviderStatus.HEALTHY

                if latency_ms:
                    health.latency_ms = latency_ms
            else:
                health.consecutive_failures += 1
                if health.consecutive_failures >= 3:
                    health.status = ProviderStatus.UNHEALTHY
                else:
                    health.status = ProviderStatus.DEGRADED

            # Update success rate
            total = self._request_counts[name]
            if total > 0:
                failures = health.consecutive_failures
                health.success_rate = max(0, (total - failures) / total)

    def check_rate_limit(self, name: str) -> bool:
        """Check if provider is within rate limit."""
        with self._lock:
            config = self._providers.get(name)
            if not config or not config.rate_limit:
                return True

            # Simple per-minute rate limiting
            now = time.time()
            last = self._last_requests.get(name, 0)

            # Reset counter if more than a minute passed
            if now - last > 60:
                self._request_counts[name] = 0
                return True

            return self._request_counts[name] < config.rate_limit

    async def health_check(self, name: str) -> ProviderHealth:
        """Perform health check on a provider."""
        config = self._providers.get(name)
        if not config:
            return ProviderHealth(
                status=ProviderStatus.UNKNOWN,
                last_check=time.time(),
                error="Provider not found"
            )

        start = time.time()

        try:
            # Simple connectivity check based on provider type
            import aiohttp

            async with aiohttp.ClientSession() as session:
                if config.type == ProviderType.OLLAMA:
                    url = f"{config.base_url}/api/tags"
                elif config.type in (ProviderType.OPENAI, ProviderType.NEBIUS):
                    url = f"{config.base_url}/v1/models"
                else:
                    url = config.base_url

                async with session.get(url, timeout=5) as response:
                    latency = (time.time() - start) * 1000

                    if response.status == 200:
                        self.update_health(
                            name,
                            ProviderStatus.HEALTHY,
                            latency_ms=latency
                        )
                    else:
                        self.update_health(
                            name,
                            ProviderStatus.DEGRADED,
                            latency_ms=latency,
                            error=f"HTTP {response.status}"
                        )

        except asyncio.TimeoutError:
            self.update_health(
                name,
                ProviderStatus.UNHEALTHY,
                error="Health check timeout"
            )

        except Exception as e:
            self.update_health(
                name,
                ProviderStatus.UNHEALTHY,
                error=str(e)
            )

        return self._health[name]

    async def health_check_all(self) -> Dict[str, ProviderHealth]:
        """Check health of all providers."""
        tasks = [
            self.health_check(name)
            for name in self._providers
        ]

        await asyncio.gather(*tasks, return_exceptions=True)
        return {name: self._health[name] for name in self._providers}

    def enable_provider(self, name: str) -> bool:
        """Enable a provider."""
        if name in self._providers:
            self._providers[name].enabled = True
            return True
        return False

    def disable_provider(self, name: str) -> bool:
        """Disable a provider."""
        if name in self._providers:
            self._providers[name].enabled = False
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        stats = {}

        for name, config in self._providers.items():
            health = self._health[name]
            stats[name] = {
                "type": config.type.value,
                "enabled": config.enabled,
                "priority": config.priority,
                "status": health.status.name,
                "latency_ms": health.latency_ms,
                "success_rate": f"{health.success_rate:.2%}",
                "request_count": self._request_counts[name],
                "consecutive_failures": health.consecutive_failures,
            }

        return stats


__all__ = [
    'ProviderManager',
    'ProviderConfig',
    'ProviderStatus',
    'ProviderType',
    'ProviderHealth',
]
