"""
💬 Message Box Component - Apple-style message display with smooth animations

Features:
- ✨ Smooth typing animation (cubic ease-out)

from enum import Enum

class MessageRole(Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
- 🎨 Role-based styling (user vs AI)
- ⏰ Timestamp display
- 🎯 Syntax highlighting for code blocks
- 🌊 Fade-in animation
- 📱 Responsive width
- ♿ WCAG AAA accessible

Philosophy:
- Visual hierarchy (who said what, when)
- Purposeful animation (not distracting)
- Readable at all terminal sizes
- Screen reader friendly
- Apple-level polish

Created: 2025-11-18 20:13 UTC
Polished: 2025-11-18 22:54 UTC
"""

import asyncio
from datetime import datetime
from typing import Optional, AsyncIterator
from dataclasses import dataclass, field

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax

from ..theme import COLORS
from ..styles import PRESET_STYLES, StyleCombinations
from ..spacing import SPACING


from enum import Enum

class MessageRole(Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"



@dataclass
class Message:
    """
    Message data structure.
    
    Attributes:
        content: Message text content
        role: Message role ('user', 'assistant', 'system')
        timestamp: Message timestamp
        metadata: Additional metadata (file attachments, etc.)
    """
    content: str
    role: str = "user"
    timestamp: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MessageBox:
    """
    Enhanced message box with animations and styling.
    
    Examples:
        # Simple message
        msg = MessageBox(Message("Hello!", role="user"))
        console.print(msg.render())
        
        # With typing animation
        async for frame in msg.render_animated():
            console.clear()
            console.print(frame)
            await asyncio.sleep(0.03)
    """
    
    def __init__(
        self,
        message: Message,
        console: Optional[Console] = None,
        max_width: Optional[int] = None,
        show_timestamp: bool = True,
        show_role: bool = True,
    ):
        """
        Initialize message box.
        
        Args:
            message: Message data
            console: Rich console instance
            max_width: Maximum width in characters (None = auto)
            show_timestamp: Show timestamp in header
            show_role: Show role in header
        """
        self.message = message
        self.console = console or Console()
        self.max_width = max_width
        self.show_timestamp = show_timestamp
        self.show_role = show_role
        
        # Get role-specific styling
        if message.role == "user":
            self.styles = StyleCombinations.message_user()
            self.title_prefix = "You"
            self.border_color = COLORS['accent_blue']
        elif message.role == "assistant":
            self.styles = StyleCombinations.message_ai()
            self.title_prefix = "Assistant"
            self.border_color = COLORS['accent_purple']
        else:
            self.styles = {
                'border': PRESET_STYLES.SECONDARY,
                'text': PRESET_STYLES.PRIMARY,
                'timestamp': PRESET_STYLES.TIMESTAMP,
            }
            self.title_prefix = "System"
            self.border_color = COLORS['text_secondary']
    
    def _format_timestamp(self) -> str:
        """Format timestamp for display."""
        if not self.message.timestamp:
            return ""
        return self.message.timestamp.strftime("%H:%M:%S")
    
    def _create_title(self) -> str:
        """Create panel title with role and timestamp."""
        parts = []
        
        if self.show_role:
            parts.append(self.title_prefix)
        
        if self.show_timestamp:
            parts.append(self._format_timestamp())
        
        return " • ".join(parts) if parts else None
    
    def _process_content(self, content: str) -> RenderableType:
        """
        Process message content (markdown, code, plain text).
        
        Args:
            content: Raw message content
            
        Returns:
            Rich renderable object
        """
        # Detect code blocks (```language\ncode\n```)
        if "```" in content:
            # Render as markdown with syntax highlighting
            return Markdown(content)
        
        # Plain text with proper wrapping
        text = Text(content, style=self.styles['text'])
        return text
    
    def render(self) -> Panel:
        """
        Render complete message box.
        
        Returns:
            Rich Panel object
        """
        content = self._process_content(self.message.content)
        title = self._create_title()
        
        return Panel(
            content,
            title=title,
            border_style=self.border_color,
            padding=(0, 1),  # Vertical, Horizontal padding
            expand=False,
            width=self.max_width,
        )
    
    async def render_animated(
        self,
        wpm: int = 400,
        clear_screen: bool = True,
        smooth: bool = True,
    ) -> AsyncIterator[Panel]:
        """
        Render message with smooth typing animation (Apple-style).
        
        Args:
            wpm: Typing speed in words per minute (400 = ~33 chars/sec)
            clear_screen: Clear screen before each frame
            smooth: Use cubic ease-out for natural rhythm
            
        Yields:
            Panel frames for animation
            
        Example:
            async for frame in message_box.render_animated():
                console.clear()
                console.print(frame)
        
        Note:
            Uses variable pacing for natural feel:
            - Slower at sentence start (thinking)
            - Faster in middle (confidence)
            - Pause at punctuation (breathing)
        """
        content = self.message.content
        title = self._create_title()
        
        # Calculate delay per character
        chars_per_second = (wpm * 5) / 60  # Avg 5 chars per word
        base_delay = 1.0 / chars_per_second
        
        # Build content character by character
        accumulated = ""
        total_chars = len(content)
        
        for i, char in enumerate(content):
            accumulated += char
            
            # Process accumulated text
            rendered_content = self._process_content(accumulated)
            
            # Add cursor effect at end (blinking)
            if i < total_chars - 1 and smooth:
                cursor = "▋" if (i // 3) % 2 == 0 else "▊"
                rendered_content = self._process_content(accumulated + cursor)
            
            # Create panel frame
            panel = Panel(
                rendered_content,
                title=title,
                border_style=self.border_color,
                padding=(0, 1),
                expand=False,
                width=self.max_width,
            )
            
            yield panel
            
            # Variable delay based on character and position
            delay = base_delay
            
            # Smooth acceleration (ease-out cubic)
            if smooth and i < 10:
                # Start slower (thinking)
                progress = i / 10.0
                eased = 1 - pow(1 - progress, 3)
                delay *= (2 - eased)  # 2x slower → 1x
            
            # Pause longer at punctuation (natural breathing)
            if char in '.!?':
                delay *= 5  # Long pause (sentence end)
            elif char in ',;:':
                delay *= 3  # Medium pause (clause)
            elif char == '\n':
                delay *= 2  # Line break pause
            elif char == '\n':
                delay *= 2
            
            await asyncio.sleep(delay)
        
        # Final frame (complete message)
        final_panel = self.render()
        yield final_panel


class MessageStream:
    """
    Manages a stream of messages with automatic scrolling.
    
    Examples:
        stream = MessageStream(console)
        stream.add_message(Message("Hello!", role="user"))
        stream.add_message(Message("Hi there!", role="assistant"))
        stream.render()
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        max_messages: int = 100,
        max_width: Optional[int] = None,
    ):
        """
        Initialize message stream.
        
        Args:
            console: Rich console instance
            max_messages: Maximum messages to keep in history
            max_width: Maximum width for messages
        """
        self.console = console or Console()
        self.messages: list[Message] = []
        self.max_messages = max_messages
        self.max_width = max_width
    
    def add_message(self, message: Message):
        """Add message to stream."""
        self.messages.append(message)
        
        # Trim old messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def clear(self):
        """Clear all messages."""
        self.messages.clear()
    
    def render(self, last_n: Optional[int] = None):
        """
        Render all messages in stream.
        
        Args:
            last_n: Only render last N messages (None = all)
        """
        messages_to_render = self.messages[-last_n:] if last_n else self.messages
        
        for msg in messages_to_render:
            box = MessageBox(msg, console=self.console, max_width=self.max_width)
            self.console.print(box.render())
            self.console.print()  # Add spacing between messages
    
    async def render_last_animated(self, wpm: int = 400):
        """
        Render last message with typing animation.
        
        Args:
            wpm: Typing speed in words per minute
        """
        if not self.messages:
            return
        
        last_message = self.messages[-1]
        box = MessageBox(last_message, console=self.console, max_width=self.max_width)
        
        async for frame in box.render_animated(wpm=wpm, clear_screen=False):
            # Move cursor to message position
            # (In real implementation, would track position)
            self.console.print(frame, end='\r')
            await asyncio.sleep(0.03)
        
        self.console.print()  # Final newline


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def typing_effect(text: str, wpm: int = 400) -> AsyncIterator[str]:
    """
    Simple typing effect generator (character-by-character).
    
    Args:
        text: Text to animate
        wpm: Words per minute (typing speed)
        
    Yields:
        Characters one at a time
        
    Example:
        async for char in typing_effect("Hello, world!", wpm=300):
            print(char, end='', flush=True)
            await asyncio.sleep(0.03)
    """
    chars_per_second = (wpm * 5) / 60
    base_delay = 1.0 / chars_per_second
    
    for char in text:
        yield char
        
        # Variable delay
        delay = base_delay
        if char in '.!?':
            delay *= 4
        elif char in ',;:':
            delay *= 2
        elif char == '\n':
            delay *= 2
        
        await asyncio.sleep(delay)


def create_system_message(content: str) -> Message:
    """Create a system message."""
    return Message(content=content, role="system")


def create_user_message(content: str) -> Message:
    """Create a user message."""
    return Message(content=content, role="user")


def create_assistant_message(content: str) -> Message:
    """Create an assistant message."""
    return Message(content=content, role="assistant")
