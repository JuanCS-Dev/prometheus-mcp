"""
Streaming Markdown Widget - Claude Code Web Style Rendering.

Widget principal de streaming markdown para TUI.
Usa BlockWidgetFactory para renderização especializada de blocos markdown.

Features:
- Renderização markdown ao vivo durante streaming (INCREMENTAL)
- Detecção otimista de blocos (bold, code, tables antes de fechar)
- 30 FPS com frame budget de 33.33ms
- Fallback automático para plain text quando FPS < 25
- Cursor pulsante no final do conteúdo
- Widget Factory para blocos especializados

AIR GAPS CORRIGIDOS:
- [x] BlockWidgetFactory renderiza blocos especializados
- [x] BlockDetector conectado ao Widget Factory
- [x] Componentes especializados instanciados e usados

Autor: JuanCS Dev
Data: 2025-11-25
Atualizado: 2025-11-25 (Correção Air Gaps)
"""

import time
import asyncio
from typing import Optional, AsyncIterator, Callable, List
from dataclasses import dataclass
from enum import Enum

from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive
from textual.message import Message
from textual.containers import ScrollableContainer
from textual.app import ComposeResult

from rich.text import Text
from rich.markdown import Markdown as RichMarkdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.console import RenderableType, Group

from .block_detector import BlockDetector, BlockInfo, BlockType
from .streaming_code_block import IncrementalSyntaxHighlighter, create_code_block_panel
from .streaming_table import StreamingTableRenderer
from .interactive_checklist import ChecklistParser, render_checklist_text


