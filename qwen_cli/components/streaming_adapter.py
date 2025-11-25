"""
Streaming Adapter - Bridge between qwen_cli and streaming components.

CORRIGE AIR GAPS:
- [x] Entry point usa qwen_cli.app, não qwen_dev_cli.tui
- [x] Componentes órfãos agora conectados via este adapter
- [x] Interface compatível com ResponseView.append_chunk()

Este adapter expõe uma interface sync-compatible para uso em
ResponseView.append_chunk() que é chamada de forma síncrona,
mas internamente usa os componentes async de streaming.

Autor: JuanCS Dev
Data: 2025-11-25
"""

from typing import Optional, Callable
import asyncio
import threading

from textual.widgets import Static
from textual.containers import Container
from textual.reactive import reactive
from textual.message import Message

from rich.text import Text
from rich.markdown import Markdown as RichMarkdown
from rich.console import RenderableType, Group

# Import dos componentes de streaming de qwen_dev_cli
from qwen_dev_cli.tui.components.block_detector import BlockDetector
from qwen_dev_cli.tui.components.streaming_markdown import (
    BlockWidgetFactory,
    RenderMode,
    PerformanceMetrics,
)


class StreamingResponseWidget(Static):
    """
    Drop-in replacement for SelectableStatic with streaming markdown.

    Interface compatível com ResponseView.append_chunk() - método SYNC!

    Features:
    - Markdown rendering durante streaming
    - Detecção de blocos (code, table, checklist)
    - Renderização especializada por tipo de bloco
    - Cursor pulsante durante streaming
    - Fallback para plain text em caso de performance baixa

    Uso:
        # Em ResponseView.append_chunk():
        if self._response_widget is None:
            self._response_widget = StreamingResponseWidget()
            self.mount(self._response_widget)

        self._response_widget.append_chunk(chunk)  # SYNC!
    """

    DEFAULT_CSS = """
    StreamingResponseWidget {
        width: 100%;
        height: auto;
        min-height: 1;
    }

    StreamingResponseWidget.streaming {
        border-left: solid $accent 2;
        padding-left: 1;
    }

    StreamingResponseWidget.plain-mode {
        border-left: dashed yellow 1;
    }
    """

    # Cursor animation frames
    CURSOR_FRAMES = ["▋", "▌", "▍", "▎", "▏", " ", "▏", "▎", "▍", "▌"]

    # Reactive properties
    is_streaming = reactive(False)

    class StreamCompleted(Message):
        """Emitido quando streaming termina."""
        def __init__(self, content: str, metrics: PerformanceMetrics):
            self.content = content
            self.metrics = metrics
            super().__init__()

    def __init__(
        self,
        *args,
        enable_markdown: bool = True,
        **kwargs
    ):
        """
        Inicializa StreamingResponseWidget.

        Args:
            enable_markdown: Habilita renderização markdown (default: True)
        """
        super().__init__(*args, **kwargs)

        self._content = ""
        self._enable_markdown = enable_markdown

        # Streaming components
        self._block_detector = BlockDetector()
        self._widget_factory = BlockWidgetFactory()
        self._metrics = PerformanceMetrics()

        # Cursor state with thread-safety lock
        self._cursor_index = 0
        self._cursor_lock = threading.Lock()  # Protege _cursor_index
        self._cursor_task: Optional[asyncio.Task] = None

        # Render mode
        self._render_mode = RenderMode.MARKDOWN if enable_markdown else RenderMode.PLAIN_TEXT

        # Flag para cleanup seguro
        self._is_finalizing = False

    def on_mount(self) -> None:
        """Chamado quando widget é montado."""
        self.is_streaming = True
        self.add_class("streaming")

        # Inicia animação do cursor
        self._cursor_task = asyncio.create_task(self._animate_cursor())

    def append_chunk(self, chunk: str) -> None:
        """
        Append chunk - SYNC interface compatível com ResponseView.

        Esta é a interface principal. É chamada de forma síncrona
        pelo ResponseView.append_chunk().

        Args:
            chunk: Texto a adicionar ao stream
        """
        self._content += chunk

        # Processa com block detector (incremental)
        self._block_detector.process_chunk(chunk)

        # Atualiza display
        self._update_display()

    def _update_display(self) -> None:
        """Atualiza o display com conteúdo atual."""
        if self._is_finalizing:
            return  # Não atualiza durante finalização

        if self._render_mode == RenderMode.PLAIN_TEXT:
            renderable = self._render_plain_text()
        else:
            try:
                renderable = self._render_with_blocks()
            except Exception as e:
                # Log para debugging (não silencia mais)
                import logging
                logging.warning(f"StreamingResponseWidget render error: {e}")
                renderable = self._render_plain_text()

        self.update(renderable)

    def _get_cursor_index(self) -> int:
        """Thread-safe access ao cursor index."""
        with self._cursor_lock:
            return self._cursor_index

    def _advance_cursor(self) -> None:
        """Thread-safe advance do cursor."""
        with self._cursor_lock:
            self._cursor_index = (self._cursor_index + 1) % len(self.CURSOR_FRAMES)

    def _render_plain_text(self) -> Text:
        """Renderiza como plain text."""
        text = Text(self._content)

        # Cursor pulsante (thread-safe)
        if self.is_streaming and not self._is_finalizing:
            cursor = self.CURSOR_FRAMES[self._get_cursor_index()]
            text.append(cursor, style="bold bright_cyan")

        return text

    def _render_with_blocks(self) -> RenderableType:
        """Renderiza usando Widget Factory para blocos especializados."""
        blocks = self._block_detector.get_all_blocks()

        if not blocks:
            # Sem blocos, usa markdown simples
            content = self._content
            if self.is_streaming and not self._is_finalizing:
                content += self.CURSOR_FRAMES[self._get_cursor_index()]
            try:
                return RichMarkdown(content)
            except Exception as e:
                import logging
                logging.warning(f"RichMarkdown error: {e}")
                return Text(content)

        # Renderiza cada bloco com widget especializado
        renderables = []
        for block in blocks:
            rendered = self._widget_factory.render_block(block)
            renderables.append(rendered)

        # Cursor no final (thread-safe)
        if self.is_streaming and not self._is_finalizing:
            cursor_text = Text()
            cursor_text.append(self.CURSOR_FRAMES[self._get_cursor_index()], style="bold bright_cyan")
            renderables.append(cursor_text)

        return Group(*renderables) if renderables else Text("")

    async def _animate_cursor(self) -> None:
        """Anima o cursor durante streaming."""
        while self.is_streaming and not self._is_finalizing:
            self._advance_cursor()  # Thread-safe
            self._update_display()
            await asyncio.sleep(0.08)  # 80ms per frame

    async def finalize(self) -> None:
        """
        Finaliza streaming e aplica formatação final.

        Deve ser chamado quando o streaming terminar.
        """
        # Seta flag ANTES para evitar race conditions
        self._is_finalizing = True
        self.is_streaming = False
        self.remove_class("streaming")

        # Cancela animação do cursor de forma segura
        if self._cursor_task and not self._cursor_task.done():
            self._cursor_task.cancel()
            try:
                await self._cursor_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                import logging
                logging.warning(f"Error cancelling cursor task: {e}")
            finally:
                self._cursor_task = None

        # Render final (sem cursor)
        self._is_finalizing = False  # Permite render final
        self._update_display()

        # Emite evento
        self.post_message(self.StreamCompleted(self._content, self._metrics))

    def finalize_sync(self) -> None:
        """
        Versão sync de finalize() para uso em contextos síncronos.

        Usa call_later para executar a versão async.
        """
        # Seta flags imediatamente para evitar race conditions
        self._is_finalizing = True
        self.is_streaming = False
        self.remove_class("streaming")

        # Agenda finalização async
        self.call_later(self._finalize_async)

    async def _finalize_async(self) -> None:
        """Helper async para finalize_sync."""
        if self._cursor_task and not self._cursor_task.done():
            self._cursor_task.cancel()
            try:
                await self._cursor_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                import logging
                logging.warning(f"Error cancelling cursor task: {e}")
            finally:
                self._cursor_task = None

        # Render final
        self._is_finalizing = False
        self._update_display()
        self.post_message(self.StreamCompleted(self._content, self._metrics))

    def get_content(self) -> str:
        """Retorna o conteúdo acumulado."""
        return self._content

    def get_metrics(self) -> PerformanceMetrics:
        """Retorna métricas de performance."""
        return self._metrics

    def set_render_mode(self, mode: str) -> None:
        """
        Define modo de renderização.

        Args:
            mode: "markdown" ou "plain_text"
        """
        if mode == "markdown":
            self._render_mode = RenderMode.MARKDOWN
            self.remove_class("plain-mode")
        else:
            self._render_mode = RenderMode.PLAIN_TEXT
            self.add_class("plain-mode")

        self._update_display()


