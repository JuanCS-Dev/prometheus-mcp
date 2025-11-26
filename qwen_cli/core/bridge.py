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

import json
import os
import threading
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

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

# History Manager - Command and session history
from .history_manager import HistoryManager

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

    # Thread locks for thread-safe operations
    _router_lock = threading.Lock()
    _plan_mode_lock = threading.Lock()

    def __init__(self):
        """Initialize Bridge with all subsystems."""
        # Load credentials BEFORE creating LLM
        self._load_credentials()

        # Core systems
        self.llm = GeminiClient()
        self.governance = GovernanceObserver()
        self.agents = AgentManager(self.llm)
        self.tools = ToolBridge()
        self.palette = CommandPaletteBridge()
        self.autocomplete = AutocompleteBridge(self.tools)
        self.history = HistoryManager()

        # State
        self._session_tokens = 0
        self._tools_configured = False
        self._auto_route_enabled = True
        self._sandbox = False
        self._todos: List[Dict[str, Any]] = []

        # Optional managers (graceful degradation)
        self._custom_commands_manager = CustomCommandsManager() if CustomCommandsManager else None
        self._hooks_manager = HooksManager() if HooksManager else None
        self._plan_mode_manager = PlanModeManager() if PlanModeManager else None

    def _load_credentials(self) -> None:
        """Load API credentials from config file."""
        creds_file = self._get_credentials_file()
        if creds_file.exists():
            try:
                creds = json.loads(creds_file.read_text())
                for key, value in creds.items():
                    if key not in os.environ:
                        os.environ[key] = value
            except Exception:
                pass

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
            from qwen_cli.core.agentic_prompt import (
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

                # Show routing decision
                yield f"🎯 **Auto-routing to {agent_name.title()}Agent** (confidence: {int(confidence*100)}%)\n"
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
            async for chunk in self.llm.stream(
                current_message,
                system_prompt=system_prompt,
                context=self.history.get_context()
            ):
                response_chunks.append(chunk)
                # Don't yield tool call markers directly - process them
                if not chunk.startswith("[TOOL_CALL:"):
                    yield chunk

            # Accumulate response
            accumulated = "".join(response_chunks)

            # Check for tool calls
            tool_calls = ToolCallParser.extract(accumulated)

            if not tool_calls:
                # No tool calls - we're done
                clean_response = ToolCallParser.remove(accumulated)
                full_response_parts.append(clean_response)
                break

            # Execute tool calls
            tool_results = []
            for tool_name, args in tool_calls:
                # Yield execution indicator
                yield f"\n[dim]● Executing: {tool_name}[/dim]\n"

                # Execute tool
                result = await self.tools.execute_tool(tool_name, **args)

                if result.get("success"):
                    yield f"[green]✓ {tool_name}: Success[/green]\n"
                    tool_results.append(f"Tool {tool_name} succeeded: {result.get('data', 'OK')}")
                else:
                    error = result.get("error", "Unknown error")
                    yield f"[red]✗ {tool_name}: {error}[/red]\n"
                    tool_results.append(f"Tool {tool_name} failed: {error}")

            # Prepare next iteration message with tool results
            clean_text = ToolCallParser.remove(accumulated)
            full_response_parts.append(clean_text)

            # Feed tool results back to LLM for continuation
            current_message = f"Tool execution results:\n" + "\n".join(tool_results) + "\n\nContinue or summarize."

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

        # Governance observation
        gov_report = self.governance.observe(f"agent:{agent_name}", task, agent_name)
        yield f"{gov_report}\n"
        yield f"{ELP['agent']} Routing to {agent_name.title()}Agent...\n\n"

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
        yield f"{gov_report}\n"
        yield f"{ELP['agent']} Multi-Plan Generation Mode (v6.1)...\n\n"

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
        yield f"{gov_report}\n"
        yield f"{ELP['agent']} Clarification Mode (v6.1)...\n\n"

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
        yield f"{gov_report}\n"
        yield f"{ELP['agent']} Exploration Mode (Read-Only v6.1)...\n\n"

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

    def compact_context(self, focus: Optional[str] = None) -> Dict[str, Any]:
        """Compact conversation context, optionally focusing on specific topic."""
        before = len(self.history.context)
        # Keep only last N messages, summarize if needed
        if len(self.history.context) > 10:
            # Keep first 2 (system context) and last 8
            self.history.context = self.history.context[:2] + self.history.context[-8:]
        after = len(self.history.context)
        tokens_saved = (before - after) * 500  # Rough estimate
        return {
            "before": before,
            "after": after,
            "tokens_saved": tokens_saved,
            "focus": focus
        }

    def get_token_stats(self) -> Dict[str, Any]:
        """Get token usage statistics."""
        return {
            "session_tokens": self._session_tokens,
            "total_tokens": self._session_tokens,
            "input_tokens": int(self._session_tokens * 0.6),
            "output_tokens": int(self._session_tokens * 0.4),
            "context_tokens": len(str(self.history.context)) // 4,
            "max_tokens": 128000,
            "cost": self._session_tokens * 0.000001  # Rough Gemini pricing
        }

    def get_todos(self) -> List[Dict[str, Any]]:
        """Get current todo list."""
        return self._todos

    def add_todo(self, text: str) -> None:
        """Add a todo item."""
        self._todos.append({"text": text, "done": False})

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

    def check_health(self) -> Dict[str, Dict[str, Any]]:
        """Check system health."""
        health = {}
        # Check LLM
        health["LLM"] = {
            "ok": self.is_connected,
            "message": "Connected" if self.is_connected else "Not connected"
        }
        # Check tools
        tool_count = self.tools.get_tool_count()
        health["Tools"] = {
            "ok": tool_count > 0,
            "message": f"{tool_count} tools loaded"
        }
        # Check agents
        agent_count = len(self.agents.available_agents)
        health["Agents"] = {
            "ok": agent_count > 0,
            "message": f"{agent_count} agents available"
        }
        return health

    def get_permissions(self) -> Dict[str, bool]:
        """Get current permissions."""
        return {
            "read_files": True,
            "write_files": True,
            "execute_commands": True,
            "network_access": True,
            "sandbox_mode": self._sandbox
        }

    def set_sandbox(self, enabled: bool) -> None:
        """Enable or disable sandbox mode."""
        self._sandbox = enabled

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
    # PR CREATION (Claude Code Parity)
    # =========================================================================

    async def create_pull_request(
        self,
        title: str,
        body: str = None,
        base: str = "main",
        draft: bool = False
    ) -> Dict[str, Any]:
        """Create a GitHub pull request using gh CLI."""
        import subprocess
        import shutil

        # Check if gh is available
        if not shutil.which("gh"):
            return {
                "success": False,
                "error": "GitHub CLI (gh) not installed. Install with: brew install gh"
            }

        # Check if authenticated
        try:
            auth_check = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if auth_check.returncode != 0:
                return {
                    "success": False,
                    "error": "Not authenticated with GitHub. Run: gh auth login"
                }
        except Exception as e:
            return {"success": False, "error": f"Auth check failed: {e}"}

        # Get current branch
        try:
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            current_branch = branch_result.stdout.strip()
        except Exception:
            current_branch = "unknown"

        # Build PR body if not provided
        if not body:
            body = f"""## Summary
{title}

## Changes
- See commit history for details

## Test Plan
- [ ] Tests pass
- [ ] Manual testing done

---
🤖 Generated with [JuanCS Dev-Code](https://github.com/juancs/dev-code)
"""

        # Create PR command
        cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]

        if draft:
            cmd.append("--draft")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                pr_url = result.stdout.strip()
                return {
                    "success": True,
                    "url": pr_url,
                    "branch": current_branch,
                    "base": base,
                    "draft": draft,
                    "message": f"PR created: {pr_url}"
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() or "PR creation failed",
                    "stdout": result.stdout
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "PR creation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_pr_template(self) -> str:
        """Get PR template if exists."""
        templates = [
            Path.cwd() / ".github" / "pull_request_template.md",
            Path.cwd() / ".github" / "PULL_REQUEST_TEMPLATE.md",
            Path.cwd() / "pull_request_template.md",
        ]

        for template in templates:
            if template.exists():
                try:
                    return template.read_text()
                except Exception:
                    continue

        return ""

    # =========================================================================
    # API KEY MANAGEMENT - /login, /logout (Claude Code Parity)
    # =========================================================================

    def _get_credentials_file(self) -> Path:
        """Get credentials file path."""
        config_dir = Path.home() / ".config" / "juancs"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "credentials.json"

    def _get_env_file(self) -> Path:
        """Get .env file path in current project."""
        return Path.cwd() / ".env"

    def login(self, provider: str = "gemini", api_key: str = None, scope: str = "global") -> Dict[str, Any]:
        """Login/configure API key for a provider."""
        import re

        valid_providers = {
            "gemini": "GEMINI_API_KEY",
            "google": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "nebius": "NEBIUS_API_KEY",
            "groq": "GROQ_API_KEY",
        }

        provider_lower = provider.lower()
        if provider_lower not in valid_providers:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}. Valid: {', '.join(valid_providers.keys())}"
            }

        env_var = valid_providers[provider_lower]

        # If no key provided, check environment
        if not api_key:
            existing = os.environ.get(env_var)
            if existing:
                return {
                    "success": True,
                    "message": f"Already logged in to {provider} (key from environment)",
                    "provider": provider,
                    "source": "environment"
                }
            return {
                "success": False,
                "error": f"No API key provided. Use: /login {provider} YOUR_API_KEY"
            }

        # Validate key format (basic check)
        if len(api_key) < 10:
            return {
                "success": False,
                "error": "API key too short. Please provide a valid key."
            }

        # Sanitize API key - prevent injection attacks
        sanitized_key = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', api_key)
        if sanitized_key != api_key:
            return {
                "success": False,
                "error": "API key contains invalid characters (newlines, control chars not allowed)"
            }

        # Limit key length to prevent DoS
        if len(api_key) > 500:
            return {
                "success": False,
                "error": "API key too long (max 500 characters)"
            }

        try:
            if scope == "global":
                # Save to global credentials
                creds_file = self._get_credentials_file()
                creds = {}
                if creds_file.exists():
                    try:
                        creds = json.loads(creds_file.read_text())
                    except json.JSONDecodeError:
                        creds = {}

                creds[env_var] = api_key
                creds_file.write_text(json.dumps(creds, indent=2))
                creds_file.chmod(0o600)  # Secure permissions

                # Also set in environment for current session
                os.environ[env_var] = api_key

                return {
                    "success": True,
                    "message": f"Logged in to {provider} (global)",
                    "provider": provider,
                    "scope": "global",
                    "file": str(creds_file)
                }

            elif scope == "project":
                # Save to project .env
                env_file = self._get_env_file()
                lines = []
                key_found = False

                if env_file.exists():
                    for line in env_file.read_text().splitlines():
                        if line.startswith(f"{env_var}="):
                            lines.append(f"{env_var}={api_key}")
                            key_found = True
                        else:
                            lines.append(line)

                if not key_found:
                    lines.append(f"{env_var}={api_key}")

                env_file.write_text("\n".join(lines) + "\n")

                # Set in environment for current session
                os.environ[env_var] = api_key

                return {
                    "success": True,
                    "message": f"Logged in to {provider} (project)",
                    "provider": provider,
                    "scope": "project",
                    "file": str(env_file)
                }

            else:
                return {
                    "success": False,
                    "error": f"Invalid scope: {scope}. Use 'global' or 'project'"
                }

        except Exception as e:
            return {"success": False, "error": f"Login failed: {e}"}

    def logout(self, provider: str = None, scope: str = "all") -> Dict[str, Any]:
        """Logout/remove API key for a provider."""
        valid_providers = {
            "gemini": "GEMINI_API_KEY",
            "google": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "nebius": "NEBIUS_API_KEY",
            "groq": "GROQ_API_KEY",
        }

        removed = []

        try:
            # Determine which keys to remove
            if provider:
                provider_lower = provider.lower()
                if provider_lower not in valid_providers:
                    return {
                        "success": False,
                        "error": f"Unknown provider: {provider}"
                    }
                keys_to_remove = [valid_providers[provider_lower]]
            else:
                keys_to_remove = list(valid_providers.values())

            # Remove from global credentials
            if scope in ("global", "all"):
                creds_file = self._get_credentials_file()
                if creds_file.exists():
                    try:
                        creds = json.loads(creds_file.read_text())
                        for key in keys_to_remove:
                            if key in creds:
                                del creds[key]
                                removed.append(f"{key} (global)")
                        creds_file.write_text(json.dumps(creds, indent=2))
                    except Exception:
                        pass

            # Remove from project .env
            if scope in ("project", "all"):
                env_file = self._get_env_file()
                if env_file.exists():
                    try:
                        lines = []
                        original = env_file.read_text().splitlines()
                        for line in original:
                            should_keep = True
                            for key in keys_to_remove:
                                if line.startswith(f"{key}="):
                                    removed.append(f"{key} (project)")
                                    should_keep = False
                                    break
                            if should_keep:
                                lines.append(line)
                        if len(lines) != len(original):
                            env_file.write_text("\n".join(lines) + "\n" if lines else "")
                    except Exception:
                        pass

            # Remove from current environment
            for key in keys_to_remove:
                if key in os.environ:
                    del os.environ[key]
                    if f"{key} (env)" not in removed:
                        removed.append(f"{key} (session)")

            if removed:
                return {
                    "success": True,
                    "message": f"Logged out: {', '.join(removed)}",
                    "removed": removed
                }
            else:
                return {
                    "success": True,
                    "message": "No credentials found to remove",
                    "removed": []
                }

        except Exception as e:
            return {"success": False, "error": f"Logout failed: {e}"}

    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status for all providers."""
        providers = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "nebius": "NEBIUS_API_KEY",
            "groq": "GROQ_API_KEY",
        }

        status = {}

        # Check global credentials
        creds_file = self._get_credentials_file()
        global_creds = {}
        if creds_file.exists():
            try:
                global_creds = json.loads(creds_file.read_text())
            except Exception:
                pass

        # Check project .env
        env_file = self._get_env_file()
        project_creds = {}
        if env_file.exists():
            try:
                for line in env_file.read_text().splitlines():
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        project_creds[key.strip()] = value.strip()
            except Exception:
                pass

        for provider, env_var in providers.items():
            sources = []
            if env_var in os.environ:
                sources.append("environment")
            if env_var in global_creds:
                sources.append("global")
            if env_var in project_creds:
                sources.append("project")

            status[provider] = {
                "logged_in": len(sources) > 0,
                "sources": sources,
                "env_var": env_var
            }

        return {
            "providers": status,
            "global_file": str(creds_file),
            "project_file": str(env_file)
        }

    # =========================================================================
    # MEMORY PERSISTENCE - MEMORY.md (Claude Code Parity with CLAUDE.md)
    # =========================================================================

    def _get_memory_file(self, scope: str = "project") -> Path:
        """Get memory file path."""
        if scope == "global":
            config_dir = Path.home() / ".config" / "juancs"
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir / "MEMORY.md"
        else:
            return Path.cwd() / "MEMORY.md"

    def read_memory(self, scope: str = "project") -> Dict[str, Any]:
        """Read memory/context from MEMORY.md file."""
        memory_file = self._get_memory_file(scope)

        if not memory_file.exists():
            return {
                "success": True,
                "content": "",
                "exists": False,
                "file": str(memory_file),
                "scope": scope
            }

        try:
            content = memory_file.read_text()
            return {
                "success": True,
                "content": content,
                "exists": True,
                "file": str(memory_file),
                "scope": scope,
                "size": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file": str(memory_file)
            }

    def write_memory(self, content: str, scope: str = "project", append: bool = False) -> Dict[str, Any]:
        """Write to MEMORY.md file."""
        memory_file = self._get_memory_file(scope)

        try:
            if append and memory_file.exists():
                existing = memory_file.read_text()
                content = existing + "\n" + content

            memory_file.write_text(content)

            return {
                "success": True,
                "message": f"Memory {'appended to' if append else 'written to'} {memory_file}",
                "file": str(memory_file),
                "scope": scope
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def remember(self, note: str, scope: str = "project") -> Dict[str, Any]:
        """Add a note to memory (convenience method)."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        formatted = f"\n## Note ({timestamp})\n{note}\n"
        return self.write_memory(formatted, scope=scope, append=True)


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
