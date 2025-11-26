"""
Streaming Code Block - Syntax highlighting incremental durante streaming.

Code block que cresce durante streaming com:
- Syntax highlighting via Pygments (50+ linguagens)
- Cache de tokens já parseados (incremental)
- Cursor pulsante no final do código
- Line numbers opcionais
- Copy indicator

Autor: JuanCS Dev
Data: 2025-11-25
"""

import time
import asyncio
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive
from textual.message import Message
from textual.app import ComposeResult

from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel
from rich.style import Style
from rich.console import Console, RenderableType

try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.token import Token
    from pygments.util import ClassNotFound
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


# Mapeamento de linguagens comuns
LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "rb": "ruby",
    "rs": "rust",
    "go": "go",
    "java": "java",
    "cpp": "cpp",
    "c++": "cpp",
    "cs": "csharp",
    "c#": "csharp",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "yml": "yaml",
    "md": "markdown",
    "json": "json",
    "xml": "xml",
    "html": "html",
    "css": "css",
    "sql": "sql",
    "dockerfile": "docker",
    "docker": "docker",
    "makefile": "make",
    "make": "make",
    "toml": "toml",
    "ini": "ini",
    "conf": "ini",
    "diff": "diff",
    "patch": "diff",
}

# Tema de cores para tokens (estilo Claude Code)
TOKEN_STYLES = {
    "keyword": Style(color="#ff79c6", bold=True),
    "keyword.type": Style(color="#8be9fd"),
    "name.function": Style(color="#50fa7b"),
    "name.class": Style(color="#8be9fd", bold=True),
    "name.decorator": Style(color="#ff79c6"),
    "name.builtin": Style(color="#8be9fd"),
    "name.variable": Style(color="#f8f8f2"),
    "string": Style(color="#f1fa8c"),
    "string.doc": Style(color="#6272a4", italic=True),
    "number": Style(color="#bd93f9"),
    "operator": Style(color="#ff79c6"),
    "comment": Style(color="#6272a4", italic=True),
    "punctuation": Style(color="#f8f8f2"),
    "default": Style(color="#f8f8f2"),
}


@dataclass
class CachedToken:
    """Token com informação de cache."""
    token_type: str
    value: str
    style: Style
    line_number: int


@dataclass
class IncrementalState:
    """Estado do highlighting incremental."""
    cached_tokens: List[CachedToken] = field(default_factory=list)
    last_complete_line: int = 0
    incomplete_line: str = ""
    language: str = "text"
    total_lines: int = 0


