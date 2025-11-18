"""
Notification Toasts - Non-intrusive status messages
Gemini-inspired visual feedback system

Features:
- Success, warning, error, info types
- Auto-dismiss with timers
- Stack management (multiple toasts)
- Slide-in/fade-out animations (textual)
- Position: top-right (default) or customizable
- Max queue size (prevent overflow)
- Priority system (errors > warnings > info)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, List
from datetime import datetime, timedelta

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static
from textual.containers import VerticalScroll

from qwen_dev_cli.tui.theme import COLORS
from qwen_dev_cli.tui.wisdom import wisdom_system


class ToastType(Enum):
    """Toast notification types with semantic meaning"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    WISDOM = "wisdom"  # Biblical verses


@dataclass
class Toast:
    """Single toast notification"""
    id: str
    type: ToastType
    title: str
    message: str
    duration: float  # seconds (0 = persistent)
    created_at: datetime
    on_dismiss: Optional[Callable] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if toast has expired"""
        if self.duration == 0:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.duration)
    
    @property
    def icon(self) -> str:
        """Get icon for toast type"""
        return TOAST_ICONS[self.type]
    
    @property
    def color(self) -> str:
        """Get color for toast type"""
        return TOAST_COLORS[self.type]


# Toast type styling (Gemini-inspired colors)
TOAST_ICONS = {
    ToastType.SUCCESS: "✓",
    ToastType.WARNING: "⚠",
    ToastType.ERROR: "✗",
    ToastType.INFO: "ℹ",
    ToastType.WISDOM: "💎",
}

TOAST_COLORS = {
    ToastType.SUCCESS: COLORS['accent_green'],
    ToastType.WARNING: COLORS['accent_yellow'],
    ToastType.ERROR: COLORS['accent_red'],
    ToastType.INFO: COLORS['accent_blue'],
    ToastType.WISDOM: COLORS['accent_purple'],
}

TOAST_BG_COLORS = {
    ToastType.SUCCESS: "#064e3b",  # Dark green
    ToastType.WARNING: "#78350f",  # Dark yellow
    ToastType.ERROR: "#7f1d1d",    # Dark red
    ToastType.INFO: "#1e3a8a",     # Dark blue
    ToastType.WISDOM: "#4c1d95",   # Dark purple
}


class ToastManager:
    """
    Manages toast notifications lifecycle
    
    Features:
    - Queue management (max 5 visible)
    - Priority system (error > warning > info)
    - Auto-dismiss timers
    - Stack overflow protection
    """
    
    def __init__(self, max_toasts: int = 5):
        self.max_toasts = max_toasts
        self.toasts: List[Toast] = []
        self._id_counter = 0
    
    def add_toast(
        self,
        type: ToastType,
        title: str,
        message: str,
        duration: float = 5.0,
        on_dismiss: Optional[Callable] = None
    ) -> str:
        """
        Add a new toast notification
        
        Args:
            type: Toast type (success, warning, error, info, wisdom)
            title: Toast title (short, bold)
            message: Toast message (detail)
            duration: Auto-dismiss time in seconds (0 = persistent)
            on_dismiss: Callback when dismissed
            
        Returns:
            Toast ID
        """
        self._id_counter += 1
        toast_id = f"toast-{self._id_counter}"
        
        toast = Toast(
            id=toast_id,
            type=type,
            title=title,
            message=message,
            duration=duration,
            created_at=datetime.now(),
            on_dismiss=on_dismiss
        )
        
        # Priority insertion (errors first, then warnings, then others)
        priority_order = [ToastType.ERROR, ToastType.WARNING, ToastType.WISDOM, ToastType.INFO, ToastType.SUCCESS]
        insert_index = 0
        
        for i, existing_toast in enumerate(self.toasts):
            if priority_order.index(toast.type) <= priority_order.index(existing_toast.type):
                insert_index = i
                break
            insert_index = i + 1
        
        self.toasts.insert(insert_index, toast)
        
        # Trim if exceeds max (remove oldest non-error toasts)
        while len(self.toasts) > self.max_toasts:
            # Find oldest non-error toast to remove
            for i, t in enumerate(reversed(self.toasts)):
                if t.type != ToastType.ERROR:
                    removed = self.toasts.pop(len(self.toasts) - 1 - i)
                    if removed.on_dismiss:
                        removed.on_dismiss()
                    break
            else:
                # All are errors, remove oldest
                removed = self.toasts.pop()
                if removed.on_dismiss:
                    removed.on_dismiss()
        
        return toast_id
    
    def dismiss_toast(self, toast_id: str) -> bool:
        """
        Dismiss a toast by ID
        
        Returns:
            True if dismissed, False if not found
        """
        for i, toast in enumerate(self.toasts):
            if toast.id == toast_id:
                removed = self.toasts.pop(i)
                if removed.on_dismiss:
                    removed.on_dismiss()
                return True
        return False
    
    def clear_expired(self) -> List[str]:
        """
        Remove expired toasts
        
        Returns:
            List of dismissed toast IDs
        """
        dismissed = []
        self.toasts = [t for t in self.toasts if not t.is_expired or dismissed.append(t.id)]
        return dismissed
    
    def get_active_toasts(self) -> List[Toast]:
        """Get all active (non-expired) toasts"""
        self.clear_expired()
        return self.toasts.copy()
    
    def clear_all(self):
        """Clear all toasts"""
        for toast in self.toasts:
            if toast.on_dismiss:
                toast.on_dismiss()
        self.toasts.clear()


class ToastWidget(Static):
    """
    Single toast widget (Textual component)
    
    Gemini-inspired design:
    - Clean panel with rounded corners
    - Icon + title + message
    - Color-coded border
    - Close button (×)
    """
    
    def __init__(self, toast: Toast, on_close: Optional[Callable] = None):
        super().__init__()
        self.toast = toast
        self.on_close = on_close
    
    def render(self) -> RenderableType:
        """Render the toast as a Rich panel"""
        # Build content
        content = Text()
        
        # Icon + Title (bold, colored)
        content.append(f"{self.toast.icon} ", style=f"bold {self.toast.color}")
        content.append(self.toast.title, style=f"bold {COLORS['text_primary']}")
        content.append(" ")
        
        # Close button (right-aligned)
        content.append("×", style=f"{COLORS['text_tertiary']} dim")
        content.append("\n")
        
        # Message (normal weight)
        content.append(self.toast.message, style=COLORS['text_secondary'])
        
        # Create panel with colored border
        panel = Panel(
            content,
            border_style=self.toast.color,
            box=None,  # Use default
            padding=(0, 1),
            style=f"on {TOAST_BG_COLORS[self.toast.type]}",
        )
        
        return panel
    
    def on_click(self):
        """Handle click to dismiss"""
        if self.on_close:
            self.on_close(self.toast.id)


class ToastContainer(VerticalScroll):
    """
    Container for multiple toasts (stacked)
    
    Position: top-right corner of screen
    Max height: 50% of screen
    Auto-scroll to newest
    """
    
    def __init__(self, manager: ToastManager):
        super().__init__()
        self.manager = manager
        self.styles.height = "auto"
        self.styles.max_height = "50%"
        self.styles.align = ("right", "top")
    
    def refresh_toasts(self):
        """Refresh displayed toasts"""
        # Clear current widgets
        self.remove_children()
        
        # Add active toasts
        for toast in self.manager.get_active_toasts():
            widget = ToastWidget(toast, on_close=self._on_toast_close)
            self.mount(widget)
    
    def _on_toast_close(self, toast_id: str):
        """Handle toast close"""
        self.manager.dismiss_toast(toast_id)
        self.refresh_toasts()


# Convenience functions for quick toasts
def create_toast_manager() -> ToastManager:
    """Create a default toast manager"""
    return ToastManager(max_toasts=5)


def show_success(
    manager: ToastManager,
    title: str,
    message: str,
    duration: float = 5.0
) -> str:
    """Show a success toast"""
    return manager.add_toast(ToastType.SUCCESS, title, message, duration)


def show_warning(
    manager: ToastManager,
    title: str,
    message: str,
    duration: float = 7.0
) -> str:
    """Show a warning toast"""
    return manager.add_toast(ToastType.WARNING, title, message, duration)


def show_error(
    manager: ToastManager,
    title: str,
    message: str,
    duration: float = 0  # Errors persist until dismissed
) -> str:
    """Show an error toast (persistent)"""
    return manager.add_toast(ToastType.ERROR, title, message, duration)


def show_info(
    manager: ToastManager,
    title: str,
    message: str,
    duration: float = 4.0
) -> str:
    """Show an info toast"""
    return manager.add_toast(ToastType.INFO, title, message, duration)


def show_wisdom(
    manager: ToastManager,
    category: str = "construction",
    duration: float = 8.0
) -> str:
    """
    Show a biblical wisdom toast
    
    Args:
        manager: Toast manager
        category: Wisdom category (construction, purpose, persistence, etc.)
        duration: Display time
        
    Returns:
        Toast ID
    """
    verse = wisdom_system.get_verse(category)
    
    return manager.add_toast(
        ToastType.WISDOM,
        title="Biblical Wisdom",
        message=f"{verse['text']} — {verse['reference']}",
        duration=duration
    )


# Example usage patterns
def example_usage():
    """Example of how to use the toast system"""
    manager = create_toast_manager()
    
    # Success toast
    show_success(
        manager,
        title="File Saved",
        message="config.py has been saved successfully.",
        duration=3.0
    )
    
    # Warning toast
    show_warning(
        manager,
        title="Large Context",
        message="File context exceeds 10,000 tokens. Consider reducing.",
        duration=5.0
    )
    
    # Error toast (persistent)
    show_error(
        manager,
        title="Syntax Error",
        message="Invalid Python syntax on line 42: unexpected indent",
        duration=0  # Persistent
    )
    
    # Info toast
    show_info(
        manager,
        title="Model Switched",
        message="Now using Qwen2.5-Coder-32B-Instruct",
        duration=3.0
    )
    
    # Wisdom toast
    show_wisdom(
        manager,
        category="construction",
        duration=8.0
    )


if __name__ == "__main__":
    # Demo
    print("🎨 Toast Notification System")
    print("=" * 70)
    print("✓ Gemini-inspired non-intrusive notifications")
    print("✓ 5 types: success, warning, error, info, wisdom")
    print("✓ Auto-dismiss with timers")
    print("✓ Priority system (errors first)")
    print("✓ Stack management (max 5 visible)")
    print("✓ Biblical wisdom integration")
    print("=" * 70)
    print("\n'Let your light shine before others.' — Matthew 5:16")
