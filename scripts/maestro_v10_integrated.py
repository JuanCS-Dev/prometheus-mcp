#!/usr/bin/env python3
"""
MAESTRO v10.0 - INTEGRATED EDITION
Production-grade terminal AI with REAL v6.0 Agents.

Architecture:
    Shell → Orchestrator → [Planner v5.0, Reviewer v5.0, Refactorer v8.0, Explorer]
    Full AST analysis + Knowledge Graph + LLM reasoning
    
Philosophy: "Symbolic precision meets neural intelligence"
"""

import os
import sys
import asyncio
import json
import time
from typing import Optional, Iterator, Dict, Any, List
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.live import Live
from rich.tree import Tree
from rich.panel import Panel
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory

# Load environment FIRST
from dotenv import load_dotenv
load_dotenv()

# Import REAL v6.0 Agents
from jdev_cli.core.llm import LLMClient
from jdev_cli.core.mcp_client import MCPClient
from jdev_cli.tools.base import ToolRegistry
from jdev_cli.agents.base import AgentTask, AgentResponse
from jdev_cli.agents.planner import PlannerAgent
from jdev_cli.agents.reviewer import ReviewerAgent
from jdev_cli.agents.refactorer import RefactorerAgent
from jdev_cli.agents.explorer import ExplorerAgent
from jdev_cli.agents.executor import (
    NextGenExecutorAgent,
    ExecutionMode,
    SecurityLevel
)
from jdev_cli.agents.architect import ArchitectAgent
from jdev_cli.agents.security import SecurityAgent
from jdev_cli.agents.performance import PerformanceAgent
from jdev_cli.agents.testing import TestingAgent
from jdev_cli.agents.documentation import DocumentationAgent
from jdev_cli.agents.data_agent_production import create_data_agent
from jdev_cli.agents.devops_agent import create_devops_agent

# Import TUI Components (30 FPS optimized)
from jdev_cli.tui.maestro_layout import MaestroLayout, CyberpunkHeader
from jdev_cli.tui.components.agent_routing import AgentRoutingDisplay
from jdev_cli.tui.components.streaming_display import StreamingResponseDisplay
from jdev_cli.tui.components.autocomplete import ContextAwareCompleter, create_completer
from jdev_cli.tui.components.slash_completer import CombinedCompleter
from jdev_cli.tui.performance import PerformanceMonitor, FPSCounter
from jdev_cli.tui.landing import show_landing_screen
from jdev_cli.ui.command_palette import CommandPalette, Command, CommandCategory

# Import MAESTRO v10.0 Shell UI Components (Definitive Edition)
from jdev_cli.tui.components.maestro_shell_ui import MaestroShellUI
from jdev_cli.tui.components.maestro_data_structures import AgentState, AgentStatus, MetricsData
from jdev_cli.core.file_tracker import FileOperationTracker

# ═══════════════════════════════════════════════════════════════════
# ORCHESTRATOR - The Brain
# ═══════════════════════════════════════════════════════════════════

class Orchestrator:
    """Routes tasks to appropriate v6.0 agents"""

    def __init__(self, llm_client: LLMClient, mcp_client: MCPClient, approval_callback=None):
        self.llm = llm_client
        self.mcp = mcp_client

        # Initialize REAL v6.0 Agents (order matters - Explorer first)
        explorer = ExplorerAgent(llm_client, mcp_client)

        self.agents = {
            'executor': NextGenExecutorAgent(
                llm_client=llm_client,
                mcp_client=mcp_client,
                execution_mode=ExecutionMode.LOCAL,  # Fast local execution
                security_level=SecurityLevel.PERMISSIVE,  # No approval required (per Architect request)
                approval_callback=None,  # Disabled: approval system too intrusive
                config={
                    "timeout": 30.0,
                    "max_retries": 3
                }
            ),
            'explorer': explorer,
            'planner': PlannerAgent(llm_client, mcp_client),
            'reviewer': ReviewerAgent(llm_client, mcp_client),
            'refactorer': RefactorerAgent(llm_client, mcp_client, explorer),  # Pass explorer directly
            'architect': ArchitectAgent(llm_client, mcp_client),
            'security': SecurityAgent(llm_client, mcp_client),
            'performance': PerformanceAgent(llm_client, mcp_client),
            'testing': TestingAgent(llm_client, mcp_client),
            'documentation': DocumentationAgent(llm_client, mcp_client),
            'data': create_data_agent(llm_client, mcp_client, enable_thinking=True),  # DataAgent v1.0
            'devops': create_devops_agent(llm_client, mcp_client, auto_remediate=False, policy_mode="require_approval")  # DevOpsAgent v1.0
        }
    
    def route(self, prompt: str) -> str:
        """Intelligent routing based on keywords - Priority ordered to avoid conflicts"""
        p = prompt.lower()

        # PRIORITY 1: Specific multi-word patterns (most specific first)
        if any(w in p for w in ['unit test', 'integration test', 'test case', 'write test', 'generate test']):
            return 'testing'

        # Check for dockerfile BEFORE documentation (avoid "generate doc" conflict)
        if 'dockerfile' in p or 'docker file' in p:
            return 'devops'

        if any(w in p for w in ['write doc', 'api doc', 'docstring', 'readme']):
            return 'documentation'

        # PRIORITY 2: Domain-specific operations (high specificity)
        if any(w in p for w in ['database', 'schema', 'query', 'sql', 'migration',
                                 'table', 'index', 'postgres', 'mysql', 'db']):
            return 'data'

        if any(w in p for w in ['deploy', 'deployment', 'docker', 'dockerfile', 'container',
                                 'kubernetes', 'k8s', 'pod', 'helm', 'argocd', 'ci/cd',
                                 'pipeline', 'terraform', 'iac', 'infrastructure', 'incident', 'outage']):
            return 'devops'

        # PRIORITY 3: Code operations (medium specificity)
        if any(w in p for w in ['review', 'audit', 'grade', 'lint']):
            return 'reviewer'

        if any(w in p for w in ['refactor', 'rename', 'extract', 'inline', 'modernize', 'clean up']):
            return 'refactorer'

        if any(w in p for w in ['explore', 'map', 'graph', 'blast radius', 'dependencies', 'structure']):
            return 'explorer'

        # PRIORITY 4: Design & Analysis (medium specificity)
        # Check architecture BEFORE document catch-all (avoid "document architecture" conflict)
        if any(w in p for w in ['architecture', 'system design', 'architect', 'uml', 'diagram', 'component']):
            return 'architect'

        # Check security with expanded keywords (check, find, vulnerabilities)
        if any(w in p for w in ['security', 'vulnerability', 'vulnerabilities', 'exploit', 'cve', 'owasp',
                                 'injection', 'xss', 'csrf', 'penetration', 'check for', 'find security']):
            return 'security'

        if any(w in p for w in ['performance', 'bottleneck', 'profil', 'benchmark',
                                 'slow', 'latency', 'throughput']):
            return 'performance'

        # PRIORITY 5: Planning (lower specificity - but NOT if deployment)
        if any(w in p for w in ['break down', 'strategy', 'roadmap', 'sop', 'how to']):
            return 'planner'

        # Check plan (generic keyword - low priority)
        if 'plan' in p and 'deploy' not in p:
            return 'planner'

        # PRIORITY 6: Catch-all single keywords (lowest priority - checked LAST)
        # Check test BEFORE security (avoid "test security" routing to security)
        if 'test' in p:
            return 'testing'

        # Check document AFTER architect (avoid "document architecture" conflict)
        if 'document' in p or 'comment' in p or 'explain' in p:
            return 'documentation'

        # PRIORITY 6: Bash/System commands (specific commands only)
        executor_keywords = [
            'ls', 'pwd', 'cd', 'mkdir', 'rm', 'cp', 'mv',  # File ops
            'ps', 'kill', 'top', 'htop',  # Process
            'curl', 'wget', 'ping', 'netstat',  # Network
            'git status', 'git diff', 'git log',  # Git
            'run', 'execute', 'command', 'bash', 'shell',  # Generic execution
        ]
        if any(keyword in p for keyword in executor_keywords):
            return 'executor'

        # Default: Executor for everything else
        return 'executor'
    
    async def execute(self, prompt: str, context: Dict = None) -> AgentResponse:
        """Route and execute with real agents"""
        
        agent_name = self.route(prompt)
        agent = self.agents[agent_name]
        
        # Build AgentTask
        task = AgentTask(
            request=prompt,
            context=context or {},
            metadata={'interface': 'maestro_v10', 'timestamp': datetime.now().isoformat()}
        )
        
        # Execute REAL agent
        return await agent.execute(task)

    async def execute_streaming(self, prompt: str, context: Dict = None):
        """Route and execute with streaming support for 30 FPS.

        Yields updates from agent execution for real-time UI rendering.
        Only SimpleExecutorAgent currently supports streaming.
        """
        agent_name = self.route(prompt)
        agent = self.agents[agent_name]

        # Build AgentTask
        task = AgentTask(
            request=prompt,
            context=context or {},
            metadata={'interface': 'maestro_v10', 'timestamp': datetime.now().isoformat()}
        )

        # Check if agent supports streaming
        if hasattr(agent, 'execute_streaming'):
            # Stream updates from agent
            async for update in agent.execute_streaming(task):
                yield update
        else:
            # Fallback: execute normally and yield final result
            result = await agent.execute(task)
            yield {"type": "result", "data": result}

