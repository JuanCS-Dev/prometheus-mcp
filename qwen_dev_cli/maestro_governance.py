"""
Maestro Governance Integration Module

Integrates Justiça (governance) and Sofia (counselor) into Maestro orchestrator.

Based on Phase 5 research (Nov 2025):
- Anthropic: Orchestrator-worker pattern with governance checks
- Google: Agent identities with IAM enforcement
- MCP: Single audit trail with observability

Architecture:
    User Request
        ↓
    Maestro (orchestrator)
        ↓
    Governance Pipeline (parallel)
        ├── Justiça (constitutional check) ──┐
        └── Sofia (ethical counsel)          ├──→ PARALLEL
                                             ┘
        ↓
    Worker Agent (if approved)
        ↓
    Response + Governance Metadata
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from qwen_dev_cli.core.llm import LLMClient
from qwen_dev_cli.core.mcp_client import MCPClient
from qwen_dev_cli.agents.base import AgentTask, AgentResponse, BaseAgent
from qwen_dev_cli.agents.justica_agent import JusticaIntegratedAgent
from qwen_dev_cli.agents.sofia_agent import SofiaIntegratedAgent
from qwen_dev_cli.core.governance_pipeline import GovernancePipeline
from qwen_dev_cli.core.observability import setup_observability, trace_operation

logger = logging.getLogger(__name__)
console = Console()


class MaestroGovernance:
    """
    Governance integration for Maestro orchestrator.

    Features:
    - Pre-execution constitutional checks (Justiça)
    - Ethical counsel for high-risk operations (Sofia)
    - Parallel execution of governance checks
    - OpenTelemetry observability
    - Risk-level based routing
    - Audit trail generation

    Example:
        >>> gov = MaestroGovernance(llm_client, mcp_client)
        >>> await gov.initialize()
        >>>
        >>> # Execute with governance
        >>> response = await gov.execute_with_governance(
        ...     agent=planner_agent,
        ...     task=task,
        ...     risk_level="HIGH"
        ... )
    """

    def __init__(
        self,
        llm_client: LLMClient,
        mcp_client: MCPClient,
        enable_governance: bool = True,
        enable_counsel: bool = True,
        enable_observability: bool = True,
        auto_risk_detection: bool = True
    ):
        """
        Initialize Maestro governance.

        Args:
            llm_client: LLM client for agent reasoning
            mcp_client: MCP client for tool access
            enable_governance: Enable Justiça constitutional checks
            enable_counsel: Enable Sofia ethical counsel
            enable_observability: Enable OpenTelemetry tracing
            auto_risk_detection: Automatically detect risk levels from prompts

        Raises:
            TypeError: If llm_client or mcp_client have wrong type
            ValueError: If llm_client or mcp_client are None
        """
        # 🔒 INPUT VALIDATION (AIR GAP #1-6): Validate critical parameters
        if llm_client is None:
            raise ValueError("llm_client cannot be None")
        if mcp_client is None:
            raise ValueError("mcp_client cannot be None")

        # Type validation (duck typing - check for required methods)
        if not hasattr(llm_client, 'generate') and not hasattr(llm_client, 'chat'):
            raise TypeError(
                f"llm_client must have 'generate' or 'chat' method, "
                f"got {type(llm_client).__name__}"
            )

        if not hasattr(mcp_client, 'call_tool') and not hasattr(mcp_client, 'list_tools'):
            raise TypeError(
                f"mcp_client must have 'call_tool' or 'list_tools' method, "
                f"got {type(mcp_client).__name__}"
            )

        # Boolean validation
        if not isinstance(enable_governance, bool):
            raise TypeError(f"enable_governance must be bool, got {type(enable_governance).__name__}")
        if not isinstance(enable_counsel, bool):
            raise TypeError(f"enable_counsel must be bool, got {type(enable_counsel).__name__}")
        if not isinstance(enable_observability, bool):
            raise TypeError(f"enable_observability must be bool, got {type(enable_observability).__name__}")
        if not isinstance(auto_risk_detection, bool):
            raise TypeError(f"auto_risk_detection must be bool, got {type(auto_risk_detection).__name__}")

        self.llm_client = llm_client
        self.mcp_client = mcp_client
        self.enable_governance = enable_governance
        self.enable_counsel = enable_counsel
        self.enable_observability = enable_observability
        self.auto_risk_detection = auto_risk_detection

        # Components (initialized lazily)
        self.justica: Optional[JusticaIntegratedAgent] = None
        self.sofia: Optional[SofiaIntegratedAgent] = None
        self.pipeline: Optional[GovernancePipeline] = None
        self.initialized = False

        logger.info("MaestroGovernance instance created")

    async def initialize(self):
        """
        Initialize governance components.

        Lazy initialization pattern - only called when first needed.
        """
        if self.initialized:
            return

        console.print("[dim]🛡️  Initializing Constitutional Governance...[/dim]")

        try:
            # Setup observability first
            if self.enable_observability:
                setup_observability(
                    service_name="maestro-governance",
                    enable_console=False,  # Don't pollute terminal
                    enable_file=True
                )

            # Initialize Justiça (constitutional governance)
            if self.enable_governance:
                with console.status("[bold cyan]Waking Justiça (Constitutional Guardian)...[/bold cyan]"):
                    self.justica = JusticaIntegratedAgent(
                        llm_client=self.llm_client,
                        mcp_client=self.mcp_client
                    )
                    logger.info("✓ Justiça initialized")

            # Initialize Sofia (wise counselor)
            if self.enable_counsel:
                with console.status("[bold magenta]Waking Sofia (Wise Counselor)...[/bold magenta]"):
                    self.sofia = SofiaIntegratedAgent(
                        llm_client=self.llm_client,
                        mcp_client=self.mcp_client
                    )
                    logger.info("✓ Sofia initialized")

            # Create governance pipeline
            if self.justica and self.sofia:
                self.pipeline = GovernancePipeline(
                    justica=self.justica,
                    sofia=self.sofia,
                    enable_governance=self.enable_governance,
                    enable_counsel=self.enable_counsel,
                    enable_observability=self.enable_observability,
                    fail_safe=True  # Block on error (recommended)
                )
                logger.info("✓ Governance pipeline initialized")

            self.initialized = True
            console.print("[green]✓[/green] [bold]Constitutional Governance Online[/bold]")

        except Exception as e:
            logger.exception(f"Failed to initialize governance: {e}")
            console.print(f"[yellow]⚠️  Governance initialization failed: {e}[/yellow]")
            console.print("[yellow]   Continuing without governance (degraded mode)[/yellow]")
            # Don't raise - allow Maestro to continue without governance

    def detect_risk_level(self, prompt: str, agent_name: str) -> str:
        """
        Automatically detect risk level from prompt.

        Risk Levels:
        - CRITICAL: System-level changes, production deployments, security, COMMAND INJECTION
        - HIGH: Database changes, API changes, refactoring
        - MEDIUM: Feature additions, bug fixes (default)
        - LOW: Documentation, tests, read-only operations

        Args:
            prompt: User prompt/request
            agent_name: Name of target agent

        Returns:
            Risk level string (LOW, MEDIUM, HIGH, CRITICAL)
        """
        # Handle None/invalid input (AIR GAP #7, #11 FIX)
        if prompt is None:
            return "MEDIUM"
        if not isinstance(prompt, str):
            try:
                prompt = str(prompt)
            except (TypeError, ValueError):
                return "MEDIUM"

        if not self.auto_risk_detection:
            return "MEDIUM"  # Default

        prompt_lower = prompt.lower()

        # 🔥 COMMAND INJECTION PATTERNS (AIR GAP #36 FIX) - CHECK FIRST!
        # These are EXTREMELY CRITICAL and must be detected before other patterns
        command_injection_patterns = [
            ";",      # Command chaining: "ls; rm -rf /"
            "|",      # Pipe: "ls | bash"
            "&&",     # AND operator: "ls && rm file"
            "||",     # OR operator: "fail || rm file"
            "$(",     # Command substitution: "$(rm file)"
            "${",     # Shell expansion: "${IFS}rm${IFS}file"
            "`",      # Backticks: "`rm file`"
            "\n",     # Newline injection
            "bash",   # Shell execution
            "sh ",    # Shell execution (with space to avoid "show", "shell")
            "/bin/",  # Direct binary execution
            "curl ",  # Network download
            "wget ",  # Network download
            "nc ",    # Netcat
            "eval",   # Code evaluation
            "exec",   # Code execution
        ]

        # Check for command injection - HIGHEST PRIORITY
        for pattern in command_injection_patterns:
            if pattern in prompt or pattern in prompt_lower:
                logger.warning(f"🔥 COMMAND INJECTION DETECTED: '{pattern}' in prompt")
                return "CRITICAL"

        # CRITICAL risk patterns (after command injection check)
        critical_patterns = [
            "delete", "drop", "production", "deploy", "security", "auth",
            "password", "token", "credential", "sudo", "root", "admin"
        ]

        # HIGH risk patterns
        high_patterns = [
            "database", "schema", "migration", "api", "refactor", "redesign",
            "architecture", "breaking change"
        ]

        # LOW risk patterns
        low_patterns = [
            "document", "test", "read", "show", "display", "list", "search",
            "explore", "explain"
        ]

        # Check patterns
        if any(pattern in prompt_lower for pattern in critical_patterns):
            return "CRITICAL"

        if any(pattern in prompt_lower for pattern in high_patterns):
            return "HIGH"

        if any(pattern in prompt_lower for pattern in low_patterns):
            return "LOW"

        # Default to MEDIUM
        return "MEDIUM"

    async def execute_with_governance(
        self,
        agent: BaseAgent,
        task: AgentTask,
        risk_level: Optional[str] = None
    ) -> AgentResponse:
        """
        Execute agent with complete governance pipeline.

        Flow:
        1. Detect risk level (if not provided)
        2. Pre-execution checks (Justiça + Sofia in parallel)
        3. Execute agent (if approved)
        4. Return response with governance metadata

        Args:
            agent: Worker agent to execute
            task: Task to execute
            risk_level: Optional manual risk level override

        Returns:
            AgentResponse with execution result + governance metadata
        """
        # Ensure initialized
        if not self.initialized:
            await self.initialize()

        # If governance not available, execute directly
        if not self.pipeline:
            logger.warning("Governance pipeline not available, executing without checks")
            return await agent.execute(task)

        # Detect risk level if not provided
        if risk_level is None:
            risk_level = self.detect_risk_level(task.request, agent.role.value)

        # Show governance banner
        self._render_governance_banner(risk_level)

        # Execute through governance pipeline
        with trace_operation(
            "maestro.execute_with_governance",
            {"agent": agent.role.value, "risk_level": risk_level}
        ):
            response = await self.pipeline.execute_with_governance(
                agent=agent,
                task=task,
                risk_level=risk_level
            )

        # Render governance results
        if response.success:
            self._render_governance_success(response)
        else:
            self._render_governance_blocked(response)

        return response

    async def ask_sofia(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ask Sofia for ethical counsel (direct access).

        This is for interactive counsel sessions, not pre-execution checks.

        Args:
            question: Ethical question or dilemma
            context: Optional context

        Returns:
            Dict with counsel response

        Raises:
            TypeError: If question is not a string
            ValueError: If question is None or empty
        """
        # 🔒 INPUT VALIDATION (AIR GAP #16-18): Validate question parameter
        if question is None:
            raise ValueError("question cannot be None")
        if not isinstance(question, str):
            raise TypeError(f"question must be str, got {type(question).__name__}")
        if not question.strip():
            raise ValueError("question cannot be empty")

        # Validate context if provided
        if context is not None and not isinstance(context, dict):
            raise TypeError(f"context must be dict or None, got {type(context).__name__}")

        if not self.initialized:
            await self.initialize()

        if not self.sofia:
            return {
                "error": "Sofia not available",
                "message": "Counsel service is disabled"
            }

        console.print("\n[bold magenta]🕊️  Consulting Sofia (Wise Counselor)...[/bold magenta]\n")

        try:
            # Use chat mode for interactive counsel
            response = await self.sofia.chat_mode(
                user_input=question,
                context=context or {}
            )

            return {
                "success": True,
                "counsel": response.counsel,
                "counsel_type": response.counsel_type,
                "confidence": response.confidence,
                "requires_professional": response.requires_professional,
                "sources": response.sources
            }

        except Exception as e:
            logger.exception(f"Sofia counsel failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _render_governance_banner(self, risk_level: str):
        """Render governance check banner."""
        risk_colors = {
            "LOW": "green",
            "MEDIUM": "yellow",
            "HIGH": "red",
            "CRITICAL": "bold red"
        }

        color = risk_colors.get(risk_level, "yellow")
        console.print(f"\n[{color}]🛡️  Governance Check (Risk: {risk_level})[/{color}]")

    def _render_governance_success(self, response: AgentResponse):
        """Render successful governance check."""
        if not response.data or "governance_traces" not in response.data:
            return

        traces = response.data["governance_traces"]

        # Show quick summary
        console.print("[green]✓[/green] [dim]Governance approved[/dim]")

        # Show if Sofia provided counsel
        if traces.get("counsel_check", {}).get("triggered"):
            console.print("[dim]💡 Sofia provided counsel (check logs for details)[/dim]")

    def _render_governance_blocked(self, response: AgentResponse):
        """Render blocked action."""
        console.print(Panel(
            f"[bold red]🛑 Action Blocked by Governance[/bold red]\n\n"
            f"[yellow]Reason:[/yellow] {response.error}\n\n"
            f"[dim]This action was blocked for constitutional or ethical reasons.\n"
            f"Review the governance policy or consult with Sofia.[/dim]",
            border_style="red"
        ))

    def get_governance_status(self) -> Dict[str, Any]:
        """
        Get current governance status.

        Returns:
            Dict with governance component status
        """
        # 🔒 SECURITY FIX (AIR GAP #37): Use hasattr for graceful degradation
        # Prevents AttributeError if attributes are deleted during execution
        return {
            "initialized": getattr(self, "initialized", False),
            "governance_enabled": getattr(self, "enable_governance", False),
            "counsel_enabled": getattr(self, "enable_counsel", False),
            "observability_enabled": getattr(self, "enable_observability", False),
            "justica_available": hasattr(self, "justica") and self.justica is not None,
            "sofia_available": hasattr(self, "sofia") and self.sofia is not None,
            "pipeline_available": hasattr(self, "pipeline") and self.pipeline is not None,
            "auto_risk_detection": getattr(self, "auto_risk_detection", True)
        }


def render_sofia_counsel(counsel_data: Dict[str, Any]):
    """
    Render Sofia's counsel beautifully.

    Args:
        counsel_data: Counsel response from ask_sofia()
    """
    if not counsel_data.get("success"):
        console.print(f"[red]❌ Error: {counsel_data.get('error', 'Unknown')}[/red]")
        return

    # Create counsel panel
    counsel_text = counsel_data["counsel"]
    counsel_type = counsel_data.get("counsel_type", "general")
    confidence = counsel_data.get("confidence", 0.0)
    requires_prof = counsel_data.get("requires_professional", False)

    # Header with confidence
    header = f"🕊️  Sofia's Counsel ({counsel_type.title()}) - Confidence: {confidence:.0%}"

    # Build content
    content = f"{counsel_text}\n"

    if requires_prof:
        content += "\n[bold yellow]⚠️  Professional Help Recommended[/bold yellow]"
        content += "\n[dim]This situation may require consultation with a human expert.[/dim]"

    # Render
    console.print(Panel(
        content,
        title=header,
        border_style="magenta",
        padding=(1, 2)
    ))

    # Show sources if available
    sources = counsel_data.get("sources", [])
    if sources:
        console.print("\n[dim]Sources:[/dim]")
        for source in sources[:3]:  # Limit to 3
            console.print(f"[dim]  • {source}[/dim]")
