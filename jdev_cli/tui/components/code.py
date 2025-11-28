"""
Code Block Component - Enhanced code display with syntax highlighting.

Features:
- Syntax highlighting (Pygments)
- Line numbers with padding
- Language badge
- Copy button indicator
- Multiple themes
- Responsive width

Philosophy:
- Readable code is usable code
- Clear language identification
- Easy to scan (line numbers)
- Copy-friendly (indicate copyable)

Created: 2025-11-18 20:50 UTC
"""

from typing import Optional
from pathlib import Path

from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text

from ..theme import COLORS, ThemeVariant
from ..styles import PRESET_STYLES


class CodeBlock:
    """
    Enhanced code block with syntax highlighting.
    
    Examples:
        code = CodeBlock(
            'def hello():\\n    print("Hello!")',
            language="python"
        )
        console.print(code.render())
    """

    # Language icons/badges
    LANGUAGE_ICONS = {
        'python': '🐍',
        'javascript': '📜',
        'typescript': '🔷',
        'java': '☕',
        'go': '🐹',
        'rust': '🦀',
        'cpp': '⚙️',
        'c': '⚙️',
        'ruby': '💎',
        'php': '🐘',
        'swift': '🦅',
        'kotlin': '🅺',
        'shell': '🐚',
        'bash': '🐚',
        'sql': '📊',
        'html': '🌐',
        'css': '🎨',
        'json': '📦',
        'yaml': '📄',
        'markdown': '📝',
        'xml': '📋',
    }

    def __init__(
        self,
        code: str,
        language: str = "text",
        show_line_numbers: bool = True,
        start_line: int = 1,
        highlight_lines: Optional[set[int]] = None,
        theme: ThemeVariant = ThemeVariant.DARK,
        show_language: bool = True,
        copyable: bool = True,
        max_width: Optional[int] = None,
    ):
        """
        Initialize code block.
        
        Args:
            code: Code content
            language: Programming language
            show_line_numbers: Show line numbers
            start_line: Starting line number
            highlight_lines: Lines to highlight
            theme: Color theme
            show_language: Show language badge
            copyable: Show copy indicator
            max_width: Maximum width (None = auto)
        """
        self.code = code
        self.language = language.lower()
        self.show_line_numbers = show_line_numbers
        self.start_line = start_line
        self.highlight_lines = highlight_lines or set()
        self.theme = theme
        self.show_language = show_language
        self.copyable = copyable
        self.max_width = max_width

    def _get_language_display(self) -> str:
        """Get language display name with icon."""
        icon = self.LANGUAGE_ICONS.get(self.language, '📄')
        lang_name = self.language.upper() if len(self.language) <= 4 else self.language.capitalize()
        return f"{icon} {lang_name}"

    def _create_syntax(self) -> Syntax:
        """
        Create Rich Syntax object.
        
        Returns:
            Rich Syntax object
        """
        # Map our theme to Pygments theme
        pygments_theme = "monokai" if self.theme == ThemeVariant.DARK else "github-dark"

        return Syntax(
            self.code,
            lexer=self.language,
            line_numbers=self.show_line_numbers,
            start_line=self.start_line,
            highlight_lines=self.highlight_lines,
            theme=pygments_theme,
            word_wrap=True,
            background_color=COLORS['bg_secondary'],
        )

    def _create_header(self) -> Optional[Text]:
        """
        Create code block header with language and copy indicator.
        
        Returns:
            Rich Text object or None
        """
        if not (self.show_language or self.copyable):
            return None

        parts = []

        # Language badge
        if self.show_language:
            lang_display = self._get_language_display()
            parts.append(Text(lang_display, style=PRESET_STYLES.INFO))

        # Copy indicator
        if self.copyable:
            if parts:
                parts.append(Text(" • ", style=PRESET_STYLES.TERTIARY))
            parts.append(Text("📋 Copyable", style=PRESET_STYLES.TERTIARY))

        # Combine
        result = Text()
        for part in parts:
            result.append(part)

        return result

    def render(self) -> Panel:
        """
        Render code block as Panel.
        
        Returns:
            Rich Panel object
        """
        syntax = self._create_syntax()
        header = self._create_header()

        return Panel(
            syntax,
            title=header if header else None,
            title_align="left",
            border_style=COLORS['border_muted'],
            padding=(0, 1),
            expand=False,
            width=self.max_width,
        )

    def render_inline(self) -> Text:
        """
        Render as inline code (single line, no panel).
        
        Returns:
            Rich Text object
        """
        return Text(self.code, style=PRESET_STYLES.CODE)


