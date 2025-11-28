"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║                        OBSERVABILITY - OpenTelemetry                             ║
║                                                                                  ║
║  OpenTelemetry instrumentation for multi-agent orchestration                    ║
║                                                                                  ║
║  Based on Nov 2025 best practices:                                              ║
║  - Anthropic: "capturing OpenTelemetry traces for prompts, tool invocations"   ║
║  - Google: "agent-level tracing, tool auditing, orchestrator visualization"    ║
║                                                                                  ║
║  Features:                                                                       ║
║  - Distributed tracing with correlation IDs                                     ║
║  - Agent-level spans                                                             ║
║  - Tool invocation tracking                                                      ║
║  - Token usage metrics                                                           ║
║  - Latency monitoring                                                            ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    # Fallback: no-op implementations
    class DummySpan:
        def set_attribute(self, *args, **kwargs): pass
        def set_status(self, *args, **kwargs): pass
        def record_exception(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass

    class DummyTracer:
        def start_as_current_span(self, name, *args, **kwargs):
            return DummySpan()

logger = logging.getLogger(__name__)

# Global tracer instance
_tracer: Optional[Any] = None


def setup_observability(
    service_name: str = "maestro-orchestrator",
    enable_console: bool = True,
    enable_file: bool = True
) -> None:
    """
    Setup OpenTelemetry observability for multi-agent system.

    Based on:
    - Anthropic: Traces for prompts, tool invocations, orchestration
    - Google: Agent-level tracing, tool auditing, orchestrator viz

    Args:
        service_name: Name of the service (appears in traces)
        enable_console: Export traces to console (for development)
        enable_file: Export traces to file (for production)

    Example:
        >>> setup_observability("maestro")
        >>> with get_tracer().start_as_current_span("my_operation") as span:
        ...     span.set_attribute("agent_id", "executor")
        ...     # do work
    """
    global _tracer

    if not OTEL_AVAILABLE:
        logger.warning(
            "⚠️  OpenTelemetry not installed. Install with: pip install opentelemetry-sdk"
        )
        logger.warning("   Observability disabled - using no-op tracer")
        _tracer = DummyTracer()
        return

    try:
        # Create resource with service metadata
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": "development"
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Add console exporter (for development)
        if enable_console:
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))

        # TODO: Add file exporter if needed
        # if enable_file:
        #     file_exporter = FileSpanExporter("traces.jsonl")
        #     provider.add_span_processor(BatchSpanProcessor(file_exporter))

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer instance
        _tracer = trace.get_tracer(__name__)

        logger.info(f"✓ Observability initialized: {service_name}")
        logger.info(f"  - Console export: {enable_console}")
        logger.info("  - OpenTelemetry enabled")

    except Exception as e:
        logger.error(f"❌ Failed to setup observability: {e}")
        logger.warning("   Falling back to no-op tracer")
        _tracer = DummyTracer()


def get_tracer():
    """
    Get the global tracer instance.

    Returns:
        Tracer: OpenTelemetry tracer or no-op dummy

    Example:
        >>> tracer = get_tracer()
        >>> with tracer.start_as_current_span("my_span"):
        ...     # instrumented code
    """
    global _tracer

    if _tracer is None:
        # Auto-initialize with defaults
        setup_observability()

    return _tracer


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Context manager for tracing an operation.

    Args:
        operation_name: Name of the operation (e.g., "governance.evaluate")
        attributes: Optional attributes to attach to span

    Yields:
        Span: The span object for additional instrumentation

    Example:
        >>> with trace_operation("agent.execute", {"agent_id": "executor"}):
        ...     # do work
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(operation_name) as span:
        # Add attributes if provided
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        try:
            yield span
            if OTEL_AVAILABLE:
                span.set_status(Status(StatusCode.OK))
        except Exception as e:
            if OTEL_AVAILABLE:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
            raise


def trace_agent_execution(agent_id: str, task_id: str):
    """
    Decorator for tracing agent execution.

    Args:
        agent_id: ID of the agent executing
        task_id: ID of the task being executed

    Example:
        >>> @trace_agent_execution("executor", "task-123")
        >>> async def execute_task():
        ...     # agent work
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with trace_operation(
                f"agent.{agent_id}.execute",
                {"agent_id": agent_id, "task_id": task_id}
            ):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


class ObservabilityContext:
    """
    Context object for tracking observability metadata.

    Stores correlation IDs, parent spans, etc. for distributed tracing.
    """

    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.metadata: Dict[str, Any] = {}

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to context."""
        self.metadata[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "correlation_id": self.correlation_id,
            **self.metadata
        }


# Convenience function for getting status codes
def get_status_code(success: bool):
    """Get OpenTelemetry status code from success boolean."""
    if not OTEL_AVAILABLE:
        return None
    return StatusCode.OK if success else StatusCode.ERROR
