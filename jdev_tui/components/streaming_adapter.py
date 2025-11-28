"""
Streaming Adapter - Bridge between jdev_tui and streaming components.

CORRIGE AIR GAPS:
- [x] Entry point usa jdev_tui.app, não jdev_cli.tui
- [x] Componentes órfãos agora conectados via este adapter
- [x] Interface compatível com ResponseView.append_chunk()

Este adapter expõe uma interface sync-compatible para uso em
ResponseView.append_chunk() que é chamada de forma síncrona,
mas internamente usa os componentes async de streaming.

Autor: JuanCS Dev
Data: 2025-11-25
"""

from typing import Optional, Callable, List
import asyncio
import threading

from textual.widgets import Static
from textual.containers import Container
from textual.reactive import reactive
from textual.message import Message

from rich.text import Text
from rich.markdown import Markdown as RichMarkdown
from rich.console import RenderableType, Group

# Import dos componentes de streaming de jdev_cli
from jdev_cli.tui.components.block_detector import BlockDetector
from jdev_cli.tui.components.streaming_markdown import (
    BlockWidgetFactory,
    RenderMode,
    PerformanceMetrics,
)

# Import colors for brand consistency
from jdev_tui.core.output_formatter import Colors


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
        color: $foreground;
    }

    StreamingResponseWidget.streaming {
        border-left: solid $primary;
        padding-left: 1;
    }

    StreamingResponseWidget.plain-mode {
        border-left: dashed $warning;
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

        # Deduplication: track last N lines to detect LLM repetitions
        self._last_lines: List[str] = []
        self._max_line_history = 10

        # Tool call JSON buffer for multi-chunk JSON parsing
        self._json_buffer = ""

    def _sanitize_tool_call_json(self, chunk: str) -> str:
        """
        BLINDAGEM: Converte JSON tool calls em exibição amigável.

        Detecta padrões como:
        - {"tool": "bash_command", "args": {"command": "..."}}
        - {"name": "bash_command", "arguments": {"command": "..."}}
        - {"functionCall": {"name": "...", "args": {...}}}

        E converte para formato legível:
        ```bash
        sudo apt install ...
        ```
        """
        import re
        import json

        # Patterns para detectar tool calls JSON (ordem importa - mais específico primeiro)
        TOOL_PATTERNS = [
            # Nested PRIMEIRO: {"tool":{"tool":"bash_command","args":{...}}}
            (re.compile(r'\{"tool"\s*:\s*\{\s*"tool"\s*:\s*"(\w+)"\s*,\s*"args"\s*:\s*(\{[^{}]*\})\s*\}\s*\}', re.DOTALL), True),
            # {"tool": "bash_command", "args": {"command": "..."}}
            (re.compile(r'\{\s*"tool"\s*:\s*"(\w+)"\s*,\s*"args"\s*:\s*(\{[^{}]*\})\s*\}', re.DOTALL), False),
            # {"name": "bash_command", "arguments": {"command": "..."}}
            (re.compile(r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"(?:arguments|params)"\s*:\s*(\{[^{}]*\})\s*\}', re.DOTALL), False),
        ]

        result = chunk

        for pattern, _ in TOOL_PATTERNS:
            def replace_tool_call(match):
                tool_name = match.group(1)
                try:
                    args = json.loads(match.group(2))
                except json.JSONDecodeError:
                    return match.group(0)  # Retorna original se não conseguir parsear

                # Converte para formato amigável baseado no tool
                if tool_name in ('bash_command', 'bash'):
                    cmd = args.get('command', args.get('cmd', ''))
                    if cmd:
                        return f"```bash\n{cmd}\n```"
                elif tool_name == 'write_file':
                    path = args.get('path', args.get('file_path', ''))
                    return f"📝 **Escrevendo arquivo:** `{path}`"
                elif tool_name == 'read_file':
                    path = args.get('path', args.get('file_path', ''))
                    return f"📖 **Lendo arquivo:** `{path}`"
                elif tool_name == 'edit_file':
                    path = args.get('path', args.get('file_path', ''))
                    return f"✏️ **Editando arquivo:** `{path}`"
                elif tool_name in ('web_search', 'search'):
                    query = args.get('query', args.get('q', ''))
                    return f"🔍 **Pesquisando:** `{query}`"
                elif tool_name in ('web_fetch', 'fetch_url'):
                    url = args.get('url', '')
                    return f"🌐 **Acessando:** `{url}`"

                # Fallback: mostra tool call de forma limpa
                args_str = ', '.join(f"{k}={repr(v)}" for k, v in args.items())
                return f"🔧 **{tool_name}**({args_str})"

            result = pattern.sub(replace_tool_call, result)

        return result

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

        Implements throttling to maintain 60fps (16.67ms between renders).

        Args:
            chunk: Texto a adicionar ao stream
        """
        import time
        import re
        import json

        # =================================================================
        # BLINDAGEM 1: Sanitizar Rich markup que o LLM gerou erroneamente
        # =================================================================
        chunk = re.sub(
            r'\[/?(?:bold|italic|dim|underline|strike|blink|reverse|#[0-9a-fA-F]{6}|'
            r'red|green|blue|yellow|magenta|cyan|white|black|'
            r'bright_\w+|rgb\([^)]+\)|on\s+\w+)[^\]]*\]',
            '',
            chunk
        )

        # =================================================================
        # BLINDAGEM 2: Converter JSON tool calls em exibição amigável
        # Detecta {"tool": "bash_command", "args": {...}} e converte
        # =================================================================
        chunk = self._sanitize_tool_call_json(chunk)

        # DEDUPLICATION: Remove LLM-generated duplicate lines
        # Split chunk into lines and filter duplicates
        if '\n' in chunk:
            lines = chunk.split('\n')
            filtered_lines = []

            for line in lines:
                line_stripped = line.strip()

                # Skip empty lines
                if not line_stripped:
                    filtered_lines.append(line)
                    continue

                # Check if this line is a duplicate of recent lines
                is_duplicate = False
                for prev_line in self._last_lines[-5:]:  # Check last 5 lines
                    if line_stripped == prev_line.strip():
                        is_duplicate = True
                        break

                if not is_duplicate:
                    filtered_lines.append(line)
                    # Track this line for future dedup
                    self._last_lines.append(line_stripped)
                    # Keep only last N lines
                    if len(self._last_lines) > self._max_line_history:
                        self._last_lines.pop(0)

            chunk = '\n'.join(filtered_lines)

        self._content += chunk

        # Processa com block detector (incremental)
        self._block_detector.process_chunk(chunk)

        # Throttling: only update if enough time has passed (60fps = 16.67ms)
        current_time = time.time()
        if not hasattr(self, '_last_update_time'):
            self._last_update_time = 0
            self._pending_update = False

        time_since_last = current_time - self._last_update_time

        # Update immediately if >16ms since last update, or chunk ends with newline
        if time_since_last >= 0.016 or chunk.endswith('\n'):
            self._update_display()
            self._last_update_time = current_time
            self._pending_update = False
        else:
            # Mark that we have pending content
            self._pending_update = True

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

        # Cursor pulsante (thread-safe) - Orange brand color
        if self.is_streaming and not self._is_finalizing:
            cursor = self.CURSOR_FRAMES[self._get_cursor_index()]
            text.append(cursor, style=f"bold {Colors.PRIMARY}")

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

        # Cursor no final (thread-safe) - Orange brand color
        if self.is_streaming and not self._is_finalizing:
            cursor_text = Text()
            cursor_text.append(self.CURSOR_FRAMES[self._get_cursor_index()], style=f"bold {Colors.PRIMARY}")
            renderables.append(cursor_text)

        return Group(*renderables) if renderables else Text("")

    async def _animate_cursor(self) -> None:
        """
        Anima o cursor durante streaming.

        Also flushes any pending updates from throttling.
        """
        while self.is_streaming and not self._is_finalizing:
            self._advance_cursor()  # Thread-safe

            # Flush pending updates if any (from throttling)
            if getattr(self, '_pending_update', False):
                self._pending_update = False

            self._update_display()
            await asyncio.sleep(0.08)  # 80ms per frame (~12.5fps for cursor)

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
