"""
Bridge Module - Facade Pattern Integration
==========================================

Main integration bridge between TUI and agent system.

Nov 2025 REFACTORING: Reduced from 5493 lines GOD CLASS to Facade pattern
that coordinates all extracted modules:

- governance.py: RiskLevel, GovernanceConfig, GovernanceObserver, ELP
- llm_client.py: GeminiClient, ToolCallParser
- agents_bridge.py: AgentInfo, AGENT_REGISTRY, AgentRouter, AgentManager
- tools_bridge.py: ToolBridge, MinimalRegistry
- ui_bridge.py: CommandPaletteBridge, MinimalCommandPalette, AutocompleteBridge
- history_manager.py: HistoryManager
- custom_commands.py: CustomCommandsManager
- hooks_manager.py: HooksManager
- plan_mode_manager.py: PlanModeManager

Usage in app.py:
    bridge = Bridge()
    async for chunk in bridge.chat(message):
        view.append_chunk(chunk)
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

# CHAOS ORCHESTRATOR - Thread-safe primitives
from jdev_tui.core.resilience import AsyncLock
from jdev_tui.core.prometheus_client import PrometheusClient
import re

# Padrões para detectar tasks complexas que devem usar PROMETHEUS
COMPLEX_TASK_PATTERNS = [
    r'\b(create|build|implement|design|architect)\b.*\b(system|pipeline|framework|application)\b',
    r'\b(analyze|debug|investigate|troubleshoot)\b.*\b(complex|multiple|entire)\b',
    r'\b(refactor|optimize|improve)\b.*\b(codebase|architecture|performance)\b',
    r'\b(multi.?step|step.?by.?step|sequentially|iteratively)\b',
    r'\b(remember|recall|previous|earlier|context)\b',  # Memory-dependent
    r'\b(simulate|predict|plan|strategy)\b',  # World model
    r'\b(evolve|learn|adapt|improve over time)\b',  # Evolution
]

SIMPLE_TASK_PATTERNS = [
    r'^(what|who|when|where|how|why)\s+\w+\??$',  # Simple questions
    r'^\w+\s*\?$',  # Single word question
    r'^(hi|hello|hey|thanks|ok|yes|no)\b',  # Greetings
]

# Load .env file if exists
try:
    from dotenv import load_dotenv
    load_dotenv()

    # Also try to load from script directory
    script_dir = Path(__file__).parent.parent.parent
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# =============================================================================
# IMPORTS FROM EXTRACTED MODULES
# =============================================================================

# Governance - Risk assessment and ELP
from .governance import (
    RiskLevel,
    GovernanceConfig,
    GovernanceObserver,
    ELP,
)

# LLM Client - Gemini streaming with function calling
from .llm_client import (
    GeminiClient,
    ToolCallParser,
)
from .parsing.stream_filter import StreamFilter

# Agents Bridge - Agent registry and routing
from .agents_bridge import (
    AgentInfo,
    AGENT_REGISTRY,
    AgentRouter,
    AgentManager,
)

# Tools Bridge - 47 tools integration
from .tools_bridge import (
    ToolBridge,
    MinimalRegistry,
)

# UI Bridge - Command palette and autocomplete
from .ui_bridge import (
    CommandPaletteBridge,
    MinimalCommandPalette,
    AutocompleteBridge,
)

# Output formatting - Centralized colors and icons
from .output_formatter import (
    tool_success_markup,
    tool_error_markup,
    agent_routing_markup,
)

# History Manager - Command and session history
from .history_manager import HistoryManager

# Extracted Managers (SCALE & SUSTAIN Phase 1.1)
from .managers import (
    TodoManager,
    StatusManager,
    PullRequestManager,
    MemoryManager,
    ContextManager,
    AuthenticationManager,
)

# Custom Commands - Slash command system (Claude Code parity)
try:
    from .custom_commands import CustomCommandsManager
except ImportError:
    CustomCommandsManager = None

# Hooks Manager - Pre/post hooks (Claude Code parity)
try:
    from .hooks_manager import HooksManager
except ImportError:
    HooksManager = None

# Plan Mode Manager - Plan mode state (Claude Code parity)
try:
    from .plan_mode_manager import PlanModeManager
except ImportError:
    PlanModeManager = None


# Parallel Executor - extracted module (Nov 2025)
from .parallel_executor import (
    ParallelExecutionResult,
    ParallelToolExecutor,
)


# =============================================================================
# BRIDGE FACADE - Main Integration Point
# =============================================================================

class Bridge:
    """
    Main integration bridge between TUI and agent system.

    Enhanced with:
    - 47 tools via ToolBridge
    - Command palette with fuzzy search
    - Autocomplete with fuzzy matching
    - History management with context

    Usage in app.py:
        bridge = Bridge()
        async for chunk in bridge.chat(message):
            view.append_chunk(chunk)
    """

    # Maximum iterations for agentic tool loop
    MAX_TOOL_ITERATIONS = 5

    # Parallel execution configuration
    MAX_PARALLEL_TOOLS = 5  # Max concurrent tool executions

    # Thread locks for thread-safe operations
    _router_lock = threading.Lock()
    _plan_mode_lock = threading.Lock()

    def __init__(self):
        """Initialize Bridge with all subsystems."""
        # =====================================================================
        # EXTRACTED MANAGERS (SCALE & SUSTAIN Phase 1.1)
        # =====================================================================
        # Initialize managers FIRST (they handle credentials, etc.)
        self._auth_manager = AuthenticationManager()
        self._auth_manager.load_credentials()  # Load before LLM init

        # Core systems
        self.llm = GeminiClient()
        self.governance = GovernanceObserver()
        self.agents = AgentManager(self.llm)
        self.tools = ToolBridge()
        self.palette = CommandPaletteBridge()
        self.autocomplete = AutocompleteBridge(self.tools)
        self.history = HistoryManager()

        # Extracted managers with dependency injection
        self._todo_manager = TodoManager()
        self._status_manager = StatusManager(
            llm_checker=lambda: self.llm.is_available,
            tool_counter=lambda: self.tools.get_tool_count(),
            agent_counter=lambda: len(self.agents.available_agents)
        )
        self._pr_manager = PullRequestManager()
        self._memory_manager = MemoryManager()
        self._context_manager = ContextManager(
            context_getter=lambda: self.history.context,
            context_setter=lambda ctx: setattr(self.history, 'context', ctx)
        )

        # State (with thread-safe primitives)
        self._tools_configured = False
        self._auto_route_enabled = True
        self._state_lock = AsyncLock("bridge_state")

        # Optional managers (graceful degradation)
        self._custom_commands_manager = CustomCommandsManager() if CustomCommandsManager else None
        self._hooks_manager = HooksManager() if HooksManager else None
        self._plan_mode_manager = PlanModeManager() if PlanModeManager else None

        # Provider selection: auto, prometheus, or gemini
        self._provider_mode = os.getenv("JDEV_PROVIDER", "auto")  # DEFAULT: auto
        self._prometheus_client: Optional[PrometheusClient] = None
        self._task_complexity_cache: Dict[str, str] = {}

    def _detect_task_complexity(self, message: str) -> str:
        """
        Auto-detect task complexity to choose provider.

        Returns: 'prometheus' for complex tasks, 'gemini' for simple ones.
        """
        message_lower = message.lower()

        # Check for simple patterns first
        for pattern in SIMPLE_TASK_PATTERNS:
            if re.search(pattern, message_lower):
                return "gemini"

        # Check for complex patterns
        complexity_score = 0
        for pattern in COMPLEX_TASK_PATTERNS:
            if re.search(pattern, message_lower):
                complexity_score += 1

        # Length heuristic: long prompts usually need more processing
        if len(message) > 500:
            complexity_score += 1
        if len(message) > 1000:
            complexity_score += 1

        # Code blocks indicate technical tasks
        if '```' in message or 'def ' in message or 'class ' in message:
            complexity_score += 1

        # Threshold: 2+ indicators = complex
        return "prometheus" if complexity_score >= 2 else "gemini"

    def _get_client(self, message: str = ""):
        """Get appropriate LLM client based on provider mode and task complexity."""
        if self._provider_mode == "prometheus":
            # Force PROMETHEUS
            if self._prometheus_client is None:
                self._prometheus_client = PrometheusClient()
            return self._prometheus_client, "prometheus"

        elif self._provider_mode == "gemini":
            # Force Gemini
            return self.llm, "gemini"

        else:  # auto mode (DEFAULT)
            detected = self._detect_task_complexity(message)
            if detected == "prometheus":
                if self._prometheus_client is None:
                    self._prometheus_client = PrometheusClient()
                return self._prometheus_client, "prometheus"
            else:
                return self.llm, "gemini"

    def _configure_llm_tools(self) -> None:
        """Configure LLM with tool schemas for function calling."""
        if self._tools_configured:
            return

        schemas = self.tools.get_schemas_for_llm()
        if schemas:
            self.llm.set_tools(schemas)
            self._tools_configured = True

    def _get_system_prompt(self) -> str:
        """
        Get system prompt optimized for agentic, symbiotic interaction.

        Uses Claude Code-style agentic prompt for natural language understanding
        and autonomous task execution.
        """
        # Try to use the new agentic prompt system
        try:
            from jdev_tui.core.agentic_prompt import (
                build_agentic_system_prompt,
                load_project_memory,
                get_dynamic_context
            )

            # Get tool schemas
            tool_schemas = self.tools.get_schemas_for_llm()

            # Get dynamic context
            context = get_dynamic_context()

            # Load project memory (JUANCS.md)
            project_memory = load_project_memory()

            # Load user memory
            user_memory = None
            memory_result = self.read_memory(scope="project")
            if memory_result.get("success"):
                user_memory = memory_result.get("content")

            # Build agentic prompt
            return build_agentic_system_prompt(
                tools=tool_schemas,
                context=context,
                project_memory=project_memory,
                user_memory=user_memory
            )

        except Exception:
            # Fallback to simple prompt if agentic fails
            pass

        # Fallback: Simple but effective prompt
        tool_names = self.tools.list_tools()[:25]
        tool_list = ", ".join(tool_names) if tool_names else "none loaded"

        return f"""You are juancs-code, an AI coding assistant with direct tool access.

