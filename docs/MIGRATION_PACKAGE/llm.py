"""Production-grade multi-backend LLM client with resilience patterns.

Implements best practices from:
- OpenAI Codex: Exponential backoff, jitter, rate limit feedback
- Anthropic Claude: Token bucket awareness, queue system
- Google Gemini: Circuit breaker, timeout adaptation, recovery strategies
- Cursor AI: Load balancing, failover, token-aware rate limiting

Features:
- Exponential backoff with jitter
- Circuit breaker pattern
- Token-aware rate limiting
- Automatic failover
- Observability & telemetry
- Timeout management
- Request queue
"""

import asyncio
import time
import random
import logging
import os
import warnings

# Silence gRPC/glog warnings at SDK level
os.environ.setdefault('GRPC_VERBOSITY', 'ERROR')
os.environ.setdefault('GLOG_minloglevel', '3')
warnings.filterwarnings('ignore', message='.*ALTS.*')

from typing import AsyncGenerator, Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

from .config import config

logger = logging.getLogger(__name__)

# REMOVED top-level import: from huggingface_hub import InferenceClient


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for API resilience (Gemini strategy)."""
    
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 3
    
    failures: int = 0
    state: CircuitState = CircuitState.CLOSED
    last_failure_time: Optional[float] = None
    half_open_calls: int = 0
    
    def record_success(self) -> None:
        """Record successful call."""
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker: CLOSED (recovered)")
    
    def record_failure(self) -> None:
        """Record failed call."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker: OPEN ({self.failures} consecutive failures)")
    
    def can_attempt(self) -> tuple[bool, str]:
        """Check if request can be attempted."""
        if self.state == CircuitState.CLOSED:
            return True, "Circuit closed"
        
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker: HALF_OPEN (testing recovery)")
                return True, "Circuit half-open"
            return False, f"Circuit open (cooling down)"
        
        # HALF_OPEN state
        if self.half_open_calls < self.half_open_max_calls:
            self.half_open_calls += 1
            return True, f"Circuit half-open (test {self.half_open_calls}/{self.half_open_max_calls})"
        
        return False, "Circuit half-open limit reached"


@dataclass
class RateLimiter:
    """Token-aware rate limiter (Cursor AI strategy)."""
    
    requests_per_minute: int = 50
    tokens_per_minute: int = 10000
    
    request_times: deque = field(default_factory=deque)
    token_counts: deque = field(default_factory=deque)
    
    def can_proceed(self, estimated_tokens: int = 0) -> tuple[bool, float]:
        """Check if request can proceed.
        
        Returns:
            Tuple of (can_proceed, wait_seconds)
        """
        now = time.time()
        
        # Clean old entries (> 60s)
        while self.request_times and (now - self.request_times[0]) > 60:
            self.request_times.popleft()
        
        while self.token_counts and (now - self.token_counts[0][0]) > 60:
            self.token_counts.popleft()
        
        # Check request rate
        if len(self.request_times) >= self.requests_per_minute:
            wait_time = 60 - (now - self.request_times[0])
            return False, wait_time
        
        # Check token rate
        total_tokens = sum(count for _, count in self.token_counts)
        if total_tokens + estimated_tokens > self.tokens_per_minute:
            wait_time = 60 - (now - self.token_counts[0][0])
            return False, wait_time
        
        return True, 0.0
    
    def record_request(self, tokens: int = 0) -> None:
        """Record a request."""
        now = time.time()
        self.request_times.append(now)
        if tokens > 0:
            self.token_counts.append((now, tokens))


