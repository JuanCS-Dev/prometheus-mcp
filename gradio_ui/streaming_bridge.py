"""
Gradio 6 Streaming Bridge - Conecta GeminiClient ao Gradio 6.

Este módulo substitui o cli_bridge.py antigo que usava ShellBridge.
Agora usa diretamente o GeminiClient refatorado com:
- Streaming assíncrono convertido para sync (Gradio 6 espera generators)
- Detecção de tool calls com metadata visual
- Circuit breaker para resiliência
- Deduplicação de linhas

Hackathon Dia 30 - Prêmios Alvo:
- 🏆 Google Gemini — $30,000 em API Credits
- 💰 Modal Innovation Award — $2,500 Cash
- 💰 Blaxel Choice Award — $2,500 Cash

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple
from jdev_tui.core.prometheus_client import PrometheusClient

logger = logging.getLogger(__name__)

# =============================================================================
# GRADIO 6 CHATMESSAGE COMPATIBILITY
# =============================================================================

# Gradio 6 uses ChatMessage objects with metadata for tool display
# We create a simple dataclass to match the interface

@dataclass
class ChatMessage:
    """
    Gradio 6 ChatMessage compatible dataclass.

    Attributes:
        role: "user" or "assistant"
        content: Message text content
        metadata: Optional dict with "title" and "value" for tool display
    """
    role: str
    content: str
    metadata: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Gradio serialization."""
        result = {"role": self.role, "content": self.content}
        if self.metadata:
            result["metadata"] = self.metadata
        return result


# =============================================================================
# STREAMING METRICS
# =============================================================================

@dataclass
class StreamingMetrics:
    """Metrics for streaming performance tracking."""
    chunks_received: int = 0
    total_chars: int = 0
    start_time: float = field(default_factory=time.time)
    first_chunk_time: Optional[float] = None
    end_time: Optional[float] = None
    tool_calls: int = 0
    deduplicated_lines: int = 0

    @property
    def ttft(self) -> Optional[float]:
        """Time to first token in seconds."""
        if self.first_chunk_time:
            return self.first_chunk_time - self.start_time
        return None

    @property
    def total_time(self) -> Optional[float]:
        """Total streaming time in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def chars_per_second(self) -> float:
        """Characters per second throughput."""
        if self.total_time and self.total_time > 0:
            return self.total_chars / self.total_time
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dict."""
        return {
            "chunks": self.chunks_received,
            "chars": self.total_chars,
            "ttft_ms": int(self.ttft * 1000) if self.ttft else None,
            "total_ms": int(self.total_time * 1000) if self.total_time else None,
            "cps": int(self.chars_per_second),
            "tool_calls": self.tool_calls,
            "deduplicated": self.deduplicated_lines,
        }


# =============================================================================
# TOOL CALL PARSER
# =============================================================================

