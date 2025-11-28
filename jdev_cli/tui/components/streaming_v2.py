"""
Streaming V2 - Scalable Streaming Response System.

ARQUITETURA ESCALÁVEL:
- BlockRendererRegistry para detecção e renderização
- BlockDetectorV2 para state machine
- Zero config para adicionar novos tipos

Para adicionar novo tipo de bloco:
1. Criar classe que herda de BlockRenderer
2. Pronto! Auto-registrado.

Autor: JuanCS Dev
Data: 2025-11-25
"""

from __future__ import annotations

import asyncio
import threading
from typing import Optional, List
from dataclasses import dataclass

from textual.widgets import Static
from textual.reactive import reactive
from textual.message import Message

from rich.text import Text
from rich.console import RenderableType, Group

from .block_renderers import (
    render_block, list_renderers
)
from .block_detector_v2 import BlockDetectorV2


@dataclass
class StreamingMetrics:
    """Métricas de performance do streaming."""
    chunks_processed: int = 0
    blocks_detected: int = 0
    render_errors: int = 0


class StreamingResponseV2(Static):
    """
    Streaming Response Widget V2 - Arquitetura Escalável.

    Features:
    - Auto-detecção de blocos via registry
    - Auto-renderização via registry
    - Cursor pulsante durante streaming
    - Fallback seguro para erros

    Uso:
        widget = StreamingResponseV2()
        container.mount(widget)
        widget.append_chunk("# Hello\\n")
        widget.append_chunk("```python\\nprint('hi')\\n```\\n")
        widget.finalize_sync()
    """

    DEFAULT_CSS = """
    StreamingResponseV2 {
        width: 100%;
        height: auto;
        min-height: 1;
    }

    StreamingResponseV2.streaming {
        border-left: solid #00d4aa;
        padding-left: 1;
    }
    """

    CURSOR_FRAMES = ["▋", "▌", "▍", "▎", "▏", " ", "▏", "▎", "▍", "▌"]

    is_streaming = reactive(False)

    class StreamCompleted(Message):
        """Emitido quando streaming termina."""
        def __init__(self, content: str, metrics: StreamingMetrics):
            self.content = content
            self.metrics = metrics
            super().__init__()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._content = ""
        self._detector = BlockDetectorV2()
        self._metrics = StreamingMetrics()

        # Cursor state
        self._cursor_index = 0
        self._cursor_lock = threading.Lock()
        self._cursor_task: Optional[asyncio.Task] = None
        self._is_finalizing = False

    def on_mount(self) -> None:
        """Chamado quando widget é montado."""
        self.is_streaming = True
        self.add_class("streaming")
        self._cursor_task = asyncio.create_task(self._animate_cursor())

    def append_chunk(self, chunk: str) -> None:
        """
        Append chunk - SYNC interface.

        Args:
            chunk: Texto a adicionar ao stream
        """
        self._content += chunk
        self._metrics.chunks_processed += 1

        # Processa com detector
        self._detector.process_chunk(chunk)
        self._metrics.blocks_detected = len(self._detector.get_all_blocks())

        # Atualiza display
        self._update_display()

    def _update_display(self) -> None:
        """Atualiza o display com conteúdo atual."""
        if self._is_finalizing:
            return

        try:
            renderable = self._create_renderable()
            self.update(renderable)
        except Exception as e:
            self._metrics.render_errors += 1
            self.update(Text(self._content))

    def _get_cursor(self) -> str:
        """Thread-safe cursor access."""
        with self._cursor_lock:
            return self.CURSOR_FRAMES[self._cursor_index]

    def _advance_cursor(self) -> None:
        """Thread-safe cursor advance."""
        with self._cursor_lock:
            self._cursor_index = (self._cursor_index + 1) % len(self.CURSOR_FRAMES)

    def _create_renderable(self) -> RenderableType:
        """Cria renderable usando registry."""
        blocks = self._detector.get_all_blocks()

        if not blocks:
            text = Text(self._content)
            if self.is_streaming and not self._is_finalizing:
                text.append(self._get_cursor(), style="bold bright_cyan")
            return text

        # Renderiza cada bloco via registry
        renderables: List[RenderableType] = []

        for block in blocks:
            try:
                rendered = render_block(block)
                renderables.append(rendered)
            except Exception:
                renderables.append(Text(block.content))

        # Cursor no final
        if self.is_streaming and not self._is_finalizing:
            cursor_text = Text()
            cursor_text.append(self._get_cursor(), style="bold bright_cyan")
            renderables.append(cursor_text)

        return Group(*renderables) if renderables else Text("")

    async def _animate_cursor(self) -> None:
        """Anima o cursor durante streaming."""
        while self.is_streaming and not self._is_finalizing:
            self._advance_cursor()
            self._update_display()
            await asyncio.sleep(0.08)

    async def finalize(self) -> None:
        """Finaliza streaming."""
        self._is_finalizing = True
        self.is_streaming = False
        self.remove_class("streaming")

        if self._cursor_task and not self._cursor_task.done():
            self._cursor_task.cancel()
            try:
                await self._cursor_task
            except asyncio.CancelledError:
                pass
            self._cursor_task = None

        self._is_finalizing = False
        self._update_display()
        self.post_message(self.StreamCompleted(self._content, self._metrics))

    def finalize_sync(self) -> None:
        """Versão sync de finalize()."""
        self._is_finalizing = True
        self.is_streaming = False
        self.remove_class("streaming")
        self.call_later(self._finalize_async)

    async def _finalize_async(self) -> None:
        """Helper async para finalize_sync."""
        if self._cursor_task and not self._cursor_task.done():
            self._cursor_task.cancel()
            try:
                await self._cursor_task
            except asyncio.CancelledError:
                pass
            self._cursor_task = None

        self._is_finalizing = False
        self._update_display()
        self.post_message(self.StreamCompleted(self._content, self._metrics))

    def get_content(self) -> str:
        """Retorna conteúdo acumulado."""
        return self._content

    def get_metrics(self) -> StreamingMetrics:
        """Retorna métricas."""
        return self._metrics

    @staticmethod
    def list_supported_blocks() -> List[str]:
        """Lista tipos de blocos suportados."""
        return list_renderers()


# =============================================================================
# EXAMPLE: Adding a new block type (for documentation)
# =============================================================================

# To add a new block type, just create a class:
#
# from jdev_cli.tui.components.block_renderers import BlockRenderer, BlockType
#
# class MermaidRenderer(BlockRenderer):
#     """Renderiza diagramas Mermaid."""
#     block_type = BlockType.MERMAID_DIAGRAM
#     pattern = r'^```mermaid'
#     priority = 91
#
#     def render(self, block: BlockInfo) -> RenderableType:
#         return Panel(
#             Text(block.content, style="cyan"),
#             title="[bold]Mermaid Diagram[/bold]",
#             border_style="blue"
#         )
#
# That's it! The renderer is auto-registered and will be used automatically.


__all__ = [
    'StreamingResponseV2',
    'StreamingMetrics',
]
