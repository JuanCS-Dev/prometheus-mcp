"""
todo_tracker.py: Task Progress Tracking Component.

Inspired by Claude Code's TodoWrite feature.
Shows visual task progress with checkboxes and status.

Usage:
    tracker = TodoTracker()
    tracker.add("Implement feature X", status="in_progress")
    tracker.add("Write tests", status="pending")
    tracker.complete("Implement feature X")
    tracker.render()  # Shows visual checklist

Visual Output:
    ⎿  ☒ Implement feature X
       ☐ Write tests
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table


class TaskStatus(str, Enum):
    """Task status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# Status icons (Claude Code style)
STATUS_ICONS = {
    TaskStatus.PENDING: "☐",
    TaskStatus.IN_PROGRESS: "◐",
    TaskStatus.COMPLETED: "☒",
    TaskStatus.FAILED: "✗",
    TaskStatus.SKIPPED: "⊘",
}

STATUS_COLORS = {
    TaskStatus.PENDING: "dim",
    TaskStatus.IN_PROGRESS: "cyan",
    TaskStatus.COMPLETED: "green",
    TaskStatus.FAILED: "red",
    TaskStatus.SKIPPED: "yellow",
}


@dataclass
class Task:
    """A single task in the tracker."""
    content: str
    status: TaskStatus = TaskStatus.PENDING
    active_form: str = ""  # Present continuous form (e.g., "Implementing...")
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    parent_id: Optional[str] = None  # For subtasks

    @property
    def id(self) -> str:
        """Generate unique ID from content."""
        return self.content[:50].replace(" ", "_").lower()

    @property
    def icon(self) -> str:
        """Get status icon."""
        return STATUS_ICONS.get(self.status, "?")

    @property
    def color(self) -> str:
        """Get status color."""
        return STATUS_COLORS.get(self.status, "white")

    @property
    def display_text(self) -> str:
        """Get display text based on status."""
        if self.status == TaskStatus.IN_PROGRESS and self.active_form:
            return self.active_form
        return self.content