class ToolCallDetector:
    """
    Detects tool calls in streaming output.

    Supports multiple formats:
    - [TOOL_CALL:name:{"arg": "value"}]
    - ```tool_call\nname(arg=value)\n```
    - JSON function call format
    """

    TOOL_CALL_PATTERN = re.compile(
        r'\[TOOL_CALL:(\w+):(\{.*?\})\]',
        re.DOTALL
    )

    CODE_BLOCK_TOOL_PATTERN = re.compile(
        r'```tool_call\n(\w+)\((.*?)\)\n```',
        re.DOTALL
    )

    def detect(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Detect tool call in text.

        Returns:
            Tuple of (tool_name, args_dict) if found, None otherwise
        """
        # Try [TOOL_CALL:...] format first
        match = self.TOOL_CALL_PATTERN.search(text)
        if match:
            name = match.group(1)
            try:
                args = json.loads(match.group(2))
                return (name, args)
            except json.JSONDecodeError:
                return (name, {})

        # Try code block format
        match = self.CODE_BLOCK_TOOL_PATTERN.search(text)
        if match:
            name = match.group(1)
            args_str = match.group(2)
            args = self._parse_function_args(args_str)
            return (name, args)

        return None

    def _parse_function_args(self, args_str: str) -> Dict[str, Any]:
        """Parse function-style arguments like 'path="/tmp", content="hello"'."""
        args = {}
        # Simple key=value parsing
        for part in args_str.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                args[key] = value
        return args


# =============================================================================
# DEDUPLICATION FILTER
# =============================================================================

class DeduplicationFilter:
    """
    Filters duplicate lines from LLM output.

    LLMs sometimes repeat lines during streaming. This filter
    tracks recent lines and removes exact duplicates.
    """

    def __init__(self, history_size: int = 10):
        self._history: List[str] = []
        self._history_size = history_size
        self._deduplicated_count = 0

    def filter_chunk(self, chunk: str) -> str:
        """
        Filter duplicate lines from chunk.

        Args:
            chunk: Raw text chunk from LLM

        Returns:
            Filtered chunk with duplicates removed
        """
        if '\n' not in chunk:
            return chunk

        lines = chunk.split('\n')
        filtered_lines = []

        for line in lines:
            line_stripped = line.strip()

            # Keep empty lines
            if not line_stripped:
                filtered_lines.append(line)
                continue

            # Check for duplicate
            if line_stripped in self._history[-5:]:
                self._deduplicated_count += 1
                continue

            filtered_lines.append(line)
            self._history.append(line_stripped)

            # Maintain history size
            if len(self._history) > self._history_size:
                self._history.pop(0)

        return '\n'.join(filtered_lines)

    @property
    def deduplicated_count(self) -> int:
        """Number of lines that were deduplicated."""
        return self._deduplicated_count

    def reset(self) -> None:
        """Reset filter state."""
        self._history.clear()
        self._deduplicated_count = 0


# =============================================================================
# GRADIO STREAMING BRIDGE
# =============================================================================

class GradioStreamingBridge:
    """
    Bridge entre GeminiClient e Gradio 6 ChatInterface.

    Responsabilidades:
    - Converte AsyncIterator[str] → Generator[List[ChatMessage], None, None]
    - Integra GeminiClient com circuit breaker
    - Detecta tool calls e formata com metadata visual
    - Deduplica linhas repetidas
    - Gerencia event loop próprio para conversão async→sync

    Usage:
        bridge = GradioStreamingBridge()
        if not bridge.initialize():
            print("Failed to initialize")
            return

        history = []
        for updated_history in bridge.stream_chat("Hello!", history):
            # Update UI with updated_history
            pass
    """

    # Cursor frames for streaming animation
    CURSOR_FRAMES = ["▋", "▌", "▍", "▎", "▏", " "]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: str = "",
        chunk_timeout: float = 30.0,
        enable_prometheus: bool = False,
    ):
        """
        Initialize GradioStreamingBridge.

        Args:
            api_key: Gemini API key (defaults to env vars)
            model: Model name (defaults to env var or gemini-2.0-flash)
            system_prompt: System instructions for all conversations
            chunk_timeout: Timeout for individual chunks in seconds
            enable_prometheus: Enable PROMETHEUS provider
        """
        self._api_key = api_key
        self._model = model
        self._system_prompt = system_prompt
        self._chunk_timeout = chunk_timeout
        self._enable_prometheus = enable_prometheus

        # Components (lazy init)
        self._client = None
        self._prometheus_client = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._initialized = False

        # Helpers
        self._tool_detector = ToolCallDetector()
        self._dedup_filter = DeduplicationFilter()

        # Conversation history for context
        self._conversation_context: List[Dict[str, str]] = []

        # Current streaming state
        self._current_metrics: Optional[StreamingMetrics] = None

    def _sanitize_tool_calls(self, chunk: str) -> str:
        """
        Converte JSON tool calls em formato amigável para Gradio.

        Transforma:
        - {"tool": "bash_command", "args": {"command": "..."}} → ```bash\n...\n```
        - write_file("path", "content") → 📝 **Escrevendo:** `path`
        """
        import re

        # Pattern para tool calls JSON
        json_patterns = [
            # {"tool": "bash_command", "args": {"command": "..."}}
            (r'\{\s*"tool"\s*:\s*"(\w+)"\s*,\s*"args"\s*:\s*\{[^}]*"command"\s*:\s*"([^"]+)"[^}]*\}\s*\}',
             lambda m: f"```bash\n{m.group(2)}\n```"),
            # Nested: {"tool":{"tool":"bash_command"...}}
            (r'\{"tool"\s*:\s*\{[^}]*"command"\s*:\s*"([^"]+)"[^}]*\}\s*\}',
             lambda m: f"```bash\n{m.group(1)}\n```"),
        ]

        result = chunk
        for pattern, replacement in json_patterns:
            result = re.sub(pattern, replacement, result, flags=re.DOTALL)

        # Pattern para function calls Python-style
        func_patterns = [
            # write_file("path", "content")
            (r'write_file\s*\(\s*["\']([^"\']+)["\']',
             lambda m: f'📝 **Escrevendo arquivo:** `{m.group(1)}`'),
            # read_file("path")
            (r'read_file\s*\(\s*["\']([^"\']+)["\']',
             lambda m: f'📖 **Lendo arquivo:** `{m.group(1)}`'),
            # execute_python("path")
            (r'execute_python\s*\(\s*["\']([^"\']+)["\']',
             lambda m: f'🐍 **Executando:** `{m.group(1)}`'),
            # bash_command("cmd")
            (r'bash_command\s*\(\s*["\']([^"\']+)["\']',
             lambda m: f"```bash\n{m.group(1)}\n```"),
        ]

        for pattern, replacement in func_patterns:
            result = re.sub(pattern, replacement, result)

        return result

    def initialize(self) -> bool:
        """
        Initialize the bridge and GeminiClient.

        Creates a dedicated event loop for async→sync conversion.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        try:
            # Import GeminiClient
            from jdev_tui.core.llm_client import GeminiClient

            # Create dedicated event loop
            self._loop = asyncio.new_event_loop()

            # Initialize client
            self._client = GeminiClient(
                api_key=self._api_key,
                model=self._model,
            )

            # Initialize Prometheus if enabled
            if self._enable_prometheus:
                self._prometheus_client = PrometheusClient()
                # Pre-warm provider
                self._loop.run_until_complete(self._prometheus_client._ensure_provider())

            # Test initialization
            result = self._loop.run_until_complete(
                asyncio.wait_for(
                    self._client._ensure_initialized(),
                    timeout=10.0
                )
            )

            if result:
                self._initialized = True
                logger.info("GradioStreamingBridge initialized successfully")
                return True
            else:
                logger.error("GeminiClient initialization returned False")
                return False

        except ImportError as e:
            logger.error(f"Failed to import GeminiClient: {e}")
            return False
        except asyncio.TimeoutError:
            logger.error("GeminiClient initialization timed out")
            return False
        except Exception as e:
            logger.error(f"GradioStreamingBridge initialization failed: {e}")
            return False

    @property
    def available(self) -> bool:
        """Check if bridge is available for streaming."""
        return self._initialized and self._client is not None

    @property
    def backend_label(self) -> str:
        """Label for the active backend."""
        if self._initialized:
            base = f"gemini-{self._model or 'default'}"
            if self._enable_prometheus:
                return f"PROMETHEUS ({base})"
            return base
        return "not-initialized"

    def stream_chat(
        self,
        message: str,
        history: List[ChatMessage],
        session_id: Optional[str] = None,
    ) -> Generator[List[ChatMessage], None, None]:
        """
        Stream chat response for Gradio 6 ChatInterface.

        This is the main entry point. Converts async GeminiClient.stream()
        to a sync generator that Gradio 6 expects.

        Args:
            message: User's message
            history: Current chat history (will be modified)
            session_id: Optional session identifier

        Yields:
            Updated history list after each chunk
        """
        # Reset dedup filter for new message
        self._dedup_filter.reset()

        # Initialize metrics
        self._current_metrics = StreamingMetrics()

        # Ensure initialized
        if not self.available:
            if not self.initialize():
                history.append(ChatMessage(
                    role="assistant",
                    content="❌ Failed to initialize Gemini client. Check GEMINI_API_KEY.",
                    metadata={"title": "⚠️ Error"}
                ))
                yield history
                return

        # Add user message
        history.append(ChatMessage(role="user", content=message))
        yield history

        # Add thinking indicator
        thinking_msg = ChatMessage(
            role="assistant",
            content="⏳ Analyzing your request...",
            metadata={"title": "🧠 Thinking"}
        )
        history.append(thinking_msg)
        yield history

        # Stream from LLM
        response = ""
        cursor_index = 0

        try:
            # Get async generator
            if self._enable_prometheus and self._prometheus_client:
                async_gen = self._prometheus_client.stream(
                    prompt=message,
                    system_prompt=self._system_prompt,
                    context=self._conversation_context,
                )
            else:
                async_gen = self._client.stream(
                    prompt=message,
                    system_prompt=self._system_prompt,
                    context=self._conversation_context,
                )

            while True:
                try:
                    # Get next chunk with timeout
                    chunk = self._loop.run_until_complete(
                        asyncio.wait_for(
                            async_gen.__anext__(),
                            timeout=self._chunk_timeout
                        )
                    )

                    # Record first chunk time
                    if self._current_metrics.first_chunk_time is None:
                        self._current_metrics.first_chunk_time = time.time()

                    self._current_metrics.chunks_received += 1

                    # Check for tool call
                    tool_info = self._tool_detector.detect(chunk)
                    if tool_info:
                        name, args = tool_info
                        self._current_metrics.tool_calls += 1

                        # Add tool call message with metadata
                        tool_msg = ChatMessage(
                            role="assistant",
                            content=f"Executing {name}...",
                            metadata={
                                "title": f"🔧 Tool: {name}",
                                "value": json.dumps(args, indent=2)[:200]  # Truncate for display
                            }
                        )
                        history.append(tool_msg)
                        yield history
                        continue

                    # Filter duplicates
                    filtered_chunk = self._dedup_filter.filter_chunk(chunk)
                    if not filtered_chunk:
                        continue

                    # Sanitize tool call JSON to friendly format
                    filtered_chunk = self._sanitize_tool_calls(filtered_chunk)

                    response += filtered_chunk
                    self._current_metrics.total_chars += len(filtered_chunk)

                    # Update message with cursor
                    cursor = self.CURSOR_FRAMES[cursor_index % len(self.CURSOR_FRAMES)]
                    cursor_index += 1

                    history[-1] = ChatMessage(
                        role="assistant",
                        content=response + f" {cursor}"
                    )
                    yield history

                except StopAsyncIteration:
                    break

        except asyncio.TimeoutError:
            logger.warning(f"Stream timed out after {self._chunk_timeout}s")
            response += f"\n\n⚠️ Response timed out after {self._chunk_timeout}s"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            response += f"\n\n❌ Error: {str(e)}"

        finally:
            # Record end time
            self._current_metrics.end_time = time.time()
            self._current_metrics.deduplicated_lines = self._dedup_filter.deduplicated_count

        # Final update without cursor
        history[-1] = ChatMessage(role="assistant", content=response)
        yield history

        # Update conversation context
        self._conversation_context.append({"role": "user", "content": message})
        self._conversation_context.append({"role": "assistant", "content": response})

        # Keep context manageable (last 20 messages)
        if len(self._conversation_context) > 20:
            self._conversation_context = self._conversation_context[-20:]

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get metrics from the last streaming session."""
        if self._current_metrics:
            return self._current_metrics.to_dict()
        return None

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        status = {
            "bridge": "GradioStreamingBridge",
            "initialized": self._initialized,
            "available": self.available,
            "backend": self.backend_label,
        }

        if self._client:
            client_health = self._client.get_health_status()
            status["client"] = client_health

        if self._current_metrics:
            status["last_metrics"] = self._current_metrics.to_dict()

        if self._enable_prometheus and self._prometheus_client:
            status["prometheus"] = self._prometheus_client.get_health_status()

        return status

    def reset_conversation(self) -> None:
        """Clear conversation context for new session."""
        self._conversation_context.clear()
        self._dedup_filter.reset()
        logger.info("Conversation context reset")

    def set_system_prompt(self, prompt: str) -> None:
        """Update system prompt for future messages."""
        self._system_prompt = prompt

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._loop:
            try:
                self._loop.close()
            except Exception as e:
                logger.warning(f"Error closing event loop: {e}")
            self._loop = None

        self._client = None
        self._initialized = False
        logger.info("GradioStreamingBridge cleaned up")


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_streaming_bridge(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: str = "",
    enable_prometheus: bool = False,
) -> GradioStreamingBridge:
    """
    Factory function to create and initialize a streaming bridge.

    Args:
        api_key: Optional API key (uses env var if not provided)
        model: Optional model name (uses env var if not provided)
        system_prompt: System instructions
        enable_prometheus: Enable PROMETHEUS provider

    Returns:
        Initialized GradioStreamingBridge
    """
    bridge = GradioStreamingBridge(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        enable_prometheus=enable_prometheus,
    )
    bridge.initialize()
    return bridge


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ChatMessage",
    "StreamingMetrics",
    "ToolCallDetector",
    "DeduplicationFilter",
    "GradioStreamingBridge",
    "create_streaming_bridge",
]