class IncrementalSyntaxHighlighter:
    """
    Syntax highlighter incremental para streaming.

    Princípios:
    - Linhas completas são parseadas e cacheadas
    - Apenas a última linha (incompleta) é re-parseada
    - Tokens são armazenados para evitar re-parse
    """

    def __init__(self, language: str = "text"):
        """
        Inicializa highlighter.

        Args:
            language: Linguagem de programação
        """
        self.language = self._normalize_language(language)
        self.state = IncrementalState(language=self.language)
        self._lexer = None

        if PYGMENTS_AVAILABLE:
            try:
                self._lexer = get_lexer_by_name(self.language)
            except ClassNotFound:
                self._lexer = None

    def _normalize_language(self, language: str) -> str:
        """Normaliza nome da linguagem."""
        language = language.lower().strip()
        return LANGUAGE_ALIASES.get(language, language)

    def _get_token_style(self, token_type) -> Style:
        """Obtém estilo para tipo de token."""
        if not PYGMENTS_AVAILABLE:
            return TOKEN_STYLES["default"]

        # Converte tipo de token para string
        type_str = str(token_type).lower()

        # Busca estilo mais específico primeiro
        for key, style in TOKEN_STYLES.items():
            if key in type_str:
                return style

        return TOKEN_STYLES["default"]

    def process_chunk(self, chunk: str) -> List[CachedToken]:
        """
        Processa chunk de código e retorna tokens.

        Args:
            chunk: Novo código a processar

        Returns:
            Lista de tokens (incluindo cached)
        """
        # Adiciona ao buffer
        self.state.incomplete_line += chunk

        # Divide em linhas
        lines = self.state.incomplete_line.split('\n')

        # Processa linhas completas (todas exceto última)
        for line in lines[:-1]:
            self._process_complete_line(line)

        # Guarda linha incompleta
        self.state.incomplete_line = lines[-1]

        # Retorna todos os tokens + tokens da linha incompleta
        all_tokens = self.state.cached_tokens.copy()

        # Parseia linha incompleta (sem cachear)
        if self.state.incomplete_line:
            incomplete_tokens = self._tokenize_line(
                self.state.incomplete_line,
                self.state.total_lines + 1
            )
            all_tokens.extend(incomplete_tokens)

        return all_tokens

    def _process_complete_line(self, line: str) -> None:
        """Processa e cacheia uma linha completa."""
        self.state.total_lines += 1
        tokens = self._tokenize_line(line, self.state.total_lines)
        self.state.cached_tokens.extend(tokens)
        self.state.last_complete_line = self.state.total_lines

    def _tokenize_line(self, line: str, line_number: int) -> List[CachedToken]:
        """Tokeniza uma linha."""
        tokens = []

        if PYGMENTS_AVAILABLE and self._lexer:
            try:
                for token_type, value in lex(line + '\n', self._lexer):
                    if value.strip() or value == '\n':
                        tokens.append(CachedToken(
                            token_type=str(token_type),
                            value=value.rstrip('\n'),
                            style=self._get_token_style(token_type),
                            line_number=line_number,
                        ))
            except Exception:
                # Fallback: texto simples
                tokens.append(CachedToken(
                    token_type="text",
                    value=line,
                    style=TOKEN_STYLES["default"],
                    line_number=line_number,
                ))
        else:
            # Sem Pygments: texto simples
            tokens.append(CachedToken(
                token_type="text",
                value=line,
                style=TOKEN_STYLES["default"],
                line_number=line_number,
            ))

        return tokens

    def get_highlighted_text(
        self,
        show_line_numbers: bool = True,
        cursor: str = "",
    ) -> Text:
        """
        Retorna Text com highlighting aplicado.

        Args:
            show_line_numbers: Mostrar números de linha
            cursor: Cursor a adicionar no final

        Returns:
            Rich Text com estilos aplicados
        """
        text = Text()
        current_line = 0

        for token in self.state.cached_tokens:
            # Adiciona número de linha se mudou
            if show_line_numbers and token.line_number != current_line:
                if current_line > 0:
                    text.append("\n")
                line_num = f"{token.line_number:4d} "
                text.append(line_num, style=Style(color="#6272a4", dim=True))
                current_line = token.line_number

            # Adiciona token com estilo
            text.append(token.value, style=token.style)

        # Adiciona linha incompleta
        if self.state.incomplete_line:
            if show_line_numbers:
                if current_line > 0:
                    text.append("\n")
                line_num = f"{self.state.total_lines + 1:4d} "
                text.append(line_num, style=Style(color="#6272a4", dim=True))

            # Tokeniza e adiciona
            incomplete_tokens = self._tokenize_line(
                self.state.incomplete_line,
                self.state.total_lines + 1
            )
            for token in incomplete_tokens:
                text.append(token.value, style=token.style)

        # Adiciona cursor
        if cursor:
            text.append(cursor, style=Style(bgcolor="#ff79c6"))

        return text

    def reset(self) -> None:
        """Reseta estado do highlighter."""
        self.state = IncrementalState(language=self.language)