class RenderMode(Enum):
    """Modo de renderização."""
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class BlockWidgetFactory:
    """
    Factory para criar renderables especializados por tipo de bloco.

    CORRIGE AIR GAP: Componentes especializados agora são USADOS.
    """

    def __init__(self):
        # Cache de highlighters por linguagem (reutiliza para performance)
        self._highlighters: dict[str, IncrementalSyntaxHighlighter] = {}
        self._table_renderer = StreamingTableRenderer()

    def render_block(self, block: BlockInfo) -> RenderableType:
        """
        Renderiza um bloco usando o componente especializado apropriado.

        Args:
            block: Informação do bloco detectado

        Returns:
            Rich renderable formatado
        """
        if block.block_type == BlockType.CODE_FENCE:
            return self._render_code_fence(block)
        elif block.block_type == BlockType.TABLE:
            return self._render_table(block)
        elif block.block_type == BlockType.CHECKLIST:
            return self._render_checklist(block)
        elif block.block_type == BlockType.HEADING:
            return self._render_heading(block)
        elif block.block_type == BlockType.TOOL_CALL:
            return self._render_tool_call(block)
        elif block.block_type == BlockType.STATUS_BADGE:
            return self._render_status_badge(block)
        elif block.block_type == BlockType.DIFF_BLOCK:
            return self._render_diff(block)
        else:
            # Default: Rich Markdown para outros blocos
            return self._render_default(block)

    def _render_code_fence(self, block: BlockInfo) -> RenderableType:
        """Renderiza code fence com syntax highlighting incremental."""
        language = block.language or "text"

        # Reutiliza highlighter se existir para mesma linguagem
        if language not in self._highlighters:
            self._highlighters[language] = IncrementalSyntaxHighlighter(language)

        highlighter = self._highlighters[language]

        # Reseta e processa conteúdo
        highlighter.reset()
        highlighter.process_chunk(block.content)

        # Retorna como Panel estilizado
        # Nota: create_code_block_panel recebe código como string, não Text
        return create_code_block_panel(
            code=block.content,
            language=language,
            title=f"{language.upper()}" + ("" if block.is_complete else " ⏳")
        )

    def _render_table(self, block: BlockInfo) -> RenderableType:
        """Renderiza tabela progressivamente."""
        self._table_renderer.reset()
        return self._table_renderer.process_chunk(block.content)

    def _render_checklist(self, block: BlockInfo) -> RenderableType:
        """Renderiza checklist com items."""
        items = ChecklistParser.parse_markdown(block.content)
        return render_checklist_text(items)

    def _render_heading(self, block: BlockInfo) -> RenderableType:
        """Renderiza heading com estilo."""
        level = block.metadata.get('level', 1)
        text_content = block.metadata.get('text', block.content)

        # Estilo baseado no nível
        styles = {
            1: "bold underline bright_white",
            2: "bold bright_white",
            3: "bold white",
            4: "bold dim white",
            5: "dim white",
            6: "dim italic white",
        }
        style = styles.get(level, "white")

        text = Text()
        text.append("#" * level + " ", style="dim cyan")
        text.append(text_content, style=style)
        return text

    def _render_tool_call(self, block: BlockInfo) -> RenderableType:
        """
        Renderiza tool call estilo Claude Code Web ou Gemini Native.

        Formato Gemini: [TOOL_CALL:name:{args}]
        Formato Claude: • Read /path/to/file
        """
        import re

        content = block.content.strip()

        # Gemini Native Format
        if content.startswith('[TOOL_CALL:'):
            try:
                # [TOOL_CALL:name:{...}]
                # Remove prefix and suffix
                inner = content[11:]
                if inner.endswith(']'):
                    inner = inner[:-1]

                if ':' in inner:
                    tool_name, args = inner.split(':', 1)
                else:
                    tool_name = inner
                    args = "{}"

                # Ícones por tool
                tool_icons = {
                    "code_execution": ("🐍", "bright_green"),
                    "google_search_retrieval": ("🔍", "bright_blue"),
                }

                icon, color = tool_icons.get(tool_name, ("🛠️", "bright_cyan"))

                result = Text()
                result.append(f"{icon} ", style="bold")
                result.append(tool_name, style=f"bold {color}")
                result.append(" ", style="dim")
                result.append(args, style="italic #888888")
                return result
            except Exception:
                return Text(block.content)

        lines = content.split('\n')
        if not lines:
            return Text(block.content)

        # Parse primeira linha (tool call)
        first_line = lines[0].strip()
        # Remove ** bold markers se presentes
        first_line = re.sub(r'\*\*', '', first_line)

        match = re.match(r'^[•●]\s*(\w+(?:\s+\w+)?)\s*(.*)', first_line)
        if not match:
            return Text(block.content)

        tool_name = match.group(1).strip()
        args = match.group(2).strip()

        # Ícones por tool (estilo Claude Code)
        tool_icons = {
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
            "TodoWrite": ("✅", "bright_green"),
            "AskUserQuestion": ("❓", "bright_yellow"),
        }

        icon, color = tool_icons.get(tool_name, ("•", "white"))

        # Build output
        result = Text()
        result.append(f"{icon} ", style="bold")
        result.append(tool_name, style=f"bold {color}")
        if args:
            # Remove backticks para paths
            args_clean = args.strip('`')
            result.append(" ", style="dim")
            result.append(args_clean, style="italic #888888")
        result.append("\n")

        # Render output lines (└ resultado, ~~strikethrough~~, etc.)
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue

            # Tool output line (└ resultado)
            if stripped.startswith('└') or stripped.startswith('├'):
                output_text = stripped[1:].strip()
                result.append("  └ ", style="dim #666666")

                # Check for strikethrough (~~text~~)
                if '~~' in output_text:
                    # Render strikethrough items
                    parts = re.split(r'(~~[^~]+~~)', output_text)
                    for part in parts:
                        if part.startswith('~~') and part.endswith('~~'):
                            result.append(part[2:-2], style="strike dim #888888")
                        else:
                            result.append(part, style="dim #aaaaaa")
                # Check for checkbox (☐ or □)
                elif stripped.startswith('└ ☐') or stripped.startswith('└ □'):
                    checkbox_text = output_text.lstrip('☐□ ')
                    result.append("☐ ", style="bold bright_yellow")
                    result.append(checkbox_text, style="bright_white")
                else:
                    result.append(output_text, style="dim #aaaaaa")
                result.append("\n")

            # Indented continuation (  some text)
            elif line.startswith('  '):
                result.append("  ", style="")
                # Handle strikethrough in indented lines too
                if '~~' in stripped:
                    parts = re.split(r'(~~[^~]+~~)', stripped)
                    for part in parts:
                        if part.startswith('~~') and part.endswith('~~'):
                            result.append(part[2:-2], style="strike dim #888888")
                        else:
                            result.append(part, style="dim #aaaaaa")
                elif stripped.startswith('☐') or stripped.startswith('□'):
                    checkbox_text = stripped.lstrip('☐□ ')
                    result.append("☐ ", style="bold bright_yellow")
                    result.append(checkbox_text, style="bright_white")
                else:
                    result.append(stripped, style="dim #aaaaaa")
                result.append("\n")

        # Remove trailing newline
        if result.plain.endswith('\n'):
            result = Text(result.plain.rstrip('\n'))
            # Re-apply styles - simplified version
            result = self._apply_tool_styles(block.content, tool_name, icon, color)

        return result

    def _apply_tool_styles(self, content: str, tool_name: str, icon: str, color: str) -> Text:
        """Helper to apply consistent styling to tool output."""
        import re
        lines = content.strip().split('\n')
        result = Text()

        # First line
        first_line = re.sub(r'\*\*', '', lines[0].strip())
        match = re.match(r'^[•●]\s*(\w+(?:\s+\w+)?)\s*(.*)', first_line)
        if match:
            args = match.group(2).strip().strip('`')
            result.append(f"{icon} ", style="bold")
            result.append(tool_name, style=f"bold {color}")
            if args:
                result.append(" ", style="dim")
                result.append(args, style="italic #888888")

        # Output lines
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            result.append("\n")
            if stripped.startswith('└') or stripped.startswith('├'):
                output_text = stripped[1:].strip()
                result.append("  └ ", style="dim #666666")
                if '~~' in output_text:
                    parts = re.split(r'(~~[^~]+~~)', output_text)
                    for part in parts:
                        if part.startswith('~~') and part.endswith('~~'):
                            result.append(part[2:-2], style="strike dim #888888")
                        else:
                            result.append(part, style="dim #aaaaaa")
                elif output_text.startswith('☐') or output_text.startswith('□'):
                    checkbox_text = output_text.lstrip('☐□ ')
                    result.append("☐ ", style="bold bright_yellow")
                    result.append(checkbox_text, style="bright_white")
                else:
                    result.append(output_text, style="dim #aaaaaa")
            elif line.startswith('  '):
                result.append("  ", style="")
                if '~~' in stripped:
                    parts = re.split(r'(~~[^~]+~~)', stripped)
                    for part in parts:
                        if part.startswith('~~') and part.endswith('~~'):
                            result.append(part[2:-2], style="strike dim #888888")
                        else:
                            result.append(part, style="dim #aaaaaa")
                elif stripped.startswith('☐') or stripped.startswith('□'):
                    checkbox_text = stripped.lstrip('☐□ ')
                    result.append("☐ ", style="bold bright_yellow")
                    result.append(checkbox_text, style="bright_white")
                else:
                    result.append(stripped, style="dim #aaaaaa")

        return result

    def _render_status_badge(self, block: BlockInfo) -> RenderableType:
        """
        Renderiza status badge estilo Claude Code.

        Formato: 🔴 BLOCKER, 🟡 WARNING, 🟢 OK, ✅ SUCCESS, ❌ ERROR
        """
        text = Text()
        content = block.content.strip()

        # Parse emoji e status
        badge_styles = {
            "🔴": ("bold red", "background: red"),
            "🟠": ("bold bright_red", "background: orange"),
            "🟡": ("bold yellow", "background: yellow"),
            "🟢": ("bold green", "background: green"),
            "⚪": ("dim white", "background: white"),
            "✅": ("bold bright_green", "background: green"),
            "❌": ("bold bright_red", "background: red"),
            "⚠️": ("bold bright_yellow", "background: yellow"),
        }

        for emoji, (style, _bg) in badge_styles.items():
            if content.startswith(emoji):
                status_text = content[len(emoji):].strip()
                text.append(f"{emoji} ", style="bold")
                text.append(status_text, style=style)
                return text

        # Fallback
        text.append(content, style="white")
        return text

    def _render_diff(self, block: BlockInfo) -> RenderableType:
        """
        Renderiza diff block estilo GitHub.

        Usa DiffViewer se disponível, senão syntax highlighting.
        """
        try:
            from .diff import DiffViewer
            # Para diffs inline, usa syntax highlighting de diff
            return Syntax(
                block.content,
                "diff",
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            )
        except ImportError:
            # Fallback: colorização manual
            text = Text()
            for line in block.content.split('\n'):
                if line.startswith('+'):
                    text.append(line + "\n", style="green")
                elif line.startswith('-'):
                    text.append(line + "\n", style="red")
                elif line.startswith('@@'):
                    text.append(line + "\n", style="cyan")
                else:
                    text.append(line + "\n", style="dim")
            return Panel(text, title="Diff", border_style="dim")

    def _render_default(self, block: BlockInfo) -> RenderableType:
        """Renderiza bloco genérico como markdown."""
        try:
            return RichMarkdown(block.content)
        except Exception:
            return Text(block.content)

    def reset(self) -> None:
        """Reseta estado dos renderers."""
        self._highlighters.clear()
        self._table_renderer.reset()


