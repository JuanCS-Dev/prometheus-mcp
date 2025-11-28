"""
Integration Coordinator - The Central Nervous System.

Boris Cherny: "Complexity is the enemy. Clarity is king."

This coordinator is the SINGLE point of integration between:
- Shell (user input)
- Agents (specialized processors)  
- Tools (function execution)
- Intelligence (context + intent)
- TUI (visual feedback)

Design Philosophy:
- Zero circular dependencies
- Clear data flow
- Type-safe all the way
- Event-driven for TUI updates
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .integration_types import (
    AgentInvoker,
    Event,
    EventBus,
    EventHandler,
    EventType,
    Intent,
    IntentType,
    ToolDefinition,
    ToolExecutionResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# SIMPLE EVENT BUS IMPLEMENTATION
# ============================================================================

class SimpleEventBus:
    """Lightweight pub/sub event bus.
    
    Boris Cherny: "Don't over-engineer. This is 50 lines and covers 99% of cases."
    """

    def __init__(self) -> None:
        """Initialize empty event bus."""
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._event_count = 0

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe handler to event type."""
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type}: {handler.__name__}")

    def publish(self, event: Event) -> None:
        """Publish event to all subscribers (synchronous)."""
        self._event_count += 1
        handlers = self._handlers.get(event.type, [])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {e}", exc_info=True)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe handler from event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]


# ============================================================================
# INTEGRATION COORDINATOR
# ============================================================================

