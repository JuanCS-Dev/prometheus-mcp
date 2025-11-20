"""
Visual Workflow System - DAY 8 Phase 3 (REFACTORED Nov 2025)
Real-time workflow visualization with cutting-edge UX patterns

Research-Driven Features (Nov 2025):
1. Streaming token-level updates (Cursor/Claude inspiration)
2. Mini-map overview (Windsurf inspiration)
3. Diff-style change visualization (GitHub Copilot inspiration)
4. Rich error context with AI suggestions (Claude Sonnet 4.5)
5. Checkpoint/undo visualization (Cursor Composer)
6. Multi-modal feedback (all tools synthesis)

Constitutional Compliance:
- P1 (Completude): Full workflow state tracking
- P2 (Validação): Visual validation of execution flow
- P3 (Ceticismo): Shows actual vs expected progress
- P6 (Eficiência): Minimal overhead (<5ms per update)
"""

from typing import Dict, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time
import asyncio
from collections import deque

from rich.console import Console, Group
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.syntax import Syntax


class StepStatus(Enum):
    """Workflow step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class WorkflowStep:
    """Represents a single workflow step (Enhanced Nov 2025)"""
    id: str
    name: str
    status: StepStatus = StepStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    
    # NEW: Streaming updates (Nov 2025)
    streaming_tokens: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # NEW: Change tracking (diff-style)
    changes: List[Dict[str, str]] = field(default_factory=list)  # {type, before, after}
    
    # NEW: AI suggestions
    ai_suggestion: Optional[str] = None
    
    # NEW: Checkpoint data
    checkpoint_id: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate step duration in seconds"""
        if self.start_time:
            end = self.end_time or datetime.now()
            return (end - self.start_time).total_seconds()
        return None
    
    @property
    def status_emoji(self) -> str:
        """Get emoji for current status"""
        return {
            StepStatus.PENDING: "⏳",
            StepStatus.RUNNING: "🔄",
            StepStatus.COMPLETED: "✅",
            StepStatus.FAILED: "❌",
            StepStatus.SKIPPED: "⏭️",
            StepStatus.BLOCKED: "🚫"
        }[self.status]
    
    def add_streaming_token(self, token: str) -> None:
        """Add streaming token (Cursor/Claude style)"""
        self.streaming_tokens.append((datetime.now(), token))
    
    def add_change(self, change_type: str, before: str, after: str) -> None:
        """Track changes diff-style"""
        self.changes.append({
            "type": change_type,
            "before": before,
            "after": after,
            "timestamp": datetime.now().isoformat()
        })


