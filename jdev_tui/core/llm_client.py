"""
LLM Client Module - Gemini API Integration
==========================================

Simplified facade after SCALE & SUSTAIN refactoring (Nov 2025).

Components extracted to dedicated modules:
- CircuitBreaker: jdev_tui/core/resilience/circuit_breaker.py
- ToolCallParser: jdev_tui/core/parsing/tool_call_parser.py
- Streaming: jdev_tui/core/streaming/gemini_stream.py

This module provides:
- GeminiClient: Main client with function calling support
- Re-exports for backward compatibility
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, AsyncIterator, Dict, List, Optional

# Import from extracted modules
from jdev_tui.core.resilience_patterns.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitBreakerStats,
    CircuitState,
)
from jdev_tui.core.parsing.tool_call_parser import (
    ToolCallParser,
    KNOWN_TOOLS,
)
from jdev_tui.core.schema_adapter import SchemaAdapter
from jdev_tui.core.streaming.gemini_stream import (
    GeminiStreamConfig,
    GeminiStreamer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# GEMINI CLIENT
# =============================================================================

class GeminiClient:
    """
    Optimized Gemini API client with streaming support.

    Best Practices (Nov 2025):
    - Temperature 1.0 for Gemini 3.x (optimized setting)
    - Streaming for UI responsiveness
    - System instructions for consistent behavior
    - Exponential backoff with jitter for rate limits
    - Circuit Breaker for fault tolerance

    Attributes:
        api_key: Gemini API key
        model_name: Model identifier
        temperature: Generation temperature
        max_output_tokens: Maximum response length

    Example:
        client = GeminiClient(api_key="...", model="gemini-2.0-flash")
        async for chunk in client.stream("Hello!"):
            print(chunk, end="")
    """

    # Timeout configuration
    INIT_TIMEOUT: float = 10.0
    STREAM_TIMEOUT: float = 60.0
    CHUNK_TIMEOUT: float = 30.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 1.0,
        max_output_tokens: int = 8192,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize Gemini client.

        Args:
            api_key: API key (defaults to GEMINI_API_KEY or GOOGLE_API_KEY env var)
            model: Model name (defaults to GEMINI_MODEL env var or gemini-2.0-flash)
            temperature: Generation temperature (0-2, default 1.0)
            max_output_tokens: Maximum response tokens (default 8192)
            circuit_breaker_config: Optional circuit breaker configuration
        """
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self.model_name = model or os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

        # Streaming configuration
        self._stream_config = GeminiStreamConfig(
            model_name=self.model_name,
            api_key=self.api_key or "",
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            init_timeout=self.INIT_TIMEOUT,
            stream_timeout=self.STREAM_TIMEOUT,
            chunk_timeout=self.CHUNK_TIMEOUT,
        )
        self._streamer: Optional[GeminiStreamer] = None
        self._initialized = False

        # Function calling support
        self._tool_schemas: List[Dict[str, Any]] = []
        self._gemini_tools = None

        # Circuit Breaker for resilience
        self._circuit_breaker = CircuitBreaker(
            name="gemini_api",
            config=circuit_breaker_config or CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout=30.0,
                half_open_max_calls=3,
            )
        )

    def set_tools(self, schemas: List[Dict[str, Any]]) -> None:
        """
        Configure tools for function calling.

        Args:
            schemas: List of tool schemas with name, description, parameters
        """
        self._tool_schemas = schemas
        self._gemini_tools = None  # Reset to force rebuild

    def _build_gemini_tools(self) -> Optional[List[Any]]:
        """Convert tool schemas to Gemini Tool objects."""
        if not self._tool_schemas:
            return None

        try:
            from google.generativeai.types import (
                FunctionDeclaration,
                Tool as GeminiTool,
            )

            declarations = []
            for schema in self._tool_schemas:
                try:
                    # Use SchemaAdapter to transform and validate
                    gemini_schema = SchemaAdapter.to_gemini_schema(schema)

                    declarations.append(
                        FunctionDeclaration(
                            name=gemini_schema["name"],
                            description=gemini_schema["description"],
                            parameters=gemini_schema["parameters"]
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to adapt schema for {schema.get('name')}: {e}")
                    # Continue to try other tools, or raise if strict
                    continue

            if not declarations:
                logger.warning("No valid tool declarations built")
                return None

            self._gemini_tools = [GeminiTool(function_declarations=declarations)]
            return self._gemini_tools

        except ImportError:
            logger.warning("google-generativeai not available for function calling")
            return None
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to build Gemini tools: {e}")
            return None

    async def _ensure_initialized(self) -> bool:
        """Lazy initialization of streamer with timeout."""
        if self._initialized and self._streamer:
            return True

        if not self.api_key:
            logger.error("No API key configured")
            return False

        try:
            self._streamer = GeminiStreamer(self._stream_config)
            result = await asyncio.wait_for(
                self._streamer.initialize(),
                timeout=self.INIT_TIMEOUT
            )
            self._initialized = result
            return result

        except asyncio.TimeoutError:
            self._circuit_breaker.record_failure("Initialization timeout")
            return False
        except Exception as e:
            self._circuit_breaker.record_failure(f"Init error: {str(e)}")
            return False

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        context: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream response from Gemini.

        Args:
            prompt: User's message
            system_prompt: System instructions
            context: Optional conversation history
            **kwargs: Extra arguments (for compatibility)

        Yields:
            Text chunks for UI rendering

        Example:
            async for chunk in client.stream("Explain Python decorators"):
                print(chunk, end="", flush=True)
        """
        # Check circuit breaker first
        if not await self._circuit_breaker.can_execute():
            retry_after = self._circuit_breaker.retry_after
            yield f"⚡ Service temporarily unavailable. Retry in {retry_after:.0f}s"
            return

        if not await self._ensure_initialized():
            yield "❌ Gemini not configured. Set GEMINI_API_KEY environment variable."
            return

        # Build tools for function calling
        tools = self._build_gemini_tools() if self._tool_schemas else None

        try:
            async for chunk in self._streamer.stream(
                prompt, system_prompt, context, tools
            ):
                yield chunk

            # Success - record it
            self._circuit_breaker.record_success()

        except asyncio.TimeoutError:
            self._circuit_breaker.record_failure("Stream timeout")
            yield f"\n⚠️ Request timed out after {self.STREAM_TIMEOUT}s"
        except Exception as e:
            self._circuit_breaker.record_failure(str(e))
            yield f"\n❌ Error: {str(e)}"

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generate complete response (non-streaming).

        Args:
            prompt: User's message
            system_prompt: System instructions

        Returns:
            Complete response text
        """
        chunks = []
        async for chunk in self.stream(prompt, system_prompt):
            chunks.append(chunk)
        return "".join(chunks)

    @property
    def is_available(self) -> bool:
        """Check if Gemini is configured."""
        return bool(self.api_key)

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Access circuit breaker for external monitoring."""
        return self._circuit_breaker

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status for observability.

        Returns:
            Dict with health metrics and circuit breaker status
        """
        cb_status = self._circuit_breaker.get_status()
        return {
            "service": "gemini_api",
            "healthy": self._circuit_breaker.is_closed and self.is_available,
            "available": self.is_available,
            "initialized": self._initialized,
            "model": self.model_name,
            "circuit_breaker": cb_status,
            "config": {
                "init_timeout": self.INIT_TIMEOUT,
                "stream_timeout": self.STREAM_TIMEOUT,
                "chunk_timeout": self.CHUNK_TIMEOUT,
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
            }
        }

    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker (for recovery)."""
        self._circuit_breaker.reset()


# =============================================================================
# EXPORTS (Backward Compatibility)
# =============================================================================

__all__ = [
    # Main client
    'GeminiClient',
    # Parsing (re-exported from parsing module)
    'ToolCallParser',
    'KNOWN_TOOLS',
    # Circuit Breaker (re-exported from resilience module)
    'CircuitBreaker',
    'CircuitBreakerConfig',
    'CircuitBreakerOpen',
    'CircuitBreakerStats',
    'CircuitState',
    # Streaming config (re-exported from streaming module)
    'GeminiStreamConfig',
]