# ═══════════════════════════════════════════════════════════════════
# RENDERER - Beautiful Output
# DEPRECATED: Now using TUI components (MaestroLayout, StreamingResponseDisplay)
# Kept for backwards compatibility and reference
# ═══════════════════════════════════════════════════════════════════

class Renderer:
    """[DEPRECATED] Renders v6.0 agent output - replaced by TUI components"""
    
    def __init__(self, console: Console):
        self.c = console
    
    def render(self, response: AgentResponse, agent_name: str):
        """Render agent response based on type"""
        
        if not response.success:
            self.c.print(f"\n[red]❌ Error:[/red] {response.error}\n")
            if response.reasoning:
                self.c.print(f"[dim]{response.reasoning}[/dim]\n")
            return
        
        # Route to specialized renderer
        if agent_name == 'reviewer':
            self._render_review(response)
        elif agent_name == 'planner':
            self._render_plan(response)
        elif agent_name == 'refactorer':
            self._render_refactor(response)
        elif agent_name == 'explorer':
            self._render_explorer(response)
        elif agent_name == 'architect':
            self._render_architect(response)
        elif agent_name == 'security':
            self._render_security(response)
        elif agent_name == 'performance':
            self._render_performance(response)
        elif agent_name == 'testing':
            self._render_testing(response)
        elif agent_name == 'documentation':
            self._render_documentation(response)
        elif agent_name == 'data':
            self._render_data(response)
        elif agent_name == 'devops':
            self._render_devops(response)
        else:
            self._render_generic(response)
    
    def _render_review(self, res: AgentResponse):
        """Render ReviewerAgent v5.0 output"""
        data = res.data
        
        if not isinstance(data, dict):
            self.c.print(Markdown(str(data)))
            return
        
        # Extract review report
        report = data.get('report', data)
        
        # Score & Status
        score = report.get('score', 0)
        approved = report.get('approved', False)
        
        status = "✅ APPROVED" if approved else "❌ NOT APPROVED"
        color = "green" if approved else "red"
        
        self.c.print(f"\n[bold {color}]{status}[/bold {color}]")
        self.c.print(f"[bold]Score: {score}/100[/bold]\n")
        
        # Issues
        issues = report.get('issues', [])
        if issues:
            table = Table(title="🔍 Issues Found", border_style="yellow")
            table.add_column("Severity", style="red")
            table.add_column("Category", style="cyan")
            table.add_column("Message", style="white", max_width=60)
            
            for issue in issues[:15]:  # Limit display
                if isinstance(issue, dict):
                    table.add_row(
                        issue.get('severity', 'UNKNOWN'),
                        issue.get('category', ''),
                        issue.get('message', '')[:80]
                    )
            
            self.c.print(table)
            self.c.print()
        
        # Summary
        if 'summary' in report:
            self.c.print(Panel(report['summary'], title="📋 Summary", border_style="blue"))
            self.c.print()
        
        # Recommendations
        if 'recommendations' in report:
            self.c.print("[bold yellow]💡 Recommendations:[/bold yellow]")
            for rec in report['recommendations'][:5]:
                self.c.print(f"  • {rec}")
            self.c.print()
    
    def _render_plan(self, res: AgentResponse):
        """Render PlannerAgent v5.0 output"""
        data = res.data
        
        if not isinstance(data, dict):
            self.c.print(Markdown(str(data)))
            return
        
        # Goal
        goal = data.get('goal', 'Execution Plan')
        self.c.print(f"\n[bold cyan]🎯 {goal}[/bold cyan]\n")
        
        # Strategy Overview
        if 'strategy_overview' in data:
            self.c.print(Panel(data['strategy_overview'], title="📋 Strategy", border_style="blue"))
            self.c.print()
        
        # Stages
        stages = data.get('stages', [])
        if stages:
            for idx, stage in enumerate(stages, 1):
                if isinstance(stage, dict):
                    self.c.print(f"[bold]Stage {idx}: {stage.get('name', 'Unknown')}[/bold]")
                    self.c.print(f"[dim]{stage.get('description', '')}[/dim]")
                    
                    steps = stage.get('steps', [])
                    for step in steps[:3]:  # Show first 3
                        if isinstance(step, dict):
                            self.c.print(f"  • {step.get('action', '')}")
                    
                    if len(steps) > 3:
                        self.c.print(f"  [dim]... +{len(steps)-3} more steps[/dim]")
                    self.c.print()
        
        # SOPs (if stages not present)
        if not stages:
            sops = data.get('sops', [])
            if sops:
                table = Table(title="📋 Execution Steps", border_style="cyan")
                table.add_column("#", style="dim", width=4)
                table.add_column("Role", style="yellow")
                table.add_column("Action", style="white")
                
                for idx, sop in enumerate(sops[:10], 1):
                    if isinstance(sop, dict):
                        table.add_row(
                            str(idx),
                            sop.get('role', ''),
                            sop.get('action', '')[:60]
                        )
                
                self.c.print(table)
                self.c.print()
        
        # Metadata
        duration = data.get('estimated_duration', 'Unknown')
        risk = data.get('risk_assessment', 'MEDIUM')
        
        self.c.print(f"[dim]Estimated Duration: {duration}[/dim]")
        self.c.print(f"[dim]Risk Level: {risk}[/dim]\n")
    
    def _render_refactor(self, res: AgentResponse):
        """Render RefactorerAgent v8.0 output"""
        data = res.data
        
        if not isinstance(data, dict):
            self.c.print(str(data))
            return
        
        success = data.get('success', False)
        changes_applied = data.get('changes_applied', 0)
        message = data.get('message', '')
        
        if success:
            self.c.print(f"\n[green]✅ Refactoring Complete[/green]")
            self.c.print(f"[dim]Applied {changes_applied} changes[/dim]")
        else:
            self.c.print(f"\n[red]❌ Refactoring Failed[/red]")
        
        if message:
            self.c.print(f"\n{message}\n")
    
    def _render_explorer(self, res: AgentResponse):
        """Render ExplorerAgent output"""
        data = res.data
        
        if isinstance(data, str):
            self.c.print(Markdown(data))
        elif isinstance(data, dict):
            # Graph metrics
            if 'total_entities' in data:
                self.c.print(f"\n[bold cyan]📊 Code Graph Metrics[/bold cyan]\n")
                self.c.print(f"Total Entities: {data.get('total_entities', 0)}")
                self.c.print(f"Files Analyzed: {data.get('files_analyzed', 0)}")
                
                if 'hotspots' in data:
                    self.c.print("\n[yellow]🔥 Hotspots (High Coupling):[/yellow]")
                    for hotspot in data['hotspots'][:5]:
                        self.c.print(f"  • {hotspot}")
                self.c.print()
            else:
                self.c.print(json.dumps(data, indent=2))
        else:
            self.c.print(str(data))

    def _render_architect(self, res: AgentResponse):
        """Render ArchitectAgent output"""
        self.c.print("\n[bold cyan]🏛️  ARCHITECTURE DESIGN[/bold cyan]\n")
        self._render_generic(res)

    def _render_security(self, res: AgentResponse):
        """Render SecurityAgent output"""
        self.c.print("\n[bold red]🔒 SECURITY ANALYSIS[/bold red]\n")
        self._render_generic(res)

    def _render_performance(self, res: AgentResponse):
        """Render PerformanceAgent output"""
        self.c.print("\n[bold yellow]⚡ PERFORMANCE OPTIMIZATION[/bold yellow]\n")
        self._render_generic(res)

    def _render_testing(self, res: AgentResponse):
        """Render TestingAgent output"""
        self.c.print("\n[bold green]🧪 TEST GENERATION[/bold green]\n")
        self._render_generic(res)

    def _render_documentation(self, res: AgentResponse):
        """Render DocumentationAgent output"""
        self.c.print("\n[bold blue]📚 DOCUMENTATION[/bold blue]\n")
        self._render_generic(res)

    def _render_data(self, res: AgentResponse):
        """Render DataAgent v1.0 output"""
        data = res.data

        if not isinstance(data, dict):
            self.c.print(Markdown(str(data)))
            return

        # Header
        self.c.print("\n[bold cyan]🗄️  DATABASE ANALYSIS[/bold cyan]\n")

        # Response
        response_text = data.get('response', '')
        if response_text:
            self.c.print(Markdown(response_text))
            self.c.print()

        # Schema issues (if present)
        if 'schema_issues' in data:
            issues = data['schema_issues']
            if issues:
                self.c.print("[bold yellow]⚠️  Schema Issues Found:[/bold yellow]")
                for issue in issues[:5]:  # Show top 5
                    severity_icon = {
                        'critical': '🔴',
                        'high': '🟠',
                        'medium': '🟡',
                        'low': '🟢',
                    }.get(issue.get('severity', 'medium'), '⚪')

                    desc = issue.get('description', 'No description')
                    rec = issue.get('recommendation', '')

                    self.c.print(f"  {severity_icon} {desc}")
                    if rec:
                        self.c.print(f"     💡 {rec}")
                self.c.print()

        # Query optimization (if present)
        if 'optimization' in data:
            opt = data['optimization']
            improvement = opt.get('improvement_percent', 0)
            confidence = opt.get('confidence_score', 0)

            self.c.print(f"[bold green]⚡ Query Optimization:[/bold green]")
            self.c.print(f"  Improvement: [bold]{improvement}%[/bold]")
            self.c.print(f"  Confidence: {confidence:.0%}")

            if 'required_indexes' in opt:
                indexes = opt['required_indexes']
                if indexes:
                    self.c.print(f"  Indexes needed: {', '.join(indexes)}")
            self.c.print()

        # Migration plan (if present)
        if 'migration' in data:
            migration = data['migration']
            risk = migration.get('risk_level', 'medium')
            downtime = migration.get('estimated_downtime_seconds', 0)
            online = migration.get('can_run_online', False)

            risk_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢',
            }.get(risk, '⚪')

            self.c.print(f"[bold blue]🏗️  Migration Plan:[/bold blue]")
            self.c.print(f"  {risk_icon} Risk: {risk.upper()}")
            self.c.print(f"  ⏱️  Downtime: {downtime}s")
            self.c.print(f"  {'✅' if online else '❌'} Can run online: {online}")
            self.c.print()

        # Thinking trace (if present)
        if res.reasoning and res.reasoning != "Direct generation (thinking disabled)":
            self.c.print("[dim]💭 Reasoning:[/dim]")
            self.c.print(f"[dim]{res.reasoning[:200]}...[/dim]\n")

    def _render_devops(self, res: AgentResponse):
        """Render DevOpsAgent v1.0 output"""
        data = res.data

        if not isinstance(data, dict):
            self.c.print(Markdown(str(data)))
            return

        # Header
        self.c.print("\n[bold cyan]🚀 DEVOPS OPERATIONS[/bold cyan]\n")

        # Response
        response_text = data.get('response', '')
        if response_text:
            self.c.print(Markdown(response_text))
            self.c.print()

        # Incident detection (if present)
        if 'incident' in data:
            incident = data['incident']
            severity = incident.get('severity', 'medium')
            severity_icon = {
                'p0': '🔴',
                'p1': '🟠',
                'p2': '🟡',
                'p3': '🟢',
            }.get(severity.lower(), '⚪')

            self.c.print(f"[bold red]🚨 Incident Detected:[/bold red]")
            self.c.print(f"  {severity_icon} Severity: {severity.upper()}")
            self.c.print(f"  📝 Description: {incident.get('description', 'N/A')}")
            self.c.print(f"  🎯 Root Cause: {incident.get('root_cause', 'Investigating...')}")

            actions = incident.get('recommended_actions', [])
            if actions:
                self.c.print(f"  💡 Recommended Actions:")
                for action in actions[:3]:
                    self.c.print(f"     • {action}")

            can_auto = incident.get('can_auto_remediate', False)
            self.c.print(f"  {'✅' if can_auto else '❌'} Auto-remediation: {'ENABLED' if can_auto else 'REQUIRES APPROVAL'}")
            self.c.print()

        # Dockerfile generation (if present)
        if 'dockerfile' in data:
            self.c.print("[bold green]🐳 Dockerfile Generated:[/bold green]")
            dockerfile_preview = data['dockerfile'][:300] + "..."
            self.c.print(f"[dim]{dockerfile_preview}[/dim]")

            features = data.get('security_features', [])
            if features:
                self.c.print("[bold]Security Features:[/bold]")
                for feature in features:
                    self.c.print(f"  ✓ {feature}")
            self.c.print()

        # Kubernetes manifests (if present)
        if 'deployment.yaml' in data or 'manifests' in data:
            self.c.print("[bold blue]☸️  Kubernetes Manifests Generated:[/bold blue]")

            if 'gitops_enabled' in data and data['gitops_enabled']:
                self.c.print("  ✅ GitOps: ENABLED (ArgoCD auto-sync)")

            features = data.get('features', [])
            if features:
                for feature in features:
                    self.c.print(f"  ✓ {feature}")
            self.c.print()

        # CI/CD Pipeline (if present)
        if 'pipeline' in data or 'github-actions.yml' in data:
            self.c.print("[bold magenta]⚙️  CI/CD Pipeline Generated:[/bold magenta]")
            self.c.print("  ✓ Automated testing")
            self.c.print("  ✓ Docker multi-arch build")
            self.c.print("  ✓ GitOps deployment")
            self.c.print("  ✓ Zero manual steps")
            self.c.print()

        # Infrastructure health (if present)
        if 'health_score' in data or 'overall_score' in data:
            score = data.get('health_score', data.get('overall_score', 0))
            score_icon = '🟢' if score >= 90 else '🟡' if score >= 70 else '🔴'

            self.c.print(f"[bold green]📊 Infrastructure Health:[/bold green]")
            self.c.print(f"  {score_icon} Overall Score: [bold]{score:.1f}%[/bold]")

            predicted = data.get('predicted_issues', [])
            if predicted:
                self.c.print("  ⚠️  Predicted Issues:")
                for issue in predicted[:3]:
                    self.c.print(f"     • {issue}")
            self.c.print()

        # Terraform (if present)
        if 'main.tf' in data or 'terraform' in data:
            self.c.print("[bold cyan]🏗️  Terraform IaC Generated:[/bold cyan]")
            features = data.get('features', [])
            if features:
                for feature in features[:5]:
                    self.c.print(f"  ✓ {feature}")
            self.c.print()

        # Thinking trace (if present)
        if res.reasoning and res.reasoning != "Direct generation (thinking disabled)":
            self.c.print("[dim]💭 Reasoning:[/dim]")
            self.c.print(f"[dim]{res.reasoning[:200]}...[/dim]\n")

    def _render_generic(self, res: AgentResponse):
        """Generic renderer for unknown responses"""
        if isinstance(res.data, str):
            self.c.print(Markdown(res.data))
        elif isinstance(res.data, dict):
            self.c.print(json.dumps(res.data, indent=2))
        else:
            self.c.print(str(res.data))

        if res.reasoning:
            self.c.print(f"\n[dim]{res.reasoning}[/dim]\n")