class Coordinator:
    """Central coordinator for all integrations.
    
    Responsibilities:
    - Intent detection + routing
    - Context building + caching
    - Agent invocation
    - Tool registration + execution
    - Event publishing for TUI
    
    NOT responsible for:
    - Shell/REPL logic (stays in repl_masterpiece.py)
    - Individual agent logic (stays in agents/*.py)
    - Tool implementation (stays in tools/*.py)
    """

    def __init__(
        self,
        *,
        cwd: Optional[str] = None,
        event_bus: Optional[EventBus] = None
    ) -> None:
        """Initialize coordinator.
        
        Args:
            cwd: Working directory (default: current)
            event_bus: Event bus for pub/sub (default: create new)
        """
        self.cwd = Path(cwd or Path.cwd()).resolve()
        self.event_bus: EventBus = event_bus or SimpleEventBus()

        # State (using Any for context to avoid circular deps with existing code)
        self._context_cache: Optional[Any] = None
        self._context_cache_time: float = 0.0
        self._context_ttl_seconds = 60.0  # Refresh after 60s

        # Registries
        self._agents: Dict[IntentType, AgentInvoker] = {}
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_executors: Dict[str, Any] = {}  # name → executor callable

        # Intent mapping (keywords → intent type)
        self._intent_keywords: Dict[IntentType, List[str]] = {
            IntentType.ARCHITECTURE: [
                "design", "architecture", "structure", "pattern", "feasibility"
            ],
            IntentType.EXPLORATION: [
                "explore", "navigate", "find", "search", "where", "locate"
            ],
            IntentType.PLANNING: [
                "plan", "strategy", "roadmap", "approach", "steps"
            ],
            IntentType.REFACTORING: [
                "refactor", "improve", "clean", "optimize", "simplify"
            ],
            IntentType.REVIEW: [
                "review", "analyze", "audit", "check", "assess"
            ],
            IntentType.SECURITY: [
                "security", "vulnerability", "vulnerabilities", "exploit", "secure", "unsafe"
            ],
            IntentType.PERFORMANCE: [
                "performance", "speed", "optimize", "benchmark", "profile"
            ],
            IntentType.TESTING: [
                "test", "coverage", "unit", "integration", "e2e"
            ],
            IntentType.DOCUMENTATION: [
                "document", "readme", "docs", "explain", "guide"
            ],
        }

        logger.info(f"Coordinator initialized (cwd: {self.cwd})")

    # ========================================================================
    # AGENT REGISTRY
    # ========================================================================

    def register_agent(
        self,
        intent_type: IntentType,
        agent: AgentInvoker
    ) -> None:
        """Register agent for specific intent type.
        
        Args:
            intent_type: What intent this agent handles
            agent: Agent instance (must implement AgentInvoker protocol)
        """
        self._agents[intent_type] = agent
        logger.debug(f"Registered agent for {intent_type}")

    # ========================================================================
    # TOOL REGISTRY
    # ========================================================================

    def register_tool(
        self,
        definition: ToolDefinition,
        executor: Any  # Callable that executes the tool
    ) -> None:
        """Register tool for function calling.
        
        Args:
            definition: Tool definition with schema
            executor: Callable that executes the tool
        """
        self._tools[definition.name] = definition
        self._tool_executors[definition.name] = executor
        logger.debug(f"Registered tool: {definition.name}")

    def get_tools(self) -> List[ToolDefinition]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_tools_for_gemini(self) -> List[Dict[str, Any]]:
        """Get tools in Gemini function calling format."""
        return [tool.to_gemini_schema() for tool in self._tools.values()]

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> ToolExecutionResult:
        """Execute a tool by name.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            
        Returns:
            ToolExecutionResult with output
            
        Raises:
            ValueError: If tool not found
        """
        if tool_name not in self._tool_executors:
            raise ValueError(f"Tool not found: {tool_name}")

        definition = self._tools[tool_name]
        executor = self._tool_executors[tool_name]

        # Publish start event
        self.event_bus.publish(Event(
            type=EventType.TOOL_STARTED,
            data={"tool": tool_name, "parameters": parameters}
        ))

        start_time = time.perf_counter()

        try:
            # Execute (handle both sync and async executors)
            if asyncio.iscoroutinefunction(executor):
                output = await executor(**parameters)
            else:
                output = executor(**parameters)

            execution_time = (time.perf_counter() - start_time) * 1000

            result = ToolExecutionResult(
                success=True,
                output=str(output),
                execution_time_ms=execution_time
            )

            # Publish success event
            self.event_bus.publish(Event(
                type=EventType.TOOL_COMPLETED,
                data={
                    "tool": tool_name,
                    "success": True,
                    "execution_time_ms": execution_time
                }
            ))

            return result

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000

            logger.error(f"Tool execution failed: {e}", exc_info=True)

            result = ToolExecutionResult(
                success=False,
                output="",
                error=str(e),
                execution_time_ms=execution_time
            )

            # Publish failure event
            self.event_bus.publish(Event(
                type=EventType.TOOL_FAILED,
                data={
                    "tool": tool_name,
                    "error": str(e),
                    "execution_time_ms": execution_time
                }
            ))

            return result

    # ========================================================================
    # CONTEXT MANAGEMENT
    # ========================================================================

    def get_context(self) -> Any:
        """Get current rich context (cached).
        
        Returns cached context if fresh enough, otherwise rebuilds.
        Returns: RichContext from intelligence.context_enhanced
        """
        now = time.time()

        if (
            self._context_cache is not None
            and (now - self._context_cache_time) < self._context_ttl_seconds
        ):
            return self._context_cache

        # Cache miss - rebuild
        return self.refresh_context()

    def refresh_context(self) -> Any:
        """Force rebuild of context (after cd, git ops, etc).
        
        Returns: RichContext from intelligence.context_enhanced
        """
        from ..intelligence.context_enhanced import build_rich_context

        logger.debug("Refreshing context...")

        # Build rich context using existing infrastructure
        context = build_rich_context(working_dir=str(self.cwd))

        # Cache
        self._context_cache = context
        self._context_cache_time = time.time()

        # Publish event
        self.event_bus.publish(Event(
            type=EventType.CONTEXT_UPDATED,
            data={"context": context}
        ))

        return context

    # ========================================================================
    # INTENT DETECTION
    # ========================================================================

    def detect_intent(self, message: str) -> Intent:
        """Detect user intent from message.
        
        Simple keyword-based detection (can be enhanced later with ML).
        
        Boris Cherny: "Simple and correct > complex and buggy"
        
        Args:
            message: User's message
            
        Returns:
            Intent with confidence score
        """
        message_lower = message.lower()

        # Score each intent type
        scores: Dict[IntentType, float] = {}

        for intent_type, keywords in self._intent_keywords.items():
            matches = sum(1 for kw in keywords if kw in message_lower)
            if matches > 0:
                # Confidence = min(matches / 2, 1.0)
                # 1 keyword = 0.5, 2 keywords = 1.0
                # This gives better confidence scores
                scores[intent_type] = min(matches / 2.0, 1.0)

        if not scores:
            # No specific intent detected
            return Intent(
                type=IntentType.GENERAL,
                confidence=1.0,
                keywords=[]
            )

        # Get highest scoring intent
        best_intent = max(scores.items(), key=lambda x: x[1])
        intent_type, confidence = best_intent

        # Find matched keywords
        matched_keywords = [
            kw for kw in self._intent_keywords[intent_type]
            if kw in message_lower
        ]

        return Intent(
            type=intent_type,
            confidence=confidence,
            keywords=matched_keywords
        )

    # ========================================================================
    # MESSAGE PROCESSING (MAIN ENTRY POINT)
    # ========================================================================

    async def process_message(
        self,
        message: str,
        context: Optional[RichContext] = None
    ) -> str:
        """Process user message through full integration pipeline.
        
        Flow:
        1. Get/refresh context
        2. Detect intent
        3. Route to appropriate agent OR handle directly
        4. Publish events for TUI
        5. Return formatted response
        
        Args:
            message: User's message
            context: Optional pre-built context (otherwise will build)
            
        Returns:
            Formatted response string
        """
        # Step 1: Context
        ctx = context or self.get_context()

        # Step 2: Intent detection
        intent = self.detect_intent(message)

        logger.info(f"Detected intent: {intent.type} (confidence: {intent.confidence:.2f})")

        # Step 3: Routing
        if intent.type in self._agents and intent.confidence >= 0.3:
            # Route to agent
            agent = self._agents[intent.type]

            # Publish agent invocation event
            self.event_bus.publish(Event(
                type=EventType.AGENT_INVOKED,
                data={
                    "intent": intent.type.value,
                    "agent": agent.__class__.__name__
                }
            ))

            try:
                response = await agent.invoke(
                    request=message,
                    context=ctx.__dict__  # Convert to dict for compatibility
                )

                # Publish completion event
                self.event_bus.publish(Event(
                    type=EventType.AGENT_COMPLETED,
                    data={
                        "intent": intent.type.value,
                        "success": response["success"]
                    }
                ))

                return response["output"]

            except Exception as e:
                logger.error(f"Agent invocation failed: {e}", exc_info=True)

                # Publish failure event
                self.event_bus.publish(Event(
                    type=EventType.AGENT_FAILED,
                    data={
                        "intent": intent.type.value,
                        "error": str(e)
                    }
                ))

                return f"❌ Agent execution failed: {e}"

        # No agent route - return message for normal LLM processing
        # (Shell will handle LLM call with tools)
        return ""  # Empty string signals "no agent handled this"