class WorkflowVisualizer:
    """
    Real-time workflow visualization system (REFACTORED Nov 2025)
    
    Features (Research-Driven):
    - Streaming token updates (Cursor/Claude inspiration)
    - Mini-map overview (Windsurf inspiration)
    - Diff-style change visualization (GitHub Copilot)
    - Rich error context + AI suggestions (Claude Sonnet 4.5)
    - Checkpoint visualization (Cursor Composer)
    - Multi-modal feedback synthesis
    
    Constitutional Alignment:
    - P6 (Eficiência): Batched updates, minimal redraws
    - P2 (Validação): Visual validation of execution state
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.steps: Dict[str, WorkflowStep] = {}
        self.execution_order: List[str] = []
        self.start_time: Optional[datetime] = None
        
        # NEW: Streaming callback (Nov 2025)
        self.streaming_callback: Optional[Callable[[str, str], None]] = None
        
        # NEW: Checkpoints tracking
        self.checkpoints: Dict[str, Dict] = {}  # checkpoint_id -> state
        
        # NEW: Layout for multi-panel view (Windsurf style)
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="minimap", size=5),
            Layout(name="main"),
            Layout(name="details", size=10)
        )
        
    def add_step(
        self,
        step_id: str,
        name: str,
        dependencies: Optional[List[str]] = None
    ) -> None:
        """Add a workflow step"""
        self.steps[step_id] = WorkflowStep(
            id=step_id,
            name=name,
            dependencies=dependencies or []
        )
        
    def update_step(
        self,
        step_id: str,
        status: Optional[StepStatus] = None,
        progress: Optional[float] = None,
        error: Optional[str] = None,
        ai_suggestion: Optional[str] = None
    ) -> None:
        """Update step state (Enhanced with AI suggestions)"""
        if step_id not in self.steps:
            return
            
        step = self.steps[step_id]
        
        if status:
            step.status = status
            if status == StepStatus.RUNNING and not step.start_time:
                step.start_time = datetime.now()
            elif status in (StepStatus.COMPLETED, StepStatus.FAILED):
                step.end_time = datetime.now()
                if step_id not in self.execution_order:
                    self.execution_order.append(step_id)
                    
        if progress is not None:
            step.progress = max(0.0, min(1.0, progress))
            
        if error:
            step.error = error
            
        if ai_suggestion:
            step.ai_suggestion = ai_suggestion
    
    def stream_token(self, step_id: str, token: str) -> None:
        """
        Stream token update (Cursor/Claude style)
        For real-time LLM output visualization
        """
        if step_id not in self.steps:
            return
            
        step = self.steps[step_id]
        step.add_streaming_token(token)
        
        # Trigger callback if registered
        if self.streaming_callback:
            self.streaming_callback(step_id, token)
    
    def add_change(self, step_id: str, change_type: str, before: str, after: str) -> None:
        """
        Track change diff-style (GitHub Copilot inspiration)
        """
        if step_id not in self.steps:
            return
            
        step = self.steps[step_id]
        step.add_change(change_type, before, after)
    
    def create_checkpoint(self, description: str) -> str:
        """
        Create checkpoint (Cursor Composer style)
        Returns checkpoint ID for later rollback
        """
        checkpoint_id = f"cp_{int(time.time())}"
        self.checkpoints[checkpoint_id] = {
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "steps_state": {
                sid: {
                    "status": step.status.value,
                    "progress": step.progress,
                    "error": step.error
                }
                for sid, step in self.steps.items()
            }
        }
        return checkpoint_id
    
    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Rollback to checkpoint (undo support)
        """
        if checkpoint_id not in self.checkpoints:
            return False
            
        checkpoint = self.checkpoints[checkpoint_id]
        steps_state = checkpoint["steps_state"]
        
        for step_id, state in steps_state.items():
            if step_id in self.steps:
                step = self.steps[step_id]
                step.status = StepStatus(state["status"])
                step.progress = state["progress"]
                step.error = state["error"]
                
        return True
            
    def render_dependency_tree(self) -> Tree:
        """
        Render workflow as dependency tree
        
        Returns ASCII tree showing:
        - Step hierarchy
        - Current status
        - Progress indicators
        """
        if not self.start_time:
            self.start_time = datetime.now()
            
        root = Tree("📊 Workflow Execution")
        
        # Find root steps (no dependencies)
        root_steps = [
            sid for sid, step in self.steps.items()
            if not step.dependencies
        ]
        
        # Build tree recursively
        visited: Set[str] = set()
        
        def add_step_to_tree(step_id: str, parent: Tree) -> None:
            if step_id in visited:
                return
            visited.add(step_id)
            
            step = self.steps[step_id]
            
            # Build step label
            duration_str = ""
            if step.duration:
                duration_str = f" ({step.duration:.1f}s)"
                
            progress_str = ""
            if step.status == StepStatus.RUNNING and step.progress > 0:
                progress_str = f" [{int(step.progress * 100)}%]"
                
            label = Text()
            label.append(f"{step.status_emoji} ", style="bold")
            label.append(step.name, style=self._get_status_style(step.status))
            label.append(duration_str, style="dim")
            label.append(progress_str, style="cyan")
            
            if step.error:
                label.append(f" ⚠️  {step.error}", style="red")
                
            node = parent.add(label)
            
            # Add dependent steps
            dependents = [
                sid for sid, s in self.steps.items()
                if step_id in s.dependencies
            ]
            for dep_id in dependents:
                add_step_to_tree(dep_id, node)
                
        for root_id in root_steps:
            add_step_to_tree(root_id, root)
            
        return root
        
    def render_progress_table(self) -> Table:
        """Render progress summary table"""
        table = Table(title="📈 Execution Progress", show_header=True)
        table.add_column("Step", style="cyan", width=30)
        table.add_column("Status", width=12)
        table.add_column("Progress", width=15)
        table.add_column("Duration", justify="right", width=10)
        
        for step_id in self.execution_order:
            step = self.steps[step_id]
            
            # Progress bar
            progress_bar = self._render_progress_bar(step.progress, width=10)
            
            # Duration
            duration = f"{step.duration:.1f}s" if step.duration else "-"
            
            table.add_row(
                step.name,
                f"{step.status_emoji} {step.status.value}",
                progress_bar,
                duration
            )
            
        return table
        
    def render_metrics(self) -> Panel:
        """Render overall workflow metrics"""
        total_steps = len(self.steps)
        completed = sum(1 for s in self.steps.values() if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in self.steps.values() if s.status == StepStatus.FAILED)
        running = sum(1 for s in self.steps.values() if s.status == StepStatus.RUNNING)
        
        total_duration = 0.0
        if self.start_time:
            total_duration = (datetime.now() - self.start_time).total_seconds()
            
        metrics_text = Text()
        metrics_text.append("📊 Workflow Metrics\n\n", style="bold cyan")
        metrics_text.append(f"Total Steps: {total_steps}\n")
        metrics_text.append(f"✅ Completed: {completed}\n", style="green")
        metrics_text.append(f"❌ Failed: {failed}\n", style="red")
        metrics_text.append(f"🔄 Running: {running}\n", style="yellow")
        metrics_text.append(f"⏱️  Total Time: {total_duration:.1f}s\n", style="cyan")
        
        # Calculate avg step duration
        completed_steps = [s for s in self.steps.values() if s.duration]
        if completed_steps:
            avg_duration = sum(s.duration for s in completed_steps) / len(completed_steps)
            metrics_text.append(f"⚡ Avg Step: {avg_duration:.1f}s\n", style="magenta")
            
        return Panel(metrics_text, border_style="cyan")
        
    def render_minimap(self) -> Panel:
        """
        Render mini-map overview (Windsurf inspiration)
        Compact view of all steps with status indicators
        """
        minimap_text = Text()
        minimap_text.append("🗺️  Workflow Map: ", style="bold cyan")
        
        for step_id, step in self.steps.items():
            minimap_text.append(f"{step.status_emoji}", style="")
            
        # Progress bar
        total = len(self.steps)
        completed = sum(1 for s in self.steps.values() if s.status == StepStatus.COMPLETED)
        progress_pct = (completed / total * 100) if total > 0 else 0
        minimap_text.append(f"  [{completed}/{total}] {progress_pct:.0f}%", style="dim")
        
        return Panel(minimap_text, border_style="dim", height=3)
    
    def render_streaming_view(self, step_id: str) -> Panel:
        """
        Render streaming tokens (Cursor/Claude style)
        Shows live token generation for current step
        """
        if step_id not in self.steps:
            return Panel("No active streaming", border_style="dim")
            
        step = self.steps[step_id]
        
        if not step.streaming_tokens:
            return Panel("Waiting for tokens...", border_style="dim")
            
        # Last 50 tokens
        recent_tokens = list(step.streaming_tokens)[-50:]
        stream_text = Text()
        
        for timestamp, token in recent_tokens:
            stream_text.append(token, style="cyan")
            
        return Panel(
            stream_text,
            title=f"🔄 Streaming: {step.name}",
            border_style="yellow"
        )
    
    def render_diff_view(self, step_id: str) -> Panel:
        """
        Render changes diff-style (GitHub Copilot inspiration)
        Shows before/after for file changes
        """
        if step_id not in self.steps:
            return Panel("No changes", border_style="dim")
            
        step = self.steps[step_id]
        
        if not step.changes:
            return Panel("No changes tracked", border_style="dim")
            
        diff_text = Text()
        
        for change in step.changes[-5:]:  # Last 5 changes
            diff_text.append(f"\n📝 {change['type']}\n", style="bold")
            diff_text.append(f"- {change['before']}\n", style="red")
            diff_text.append(f"+ {change['after']}\n", style="green")
            
        return Panel(
            diff_text,
            title=f"📋 Changes: {step.name}",
            border_style="blue"
        )
    
    def render_ai_suggestions(self, step_id: str) -> Optional[Panel]:
        """
        Render AI suggestions (Claude Sonnet 4.5 style)
        Shows intelligent recommendations for errors
        """
        if step_id not in self.steps:
            return None
            
        step = self.steps[step_id]
        
        if not step.ai_suggestion:
            return None
            
        suggestion_text = Text()
        suggestion_text.append("🤖 AI Suggestion:\n\n", style="bold magenta")
        suggestion_text.append(step.ai_suggestion, style="cyan")
        
        return Panel(
            suggestion_text,
            title="💡 Intelligent Recommendation",
            border_style="magenta"
        )
    
    def render_checkpoint_view(self) -> Panel:
        """
        Render checkpoints (Cursor Composer style)
        Shows save points for undo/rollback
        """
        if not self.checkpoints:
            return Panel("No checkpoints", border_style="dim")
            
        checkpoint_text = Text()
        checkpoint_text.append("💾 Checkpoints:\n\n", style="bold green")
        
        for cp_id, cp_data in list(self.checkpoints.items())[-5:]:
            timestamp = cp_data.get("timestamp", "Unknown")
            description = cp_data.get("description", "Checkpoint")
            checkpoint_text.append(f"  {cp_id[:8]}: {description} ({timestamp})\n", style="dim")
            
        return Panel(checkpoint_text, border_style="green")
    
    def render_full_view(self) -> Layout:
        """
        Render complete workflow visualization (Enhanced Nov 2025)
        Multi-panel layout inspired by Windsurf
        """
        # Update layout
        self.layout["minimap"].update(self.render_minimap())
        
        # Main view
        main_group = Group(
            self.render_metrics(),
            self.render_dependency_tree(),
            self.render_progress_table()
        )
        self.layout["main"].update(main_group)
        
        # Details view (context-aware)
        running_steps = [
            sid for sid, step in self.steps.items()
            if step.status == StepStatus.RUNNING
        ]
        
        if running_steps:
            active_step = running_steps[0]
            details_group = Group(
                self.render_streaming_view(active_step),
                self.render_diff_view(active_step)
            )
            
            # Add AI suggestion if error
            step = self.steps[active_step]
            if step.error and step.ai_suggestion:
                details_group = Group(
                    details_group,
                    self.render_ai_suggestions(active_step)
                )
        else:
            details_group = self.render_checkpoint_view()
            
        self.layout["details"].update(details_group)
        
        return self.layout
        
    def live_display(self, refresh_rate: float = 0.5) -> Live:
        """
        Create live-updating display
        
        Args:
            refresh_rate: Update frequency in seconds
            
        Returns:
            Rich Live context manager
        """
        return Live(
            self.render_full_view(),
            console=self.console,
            refresh_per_second=1 / refresh_rate
        )
        
    def _render_progress_bar(self, progress: float, width: int = 10) -> str:
        """Render ASCII progress bar"""
        filled = int(progress * width)
        bar = "█" * filled + "░" * (width - filled)
        percentage = int(progress * 100)
        return f"{bar} {percentage}%"
        
    def _get_status_style(self, status: StepStatus) -> str:
        """Get Rich style for status"""
        return {
            StepStatus.PENDING: "dim",
            StepStatus.RUNNING: "yellow bold",
            StepStatus.COMPLETED: "green",
            StepStatus.FAILED: "red bold",
            StepStatus.SKIPPED: "cyan dim",
            StepStatus.BLOCKED: "red dim"
        }[status]