class InlineCode:
    """
    Inline code snippet (for use within text).
    
    Examples:
        inline = InlineCode("print('hello')")
        text = Text("Use ") + inline.render() + Text(" to print")
    """

    def __init__(self, code: str):
        """
        Initialize inline code.
        
        Args:
            code: Code content
        """
        self.code = code

    def render(self) -> Text:
        """
        Render inline code.
        
        Returns:
            Rich Text object
        """
        return Text(f"`{self.code}`", style=PRESET_STYLES.CODE)


class CodeSnippet:
    """
    Code snippet with context (file path, line range).
    
    Examples:
        snippet = CodeSnippet(
            code="def hello():\\n    print('Hi')",
            file_path="main.py",
            start_line=10,
            language="python"
        )
        console.print(snippet.render())
    """

    def __init__(
        self,
        code: str,
        file_path: Optional[str] = None,
        start_line: int = 1,
        end_line: Optional[int] = None,
        language: Optional[str] = None,
    ):
        """
        Initialize code snippet.
        
        Args:
            code: Code content
            file_path: Source file path
            start_line: Starting line number
            end_line: Ending line number
            language: Programming language (auto-detect from path if None)
        """
        self.code = code
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line or (start_line + code.count('\n'))

        # Auto-detect language from file path
        if language is None and file_path:
            self.language = self._detect_language(file_path)
        else:
            self.language = language or "text"

    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lstrip('.')

        # Map extensions to language names
        lang_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'jsx': 'javascript',
            'java': 'java',
            'go': 'go',
            'rs': 'rust',
            'cpp': 'cpp',
            'cc': 'cpp',
            'c': 'c',
            'h': 'c',
            'hpp': 'cpp',
            'rb': 'ruby',
            'php': 'php',
            'swift': 'swift',
            'kt': 'kotlin',
            'sh': 'bash',
            'bash': 'bash',
            'sql': 'sql',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'xml': 'xml',
        }

        return lang_map.get(ext, 'text')

    def _create_title(self) -> Optional[Text]:
        """Create title with file path and line range."""
        if not self.file_path:
            return None

        parts = []

        # File path
        parts.append(Text(self.file_path, style=PRESET_STYLES.PATH))

        # Line range
        if self.start_line:
            line_range = f":{self.start_line}"
            if self.end_line and self.end_line != self.start_line:
                line_range += f"-{self.end_line}"
            parts.append(Text(line_range, style=PRESET_STYLES.TERTIARY))

        # Combine
        result = Text()
        for part in parts:
            result.append(part)

        return result

    def render(self) -> Panel:
        """
        Render code snippet.
        
        Returns:
            Rich Panel object
        """
        code_block = CodeBlock(
            self.code,
            language=self.language,
            show_line_numbers=True,
            start_line=self.start_line,
        )

        title = self._create_title()

        return Panel(
            code_block._create_syntax(),
            title=title if title else None,
            title_align="left",
            border_style=COLORS['accent_blue'],
            padding=(0, 1),
            expand=False,
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_code_block(
    code: str,
    language: str = "python",
    **kwargs,
) -> CodeBlock:
    """
    Quick helper to create code block.
    
    Args:
        code: Code content
        language: Programming language
        **kwargs: Additional CodeBlock arguments
        
    Returns:
        CodeBlock instance
    """
    return CodeBlock(code, language, **kwargs)


def render_code_inline(code: str) -> Text:
    """
    Quick helper for inline code.
    
    Args:
        code: Code content
        
    Returns:
        Rich Text object
    """
    return InlineCode(code).render()


def detect_language_from_content(code: str) -> str:
    """
    Detect programming language from code content (heuristics).
    
    Args:
        code: Code content
        
    Returns:
        Detected language name
    """
    # Simple heuristics
    if 'def ' in code or 'import ' in code or 'class ' in code:
        return 'python'
    elif 'function ' in code or 'const ' in code or 'let ' in code:
        return 'javascript'
    elif 'public class ' in code or 'public static void' in code:
        return 'java'
    elif 'fn ' in code or 'let mut' in code:
        return 'rust'
    elif 'func ' in code or 'package ' in code:
        return 'go'

    return 'text'