CRITICAL RULES:
1. PREFER ACTIONS OVER EXPLANATIONS - When user asks to create/modify/delete files, USE TOOLS immediately
2. CODE FIRST - Show code, then 1-2 sentence explanation max
3. BE CONCISE - No verbose introductions or unnecessary elaboration
4. EXECUTE, DON'T DESCRIBE - "Create HTML file" = USE write_file tool, NOT print code

Available tools: {tool_list}

IMPORTANT: When user asks to create a file, call write_file(path, content).
When user asks to edit a file, call edit_file(path, ...).
When user asks to run a command, call bash_command(command).

Current working directory: {os.getcwd()}
"""

    # =========================================================================
    # CORE PROPERTIES
    # =========================================================================

    @property
    def is_connected(self) -> bool:
        """Check if LLM is available."""
        return self.llm.is_available

    @property
    def status_line(self) -> str:
        """Get status line for TUI."""
        llm_status = f"{ELP['approved']} Gemini" if self.is_connected else f"{ELP['error']} No LLM"
        gov_status = self.governance.get_status_emoji()
        agent_count = len(self.agents.available_agents)
        tool_count = self.tools.get_tool_count()

        return f"{llm_status} | {gov_status} | {ELP['agent']} {agent_count} agents | {ELP['tool']} {tool_count} tools"

    # =========================================================================
    # CHAT - Main Entry Point
    # =========================================================================

    async def chat(self, message: str, auto_route: bool = True) -> AsyncIterator[str]:
        """
        Handle chat message with streaming response and agentic tool execution.

        Enhanced with:
        - Conversation context
        - History tracking
        - Agentic tool loop (detects and executes tool calls)
        - **NEW**: Agent Router - auto-routes to specialized agents (Claude Code parity)

        Args:
            message: User message
            auto_route: If True, automatically route to agents based on intent
        """
        # Determine provider
        client, provider_name = self._get_client(message)

        # Log provider selection for debugging
        if self._provider_mode == "auto":
            # Yield provider indicator for UI
            yield f"[Using {provider_name.upper()}]\n"

        # Configure LLM with tools on first chat
        self._configure_llm_tools()

        # Add to history
        self.history.add_command(message)
        self.history.add_context("user", message)

        # Governance observation (never blocks)
        gov_report = self.governance.observe("chat", message)
        if self.governance.config.alerts and ("CRITICAL" in gov_report or "HIGH" in gov_report):
            yield f"{gov_report}\n\n"

        # =====================================================================
        # AGENT ROUTER - Automatic Intent Detection (Claude Code Parity)
        # =====================================================================
        if auto_route and self.is_auto_routing_enabled():
            routing = self.agents.router.route(message)
            if routing:
                agent_name, confidence = routing
                agent_info = AGENT_REGISTRY.get(agent_name)

                # Show routing decision (streaming-safe plain text)
                yield f"{agent_routing_markup(agent_name, confidence)}\n"
                if agent_info:
                    yield f"   *{agent_info.description}*\n\n"

                # Delegate to agent
                async for chunk in self.invoke_agent(agent_name, message):
                    yield chunk
                return

            # Check for ambiguous routing suggestion
            suggestion = self.agents.router.get_routing_suggestion(message)
            if suggestion:
                yield f"{suggestion}\n\n"

        # Get system prompt
        system_prompt = self._get_system_prompt()

        # Agentic loop - process tool calls iteratively
        current_message = message
        full_response_parts = []

        for iteration in range(self.MAX_TOOL_ITERATIONS):
            # Stream from LLM with context
            response_chunks = []
            stream_filter = StreamFilter()

            async for chunk in client.stream(
                current_message,
                system_prompt=system_prompt,
                context=self.history.get_context(),
                tools=self.tools.get_schemas_for_llm()
            ):
                response_chunks.append(chunk)

                # Filter chunk to prevent raw JSON leakage
                filtered_chunk = stream_filter.process_chunk(chunk)

                # Don't yield tool call markers directly - process them
                if filtered_chunk and not filtered_chunk.startswith("[TOOL_CALL:"):
                    yield filtered_chunk

            # Flush any remaining text in filter
            remaining = stream_filter.flush()
            if remaining and not remaining.startswith("[TOOL_CALL:"):
                yield remaining

            # Accumulate response
            accumulated = "".join(response_chunks)

            # Check for tool calls
            tool_calls = ToolCallParser.extract(accumulated)

            if not tool_calls:
                # No tool calls - we're done
                clean_response = ToolCallParser.remove(accumulated)
                full_response_parts.append(clean_response)
                break

            # Execute tool calls with PARALLEL EXECUTION (Claude Code Parity)
            # Detect dependencies and execute in waves
            tool_results = []
            exec_result = await self._execute_tools_parallel(tool_calls)

            # Yield results in order for consistent UI
            for call_id in sorted(exec_result.results.keys(), key=lambda x: int(x.split('_')[1])):
                result = exec_result.results[call_id]
                tool_name = result.get("tool_name", "unknown")

                if result.get("success"):
                    yield f"{tool_success_markup(tool_name)}\n"
                    tool_results.append(f"Tool {tool_name} succeeded: {result.get('data', 'OK')}")
                else:
                    error = result.get("error", "Unknown error")
                    yield f"{tool_error_markup(tool_name, error)}\n"
                    tool_results.append(f"Tool {tool_name} failed: {error}")

            # Show parallel execution stats if multiple tools
            if len(tool_calls) > 1 and exec_result.parallelism_factor > 1.0:
                yield f"\n⚡ *Parallel execution: {exec_result.wave_count} waves, {exec_result.parallelism_factor:.1f}x speedup ({exec_result.execution_time_ms:.0f}ms)*\n"

            # Prepare next iteration message with tool results
            clean_text = ToolCallParser.remove(accumulated)
            full_response_parts.append(clean_text)

            # Feed tool results back to LLM for continuation
            current_message = "Tool execution results:\n" + "\n".join(tool_results) + "\n\nContinue or summarize."

            yield "\n"  # Spacing between iterations

        # Add full response to context
        full_response = "\n".join(full_response_parts)
        self.history.add_context("assistant", full_response)

    async def invoke_agent(
        self,
        agent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke a specific agent with streaming response.

        Enhanced with history tracking.
        """
        # Add to history
        self.history.add_command(f"/{agent_name} {task}")

        # Governance observation (streaming-safe plain text)
        gov_report = self.governance.observe(f"agent:{agent_name}", task, agent_name)
        yield f"*{gov_report}*\n"
        yield f"🤖 Routing to **{agent_name.title()}Agent**...\n\n"

        # Invoke agent
        async for chunk in self.agents.invoke_agent(agent_name, task, context):
            yield chunk

    # =========================================================================
    # PLANNER v6.1 METHODS (Multi-Plan, Clarification, Exploration)
    # =========================================================================

    async def invoke_planner_multi(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke planner with Multi-Plan Generation (v6.1).

        Generates 3 alternative plans with risk/reward analysis.
        """
        self.history.add_command(f"/plan multi {task}")

        gov_report = self.governance.observe("agent:planner:multi", task, "planner")
        yield f"*{gov_report}*\n"
        yield "📋 **Multi-Plan Generation Mode** (v6.1)...\n\n"

        async for chunk in self.agents.invoke_planner_multi(task, context):
            yield chunk

    async def invoke_planner_clarify(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke planner with Clarification Mode (v6.1).

        Asks clarifying questions before planning.
        """
        self.history.add_command(f"/plan clarify {task}")

        gov_report = self.governance.observe("agent:planner:clarify", task, "planner")
        yield f"*{gov_report}*\n"
        yield "❓ **Clarification Mode** (v6.1)...\n\n"

        async for chunk in self.agents.invoke_planner_clarify(task, context):
            yield chunk

    async def invoke_planner_explore(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke planner in Exploration Mode (v6.1).

        Read-only analysis, no modifications.
        """
        self.history.add_command(f"/plan explore {task}")

        gov_report = self.governance.observe("agent:planner:explore", task, "planner")
        yield f"*{gov_report}*\n"
        yield "🔍 **Exploration Mode** (Read-Only v6.1)...\n\n"

        async for chunk in self.agents.invoke_planner_explore(task, context):
            yield chunk

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name."""
        # Governance observation
        gov_report = self.governance.observe(f"tool:{tool_name}", str(kwargs))

        # Execute tool
        result = await self.tools.execute_tool(tool_name, **kwargs)
        result["governance"] = gov_report

        return result

    # =========================================================================
    # PARALLEL TOOL EXECUTION (Claude Code Parity - Nov 2025)
    # =========================================================================

    async def _execute_tools_parallel(
        self,
        tool_calls: List[Tuple[str, Dict[str, Any]]]
    ) -> ParallelExecutionResult:
        """
        Execute tool calls with intelligent parallelization.

        Uses ParallelToolExecutor (extracted module) for wave-based execution.
        """
        executor = ParallelToolExecutor(
            self.tools.execute_tool,
            max_parallel=self.MAX_PARALLEL_TOOLS
        )
        return await executor.execute(tool_calls)

    # =========================================================================
    # AGENT COMMANDS
    # =========================================================================

    def get_agent_commands(self) -> Dict[str, str]:
        """Get mapping of slash commands to agents."""
        return {
            "/plan": "planner",
            "/execute": "executor",
            "/architect": "architect",
            "/review": "reviewer",
            "/explore": "explorer",
            "/refactor": "refactorer",
            "/test": "testing",
            "/security": "security",
            "/docs": "documentation",
            "/perf": "performance",
            "/devops": "devops",
            # Governance & Counsel
            "/justica": "justica",
            "/sofia": "sofia",
            # Data
            "/data": "data",
        }

    def get_command_help(self) -> str:
        """Get help text for agent commands."""
        lines = ["## Agent Commands\n"]
        for cmd, agent in self.get_agent_commands().items():
            info = AGENT_REGISTRY.get(agent)
            if info:
                lines.append(f"| `{cmd}` | {info.description} |")
        return "\n".join(lines)

    def get_tool_list(self) -> str:
        """Get formatted list of tools."""
        tools = self.tools.list_tools()
        if not tools:
            return "No tools loaded."

        # Group by category
        categories = {
            "File": ["read_file", "write_file", "edit_file", "list_directory", "delete_file",
                    "move_file", "copy_file", "create_directory", "read_multiple_files", "insert_lines"],
            "Terminal": ["cd", "ls", "pwd", "mkdir", "rm", "cp", "mv", "touch", "cat"],
            "Execution": ["bash_command"],
            "Search": ["search_files", "get_directory_tree"],
            "Git": ["git_status", "git_diff"],
            "Context": ["get_context", "save_session", "restore_backup"],
            "Web": ["web_search", "search_documentation", "fetch_url", "download_file",
                   "http_request", "package_search"],
        }

        lines = [f"## {ELP['tool']} Tools ({len(tools)} available)\n"]

        for category, expected_tools in categories.items():
            available = [t for t in expected_tools if t in tools]
            if available:
                lines.append(f"### {category}")
                lines.append(", ".join(f"`{t}`" for t in available))
                lines.append("")

        # Any uncategorized tools
        all_categorized = set()
        for cat_tools in categories.values():
            all_categorized.update(cat_tools)

        uncategorized = [t for t in tools if t not in all_categorized]
        if uncategorized:
            lines.append("### Other")
            lines.append(", ".join(f"`{t}`" for t in uncategorized))

        return "\n".join(lines)

    # =========================================================================
    # CLAUDE CODE PARITY - Context Management
    # =========================================================================

    # =========================================================================
    # CONTEXT MANAGEMENT (delegates to ContextManager)
    # =========================================================================

    def compact_context(self, focus: Optional[str] = None) -> Dict[str, Any]:
        """Compact conversation context, optionally focusing on specific topic."""
        return self._context_manager.compact_context(focus)

    def get_token_stats(self) -> Dict[str, Any]:
        """Get token usage statistics."""
        return self._context_manager.get_token_stats()

    # =========================================================================
    # TODO MANAGEMENT (delegates to TodoManager)
    # =========================================================================

    def get_todos(self) -> List[Dict[str, Any]]:
        """Get current todo list (thread-safe copy)."""
        return self._todo_manager.get_todos()

    def add_todo(self, text: str) -> None:
        """Add a todo item (thread-safe)."""
        self._todo_manager.add_todo(text)

    def update_todo(self, index: int, done: bool) -> bool:
        """Update todo status (thread-safe). Returns True if updated."""
        return self._todo_manager.update_todo(index, done)

    def clear_todos(self) -> None:
        """Clear all todos (thread-safe)."""
        self._todo_manager.clear_todos()

    def set_model(self, model_name: str) -> None:
        """Change the LLM model."""
        self.llm.model_name = model_name

    def get_current_model(self) -> str:
        """Get current model name."""
        return getattr(self.llm, 'model_name', 'gemini-2.0-flash')

    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ]

    def init_project(self) -> Dict[str, Any]:
        """Initialize project with JUANCS.md file."""
        import datetime

        juancs_content = f"""# JUANCS.md - Project Context

Generated: {datetime.datetime.now().isoformat()}

## Project Overview
This file helps JuanCS Dev-Code understand your project context.

## Key Files
<!-- Add important files here -->

## Architecture
<!-- Describe your architecture -->

## Conventions
<!-- Your coding conventions -->

## Notes
<!-- Additional context for the AI -->
"""
        juancs_path = Path.cwd() / "JUANCS.md"
        if not juancs_path.exists():
            juancs_path.write_text(juancs_content)
            return {"summary": "Created JUANCS.md - edit to add project context"}
        return {"summary": "JUANCS.md already exists"}

    # =========================================================================
    # SESSION MANAGEMENT (delegates to HistoryManager)
    # =========================================================================

    def resume_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Resume a previous session using HistoryManager."""
        return self.history.load_session(session_id)

    def save_session(self, session_id: Optional[str] = None) -> str:
        """Save current session using HistoryManager."""
        return self.history.save_session(session_id)

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List available sessions."""
        return self.history.list_sessions(limit)

    def create_checkpoint(self, label: str = None) -> Dict[str, Any]:
        """Create a checkpoint of current conversation state."""
        return self.history.create_checkpoint(label)

    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """Get available checkpoints for current session."""
        return self.history.get_checkpoints()

    def rewind_to(self, index: int) -> Dict[str, Any]:
        """Rewind conversation to a specific checkpoint."""
        return self.history.rewind_to_checkpoint(index)

    def export_conversation(self, filepath: str = "conversation.md") -> str:
        """Export conversation to file."""
        lines = ["# Conversation Export\n"]
        for msg in self.history.context:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"## {role.title()}\n{content}\n")
        Path(filepath).write_text("\n".join(lines))
        return filepath

    # =========================================================================
    # STATUS MANAGEMENT (delegates to StatusManager)
    # =========================================================================

    def check_health(self) -> Dict[str, Dict[str, Any]]:
        """Check system health."""
        return self._status_manager.check_health()

    def get_permissions(self) -> Dict[str, bool]:
        """Get current permissions."""
        return self._status_manager.get_permissions()

    def set_sandbox(self, enabled: bool) -> None:
        """Enable or disable sandbox mode."""
        self._status_manager.set_sandbox(enabled)

    # =========================================================================
    # HOOKS SYSTEM (delegates to HooksManager)
    # =========================================================================

    def get_hooks(self) -> Dict[str, Dict[str, Any]]:
        """Get configured hooks."""
        if self._hooks_manager:
            return self._hooks_manager.get_hooks()
        return {}

    def set_hook(self, hook_name: str, commands: List[str]) -> bool:
        """Set commands for a specific hook."""
        if self._hooks_manager:
            return self._hooks_manager.set_hook(hook_name, commands)
        return False

    def enable_hook(self, hook_name: str, enabled: bool = True) -> bool:
        """Enable or disable a hook."""
        if self._hooks_manager:
            return self._hooks_manager.enable_hook(hook_name, enabled)
        return False

    def add_hook_command(self, hook_name: str, command: str) -> bool:
        """Add a command to a hook."""
        if self._hooks_manager:
            return self._hooks_manager.add_hook_command(hook_name, command)
        return False

    def remove_hook_command(self, hook_name: str, command: str) -> bool:
        """Remove a command from a hook."""
        if self._hooks_manager:
            return self._hooks_manager.remove_hook_command(hook_name, command)
        return False

    async def execute_hook(self, hook_name: str, file_path: str) -> Dict[str, Any]:
        """Execute a hook for a specific file."""
        if self._hooks_manager:
            return await self._hooks_manager.execute_hook(hook_name, file_path)
        return {"success": False, "error": "Hooks system not available"}

    def get_hook_stats(self) -> Dict[str, Any]:
        """Get hook execution statistics."""
        if self._hooks_manager:
            return self._hooks_manager.get_stats()
        return {"total_executions": 0, "no_manager": True}

    def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP server status."""
        return {"servers": []}  # No MCP servers configured by default

    # =========================================================================
    # AGENT ROUTER CONTROL
    # =========================================================================

    def toggle_auto_routing(self) -> bool:
        """Toggle automatic agent routing on/off (thread-safe)."""
        with self._router_lock:
            self._auto_route_enabled = not self._auto_route_enabled
            return self._auto_route_enabled

    def is_auto_routing_enabled(self) -> bool:
        """Check if auto-routing is enabled (thread-safe read)."""
        with self._router_lock:
            return self._auto_route_enabled

    def get_router_status(self) -> Dict[str, Any]:
        """Get router status and statistics."""
        router = self.agents.router
        return {
            "enabled": self.is_auto_routing_enabled(),
            "min_confidence": router.MIN_CONFIDENCE,
            "agents_configured": len(router.INTENT_PATTERNS),
            "pattern_count": sum(len(p) for p in router.INTENT_PATTERNS.values()),
            "available_agents": list(router.INTENT_PATTERNS.keys())
        }

    def test_routing(self, message: str) -> Dict[str, Any]:
        """Test routing for a message without executing."""
        router = self.agents.router

        intents = router.detect_intent(message)
        routing = router.route(message)
        suggestion = router.get_routing_suggestion(message)

        return {
            "message": message,
            "should_route": router.should_route(message),
            "detected_intents": [
                {"agent": a, "confidence": f"{c*100:.0f}%"}
                for a, c in intents
            ],
            "selected_route": {
                "agent": routing[0] if routing else None,
                "confidence": f"{routing[1]*100:.0f}%" if routing else None
            } if routing else None,
            "suggestion": suggestion,
            "would_auto_route": routing is not None and self.is_auto_routing_enabled()
        }

    def manually_route(self, message: str, agent_name: str) -> AsyncIterator[str]:
        """Manually route a message to a specific agent."""
        if agent_name not in AGENT_REGISTRY:
            raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENT_REGISTRY.keys())}")

        return self.invoke_agent(agent_name, message)

    # =========================================================================
    # CUSTOM COMMANDS (delegates to CustomCommandsManager)
    # =========================================================================

    def load_custom_commands(self) -> Dict[str, Dict[str, Any]]:
        """Load custom commands from .juancs/commands/ directory."""
        if self._custom_commands_manager:
            return self._custom_commands_manager.load_commands()
        return {}

    def get_custom_commands(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded custom commands."""
        if self._custom_commands_manager:
            return self._custom_commands_manager.get_commands()
        return {}

    def get_custom_command(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific custom command by name."""
        if self._custom_commands_manager:
            return self._custom_commands_manager.get_command(name)
        return None

    def execute_custom_command(self, name: str, args: str = "") -> Optional[str]:
        """Execute a custom command and return its expanded prompt."""
        if self._custom_commands_manager:
            return self._custom_commands_manager.execute_command(name, args)
        return None

    def create_custom_command(
        self,
        name: str,
        prompt: str,
        description: str = "",
        scope: str = "project"
    ) -> Dict[str, Any]:
        """Create a new custom command."""
        if self._custom_commands_manager:
            return self._custom_commands_manager.create_command(name, prompt, description, scope)
        return {"success": False, "error": "Custom commands system not available"}

    def delete_custom_command(self, name: str) -> bool:
        """Delete a custom command."""
        if self._custom_commands_manager:
            return self._custom_commands_manager.delete_command(name)
        return False

    def refresh_custom_commands(self) -> Dict[str, Dict[str, Any]]:
        """Force reload of custom commands."""
        if self._custom_commands_manager:
            return self._custom_commands_manager.refresh()
        return {}

    # =========================================================================
    # PLAN MODE (delegates to PlanModeManager)
    # =========================================================================

    def enter_plan_mode(self, task: str = None) -> Dict[str, Any]:
        """Enter plan mode for careful task planning."""
        if self._plan_mode_manager:
            return self._plan_mode_manager.enter_plan_mode(task)
        return {"success": False, "error": "Plan mode system not available"}

    def exit_plan_mode(self, approved: bool = False) -> Dict[str, Any]:
        """Exit plan mode."""
        if self._plan_mode_manager:
            return self._plan_mode_manager.exit_plan_mode(approved)
        return {"success": False, "error": "Plan mode system not available"}

    def is_plan_mode(self) -> bool:
        """Check if currently in plan mode."""
        if self._plan_mode_manager:
            return self._plan_mode_manager.is_plan_mode()
        return False

    def get_plan_mode_state(self) -> Dict[str, Any]:
        """Get current plan mode state."""
        if self._plan_mode_manager:
            return self._plan_mode_manager.get_plan_mode_state()
        return {"active": False}

    def add_plan_note(self, note: str, category: str = "exploration") -> bool:
        """Add a note to the current plan."""
        if self._plan_mode_manager:
            return self._plan_mode_manager.add_plan_note(note, category)
        return False

    def check_plan_mode_restriction(self, operation: str) -> Tuple[bool, Optional[str]]:
        """Check if an operation is allowed in plan mode."""
        if self._plan_mode_manager:
            return self._plan_mode_manager.check_plan_mode_restriction(operation)
        return True, None

    # =========================================================================
    # PR CREATION (delegates to PullRequestManager)
    # =========================================================================

    async def create_pull_request(
        self,
        title: str,
        body: str = None,
        base: str = "main",
        draft: bool = False
    ) -> Dict[str, Any]:
        """Create a GitHub pull request using gh CLI."""
        return await self._pr_manager.create_pull_request(title, body, base, draft)

    def get_pr_template(self) -> str:
        """Get PR template if exists."""
        return self._pr_manager.get_pr_template()

    # =========================================================================
    # API KEY MANAGEMENT (delegates to AuthenticationManager)
    # =========================================================================

    def login(self, provider: str = "gemini", api_key: str = None, scope: str = "global") -> Dict[str, Any]:
        """Login/configure API key for a provider."""
        return self._auth_manager.login(provider, api_key, scope)

    def logout(self, provider: str = None, scope: str = "all") -> Dict[str, Any]:
        """Logout/remove API key for a provider."""
        return self._auth_manager.logout(provider, scope)

    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status for all providers."""
        return self._auth_manager.get_auth_status()

    # =========================================================================
    # MEMORY PERSISTENCE (delegates to MemoryManager)
    # =========================================================================

    def read_memory(self, scope: str = "project") -> Dict[str, Any]:
        """Read memory/context from MEMORY.md file."""
        return self._memory_manager.read_memory(scope)

    def write_memory(self, content: str, scope: str = "project", append: bool = False) -> Dict[str, Any]:
        """Write to MEMORY.md file."""
        return self._memory_manager.write_memory(content, scope, append)

    def remember(self, note: str, scope: str = "project") -> Dict[str, Any]:
        """Add a note to memory (convenience method)."""
        return self._memory_manager.remember(note, scope)


# =============================================================================
# SINGLETON PATTERN - For backwards compatibility
# =============================================================================

_bridge_instance: Optional[Bridge] = None
_bridge_lock = threading.Lock()


def get_bridge() -> Bridge:
    """Get or create bridge singleton (thread-safe)."""
    global _bridge_instance
    if _bridge_instance is None:
        with _bridge_lock:
            # Double-check locking pattern
            if _bridge_instance is None:
                _bridge_instance = Bridge()
    return _bridge_instance


# =============================================================================
# EXPORTS - Re-export all extracted module classes for backward compatibility
# =============================================================================

__all__ = [
    # Main facade
    'Bridge',

    # Governance
    'RiskLevel',
    'GovernanceConfig',
    'GovernanceObserver',
    'ELP',

    # LLM
    'GeminiClient',
    'ToolCallParser',

    # Agents
    'AgentInfo',
    'AGENT_REGISTRY',
    'AgentRouter',
    'AgentManager',

    # Tools
    'ToolBridge',
    'MinimalRegistry',

    # UI
    'CommandPaletteBridge',
    'MinimalCommandPalette',
    'AutocompleteBridge',

    # History
    'HistoryManager',

    # Singleton
    'get_bridge',
]