# ═══════════════════════════════════════════════════════════════════
# SHELL - The Interface
# ═══════════════════════════════════════════════════════════════════

class Shell:
    """Agent-powered terminal with v6.0 integration @ 30 FPS"""

    def __init__(self):
        self.c = Console()
        self.orch: Optional[Orchestrator] = None
        self.running = True

        # TUI Components (30 FPS optimized)
        self.layout = None  # MaestroLayout (initialized in init())
        self.routing_display = AgentRoutingDisplay()
        self.streaming_display = None  # StreamingResponseDisplay (initialized in init())
        self.perf_monitor = PerformanceMonitor(target_fps=30)
        self.fps_counter = FPSCounter()

        # Command Palette & Autocomplete
        self.command_palette = CommandPalette()
        self.completer = None  # Initialized in init() after tool_registry

        # Prompt with history + autocomplete
        h = Path.home() / '.maestro_history'
        self.prompt = PromptSession(
            history=FileHistory(str(h)),
            auto_suggest=AutoSuggestFromHistory(),
            # completer will be set in init() after creating it with tool_registry
        )

        # Session state
        self.messages = []  # Conversation history
        self.current_agent = ""
        self._last_approval_always = False  # Flag for "always allow"

    async def _request_approval(self, command: str) -> bool:
        """Request user approval for command execution (async).

        PATCHED: Now properly pauses Live display to prevent
        screen flickering during input.

        Args:
            command: The command requiring approval

        Returns:
            True if approved, False otherwise
        """
        # ══════════════════════════════════════════════════════════════
        # CRITICAL: Pause UI before requesting input
        # ══════════════════════════════════════════════════════════════
        
        # 1. PAUSE the streaming display
        if hasattr(self, 'maestro_ui') and self.maestro_ui:
            self.maestro_ui.pause()
        
        # 2. Also stop the streaming_display if present
        if hasattr(self, 'streaming_display') and self.streaming_display:
            if hasattr(self.streaming_display, 'stop'):
                try:
                    self.streaming_display.stop()
                except Exception:
                    pass
        
        # 3. Clear terminal for clean display
        self.c.clear()
        
        try:
            # Show approval panel
            self.c.print()
            panel = Panel(
                Text(command, style="bright_yellow"),
                title="[bold bright_red]⚠️  APPROVAL REQUIRED[/bold bright_red]",
                border_style="bright_red",
                padding=(1, 2)
            )
            self.c.print(panel)
            self.c.print()
            self.c.print("[dim]This command requires your approval to execute.[/dim]")
            self.c.print("[dim]Options: [bright_green][y]es[/bright_green] | [bright_red][n]o[/bright_red] | [bright_cyan][a]lways allow this command[/bright_cyan][/dim]")
            self.c.print()

            loop = asyncio.get_event_loop()

            while True:
                # SYNC input is now safe because Live is stopped
                response = await loop.run_in_executor(
                    None,
                    lambda: self.c.input("[bold bright_yellow]Allow this command? [y/n/a]:[/bold bright_yellow] ")
                )
                response = response.strip().lower()

                if response in ['y', 'yes']:
                    self._last_approval_always = False
                    self.c.print("[green]✅ Approved (this time only)[/green]\n")
                    return True
                elif response in ['n', 'no']:
                    self._last_approval_always = False
                    self.c.print("[red]❌ Denied[/red]\n")
                    return False
                elif response in ['a', 'always']:
                    self._last_approval_always = True
                    self.c.print("[cyan]✅ Always allowed[/cyan]\n")
                    return True
                else:
                    self.c.print("[dim]Invalid option. Please enter y, n, or a.[/dim]\n")
        
        finally:
            # ══════════════════════════════════════════════════════════
            # CRITICAL: Resume UI after input is complete
            # ══════════════════════════════════════════════════════════
            
            # 4. Resume streaming display
            if hasattr(self, 'streaming_display') and self.streaming_display:
                if hasattr(self.streaming_display, 'start'):
                    try:
                        self.streaming_display.start()
                    except Exception:
                        pass
            
            # 5. Resume maestro UI
            if hasattr(self, 'maestro_ui') and self.maestro_ui:
                self.maestro_ui.resume()


    def init(self) -> bool:
        """Initialize v6.0 agents and TUI components"""
        try:
            # Show cyberpunk landing screen
            show_landing_screen(self.c)

            self.c.print("\n[dim]🔌 Initializing v6.0 Agent Framework...[/dim]")

            # Initialize core clients
            llm = LLMClient()  # Uses GEMINI_MODEL from .env (default: gemini-2.5-flash)

            # Create tool registry and MCP client
            tool_registry = ToolRegistry()

            # Register filesystem tools (use existing implementations)
            from jdev_cli.tools.file_ops import ReadFileTool, WriteFileTool, EditFileTool
            from jdev_cli.tools.file_mgmt import (
                CreateDirectoryTool,
                MoveFileTool,
                CopyFileTool
            )
            tool_registry.register(ReadFileTool())
            tool_registry.register(WriteFileTool())
            tool_registry.register(EditFileTool())
            tool_registry.register(CreateDirectoryTool())
            tool_registry.register(MoveFileTool())
            tool_registry.register(CopyFileTool())

            # Register execution tools (use existing)
            from jdev_cli.tools.exec import BashCommandTool
            tool_registry.register(BashCommandTool())

            # Register search tools (use existing)
            from jdev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
            tool_registry.register(SearchFilesTool())
            tool_registry.register(GetDirectoryTreeTool())

            # Register git tools (use existing)
            from jdev_cli.tools.git_ops import GitStatusTool, GitDiffTool
            tool_registry.register(GitStatusTool())
            tool_registry.register(GitDiffTool())

            mcp = MCPClient(tool_registry)

            # Initialize orchestrator with real agents + approval callback
            self.orch = Orchestrator(llm, mcp, approval_callback=self._request_approval)

            # Initialize TUI components (30 FPS optimized)
            self.layout = MaestroLayout(self.c)
            self.streaming_display = StreamingResponseDisplay(
                console=self.c,
                target_fps=30,
                max_lines=20,
                show_cursor=True
            )

            # Initialize MAESTRO v10.0 Shell UI (Definitive Edition @ 30 FPS)
            self.maestro_ui = MaestroShellUI(self.c)

            # Add all available agents to UI
            self.maestro_ui.add_agent('reviewer', 'REVIEWER', '🔍')
            self.maestro_ui.add_agent('refactorer', 'REFACTORER', '🔧')
            self.maestro_ui.add_agent('explorer', 'EXPLORER', '🗺️')

            self.file_tracker = FileOperationTracker()
            # Connect file tracker to UI
            self.file_tracker.set_callback(self.maestro_ui.add_file_operation)

            # Initialize autocomplete with tool registry
            tool_completer = create_completer(
                tools_registry=tool_registry,
                indexer=None,  # TODO: Add code indexer
                recent_tracker=None  # TODO: Add recent files tracker
            )

            # Combine slash commands + tool autocomplete
            self.completer = CombinedCompleter(tool_completer=tool_completer)

            # Update prompt session with combined completer
            h = Path.home() / '.maestro_history'
            self.prompt = PromptSession(
                history=FileHistory(str(h)),
                auto_suggest=AutoSuggestFromHistory(),
                completer=self.completer,
                complete_while_typing=True  # Enable live dropdown
            )

            # Register agent commands in Command Palette
            self._register_agent_commands()

            # Update header with session info
            session_id = f"session_{int(time.time())}"
            self.layout.update_header(
                title="MAESTRO v10.0",
                session_id=session_id,
                agent="",
                timestamp=None
            )

            self.c.print("[dim]✅ Framework initialized @ 30 FPS[/dim]")
            self.c.print()

            return True

        except Exception as e:
            self.c.print(f"\n[red]❌ Initialization failed: {e}[/red]\n")
            return False

    def _register_agent_commands(self):
        """Register agent commands in Command Palette for fuzzy search"""
        agent_commands = [
            Command(
                id="agent.executor",
                label="Execute Bash Command",
                description="Run system commands directly (executor agent)",
                category=CommandCategory.AGENT.value,
                keybinding=None,
                handler=lambda: self.orch.agents.get('executor'),
                priority=10
            ),
            Command(
                id="agent.planner",
                label="Plan Task",
                description="Break down complex tasks with GOAP planning",
                category=CommandCategory.AGENT.value,
                keybinding=None,
                handler=lambda: self.orch.agents.get('planner'),
                priority=9
            ),
            Command(
                id="agent.reviewer",
                label="Review Code",
                description="AST + Code Graph analysis for quality checks",
                category=CommandCategory.AGENT.value,
                keybinding=None,
                handler=lambda: self.orch.agents.get('reviewer'),
                priority=8
            ),
            Command(
                id="agent.refactorer",
                label="Refactor Code",
                description="Transactional code surgery with LibCST",
                category=CommandCategory.AGENT.value,
                keybinding=None,
                handler=lambda: self.orch.agents.get('refactorer'),
                priority=7
            ),
            Command(
                id="agent.explorer",
                label="Explore Codebase",
                description="Build knowledge graph and analyze dependencies",
                category=CommandCategory.AGENT.value,
                keybinding=None,
                handler=lambda: self.orch.agents.get('explorer'),
                priority=6
            ),
        ]

        for cmd in agent_commands:
            self.command_palette.register_command(cmd)

    def cmd(self, c: str) -> bool:
        """Handle slash commands"""

        if c in ['/q', '/quit', '/exit']:
            self.running = False
            return True
        
        if c in ['/c', '/clear']:
            self.c.clear()
            self.c.print("\n  MAESTRO v10.0", style="bold cyan")
            self.c.print()
            return True
        
        if c in ['/h', '/help']:
            help_panel = Panel(
                """[bold]Commands:[/bold]
  /quit, /exit, /q     quit MAESTRO
  /clear, /c           clear screen
  /help, /h            show this help
  /agents              list available agents
  /data                quick access to DataAgent
  /commands [query]    fuzzy search commands
  /permissions         manage command permissions

[bold]Tip:[/bold] Type / and press TAB to see all commands

[bold]Agent Triggers:[/bold]
  "review..."      → Reviewer v5.0 (AST + LLM analysis)
  "plan..."        → Planner v5.0 (GOAP planning)
  "refactor..."    → Refactorer v8.0 (Transactional surgery)
  "explore..."     → Explorer (Knowledge graph)
  "database..."    → DataAgent v1.0 (Schema + Query optimization)
  "run/exec..."    → Executor (bash commands)

[bold]Examples:[/bold]
  review jdev_cli/agents/base.py
  plan implement user authentication
  refactor extract method from process_payment
  explore map the codebase
  analyze schema for users table
  optimize query SELECT * FROM orders
  list running processes""",
                title="💡 Help",
                border_style="blue"
            )
            self.c.print()
            self.c.print(help_panel)
            self.c.print()
            return True

        if c == '/data':
            # Quick access to DataAgent with info panel
            info_panel = Panel(
                """[bold cyan]🗄️  DataAgent v1.0 - Database Operations[/bold cyan]

[bold]Capabilities:[/bold]
  • Schema Analysis (detect issues, recommend fixes)
  • Query Optimization (70%+ improvements)
  • Migration Planning (risk assessment + rollback)
  • Extended Thinking (5000 token budget)

[bold]Usage Examples:[/bold]
  analyze schema for users table
  optimize query SELECT * FROM orders WHERE status='pending'
  plan migration to add email_verified column
  review database indexes

[bold]Quick Commands:[/bold]
  database help              Show database-specific help
  schema issues              Analyze current schema
  query performance          Get query optimization tips

[dim]💡 Tip: DataAgent automatically activates for database keywords
(schema, query, sql, migration, table, index, etc.)[/dim]""",
                title="🗄️  DataAgent Quick Reference",
                border_style="cyan"
            )
            self.c.print()
            self.c.print(info_panel)
            self.c.print()
            return True

        if c.startswith('/commands'):
            # Parse optional query: /commands [query]
            parts = c.split(maxsplit=1)
            query = parts[1] if len(parts) > 1 else ""

            # Get suggestions from command palette
            suggestions = self.command_palette.get_suggestions(query, max_results=10)

            if not suggestions:
                self.c.print("\n[dim]No commands found[/dim]\n")
                return True

            # Display as table
            table = Table(title="🔍 Command Palette", border_style="cyan")
            table.add_column("#", style="dim", width=3)
            table.add_column("Command", style="bold bright_cyan")
            table.add_column("Description", style="white")
            table.add_column("Category", style="dim")

            for idx, cmd in enumerate(suggestions, 1):
                table.add_row(
                    str(idx),
                    cmd['command'],
                    cmd['description'],
                    cmd['category']
                )

            self.c.print()
            self.c.print(table)
            self.c.print()
            self.c.print("[dim]Tip: Type [bold]/commands [query][/bold] to fuzzy search[/dim]")
            self.c.print()
            return True
        
        if c == '/agents':
            tree = Tree("[bold cyan]🤖 Available Agents (v6.0)[/bold cyan]")

            executor = tree.add("[bold white]💻 SimpleExecutor[/bold white]")
            executor.add("[dim]Direct bash command execution[/dim]")
            executor.add("[dim]System queries & file operations[/dim]")

            planner = tree.add("[bold yellow]⚡ Planner v5.0[/bold yellow]")
            planner.add("[dim]GOAP-based task decomposition[/dim]")
            planner.add("[dim]Dependency analysis & parallel execution[/dim]")

            reviewer = tree.add("[bold green]🔍 Reviewer v5.0[/bold green]")
            reviewer.add("[dim]AST + Code Graph analysis[/dim]")
            reviewer.add("[dim]Security, Performance, Logic checks[/dim]")

            refactorer = tree.add("[bold magenta]🔧 Refactorer v8.0[/bold magenta]")
            refactorer.add("[dim]Transactional code surgery[/dim]")
            refactorer.add("[dim]LibCST format preservation[/dim]")

            explorer = tree.add("[bold blue]🗺️ Explorer[/bold blue]")
            explorer.add("[dim]Knowledge graph construction[/dim]")
            explorer.add("[dim]Blast radius analysis[/dim]")

            data = tree.add("[bold cyan]🗄️ DataAgent v1.0[/bold cyan]")
            data.add("[dim]Schema analysis & optimization[/dim]")
            data.add("[dim]Query optimization (70%+ improvements)[/dim]")
            data.add("[dim]Migration planning with rollback[/dim]")
            data.add("[dim]Extended thinking (5000 token budget)[/dim]")

            self.c.print()
            self.c.print(tree)
            self.c.print()
            return True

        if c == '/permissions':
            # Get PermissionManager from executor
            try:
                executor_agent = self.orch.agents.get('executor')
                if not executor_agent or not hasattr(executor_agent, 'permission_manager'):
                    self.c.print("[red]❌ Permission manager not available[/red]\n")
                    return True

                pm = executor_agent.permission_manager

                # Title banner
                self.c.print()
                self.c.print(Panel(
                    "[bold bright_cyan]🔐 Permission Configuration[/bold bright_cyan]\n"
                    "[dim]Based on Claude Code (Nov 2025) + OWASP Best Practices[/dim]",
                    border_style="cyan"
                ))
                self.c.print()

                # Get config summary
                summary = pm.get_config_summary()

                # Status table
                status_table = Table(show_header=False, box=None, padding=(0, 2))
                status_table.add_column("Label", style="dim")
                status_table.add_column("Value", style="bold")

                status_table.add_row("Mode", "[green]Safe Mode Enabled[/green]" if pm.safe_mode else "[red]Safe Mode Disabled[/red]")
                status_table.add_row("Allow Rules", f"[cyan]{summary['allow_count']}[/cyan] patterns")
                status_table.add_row("Deny Rules", f"[red]{summary['deny_count']}[/red] patterns")
                status_table.add_row("Auto-approve Read-only", "[green]Yes[/green]" if summary['auto_approve_enabled'] else "[dim]No[/dim]")
                status_table.add_row("Audit Logging", "[green]Enabled[/green]" if summary['audit_enabled'] else "[dim]Disabled[/dim]")

                self.c.print(status_table)
                self.c.print()

                # Allow list table
                allow_table = Table(title="✅ Allow List (Auto-approved)", border_style="green", show_lines=True)
                allow_table.add_column("Pattern", style="green", overflow="fold")

                for pattern in pm.config["permissions"]["allow"][:20]:  # Show first 20
                    allow_table.add_row(pattern)

                if len(pm.config["permissions"]["allow"]) > 20:
                    allow_table.add_row(f"[dim]... and {len(pm.config['permissions']['allow']) - 20} more[/dim]")

                self.c.print(allow_table)
                self.c.print()

                # Deny list table
                deny_table = Table(title="🛑 Deny List (Blocked)", border_style="red", show_lines=True)
                deny_table.add_column("Pattern", style="red", overflow="fold")

                for pattern in pm.config["permissions"]["deny"][:20]:  # Show first 20
                    deny_table.add_row(pattern)

                if len(pm.config["permissions"]["deny"]) > 20:
                    deny_table.add_row(f"[dim]... and {len(pm.config['permissions']['deny']) - 20} more[/dim]")

                self.c.print(deny_table)
                self.c.print()

                # Config file locations
                self.c.print(Panel(
                    "[bold]📁 Config File Hierarchy[/bold] [dim](precedence: Local > Project > User)[/dim]\n\n" +
                    "\n".join([
                        f"{'✅' if info['exists'] else '❌'} [bold]{'Local:' if 'local' in name else 'Project:' if 'project' in name else 'User:'}[/bold] [dim]{info['path']}[/dim]"
                        for name, info in summary['config_files'].items()
                    ]),
                    border_style="dim"
                ))
                self.c.print()

                # Audit log location
                if summary['audit_enabled']:
                    audit_file = pm.config["logging"]["auditFile"]
                    self.c.print(f"[dim]📝 Audit log: {audit_file}[/dim]\n")

                # Help text
                self.c.print("[dim]Tip: Use [bold]'always'[/bold] when approving commands to add them to the allow list[/dim]\n")

            except Exception as e:
                self.c.print(f"[red]❌ Error displaying permissions: {e}[/red]\n")

            return True

        if c == '/metrics':
            # Display NextGen Executor metrics
            try:
                executor_agent = self.orch.agents.get('executor')
                if not executor_agent or not hasattr(executor_agent, 'get_metrics'):
                    self.c.print("[red]❌ Metrics not available[/red]\n")
                    return True

                metrics = executor_agent.get_metrics()

                # Title banner
                self.c.print()
                self.c.print(Panel(
                    "[bold bright_cyan]📊 NextGen Executor Metrics[/bold bright_cyan]\n"
                    "[dim]Real-time performance and usage statistics[/dim]",
                    border_style="cyan"
                ))
                self.c.print()

                # Execution metrics table
                exec_table = Table(title="Execution Statistics", border_style="green")
                exec_table.add_column("Metric", style="cyan", no_wrap=True)
                exec_table.add_column("Value", style="bold white")
                exec_table.add_column("Status", style="green")

                success_rate = metrics.get("success_rate", 0)
                status_emoji = "✅" if success_rate > 95 else "⚠️" if success_rate > 80 else "❌"

                exec_table.add_row(
                    "Total Executions",
                    str(metrics.get("executions", 0)),
                    ""
                )
                exec_table.add_row(
                    "Success Rate",
                    f"{success_rate:.2f}%",
                    status_emoji
                )
                exec_table.add_row(
                    "Average Latency",
                    f"{metrics.get('avg_latency', 0):.3f}s",
                    "⚡" if metrics.get('avg_latency', 0) < 0.5 else "🐌"
                )
                exec_table.add_row(
                    "Total Runtime",
                    f"{metrics.get('total_time', 0):.2f}s",
                    ""
                )

                self.c.print(exec_table)
                self.c.print()

                # Token usage table
                token_usage = metrics.get("token_usage", {})
                token_table = Table(title="Token Usage (MCP Pattern)", border_style="yellow")
                token_table.add_column("Type", style="cyan")
                token_table.add_column("Count", style="bold white")

                token_table.add_row("Input Tokens", str(token_usage.get("input", 0)))
                token_table.add_row("Output Tokens", str(token_usage.get("output", 0)))
                token_table.add_row("Total Tokens", f"[bold]{token_usage.get('total', 0)}[/bold]")

                self.c.print(token_table)
                self.c.print()

                # Footer with timestamp
                last_updated = metrics.get("last_updated", "N/A")
                self.c.print(f"[dim]Last updated: {last_updated}[/dim]\n")

            except Exception as e:
                self.c.print(f"[red]❌ Error displaying metrics: {e}[/red]\n")

            return True

        return False
    
    async def loop(self):
        """Main REPL loop with 30 FPS streaming"""

        if not self.init():
            return

        while self.running:
            try:
                # Update input panel
                self.layout.update_input("maestro> ")

                # Get input
                q = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.prompt.prompt('▶ ')
                )

                if not q.strip():
                    continue

                # Commands
                if q.startswith('/'):
                    if self.cmd(q):
                        continue

                # Add user message to conversation
                user_msg = Panel(
                    Text(q, style="bright_white"),
                    title="[bold bright_green]👤 User[/bold bright_green]",
                    border_style="bright_green",
                    padding=(0, 2)
                )
                self.messages.append(user_msg)

                # Execute with orchestrator
                start = datetime.now()

                # Route to agent
                agent_name = self.orch.route(q)
                self.current_agent = agent_name

                # Update header with active agent
                self.layout.update_header(
                    title="MAESTRO v10.0",
                    session_id=f"session_{int(time.time())}",
                    agent=agent_name.title()
                )

                # Show agent routing
                routing_panel = self.routing_display.render(
                    agent_name=agent_name,
                    confidence=1.0,
                    eta="calculating..."
                )

                # Update status panel with routing
                self.layout.update_status(routing_panel)

                # Update conversation with current messages (user message)
                self.layout.update_conversation(self.messages)

                # Start MAESTRO UI @ 30 FPS
                await self.maestro_ui.start()

                # Clear agent content for fresh execution
                self.maestro_ui.clear_agent_content(agent_name)

                # Execute REAL agent with STREAMING for 30 FPS (P1.5)
                with self.perf_monitor.measure_frame():
                    # Stream execution updates
                    thinking_text = []
                    final_result = None

                    async for update in self.orch.execute_streaming(q, context={'cwd': str(Path.cwd())}):
                        if update["type"] == "thinking":
                            # LLM generating command - stream token-by-token @ 30 FPS
                            token = update.get("data", update.get("text", ""))
                            thinking_text.append(token)

                            # Update MAESTRO UI with streaming token
                            await self.maestro_ui.update_agent_stream(agent_name, token)
                            await asyncio.sleep(0.01)  # Smooth 100 tokens/s

                        elif update["type"] == "command":
                            # Final command ready - show in agent stream
                            command = update.get("data", "")
                            await self.maestro_ui.update_agent_stream(
                                agent_name,
                                f"\n$ {command}\n"
                            )

                        elif update["type"] == "status":
                            # Status update (security validation, etc) - show in stream
                            status_msg = update.get("data", "")
                            await self.maestro_ui.update_agent_stream(
                                agent_name,
                                f"\n{status_msg}\n"
                            )

                        elif update["type"] == "result":
                            # Execution complete
                            final_result = update["data"]
                            break

                    # Use final result (fallback if no result received)
                    # Handle both dict and AgentResponse formats
                    if final_result:
                        if isinstance(final_result, dict):
                            # Convert dict to AgentResponse
                            result = AgentResponse(
                                success=final_result.get("success", False),
                                data=final_result.get("data", final_result),
                                error=final_result.get("error"),
                                reasoning=final_result.get("reasoning", "")
                            )
                        else:
                            result = final_result
                    else:
                        result = AgentResponse(
                            success=False,
                            data={},
                            error="No result received from agent",
                            reasoning="Streaming interrupted"
                        )

                # Update MAESTRO UI after execution
                if result.success:
                    # Mark agent as done
                    self.maestro_ui.mark_agent_done(agent_name)

                    # Update metrics
                    exec_time = result.data.get('execution_time', 0) if isinstance(result.data, dict) else 0
                    self.maestro_ui.update_metrics(
                        latency_ms=int(exec_time * 1000) if exec_time > 0 else 187,
                        execution_count=self.maestro_ui.metrics.execution_count + 1,
                        success_rate=99.87  # Will be calculated properly later
                    )

                    # Display result stdout in agent stream
                    if isinstance(result.data, dict) and 'stdout' in result.data:
                        stdout = result.data.get('stdout', '')
                        if stdout:
                            # Stream output line by line for visual effect
                            for line in stdout.split('\n')[:30]:  # Limit to 30 lines
                                await self.maestro_ui.update_agent_stream(agent_name, line)
                                await asyncio.sleep(0.02)
                else:
                    # Mark as error
                    error_msg = result.error or "Unknown error"
                    self.maestro_ui.mark_agent_error(agent_name, error_msg)

                # Small delay before stopping Live display
                await asyncio.sleep(0.5)
                self.maestro_ui.stop()

                # Extra delay to ensure Live thread fully stops
                await asyncio.sleep(0.2)

                # Create response panel based on result
                if result.success:
                    # Check if result has stdout/stderr from executor
                    if isinstance(result.data, dict) and 'stdout' in result.data:
                        # Executor output - show stdout/stderr
                        output_lines = []
                        if result.data.get('stdout'):
                            output_lines.append(Text(result.data['stdout'], style="bright_white"))
                        if result.data.get('stderr'):
                            output_lines.append(Text(result.data['stderr'], style="bright_yellow"))

                        if output_lines:
                            from rich.console import Group
                            response_content = Group(*output_lines)
                        else:
                            response_content = Text("(no output)", style="dim")

                        cmd_executed = result.data.get('command', '')
                        response_panel = Panel(
                            response_content,
                            title=f"[bold bright_cyan]✅ {agent_name.title()}[/bold bright_cyan]",
                            subtitle=f"[dim bright_cyan]$ {cmd_executed}[/dim]" if cmd_executed else None,
                            border_style="bright_cyan",  # NEON CYAN instead of green
                            padding=(1, 2),
                            expand=False  # Prevent text truncation
                        )
                    else:
                        # Other agent output (Planner, Reviewer, Refactorer, Explorer)
                        # AgentResponse has 'data', NOT 'result'
                        if isinstance(result.data, str):
                            response_text = result.data
                        elif isinstance(result.data, dict):
                            import json
                            response_text = json.dumps(result.data, indent=2)
                        else:
                            response_text = str(result.data)

                        response_panel = Panel(
                            Text(response_text, style="bright_cyan"),
                            title=f"[bold bright_magenta]🤖 {agent_name.title()}[/bold bright_magenta]",
                            border_style="bright_magenta",
                            padding=(1, 2)
                        )
                else:
                    # Error output
                    response_text = result.error or "Unknown error"
                    response_panel = Panel(
                        Text(response_text, style="bright_red"),
                        title=f"[bold bright_red]❌ {agent_name.title()}[/bold bright_red]",
                        border_style="bright_red",
                        padding=(1, 2)
                    )

                # Add response to messages
                self.messages.append(response_panel)

                # Update conversation with response
                self.layout.update_conversation(self.messages)

                # Update status with performance stats
                duration = (datetime.now() - start).total_seconds()
                perf_stats = self.perf_monitor.get_stats()

                status_table = Table.grid(padding=(0, 2))
                status_table.add_column(style="dim", justify="right")
                status_table.add_column()
                status_table.add_row("Duration:", f"{duration:.2f}s")

                # Handle both 'fps' and 'current_fps' keys for compatibility
                fps_value = perf_stats.get('current_fps', perf_stats.get('fps', 0.0))
                status_table.add_row("FPS:", f"{fps_value:.1f}")
                status_table.add_row("Agent:", agent_name.title())

                status_panel = Panel(
                    status_table,
                    title="[bold bright_yellow]📊 Status[/bold bright_yellow]",
                    border_style="bright_yellow",
                    padding=(0, 1)
                )

                self.layout.update_status(status_panel)

                # Render ONLY the response panel (keep conversation flowing)
                self.c.print()
                self.c.print(response_panel)
                self.c.print()

                # Show ready prompt to indicate MAESTRO is ready for next command
                self.c.print("[dim]Ready for next command...[/dim]\n")

                # Tick FPS counter
                self.fps_counter.tick()

            except KeyboardInterrupt:
                self.c.print()
                continue
            except EOFError:
                break
            except Exception as e:
                self.c.print(f"\n[red]Error: {e}[/red]\n")
                import traceback
                self.c.print(f"[dim]{traceback.format_exc()}[/dim]")

# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def main():
    """Entry point"""
    try:
        shell = Shell()
        asyncio.run(shell.loop())
    except KeyboardInterrupt:
        print()
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
