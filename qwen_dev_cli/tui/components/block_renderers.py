"""
Block Renderers - Scalable Registry-based Block Rendering System.

ARQUITETURA ESCALÁVEL:
Para adicionar um novo tipo de bloco, basta criar uma classe:

    @BlockRenderer.register
    class MyNewBlockRenderer(BlockRenderer):
        block_type = BlockType.MY_NEW_TYPE
        pattern = r'^my-pattern'
        priority = 50

        def render(self, block: BlockInfo) -> RenderableType:
            return Text(block.content)

O sistema automaticamente:
1. Registra o pattern no detector
2. Registra o renderer no factory
3. Usa a prioridade para ordenar detecção

Autor: JuanCS Dev
Data: 2025-11-25
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Dict, List, Optional, Type, Pattern, Callable,
    ClassVar, Any, TypeVar, Generic
)
from enum import Enum, auto

from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown as RichMarkdown
from rich.console import RenderableType, Group
from rich.table import Table


# =============================================================================
# BLOCK TYPE ENUM - Extensível via auto()
# =============================================================================

class BlockType(Enum):
    """
    Tipos de blocos suportados.

    Para adicionar novo tipo:
        MY_TYPE = auto()
    """
    # Core markdown
    UNKNOWN = auto()
    PARAGRAPH = auto()
    CODE_FENCE = auto()
    TABLE = auto()
    CHECKLIST = auto()
    HEADING = auto()
    LIST = auto()
    BLOCKQUOTE = auto()
    HORIZONTAL_RULE = auto()
    EMPTY = auto()

    # Claude Code Web style
    TOOL_CALL = auto()
    TOOL_OUTPUT = auto()
    DIFF_BLOCK = auto()
    STATUS_BADGE = auto()

    # Extensibility examples
    MERMAID_DIAGRAM = auto()
    MATH_BLOCK = auto()
    COLLAPSIBLE = auto()


# =============================================================================
# BLOCK INFO - Dados do bloco detectado
# =============================================================================

@dataclass
class BlockInfo:
    """Informação sobre um bloco detectado."""
    block_type: BlockType
    start_line: int
    end_line: Optional[int] = None
    language: Optional[str] = None
    is_complete: bool = False
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# BLOCK RENDERER - Base class com auto-registro
# =============================================================================

class BlockRendererMeta(type):
    """Metaclass para auto-registro de renderers."""

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        cls = super().__new__(mcs, name, bases, namespace)

        # Não registra a classe base
        if name != 'BlockRenderer' and hasattr(cls, 'block_type'):
            BlockRendererRegistry.register_renderer(cls)

        return cls


class BlockRenderer(metaclass=BlockRendererMeta):
    """
    Base class para renderers de blocos.

    Subclasses são automaticamente registradas.

    Attributes:
        block_type: Tipo de bloco que este renderer processa
        pattern: Regex pattern para detectar início do bloco
        priority: Prioridade de detecção (maior = primeiro)
        continues_with: Lista de BlockTypes que podem continuar este bloco
    """

    # Class attributes a serem sobrescritos
    block_type: ClassVar[BlockType]
    pattern: ClassVar[str] = ""
    priority: ClassVar[int] = 50  # 0-100, default 50
    continues_with: ClassVar[List[BlockType]] = []

    # Compiled pattern (lazy)
    _compiled_pattern: ClassVar[Optional[Pattern]] = None

    @classmethod
    def get_pattern(cls) -> Optional[Pattern]:
        """Retorna pattern compilado (lazy)."""
        if cls.pattern and cls._compiled_pattern is None:
            cls._compiled_pattern = re.compile(cls.pattern)
        return cls._compiled_pattern

    @classmethod
    def matches(cls, line: str) -> bool:
        """Verifica se a linha inicia este tipo de bloco."""
        pattern = cls.get_pattern()
        if pattern:
            return bool(pattern.match(line.strip()))
        return False

    @classmethod
    def extract_metadata(cls, line: str) -> Dict[str, Any]:
        """Extrai metadata da linha inicial (override opcional)."""
        return {}

    @classmethod
    def should_continue(cls, current_type: BlockType, new_type: BlockType, line: str) -> bool:
        """Determina se bloco atual deve continuar com nova linha."""
        return new_type in cls.continues_with or new_type == current_type

    @abstractmethod
    def render(self, block: BlockInfo) -> RenderableType:
        """Renderiza o bloco."""
        pass

    def reset(self) -> None:
        """Reseta estado interno (se houver)."""
        pass


# =============================================================================
# REGISTRY - Central de registro de renderers
# =============================================================================

class BlockRendererRegistry:
    """
    Registry central para renderers de blocos.

    Singleton pattern - acesso via métodos de classe.
    """

    _renderers: ClassVar[Dict[BlockType, Type[BlockRenderer]]] = {}
    _instances: ClassVar[Dict[BlockType, BlockRenderer]] = {}
    _detection_order: ClassVar[List[Type[BlockRenderer]]] = []
    _initialized: ClassVar[bool] = False

    @classmethod
    def register_renderer(cls, renderer_cls: Type[BlockRenderer]) -> None:
        """Registra um renderer."""
        block_type = renderer_cls.block_type
        cls._renderers[block_type] = renderer_cls

        # Atualiza ordem de detecção
        cls._update_detection_order()

    @classmethod
    def _update_detection_order(cls) -> None:
        """Atualiza ordem de detecção baseada em prioridade."""
        cls._detection_order = sorted(
            [r for r in cls._renderers.values() if r.pattern],
            key=lambda r: r.priority,
            reverse=True  # Maior prioridade primeiro
        )

    @classmethod
    def get_renderer(cls, block_type: BlockType) -> Optional[BlockRenderer]:
        """Retorna instância do renderer para o tipo."""
        if block_type not in cls._instances:
            renderer_cls = cls._renderers.get(block_type)
            if renderer_cls:
                cls._instances[block_type] = renderer_cls()
        return cls._instances.get(block_type)

    @classmethod
    def detect_block_type(cls, line: str) -> BlockType:
        """Detecta tipo de bloco a partir de uma linha."""
        stripped = line.strip()

        for renderer_cls in cls._detection_order:
            if renderer_cls.matches(stripped):
                return renderer_cls.block_type

        return BlockType.PARAGRAPH

    @classmethod
    def render_block(cls, block: BlockInfo) -> RenderableType:
        """Renderiza um bloco usando o renderer apropriado."""
        renderer = cls.get_renderer(block.block_type)
        if renderer:
            return renderer.render(block)
        return Text(block.content)

    @classmethod
    def get_all_patterns(cls) -> Dict[BlockType, Pattern]:
        """Retorna todos os patterns compilados."""
        return {
            r.block_type: r.get_pattern()
            for r in cls._renderers.values()
            if r.get_pattern()
        }

    @classmethod
    def list_renderers(cls) -> List[str]:
        """Lista todos os renderers registrados."""
        return [
            f"{r.block_type.name} (priority={r.priority})"
            for r in cls._detection_order
        ]

    @classmethod
    def reset_all(cls) -> None:
        """Reseta todos os renderers."""
        for renderer in cls._instances.values():
            renderer.reset()


# =============================================================================
# BUILT-IN RENDERERS
# =============================================================================

class ParagraphRenderer(BlockRenderer):
    """Renderiza parágrafos como markdown."""
    block_type = BlockType.PARAGRAPH
    pattern = ""  # Fallback - não tem pattern específico
    priority = 0
    continues_with = [BlockType.PARAGRAPH]

    def render(self, block: BlockInfo) -> RenderableType:
        try:
            return RichMarkdown(block.content)
        except Exception:
            return Text(block.content)


class HeadingRenderer(BlockRenderer):
    """Renderiza headings H1-H6."""
    block_type = BlockType.HEADING
    pattern = r'^(#{1,6})\s+(.*)'
    priority = 80

    # Estilos por nível
    STYLES = {
        1: "bold underline bright_white",
        2: "bold bright_white",
        3: "bold white",
        4: "bold dim white",
        5: "dim white",
        6: "dim italic white",
    }

    @classmethod
    def extract_metadata(cls, line: str) -> Dict[str, Any]:
        match = re.match(cls.pattern, line.strip())
        if match:
            return {
                'level': len(match.group(1)),
                'text': match.group(2)
            }
        return {}

    def render(self, block: BlockInfo) -> RenderableType:
        level = block.metadata.get('level', 1)
        text_content = block.metadata.get('text', block.content)
        style = self.STYLES.get(level, "white")

        text = Text()
        text.append("#" * level + " ", style="dim cyan")
        text.append(text_content, style=style)
        return text


class CodeFenceRenderer(BlockRenderer):
    """Renderiza code fences com syntax highlighting."""
    block_type = BlockType.CODE_FENCE
    pattern = r'^(`{3,}|~{3,})(\w*)\s*$'
    priority = 90

    def __init__(self):
        self._highlighters: Dict[str, Any] = {}

    @classmethod
    def extract_metadata(cls, line: str) -> Dict[str, Any]:
        match = re.match(cls.pattern, line.strip())
        if match:
            return {
                'fence_marker': match.group(1)[:3],
                'language': match.group(2) or 'text'
            }
        return {}

    def render(self, block: BlockInfo) -> RenderableType:
        language = block.language or block.metadata.get('language', 'text')

        return Panel(
            Syntax(
                block.content,
                language,
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            ),
            title=f"[bold]{language.upper()}[/bold]" + ("" if block.is_complete else " [dim]⏳[/dim]"),
            border_style="dim cyan",
            padding=(0, 1),
        )

    def reset(self) -> None:
        self._highlighters.clear()


class TableRenderer(BlockRenderer):
    """Renderiza tabelas markdown."""
    block_type = BlockType.TABLE
    pattern = r'^\|.*\|'
    priority = 70
    continues_with = [BlockType.TABLE]

    def render(self, block: BlockInfo) -> RenderableType:
        lines = block.content.strip().split('\n')
        if not lines:
            return Text(block.content)

        table = Table(show_header=True, header_style="bold cyan")

        # Parse header
        header_cells = [c.strip() for c in lines[0].split('|')[1:-1]]
        for cell in header_cells:
            table.add_column(cell)

        # Skip separator line, add data rows
        for line in lines[2:] if len(lines) > 2 else []:
            if line.strip():
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if cells:
                    table.add_row(*cells)

        return table


class ChecklistRenderer(BlockRenderer):
    """Renderiza checklists."""
    block_type = BlockType.CHECKLIST
    pattern = r'^[-*+]\s+\[[ xX]\]'
    priority = 75
    continues_with = [BlockType.CHECKLIST]

    def render(self, block: BlockInfo) -> RenderableType:
        text = Text()
        for line in block.content.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Parse checkbox
            if '[x]' in line.lower():
                checkbox = "☑"
                style = "dim strike"
            else:
                checkbox = "☐"
                style = "white"

            # Remove markdown checkbox syntax
            content = re.sub(r'^[-*+]\s+\[[ xX]\]\s*', '', line)

            text.append(f"  {checkbox} ", style="cyan")
            text.append(content + "\n", style=style)

        return text


class ToolCallRenderer(BlockRenderer):
    """Renderiza tool calls estilo Claude Code."""
    block_type = BlockType.TOOL_CALL
    pattern = r'^[•●]\s+(Read|Write|Bash|Update Todos|Edit|Glob|Grep|Task|WebFetch|WebSearch)\b'
    priority = 95  # Alta prioridade

    # Ícones e cores por ferramenta
    TOOL_STYLES = {
        "Read": ("📖", "bright_cyan"),
        "Write": ("✏️", "bright_green"),
        "Edit": ("📝", "bright_yellow"),
        "Bash": ("💻", "bright_magenta"),
        "Glob": ("🔍", "bright_blue"),
        "Grep": ("🔎", "bright_blue"),
        "Task": ("📋", "bright_white"),
        "WebFetch": ("🌐", "bright_cyan"),
        "WebSearch": ("🔍", "bright_cyan"),
        "Update Todos": ("✅", "bright_green"),
    }

    def render(self, block: BlockInfo) -> RenderableType:
        content = block.content.strip()
        text = Text()

        match = re.match(r'^[•●]\s+(\w+(?:\s+\w+)?)\s*(.*)', content)
        if match:
            tool_name = match.group(1)
            args = match.group(2).strip()

            icon, color = self.TOOL_STYLES.get(tool_name, ("•", "white"))

            text.append(f"{icon} ", style="bold")
            text.append(tool_name, style=f"bold {color}")
            if args:
                text.append(" ", style="dim")
                text.append(args, style="dim italic")
        else:
            text.append(content, style="white")

        return Panel(text, border_style="dim cyan", padding=(0, 1))


class StatusBadgeRenderer(BlockRenderer):
    """Renderiza status badges."""
    block_type = BlockType.STATUS_BADGE
    pattern = r'^[🔴🟡🟢⚪🟠]\s*\w+'
    priority = 94

    BADGE_STYLES = {
        "🔴": ("bold red", "CRITICAL"),
        "🟠": ("bold bright_red", "HIGH"),
        "🟡": ("bold yellow", "WARNING"),
        "🟢": ("bold green", "OK"),
        "⚪": ("dim white", "INFO"),
    }

    def render(self, block: BlockInfo) -> RenderableType:
        content = block.content.strip()
        text = Text()

        for emoji, (style, _label) in self.BADGE_STYLES.items():
            if content.startswith(emoji):
                status_text = content[len(emoji):].strip()
                text.append(f"{emoji} ", style="bold")
                text.append(status_text, style=style)
                return text

        text.append(content, style="white")
        return text


class DiffBlockRenderer(BlockRenderer):
    """Renderiza diffs estilo GitHub."""
    block_type = BlockType.DIFF_BLOCK
    pattern = r'^(diff --git|@@\s*-\d+.*\+\d+.*@@|[+-]{3}\s+[ab]/)'
    priority = 85
    continues_with = [BlockType.DIFF_BLOCK]

    def render(self, block: BlockInfo) -> RenderableType:
        return Syntax(
            block.content,
            "diff",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )


class BlockquoteRenderer(BlockRenderer):
    """Renderiza blockquotes."""
    block_type = BlockType.BLOCKQUOTE
    pattern = r'^>\s*'
    priority = 60
    continues_with = [BlockType.BLOCKQUOTE]

    def render(self, block: BlockInfo) -> RenderableType:
        # Remove '>' prefixes
        lines = []
        for line in block.content.split('\n'):
            cleaned = re.sub(r'^>\s*', '', line)
            lines.append(cleaned)

        text = Text('\n'.join(lines), style="italic dim")
        return Panel(text, border_style="dim", padding=(0, 1))


class ListRenderer(BlockRenderer):
    """Renderiza listas (bullet e numbered)."""
    block_type = BlockType.LIST
    pattern = r'^([-*+]|\d+\.)\s+'
    priority = 65
    continues_with = [BlockType.LIST]

    def render(self, block: BlockInfo) -> RenderableType:
        text = Text()
        for line in block.content.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Numbered list
            num_match = re.match(r'^(\d+)\.\s+(.*)$', line)
            if num_match:
                text.append(f"  {num_match.group(1)}. ", style="cyan")
                text.append(num_match.group(2) + "\n", style="white")
                continue

            # Bullet list
            bullet_match = re.match(r'^[-*+]\s+(.*)$', line)
            if bullet_match:
                text.append("  • ", style="cyan")
                text.append(bullet_match.group(1) + "\n", style="white")
                continue

            text.append(line + "\n")

        return text


class HorizontalRuleRenderer(BlockRenderer):
    """Renderiza horizontal rules."""
    block_type = BlockType.HORIZONTAL_RULE
    pattern = r'^([-*_]){3,}\s*$'
    priority = 70

    def render(self, block: BlockInfo) -> RenderableType:
        return Text("─" * 60, style="dim")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def detect_block_type(line: str) -> BlockType:
    """Detecta tipo de bloco (shortcut)."""
    return BlockRendererRegistry.detect_block_type(line)


def render_block(block: BlockInfo) -> RenderableType:
    """Renderiza bloco (shortcut)."""
    return BlockRendererRegistry.render_block(block)


def list_renderers() -> List[str]:
    """Lista renderers registrados (shortcut)."""
    return BlockRendererRegistry.list_renderers()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Core types
    'BlockType',
    'BlockInfo',
    'BlockRenderer',
    'BlockRendererRegistry',

    # Built-in renderers
    'ParagraphRenderer',
    'HeadingRenderer',
    'CodeFenceRenderer',
    'TableRenderer',
    'ChecklistRenderer',
    'ToolCallRenderer',
    'StatusBadgeRenderer',
    'DiffBlockRenderer',
    'BlockquoteRenderer',
    'ListRenderer',
    'HorizontalRuleRenderer',

    # Convenience functions
    'detect_block_type',
    'render_block',
    'list_renderers',
]