class StreamingMarkdownAdapter:
    """
    Adapter de alto nível para integração com ResponseView.

    Encapsula a lógica de criação e gerenciamento do widget,
    expondo uma interface ainda mais simples.

    Uso:
        adapter = StreamingMarkdownAdapter(response_view)
        adapter.start()
        for chunk in stream:
            adapter.append(chunk)
        adapter.finish()
    """

    def __init__(
        self,
        container: Container,
        on_complete: Optional[Callable[[str], None]] = None,
    ):
        """
        Inicializa o adapter.

        Args:
            container: Container onde montar o widget (ex: ResponseView)
            on_complete: Callback chamado quando streaming termina
        """
        self._container = container
        self._on_complete = on_complete
        self._widget: Optional[StreamingResponseWidget] = None
        self._content = ""

    def start(self) -> StreamingResponseWidget:
        """
        Inicia sessão de streaming.

        Returns:
            Widget criado
        """
        self._widget = StreamingResponseWidget()
        self._container.mount(self._widget)
        self._content = ""
        return self._widget

    def append(self, chunk: str) -> None:
        """
        Adiciona chunk ao stream.

        Args:
            chunk: Texto a adicionar
        """
        if self._widget:
            self._widget.append_chunk(chunk)
            self._content += chunk

    def finish(self) -> str:
        """
        Finaliza streaming.

        Returns:
            Conteúdo completo
        """
        if self._widget:
            self._widget.finalize_sync()

            if self._on_complete:
                self._on_complete(self._content)

        return self._content

    def get_widget(self) -> Optional[StreamingResponseWidget]:
        """Retorna o widget atual."""
        return self._widget

    def get_content(self) -> str:
        """Retorna o conteúdo acumulado."""
        return self._content