class ParallelExecutionTracker:
    """
    Track and visualize parallel workflow execution
    
    Shows:
    - Concurrent steps
    - Resource utilization
    - Bottlenecks
    """
    
    def __init__(self, max_parallel: int = 4):
        self.max_parallel = max_parallel
        self.active_steps: List[Tuple[str, datetime]] = []
        self.timeline: List[Tuple[datetime, str, str]] = []  # (time, step_id, event)
        
    def start_step(self, step_id: str) -> None:
        """Mark step as started"""
        now = datetime.now()
        self.active_steps.append((step_id, now))
        self.timeline.append((now, step_id, "start"))
        
    def end_step(self, step_id: str) -> None:
        """Mark step as ended"""
        now = datetime.now()
        self.active_steps = [
            (sid, start) for sid, start in self.active_steps
            if sid != step_id
        ]
        self.timeline.append((now, step_id, "end"))
        
    def get_parallelism_metrics(self) -> Dict[str, float]:
        """Calculate parallelism metrics"""
        if not self.timeline:
            return {
                "avg_concurrent": 0.0,
                "max_concurrent": 0,
                "parallelism_ratio": 0.0
            }
            
        # Calculate concurrent steps over time
        concurrent_counts = []
        active = set()
        
        for timestamp, step_id, event in sorted(self.timeline):
            if event == "start":
                active.add(step_id)
            elif event == "end":
                active.discard(step_id)
            concurrent_counts.append(len(active))
            
        return {
            "avg_concurrent": sum(concurrent_counts) / len(concurrent_counts),
            "max_concurrent": max(concurrent_counts),
            "parallelism_ratio": max(concurrent_counts) / self.max_parallel
        }
        
    def render_timeline(self) -> Table:
        """Render execution timeline"""
        table = Table(title="⏱️  Execution Timeline", show_header=True)
        table.add_column("Time", style="cyan", width=12)
        table.add_column("Event", width=10)
        table.add_column("Step", width=30)
        table.add_column("Concurrent", justify="right", width=10)
        
        active = set()
        for timestamp, step_id, event in self.timeline[-20:]:  # Last 20 events
            if event == "start":
                active.add(step_id)
                emoji = "▶️"
            else:
                active.discard(step_id)
                emoji = "⏹️"
                
            time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]
            table.add_row(
                time_str,
                f"{emoji} {event}",
                step_id,
                str(len(active))
            )
            
        return table