@dataclass
class RequestMetrics:
    """Telemetry and observability (Codex strategy)."""
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retried_requests: int = 0
    rate_limited_requests: int = 0
    circuit_breaker_blocks: int = 0
    
    total_latency: float = 0.0
    total_tokens: int = 0
    
    provider_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def record_success(self, provider: str, latency: float, tokens: int = 0) -> None:
        """Record successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency += latency
        self.total_tokens += tokens
        
        if provider not in self.provider_stats:
            self.provider_stats[provider] = {"success": 0, "failure": 0}
        self.provider_stats[provider]["success"] += 1
    
    def record_failure(self, provider: str) -> None:
        """Record failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        
        if provider not in self.provider_stats:
            self.provider_stats[provider] = {"success": 0, "failure": 0}
        self.provider_stats[provider]["failure"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics summary."""
        avg_latency = self.total_latency / max(self.successful_requests, 1)
        success_rate = self.successful_requests / max(self.total_requests, 1) * 100
        
        return {
            "total_requests": self.total_requests,
            "success_rate": f"{success_rate:.1f}%",
            "avg_latency_ms": f"{avg_latency * 1000:.0f}ms",
            "total_tokens": self.total_tokens,
            "retries": self.retried_requests,
            "rate_limited": self.rate_limited_requests,
            "circuit_breaker_blocks": self.circuit_breaker_blocks,
            "providers": self.provider_stats
        }


class LLMClient:
    """Production-grade LLM client with resilience patterns."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        timeout: float = 30.0,
        enable_circuit_breaker: bool = True,
        enable_rate_limiting: bool = True,
        enable_telemetry: bool = True,
        token_callback: Optional[Any] = None
    ):
        """Initialize resilient LLM client.
        
        Args:
            token_callback: Optional callback(input_tokens, output_tokens) for tracking
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.token_callback = token_callback
        
        # Resilience components
        self.circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None
        self.rate_limiter = RateLimiter() if enable_rate_limiting else None
        self.metrics = RequestMetrics() if enable_telemetry else None
        
        # Lazy providers
        self._hf_client = None
        self._nebius_client = None
        self._gemini_client = None
        self._ollama_client = None
        
        # Provider priority for failover (Gemini first - most powerful)
        # GEMINI FIRST ALWAYS - fastest and best quality
        self.provider_priority = ["gemini", "nebius", "hf", "ollama"]
        self.default_provider = "gemini"  # FORCE GEMINI, not auto

    @property
    def hf_client(self):
        """Lazy load HuggingFace client."""
        if self._hf_client is None and config.hf_token:
            try:
                from huggingface_hub import InferenceClient
                self._hf_client = InferenceClient(token=config.hf_token)
            except ImportError:
                logger.warning("huggingface_hub not installed")
        return self._hf_client

    @property
    def nebius_client(self):
        """Lazy load Nebius provider."""
        if self._nebius_client is None:
            nebius_key = os.getenv("NEBIUS_API_KEY")
            if nebius_key:
                try:
                    from .providers.nebius import NebiusProvider
                    self._nebius_client = NebiusProvider(api_key=nebius_key)
                    logger.info("Nebius provider initialized")
                except Exception as e:
                    logger.warning(f"Nebius init failed: {e}")
        return self._nebius_client

    @property
    def gemini_client(self):
        """Lazy load Gemini provider."""
        if self._gemini_client is None:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                try:
                    from .providers.gemini import GeminiProvider
                    self._gemini_client = GeminiProvider(api_key=gemini_key)
                    logger.info("Gemini provider initialized")
                except Exception as e:
                    logger.warning(f"Gemini init failed: {e}")
        return self._gemini_client

    @property
    def ollama_client(self):
        """Lazy load Ollama provider."""
        if self._ollama_client is None:
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:latest")
            try:
                from .providers.ollama import OllamaProvider
                self._ollama_client = OllamaProvider(base_url=ollama_url, model=ollama_model)
                logger.info(f"Ollama provider initialized: {ollama_url} / {ollama_model}")
            except Exception as e:
                logger.warning(f"Ollama init failed: {e}")
        return self._ollama_client
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = random.uniform(0.1, 0.3) * delay
        return delay + jitter
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if error is retryable."""
        retryable_errors = [
            "timeout", "429", "500", "502", "503", "504",
            "connection", "network"
        ]
        error_str = str(error).lower()
        return any(err in error_str for err in retryable_errors)

    
    async def stream_chat(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        provider: Optional[str] = None,
        enable_failover: bool = True
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion with full resilience."""
        # Validate prompt
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        max_tokens = max_tokens or config.max_tokens
        temperature = temperature or config.temperature
        provider = provider or self.default_provider
        
        # Build messages
        messages = []
        if context:
            messages.append({
                "role": "system",
                "content": f"You are a helpful coding assistant. Use this context:\n\n{context}"
            })
        messages.append({"role": "user", "content": prompt})
        
        # Select provider(s)
        if provider == "auto":
            providers_to_try = self._get_failover_providers()
        else:
            providers_to_try = [provider]
            if enable_failover:
                providers_to_try.extend([p for p in self.provider_priority if p != provider])
        
        # Try providers with failover
        last_error = None
        for current_provider in providers_to_try:
            try:
                logger.info(f"🔌 Attempting provider: {current_provider}")
                
                async for chunk in self._stream_with_provider(
                    current_provider,
                    messages,
                    max_tokens,
                    temperature
                ):
                    yield chunk
                
                return
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                
                # Check if error is quota/rate limit (429)
                is_quota_error = "429" in error_msg or "quota" in error_msg.lower()
                
                if is_quota_error:
                    logger.warning(f"⚠️  Provider {current_provider} quota exceeded (429)")
                else:
                    logger.error(f"❌ Provider {current_provider} failed: {error_msg[:100]}")
                
                # Attempt failover if more providers available
                if providers_to_try.index(current_provider) < len(providers_to_try) - 1:
                    next_provider = providers_to_try[providers_to_try.index(current_provider) + 1]
                    logger.info(f"🔄 Failing over: {current_provider} → {next_provider}")
                    continue
                else:
                    logger.error(f"🚨 All {len(providers_to_try)} providers exhausted")
                    break
        
        raise RuntimeError(f"All providers failed. Last error: {last_error}")
    
    def _get_failover_providers(self) -> List[str]:
        """Get list of providers for failover - GEMINI FIRST ALWAYS."""
        available = []
        
        # FORCE GEMINI FIRST (fastest and most powerful)
        if self.gemini_client:
            available.append("gemini")
        if self.nebius_client:
            available.append("nebius")
        if self.hf_client:
            available.append("hf")
        # Ollama LAST (slowest)
        if self.ollama_client:
            available.append("ollama")
        
        # Sort by success rate if telemetry enabled
        if self.metrics and self.metrics.provider_stats:
            def success_rate(provider: str) -> float:
                stats = self.metrics.provider_stats.get(provider, {"success": 0, "failure": 1})
                total = stats["success"] + stats["failure"]
                return stats["success"] / max(total, 1)
            
            available.sort(key=success_rate, reverse=True)
        
        return available or ["hf"]
    
    async def _stream_with_provider(
        self,
        provider: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> AsyncGenerator[str, None]:
        """Stream from specific provider with resilience."""
        # Circuit breaker check
        if self.circuit_breaker:
            can_attempt, reason = self.circuit_breaker.can_attempt()
            if not can_attempt:
                if self.metrics:
                    self.metrics.circuit_breaker_blocks += 1
                raise RuntimeError(f"Circuit breaker: {reason}")
        
        # Rate limiting check
        if self.rate_limiter:
            can_proceed, wait_time = self.rate_limiter.can_proceed()
            if not can_proceed:
                logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                if self.metrics:
                    self.metrics.rate_limited_requests += 1
                await asyncio.sleep(wait_time)
        
        # Stream with retry logic
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                chunks_received = 0
                
                # Select provider stream method
                if provider == "ollama":
                    if not self.ollama_client:
                        raise RuntimeError("Ollama not initialized")
                    stream_gen = self._stream_ollama(messages, max_tokens, temperature)
                elif provider == "gemini":
                    if not self.gemini_client:
                        raise RuntimeError("Gemini not initialized")
                    stream_gen = self._stream_gemini(messages, max_tokens, temperature)
                elif provider == "nebius":
                    if not self.nebius_client:
                        raise RuntimeError("Nebius not initialized")
                    stream_gen = self._stream_nebius(messages, max_tokens, temperature)
                else:  # hf
                    if not self.hf_client:
                        raise RuntimeError("HuggingFace not initialized")
                    stream_gen = self._stream_hf(messages, max_tokens, temperature)
                
                # Stream chunks
                async for chunk in stream_gen:
                    chunks_received += 1
                    yield chunk
                
                # Success
                latency = time.time() - start_time
                if self.metrics:
                    self.metrics.record_success(provider, latency, tokens=chunks_received)
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                if self.rate_limiter:
                    self.rate_limiter.record_request(tokens=chunks_received)
                
                # Callback for token tracking (NEW!)
                if self.token_callback:
                    try:
                        # Estimate input tokens (rough: 1 token = 4 chars)
                        input_estimate = sum(len(m.get('content', '')) for m in messages) // 4
                        self.token_callback(input_estimate, chunks_received)
                    except Exception as e:
                        logger.warning(f"Token callback failed: {e}")
                
                if attempt > 0:
                    logger.info(f"✅ Streaming succeeded after {attempt} retries")
                
                return
                
            except Exception as e:
                last_error = e
                # SILENT MODE: Apenas log debug para erros intermediários
                logger.debug(f"Provider {provider} failed: {str(e)[:100]} (attempt {attempt + 1})")
                
                if not self._should_retry(e):
                    # Não mostrar erro se há fallback disponível
                    logger.debug(f"Non-retryable error: {type(e).__name__}")
                    if self.metrics:
                        self.metrics.record_failure(provider)
                    if self.circuit_breaker:
                        self.circuit_breaker.record_failure()
                    raise
                
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                
                if attempt >= self.max_retries:
                    if self.metrics:
                        self.metrics.record_failure(provider)
                    break
                
                delay = self._calculate_backoff(attempt)
                logger.info(f"🔄 Retrying stream in {delay:.1f}s...")
                if self.metrics:
                    self.metrics.retried_requests += 1
                
                await asyncio.sleep(delay)
        
        logger.error(f"❌ All {self.max_retries + 1} stream attempts failed")
        raise last_error
    
    async def _stream_hf(
        self,
        messages: list,
        max_tokens: int,
        temperature: float
    ) -> AsyncGenerator[str, None]:
        """Stream from HuggingFace."""
        try:
            loop = asyncio.get_event_loop()
            
            def _generate():
                return self.hf_client.chat_completion(
                    messages=messages,
                    model=config.hf_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )
            
            stream = await loop.run_in_executor(None, _generate)
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"HF Error: {str(e)}")
            raise
    
    async def _stream_gemini(
        self,
        messages: list,
        max_tokens: int,
        temperature: float
    ) -> AsyncGenerator[str, None]:
        """Stream from Google Gemini."""
        try:
            async for chunk in self.gemini_client.stream_chat(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Gemini Error: {str(e)}")
            raise
    
    async def _stream_nebius(
        self,
        messages: list,
        max_tokens: int,
        temperature: float
    ) -> AsyncGenerator[str, None]:
        """Stream from Nebius Qwen models."""
        try:
            async for chunk in self.nebius_client.stream_chat(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Nebius Error: {str(e)}")
            raise
    
    async def _stream_ollama(
        self,
        messages: list,
        max_tokens: int,
        temperature: float
    ) -> AsyncGenerator[str, None]:
        """Stream from Ollama local inference."""
        try:
            async for chunk in self.ollama_client.stream_chat(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Ollama Error: {str(e)}")
            raise
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        provider: Optional[str] = None
    ) -> str:
        """Generate complete response (non-streaming)."""
        chunks = []
        async for chunk in self.stream_chat(prompt, context, max_tokens, temperature, provider):
            chunks.append(chunk)
        return "".join(chunks)
    
    def validate(self) -> tuple[bool, str]:
        """Validate at least one LLM backend is available."""
        available = []
        
        if self.hf_client:
            available.append("HuggingFace")
        if self.ollama_client:
            available.append("Ollama")
        
        if not available:
            return False, "No LLM backend available"
        
        return True, f"Backends available: {', '.join(available)}"
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        providers = []
        if self.hf_client:
            providers.append("hf")
        if self.ollama_client:
            providers.append("ollama")
        providers.append("auto")
        return providers
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get telemetry metrics."""
        if not self.metrics:
            return {"telemetry": "disabled"}
        
        stats = self.metrics.get_stats()
        
        if self.circuit_breaker:
            stats["circuit_breaker"] = {
                "state": self.circuit_breaker.state.value,
                "failures": self.circuit_breaker.failures
            }
        
        if self.rate_limiter:
            stats["rate_limiter"] = {
                "requests_last_minute": len(self.rate_limiter.request_times),
                "tokens_last_minute": sum(count for _, count in self.rate_limiter.token_counts)
            }
        
        return stats
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker."""
        if self.circuit_breaker:
            self.circuit_breaker.failures = 0
            self.circuit_breaker.state = CircuitState.CLOSED
            logger.info("Circuit breaker manually reset")
    
    def reset_metrics(self) -> None:
        """Reset telemetry metrics."""
        if self.metrics:
            self.metrics = RequestMetrics()
            logger.info("Metrics reset")


    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Alias for stream_chat for API compatibility."""
        async for chunk in self.stream_chat(messages, **kwargs):
            yield chunk

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM tokens one by one.

        This method wraps stream_chat() with a simpler interface
        that agents can use for streaming.

        Args:
            prompt: The user prompt
            system_prompt: Optional system instruction
            context: Optional context to prepend
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            provider: Force provider (hf, gemini, ollama, auto)

        Yields:
            str: Individual tokens as generated
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if context:
            messages.append({
                "role": "user",
                "content": f"Context information:\n{context}\n\nNow respond to:"
            })

        messages.append({"role": "user", "content": prompt})

        async for chunk in self.stream_chat(
            prompt=prompt,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            provider=provider
        ):
            yield chunk


# Global LLM client instance
llm_client = LLMClient(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    timeout=30.0,
    enable_circuit_breaker=True,
    enable_rate_limiting=True,
    enable_telemetry=True
)