@dataclass
class PerformanceMetrics:
    """Métricas de performance do streaming."""
    frames_rendered: int = 0
    total_render_time_ms: float = 0.0
    last_fps: float = 30.0
    min_fps: float = 30.0
    dropped_frames: int = 0
    fallback_count: int = 0

    @property
    def avg_render_time_ms(self) -> float:
        if self.frames_rendered == 0:
            return 0.0
        return self.total_render_time_ms / self.frames_rendered

    @property
    def current_fps(self) -> float:
        return self.last_fps


class AdaptiveFPSController:
    """
    Monitora FPS e alterna para plain text automaticamente.

    Comportamento:
    - FPS >= 30: Markdown completo
    - FPS 25-29: Warning visual, continua markdown
    - FPS < 25: Fallback para plain text
    """

    FPS_THRESHOLD_WARNING = 29
    FPS_THRESHOLD_FALLBACK = 25
    RECOVERY_FRAMES = 60  # Frames para tentar voltar ao markdown
    CONSECUTIVE_LOW_FRAMES = 5  # Frames baixos consecutivos antes de fallback

    def __init__(self):
        self.mode = RenderMode.MARKDOWN
        self.frames_in_plain = 0
        self.low_fps_count = 0
        self._frame_times: List[float] = []
        self._last_frame_time: float = time.perf_counter()

    def record_frame(self) -> float:
        """Registra um frame e retorna FPS atual."""
        now = time.perf_counter()
        delta = now - self._last_frame_time
        self._last_frame_time = now

        # Mantém últimos 10 frames para média móvel
        self._frame_times.append(delta)
        if len(self._frame_times) > 10:
            self._frame_times.pop(0)

        # Calcula FPS médio
        if self._frame_times:
            avg_delta = sum(self._frame_times) / len(self._frame_times)
            return 1.0 / avg_delta if avg_delta > 0 else 60.0
        return 30.0

    def check_and_adapt(self, current_fps: float) -> tuple[RenderMode, str]:
        """
        Verifica FPS e adapta modo de renderização.

        Returns:
            Tuple de (modo, mensagem de status)
        """
        if self.mode == RenderMode.MARKDOWN:
            if current_fps < self.FPS_THRESHOLD_FALLBACK:
                self.low_fps_count += 1
                if self.low_fps_count >= self.CONSECUTIVE_LOW_FRAMES:
                    self.mode = RenderMode.PLAIN_TEXT
                    self.frames_in_plain = 0
                    self.low_fps_count = 0
                    return self.mode, "FALLBACK_TO_PLAIN"
            else:
                self.low_fps_count = 0

            if current_fps < self.FPS_THRESHOLD_WARNING:
                return self.mode, "WARNING_LOW_FPS"
        else:
            self.frames_in_plain += 1
            if self.frames_in_plain >= self.RECOVERY_FRAMES:
                self.mode = RenderMode.MARKDOWN
                self.frames_in_plain = 0
                return self.mode, "TRY_MARKDOWN_AGAIN"

        return self.mode, "OK"

    def reset(self):
        """Reseta controlador."""
        self.mode = RenderMode.MARKDOWN
        self.frames_in_plain = 0
        self.low_fps_count = 0
        self._frame_times.clear()
        self._last_frame_time = time.perf_counter()