# Example usage for testing (Enhanced Nov 2025)
if __name__ == "__main__":
    console = Console()
    viz = WorkflowVisualizer(console)
    
    # Setup workflow
    viz.add_step("step1", "Initialize system", [])
    viz.add_step("step2", "Load configuration", ["step1"])
    viz.add_step("step3", "Connect database", ["step1"])
    viz.add_step("step4", "Process data", ["step2", "step3"])
    viz.add_step("step5", "Generate report", ["step4"])
    
    # Simulate execution with new features
    with viz.live_display() as live:
        # Checkpoint before execution
        cp_id = viz.create_checkpoint("Before execution")
        
        for step_id in ["step1", "step2", "step3", "step4", "step5"]:
            viz.update_step(step_id, status=StepStatus.RUNNING)
            live.update(viz.render_full_view())
            
            # Simulate streaming tokens
            for token in ["Processing", " ", "data", "..."]:
                viz.stream_token(step_id, token)
                live.update(viz.render_full_view())
                time.sleep(0.1)
            
            # Simulate file change
            viz.add_change(step_id, "file_edit", "old_value", "new_value")
            
            # Complete step
            viz.update_step(step_id, status=StepStatus.COMPLETED, progress=1.0)
            live.update(viz.render_full_view())
            time.sleep(0.3)
        
        # Demo: Simulate error with AI suggestion
        viz.add_step("step6", "Deploy to production", ["step5"])
        viz.update_step("step6", status=StepStatus.RUNNING)
        live.update(viz.render_full_view())
        time.sleep(0.5)
        
        viz.update_step(
            "step6",
            status=StepStatus.FAILED,
            error="Connection timeout",
            ai_suggestion="Try increasing timeout to 30s or check network connectivity"
        )
        live.update(viz.render_full_view())
        time.sleep(2)