class TodoTracker:
    """
    Task progress tracker with visual rendering.

    Features:
    - Add/remove tasks
    - Update task status
    - Render as Rich panel
    - Support for subtasks (indentation)
    - Live updates

    Example:
        tracker = TodoTracker(title="Migration Tasks")
        tracker.add("Phase 1: Setup", status="completed")
        tracker.add("Phase 2: Implementation", status="in_progress",
                    active_form="Implementing Phase 2...")
        tracker.add("Phase 2.1: Create module", parent="Phase 2: Implementation")
        tracker.render()
    """

    def __init__(self, title: str = "Tasks", console: Optional[Console] = None):
        self.title = title
        self.console = console or Console()
        self.tasks: Dict[str, Task] = {}
        self._task_order: List[str] = []  # Maintain insertion order

    def add(
        self,
        content: str,
        status: str = "pending",
        active_form: str = "",
        parent: Optional[str] = None,
    ) -> Task:
        """
        Add a new task.

        Args:
            content: Task description
            status: pending, in_progress, completed, failed, skipped
            active_form: Present continuous form for in_progress display
            parent: Parent task content (for subtasks)

        Returns:
            Created Task object
        """
        task = Task(
            content=content,
            status=TaskStatus(status),
            active_form=active_form or content,
            parent_id=parent[:50].replace(" ", "_").lower() if parent else None,
        )

        self.tasks[task.id] = task

        # Insert after parent if specified, else at end
        if parent and task.parent_id in self.tasks:
            parent_idx = self._task_order.index(task.parent_id)
            self._task_order.insert(parent_idx + 1, task.id)
        else:
            self._task_order.append(task.id)

        return task

    def update(
        self,
        content: str,
        status: Optional[str] = None,
        active_form: Optional[str] = None,
    ) -> Optional[Task]:
        """
        Update an existing task.

        Args:
            content: Task content to find
            status: New status (optional)
            active_form: New active form (optional)

        Returns:
            Updated Task or None if not found
        """
        task_id = content[:50].replace(" ", "_").lower()
        task = self.tasks.get(task_id)

        if not task:
            return None

        if status:
            task.status = TaskStatus(status)
            if task.status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now()

        if active_form:
            task.active_form = active_form

        return task

    def complete(self, content: str) -> Optional[Task]:
        """Mark task as completed."""
        return self.update(content, status="completed")

    def start(self, content: str, active_form: Optional[str] = None) -> Optional[Task]:
        """Mark task as in_progress."""
        return self.update(content, status="in_progress", active_form=active_form)

    def fail(self, content: str) -> Optional[Task]:
        """Mark task as failed."""
        return self.update(content, status="failed")

    def skip(self, content: str) -> Optional[Task]:
        """Mark task as skipped."""
        return self.update(content, status="skipped")

    def remove(self, content: str) -> bool:
        """Remove a task."""
        task_id = content[:50].replace(" ", "_").lower()
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._task_order.remove(task_id)
            return True
        return False

    def clear(self) -> None:
        """Clear all tasks."""
        self.tasks.clear()
        self._task_order.clear()

    def set_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """
        Set tasks from a list of dicts (Claude Code format).

        Args:
            tasks: List of {"content": str, "status": str, "activeForm": str}
        """
        self.clear()
        for t in tasks:
            self.add(
                content=t.get("content", ""),
                status=t.get("status", "pending"),
                active_form=t.get("activeForm", t.get("active_form", "")),
            )

    def get_stats(self) -> Dict[str, int]:
        """Get task statistics."""
        stats = {s.value: 0 for s in TaskStatus}
        for task in self.tasks.values():
            stats[task.status.value] += 1
        stats["total"] = len(self.tasks)
        return stats

    def _build_text(self) -> Text:
        """Build Rich Text representation."""
        text = Text()

        for i, task_id in enumerate(self._task_order):
            task = self.tasks.get(task_id)
            if not task:
                continue

            # Indentation for subtasks
            indent = "   " if task.parent_id else ""
            prefix = "⎿  " if i == 0 and not task.parent_id else "   "

            # Build line
            line = f"{prefix}{indent}{task.icon} {task.display_text}\n"
            text.append(line, style=task.color)

        return text

    def render(self, show_stats: bool = False) -> None:
        """
        Render the task list to console.

        Args:
            show_stats: Show statistics at bottom
        """
        text = self._build_text()

        if show_stats:
            stats = self.get_stats()
            stats_line = (
                f"\n[dim]"
                f"✓ {stats['completed']} completed | "
                f"◐ {stats['in_progress']} in progress | "
                f"☐ {stats['pending']} pending"
                f"[/dim]"
            )
            self.console.print(text)
            self.console.print(stats_line)
        else:
            self.console.print(text)

    def render_panel(self, show_stats: bool = True) -> Panel:
        """
        Render as a Rich Panel.

        Returns:
            Rich Panel object
        """
        text = self._build_text()

        if show_stats:
            stats = self.get_stats()
            footer = (
                f"✓ {stats['completed']}/{stats['total']} completed"
            )
        else:
            footer = None

        return Panel(
            text,
            title=f"[bold]{self.title}[/bold]",
            subtitle=footer,
            border_style="cyan",
        )

    def __rich__(self):
        """Rich protocol support."""
        return self._build_text()


# Global tracker instance (singleton pattern)
_global_tracker: Optional[TodoTracker] = None


def get_tracker(title: str = "Tasks") -> TodoTracker:
    """Get or create global tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TodoTracker(title=title)
    return _global_tracker


def todo_add(content: str, status: str = "pending", active_form: str = "") -> Task:
    """Add task to global tracker."""
    return get_tracker().add(content, status, active_form)


def todo_complete(content: str) -> Optional[Task]:
    """Complete task in global tracker."""
    return get_tracker().complete(content)


def todo_start(content: str, active_form: str = "") -> Optional[Task]:
    """Start task in global tracker."""
    return get_tracker().start(content, active_form)


def todo_render(show_stats: bool = False) -> None:
    """Render global tracker."""
    get_tracker().render(show_stats)


__all__ = [
    "TaskStatus",
    "Task",
    "TodoTracker",
    "get_tracker",
    "todo_add",
    "todo_complete",
    "todo_start",
    "todo_render",
]