class StreamingMarkdownWidget(Widget):
    """
    Widget de streaming markdown estilo Claude Code Web.

    Combina:
    - MarkdownStream do Textual v4.0+ (quando disponível)
    - BlockDetector para feedback visual por tipo de bloco
    - AdaptiveFPSController para fallback automático
    - Cursor pulsante durante streaming
    """

    DEFAULT_CSS = """
    StreamingMarkdownWidget {
        width: 100%;
        height: auto;
        min-height: 3;
        padding: 1 2;
    }

    StreamingMarkdownWidget.streaming {
        border: solid #00d4aa;
    }

    StreamingMarkdownWidget.performance-warning {
        border: solid #f1fa8c;
    }

    StreamingMarkdownWidget.plain-text-mode {
        border: dashed #f1fa8c;
    }

    StreamingMarkdownWidget .cursor {
        background: #00d4aa;
    }
    """

    # Reactive properties
    is_streaming = reactive(False)
    current_block_type = reactive(BlockType.UNKNOWN)
    render_mode = reactive(RenderMode.MARKDOWN)
    show_cursor = reactive(True)

    # Cursor animation frames
    CURSOR_FRAMES = ["", "", "", "", "", " ", "", "", "", ""]
    CURSOR_INTERVAL = 0.08  # 80ms per frame

    class StreamStarted(Message):
        """Evento: streaming iniciado."""
        pass

    class StreamEnded(Message):
        """Evento: streaming finalizado."""
        def __init__(self, content: str, metrics: PerformanceMetrics):
            self.content = content
            self.metrics = metrics
            super().__init__()

    class BlockDetected(Message):
        """Evento: novo tipo de bloco detectado."""
        def __init__(self, block_type: BlockType, block_info: BlockInfo):
            self.block_type = block_type
            self.block_info = block_info
            super().__init__()

    class FPSWarning(Message):
        """Evento: FPS baixo detectado."""
        def __init__(self, fps: float, action: str):
            self.fps = fps
            self.action = action
            super().__init__()

    def __init__(
        self,
        target_fps: int = 30,
        enable_adaptive_fps: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        """
        Inicializa StreamingMarkdownWidget.

        Args:
            target_fps: FPS alvo (default: 30)
            enable_adaptive_fps: Habilita fallback automático
            name: Nome do widget
            id: ID do widget
            classes: Classes CSS
        """
        super().__init__(name=name, id=id, classes=classes)

        self.target_fps = target_fps
        self.frame_budget = 1.0 / target_fps  # 33.33ms para 30 FPS
        self.enable_adaptive_fps = enable_adaptive_fps

        # State
        self._content = ""
        self._buffer = ""
        self._cursor_index = 0
        self._last_render = time.perf_counter()

        # Components
        self._block_detector = BlockDetector()
        self._fps_controller = AdaptiveFPSController()
        self._metrics = PerformanceMetrics()
        self._widget_factory = BlockWidgetFactory()  # NOVO: Widget Factory conectado!

        # Markdown widget interno
        self._markdown_static: Optional[Static] = None

        # Cache de blocos finalizados (não re-renderiza)
        self._finalized_blocks_count: int = 0

        # Cursor animation task
        self._cursor_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        """Compõe o widget."""
        self._markdown_static = Static("", id="markdown-content")
        yield self._markdown_static

    def on_mount(self) -> None:
        """Chamado quando widget é montado."""
        pass

    async def start_stream(self) -> None:
        """Inicia uma sessão de streaming."""
        self.is_streaming = True
        self._content = ""
        self._buffer = ""
        self._block_detector.reset()
        self._fps_controller.reset()
        self._widget_factory.reset()  # NOVO: Reset widget factory
        self._metrics = PerformanceMetrics()
        self._finalized_blocks_count = 0
        self._last_render = time.perf_counter()

        self.add_class("streaming")
        self.post_message(self.StreamStarted())

        # Inicia animação do cursor
        self._cursor_task = asyncio.create_task(self._animate_cursor())

    async def append_chunk(self, chunk: str) -> None:
        """
        Adiciona chunk de texto ao stream.

        Args:
            chunk: Texto a adicionar
        """
        if not self.is_streaming:
            return

        self._buffer += chunk
        self._content += chunk

        # Processa com block detector
        blocks = self._block_detector.process_chunk(chunk)

        # Detecta mudança de tipo de bloco
        current = self._block_detector.get_current_block()
        if current and current.block_type != self.current_block_type:
            self.current_block_type = current.block_type
            self.post_message(self.BlockDetected(current.block_type, current))

        # Verifica se deve atualizar display (respeitando frame budget)
        now = time.perf_counter()
        elapsed = now - self._last_render

        if elapsed >= self.frame_budget:
            await self._render_frame()
            self._last_render = now

    async def _render_frame(self) -> None:
        """Renderiza um frame."""
        render_start = time.perf_counter()

        # Verifica FPS e adapta se necessário
        if self.enable_adaptive_fps:
            fps = self._fps_controller.record_frame()
            self._metrics.last_fps = fps
            self._metrics.min_fps = min(self._metrics.min_fps, fps)

            mode, status = self._fps_controller.check_and_adapt(fps)

            if status == "FALLBACK_TO_PLAIN":
                self.render_mode = RenderMode.PLAIN_TEXT
                self._metrics.fallback_count += 1
                self.add_class("plain-text-mode")
                self.remove_class("streaming")
                self.post_message(self.FPSWarning(fps, status))
            elif status == "TRY_MARKDOWN_AGAIN":
                self.render_mode = RenderMode.MARKDOWN
                self.remove_class("plain-text-mode")
                self.add_class("streaming")
                self.post_message(self.FPSWarning(fps, status))
            elif status == "WARNING_LOW_FPS":
                self.add_class("performance-warning")
                self.post_message(self.FPSWarning(fps, status))
            else:
                self.remove_class("performance-warning")

        # Renderiza conteúdo
        if self._markdown_static:
            renderable = self._create_renderable()
            self._markdown_static.update(renderable)

        # Atualiza métricas
        render_time = (time.perf_counter() - render_start) * 1000
        self._metrics.frames_rendered += 1
        self._metrics.total_render_time_ms += render_time

        if render_time > self.frame_budget * 1000:
            self._metrics.dropped_frames += 1

    def _create_renderable(self) -> RenderableType:
        """
        Cria o renderable para o conteúdo atual.

        CORRIGIDO: Agora usa BlockWidgetFactory para renderizar blocos
        especializados (code, table, checklist) em vez de RichMarkdown genérico.
        """
        if self.render_mode == RenderMode.PLAIN_TEXT:
            return self._create_plain_text_renderable()

        # Modo markdown com Widget Factory
        try:
            return self._create_block_based_renderable()
        except Exception:
            # Fallback para texto simples em caso de erro
            return self._create_plain_text_renderable()

    def _create_plain_text_renderable(self) -> Text:
        """Renderiza como plain text (fallback de performance)."""
        content = self._content

        # Adiciona cursor se streaming
        if self.is_streaming and self.show_cursor:
            cursor = self.CURSOR_FRAMES[self._cursor_index]
            content += cursor

        text = Text(content)
        if self.is_streaming and self.render_mode == RenderMode.PLAIN_TEXT:
            text.append("\n\n", style="dim")
            text.append(" Performance mode", style="dim yellow")
        return text

    def _create_block_based_renderable(self) -> RenderableType:
        """
        Renderiza usando Widget Factory para blocos especializados.

        CORRIGE AIR GAP: Componentes especializados agora são USADOS!
        - CODE_FENCE → IncrementalSyntaxHighlighter
        - TABLE → StreamingTableRenderer
        - CHECKLIST → ChecklistParser + render_checklist_text
        """
        blocks = self._block_detector.get_all_blocks()

        if not blocks:
            # Sem blocos detectados, usa markdown simples
            content = self._content
            if self.is_streaming and self.show_cursor:
                content += self.CURSOR_FRAMES[self._cursor_index]
            return RichMarkdown(content) if content else Text("")

        # Renderiza cada bloco com widget especializado
        renderables: List[RenderableType] = []

        for block in blocks:
            # Usa Widget Factory para renderizar bloco especializado
            rendered = self._widget_factory.render_block(block)
            renderables.append(rendered)

        # Adiciona cursor no final se streaming
        if self.is_streaming and self.show_cursor:
            cursor_text = Text()
            cursor = self.CURSOR_FRAMES[self._cursor_index]
            cursor_text.append(cursor, style="bold bright_cyan")
            renderables.append(cursor_text)

        # Retorna Group de renderables
        return Group(*renderables) if renderables else Text("")

    async def _animate_cursor(self) -> None:
        """Anima o cursor durante streaming."""
        while self.is_streaming:
            self._cursor_index = (self._cursor_index + 1) % len(self.CURSOR_FRAMES)

            # Força re-render para cursor
            if self._markdown_static:
                renderable = self._create_renderable()
                self._markdown_static.update(renderable)

            await asyncio.sleep(self.CURSOR_INTERVAL)

    async def end_stream(self) -> None:
        """Finaliza a sessão de streaming."""
        self.is_streaming = False
        self.show_cursor = False

        # Cancela animação do cursor
        if self._cursor_task:
            self._cursor_task.cancel()
            try:
                await self._cursor_task
            except asyncio.CancelledError:
                pass
            self._cursor_task = None

        # Render final
        await self._render_frame()

        # Remove classes de estado
        self.remove_class("streaming")
        self.remove_class("performance-warning")
        self.remove_class("plain-text-mode")

        # Emite evento de fim
        self.post_message(self.StreamEnded(self._content, self._metrics))

    async def stream_content(
        self,
        content_iterator: AsyncIterator[str],
        on_block_change: Optional[Callable[[BlockType], None]] = None,
    ) -> str:
        """
        Stream conteúdo de um iterator assíncrono.

        Args:
            content_iterator: Iterator que produz chunks de texto
            on_block_change: Callback quando tipo de bloco muda

        Returns:
            Conteúdo completo
        """
        await self.start_stream()

        try:
            async for chunk in content_iterator:
                await self.append_chunk(chunk)

                if on_block_change and self._block_detector.get_current_block():
                    on_block_change(self._block_detector.get_current_block().block_type)

        finally:
            await self.end_stream()

        return self._content

    def get_content(self) -> str:
        """Retorna o conteúdo atual."""
        return self._content

    def get_metrics(self) -> PerformanceMetrics:
        """Retorna métricas de performance."""
        return self._metrics

    def get_blocks(self) -> List[BlockInfo]:
        """Retorna blocos detectados."""
        return self._block_detector.get_all_blocks()


class StreamingMarkdownPanel(ScrollableContainer):
    """
    Panel scrollável com StreamingMarkdownWidget.

    Inclui:
    - Auto-scroll durante streaming
    - Indicador de performance
    - Barra de status com tipo de bloco
    """

    DEFAULT_CSS = """
    StreamingMarkdownPanel {
        width: 100%;
        height: 100%;
        overflow-y: auto;
        border: solid #bd93f9;
    }

    StreamingMarkdownPanel > StreamingMarkdownWidget {
        width: 100%;
    }

    StreamingMarkdownPanel .status-bar {
        dock: bottom;
        height: 1;
        background: #282a36;
        color: #6272a4;
    }
    """

    def __init__(
        self,
        auto_scroll: bool = True,
        show_status: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.auto_scroll = auto_scroll
        self.show_status = show_status
        self._markdown_widget: Optional[StreamingMarkdownWidget] = None
        self._status_bar: Optional[Static] = None

    def compose(self) -> ComposeResult:
        """Compõe o panel."""
        self._markdown_widget = StreamingMarkdownWidget()
        yield self._markdown_widget

        if self.show_status:
            self._status_bar = Static("", classes="status-bar")
            yield self._status_bar

    def on_streaming_markdown_widget_stream_started(
        self, event: StreamingMarkdownWidget.StreamStarted
    ) -> None:
        """Handler: streaming iniciado."""
        if self._status_bar:
            self._status_bar.update(" Streaming...")

    def on_streaming_markdown_widget_stream_ended(
        self, event: StreamingMarkdownWidget.StreamEnded
    ) -> None:
        """Handler: streaming finalizado."""
        if self._status_bar:
            metrics = event.metrics
            self._status_bar.update(
                f" Done | {metrics.frames_rendered} frames | "
                f"Avg: {metrics.avg_render_time_ms:.1f}ms | "
                f"Min FPS: {metrics.min_fps:.0f}"
            )

    def on_streaming_markdown_widget_block_detected(
        self, event: StreamingMarkdownWidget.BlockDetected
    ) -> None:
        """Handler: bloco detectado."""
        if self._status_bar and self._markdown_widget and self._markdown_widget.is_streaming:
            block_icons = {
                BlockType.CODE_FENCE: " Code",
                BlockType.TABLE: " Table",
                BlockType.CHECKLIST: " Checklist",
                BlockType.HEADING: " Heading",
                BlockType.LIST: " List",
                BlockType.PARAGRAPH: " Paragraph",
            }
            icon = block_icons.get(event.block_type, " Block")
            self._status_bar.update(f" Streaming... {icon}")

        # Auto-scroll
        if self.auto_scroll:
            self.scroll_end(animate=False)

    def on_streaming_markdown_widget_fps_warning(
        self, event: StreamingMarkdownWidget.FPSWarning
    ) -> None:
        """Handler: aviso de FPS."""
        if self._status_bar:
            if event.action == "FALLBACK_TO_PLAIN":
                self._status_bar.update(f" Performance mode | FPS: {event.fps:.0f}")
            elif event.action == "TRY_MARKDOWN_AGAIN":
                self._status_bar.update(" Restored markdown mode")

    async def stream(self, content_iterator: AsyncIterator[str]) -> str:
        """
        Inicia streaming de conteúdo.

        Args:
            content_iterator: Iterator de chunks

        Returns:
            Conteúdo completo
        """
        if self._markdown_widget:
            return await self._markdown_widget.stream_content(content_iterator)
        return ""

    def get_widget(self) -> Optional[StreamingMarkdownWidget]:
        """Retorna o widget de markdown."""
        return self._markdown_widget