class StreamingCodeBlock(Widget):
    """
    Code block com streaming e syntax highlighting incremental.

    Features:
    - Syntax highlighting durante streaming
    - Cursor pulsante
    - Line numbers
    - Language badge
    - Copy indicator
    """

    DEFAULT_CSS = """
    StreamingCodeBlock {
        width: 100%;
        height: auto;
        min-height: 3;
        background: #282a36;
        padding: 0;
    }

    StreamingCodeBlock .code-header {
        background: #44475a;
        color: #f8f8f2;
        height: 1;
        padding: 0 1;
    }

    StreamingCodeBlock .code-content {
        padding: 1;
        overflow-x: auto;
    }

    StreamingCodeBlock.streaming .code-content {
        border-bottom: solid #ff79c6;
    }
    """

    # Reactive
    is_streaming = reactive(False)
    language = reactive("text")
    show_line_numbers = reactive(True)

    # Cursor frames
    CURSOR_FRAMES = ["", "", "", " "]
    CURSOR_INTERVAL = 0.1

    class CodeStreamStarted(Message):
        """Streaming de código iniciado."""
        def __init__(self, language: str):
            self.language = language
            super().__init__()

    class CodeStreamEnded(Message):
        """Streaming de código finalizado."""
        def __init__(self, code: str, language: str, line_count: int):
            self.code = code
            self.language = language
            self.line_count = line_count
            super().__init__()

    def __init__(
        self,
        language: str = "text",
        show_line_numbers: bool = True,
        show_header: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        """
        Inicializa code block.

        Args:
            language: Linguagem de programação
            show_line_numbers: Mostrar números de linha
            show_header: Mostrar header com linguagem
            name: Nome do widget
            id: ID do widget
            classes: Classes CSS
        """
        super().__init__(name=name, id=id, classes=classes)

        self.language = language
        self.show_line_numbers = show_line_numbers
        self.show_header = show_header

        # State
        self._code = ""
        self._highlighter = IncrementalSyntaxHighlighter(language)
        self._cursor_index = 0
        self._cursor_task: Optional[asyncio.Task] = None

        # Widgets internos
        self._header: Optional[Static] = None
        self._content: Optional[Static] = None

    def compose(self) -> ComposeResult:
        """Compõe o widget."""
        if self.show_header:
            lang_display = self.language.upper() if self.language else "CODE"
            self._header = Static(f" {lang_display}", classes="code-header")
            yield self._header

        self._content = Static("", classes="code-content")
        yield self._content

    async def start_stream(self, language: Optional[str] = None) -> None:
        """
        Inicia streaming de código.

        Args:
            language: Linguagem (opcional, usa a definida no init)
        """
        if language:
            self.language = language
            self._highlighter = IncrementalSyntaxHighlighter(language)
        else:
            self._highlighter.reset()

        self._code = ""
        self.is_streaming = True
        self.add_class("streaming")

        # Atualiza header
        if self._header and self.show_header:
            lang_display = self.language.upper() if self.language else "CODE"
            self._header.update(f" {lang_display} | Streaming...")

        self.post_message(self.CodeStreamStarted(self.language))

        # Inicia cursor
        self._cursor_task = asyncio.create_task(self._animate_cursor())

    async def append_code(self, chunk: str) -> None:
        """
        Adiciona chunk de código.

        Args:
            chunk: Código a adicionar
        """
        if not self.is_streaming:
            return

        self._code += chunk
        self._highlighter.process_chunk(chunk)

        # Atualiza display
        self._update_display()

    def _update_display(self) -> None:
        """Atualiza display do código."""
        if not self._content:
            return

        cursor = ""
        if self.is_streaming:
            cursor = self.CURSOR_FRAMES[self._cursor_index]

        highlighted = self._highlighter.get_highlighted_text(
            show_line_numbers=self.show_line_numbers,
            cursor=cursor,
        )

        self._content.update(highlighted)

    async def _animate_cursor(self) -> None:
        """Anima cursor durante streaming."""
        while self.is_streaming:
            self._cursor_index = (self._cursor_index + 1) % len(self.CURSOR_FRAMES)
            self._update_display()
            await asyncio.sleep(self.CURSOR_INTERVAL)

    async def end_stream(self) -> None:
        """Finaliza streaming."""
        self.is_streaming = False
        self.remove_class("streaming")

        # Cancela cursor
        if self._cursor_task:
            self._cursor_task.cancel()
            try:
                await self._cursor_task
            except asyncio.CancelledError:
                pass
            self._cursor_task = None

        # Update final
        self._update_display()

        # Atualiza header
        if self._header and self.show_header:
            lang_display = self.language.upper() if self.language else "CODE"
            line_count = self._highlighter.state.total_lines + (
                1 if self._highlighter.state.incomplete_line else 0
            )
            self._header.update(f" {lang_display} | {line_count} lines")

        self.post_message(self.CodeStreamEnded(
            self._code,
            self.language,
            self._highlighter.state.total_lines,
        ))

    def set_code(self, code: str, language: Optional[str] = None) -> None:
        """
        Define código diretamente (não streaming).

        Args:
            code: Código completo
            language: Linguagem opcional
        """
        if language:
            self.language = language
            self._highlighter = IncrementalSyntaxHighlighter(language)
        else:
            self._highlighter.reset()

        self._code = code
        self._highlighter.process_chunk(code)
        self._update_display()

        # Atualiza header
        if self._header and self.show_header:
            lang_display = self.language.upper() if self.language else "CODE"
            line_count = self._highlighter.state.total_lines + (
                1 if self._highlighter.state.incomplete_line else 0
            )
            self._header.update(f" {lang_display} | {line_count} lines")

    def get_code(self) -> str:
        """Retorna código atual."""
        return self._code


def create_code_block_panel(
    code: str,
    language: str = "python",
    show_line_numbers: bool = True,
    title: Optional[str] = None,
) -> Panel:
    """
    Cria um Panel com código highlightado (não streaming).

    Args:
        code: Código
        language: Linguagem
        show_line_numbers: Mostrar números de linha
        title: Título opcional

    Returns:
        Rich Panel
    """
    highlighter = IncrementalSyntaxHighlighter(language)
    highlighter.process_chunk(code)

    highlighted = highlighter.get_highlighted_text(
        show_line_numbers=show_line_numbers,
    )

    lang_display = language.upper() if language else "CODE"
    panel_title = title or f" {lang_display}"

    return Panel(
        highlighted,
        title=panel_title,
        border_style="#44475a",
        padding=(0, 1),
    )
