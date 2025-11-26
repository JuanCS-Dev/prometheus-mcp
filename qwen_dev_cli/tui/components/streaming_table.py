"""
Streaming Table - Renderização progressiva de tabelas durante streaming.

Renderiza tabelas markdown ao vivo:
- Renderiza após primeira row
- Adapta largura dinamicamente
- Integra com Rich.Table

Autor: JuanCS Dev
Data: 2025-11-25
"""

import re
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive
from textual.message import Message
from textual.app import ComposeResult

from rich.table import Table
from rich.text import Text
from rich.style import Style
from rich.console import Console, RenderableType
from rich import box


class TableState(Enum):
    """Estado da tabela durante parsing."""
    WAITING_HEADER = 1
    WAITING_SEPARATOR = 2
    READY_FOR_ROWS = 3
    COMPLETE = 4


@dataclass
class TableColumn:
    """Definição de uma coluna."""
    header: str
    alignment: str = "left"  # left, center, right
    min_width: int = 3
    max_width: int = 50

    @property
    def justify(self) -> str:
        """Retorna justify para Rich Table."""
        mapping = {
            "left": "left",
            "center": "center",
            "right": "right",
        }
        return mapping.get(self.alignment, "left")


@dataclass
class TableRow:
    """Uma linha da tabela."""
    cells: List[str]
    is_header: bool = False


@dataclass
class StreamingTableState:
    """Estado completo da tabela."""
    columns: List[TableColumn] = field(default_factory=list)
    rows: List[TableRow] = field(default_factory=list)
    state: TableState = TableState.WAITING_HEADER
    buffer: str = ""
    header_row: Optional[TableRow] = None


class StreamingTableRenderer:
    """
    Renderizador progressivo de tabelas markdown.

    Processa tabelas linha por linha:
    1. Header: | Col1 | Col2 | Col3 |
    2. Separator: |------|:----:|-----:|
    3. Rows: | val1 | val2 | val3 |
    """

    # Patterns
    TABLE_ROW_PATTERN = re.compile(r'^\s*\|(.+)\|\s*$')
    SEPARATOR_PATTERN = re.compile(r'^\s*\|[\s\-:|]+\|\s*$')
    ALIGNMENT_PATTERN = re.compile(r'^(:)?-+(:)?$')

    def __init__(self):
        """Inicializa renderer."""
        self.state = StreamingTableState()

    def reset(self) -> None:
        """Reseta estado."""
        self.state = StreamingTableState()

    def process_chunk(self, chunk: str) -> Optional[Table]:
        """
        Processa chunk de texto e retorna Table se pronto.

        Args:
            chunk: Texto a processar

        Returns:
            Rich Table se tabela está pronta para render, None caso contrário
        """
        self.state.buffer += chunk

        # Processa linha por linha
        while '\n' in self.state.buffer:
            line, self.state.buffer = self.state.buffer.split('\n', 1)
            result = self._process_line(line)
            if result:
                return result

        # Tenta processar linha parcial (optimistic)
        if self.state.buffer.strip():
            # Não processa linha incompleta para evitar erros
            pass

        # Retorna tabela atual se já tem dados
        if self.state.state == TableState.READY_FOR_ROWS and self.state.rows:
            return self._build_table()

        return None

    def _process_line(self, line: str) -> Optional[Table]:
        """Processa uma linha completa."""
        line = line.strip()

        # Ignora linhas vazias
        if not line:
            if self.state.state == TableState.READY_FOR_ROWS:
                self.state.state = TableState.COMPLETE
            return self._build_table() if self.state.rows else None

        # Verifica se é linha de tabela
        if not self.TABLE_ROW_PATTERN.match(line):
            # Não é tabela - finaliza se estava processando
            if self.state.state == TableState.READY_FOR_ROWS:
                self.state.state = TableState.COMPLETE
                return self._build_table()
            return None

        # É linha de tabela
        if self.state.state == TableState.WAITING_HEADER:
            return self._process_header(line)
        elif self.state.state == TableState.WAITING_SEPARATOR:
            return self._process_separator(line)
        elif self.state.state == TableState.READY_FOR_ROWS:
            return self._process_row(line)

        return None

    def _process_header(self, line: str) -> Optional[Table]:
        """Processa linha de header."""
        cells = self._parse_cells(line)
        if not cells:
            return None

        self.state.header_row = TableRow(cells=cells, is_header=True)
        self.state.state = TableState.WAITING_SEPARATOR
        return None

    def _process_separator(self, line: str) -> Optional[Table]:
        """Processa linha separadora e determina alinhamentos."""
        if not self.SEPARATOR_PATTERN.match(line):
            # Não é separator válido - reseta
            self.state.state = TableState.WAITING_HEADER
            self.state.header_row = None
            return None

        cells = self._parse_cells(line)
        if not cells:
            return None

        # Determina alinhamentos
        alignments = []
        for cell in cells:
            cell = cell.strip()
            match = self.ALIGNMENT_PATTERN.match(cell)
            if match:
                left_colon = match.group(1)
                right_colon = match.group(2)

                if left_colon and right_colon:
                    alignments.append("center")
                elif right_colon:
                    alignments.append("right")
                else:
                    alignments.append("left")
            else:
                alignments.append("left")

        # Cria colunas
        if self.state.header_row:
            for i, header in enumerate(self.state.header_row.cells):
                alignment = alignments[i] if i < len(alignments) else "left"
                self.state.columns.append(TableColumn(
                    header=header.strip(),
                    alignment=alignment,
                ))

        self.state.state = TableState.READY_FOR_ROWS
        return None

    def _process_row(self, line: str) -> Optional[Table]:
        """Processa linha de dados."""
        cells = self._parse_cells(line)
        if not cells:
            return None

        # Ajusta número de células para match com colunas
        while len(cells) < len(self.state.columns):
            cells.append("")
        cells = cells[:len(self.state.columns)]

        self.state.rows.append(TableRow(cells=[c.strip() for c in cells]))
        return self._build_table()

    def _parse_cells(self, line: str) -> List[str]:
        """Extrai células de uma linha de tabela."""
        match = self.TABLE_ROW_PATTERN.match(line)
        if not match:
            return []

        content = match.group(1)
        cells = content.split('|')
        return [cell.strip() for cell in cells]

    def _build_table(self) -> Optional[Table]:
        """Constrói Rich Table a partir do estado atual."""
        if not self.state.columns:
            return None

        table = Table(
            box=box.ROUNDED,
            border_style="cyan",
            header_style="bold cyan",
            row_styles=["", "dim"],
            padding=(0, 1),
            collapse_padding=True,
        )

        # Adiciona colunas
        for col in self.state.columns:
            table.add_column(
                col.header,
                justify=col.justify,
                min_width=col.min_width,
                max_width=col.max_width,
            )

        # Adiciona rows
        for row in self.state.rows:
            table.add_row(*row.cells)

        return table

    def is_complete(self) -> bool:
        """Verifica se tabela está completa."""
        return self.state.state == TableState.COMPLETE

    def get_table(self) -> Optional[Table]:
        """Retorna tabela atual."""
        return self._build_table()


class StreamingTableWidget(Widget):
    """
    Widget de tabela com streaming.

    Renderiza tabelas markdown progressivamente durante streaming.
    """

    DEFAULT_CSS = """
    StreamingTableWidget {
        width: 100%;
        height: auto;
        min-height: 3;
    }

    StreamingTableWidget.streaming {
        border: solid #00d4aa;
    }

    StreamingTableWidget.complete {
        border: solid #50fa7b;
    }
    """

    is_streaming = reactive(False)
    row_count = reactive(0)

    class TableUpdated(Message):
        """Tabela foi atualizada."""
        def __init__(self, row_count: int, column_count: int):
            self.row_count = row_count
            self.column_count = column_count
            super().__init__()

    class TableComplete(Message):
        """Tabela está completa."""
        def __init__(self, row_count: int, column_count: int):
            self.row_count = row_count
            self.column_count = column_count
            super().__init__()

    def __init__(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        """Inicializa widget."""
        super().__init__(name=name, id=id, classes=classes)

        self._renderer = StreamingTableRenderer()
        self._content: Optional[Static] = None

    def compose(self) -> ComposeResult:
        """Compõe widget."""
        self._content = Static("")
        yield self._content

    def start_stream(self) -> None:
        """Inicia streaming."""
        self._renderer.reset()
        self.is_streaming = True
        self.row_count = 0
        self.add_class("streaming")
        self.remove_class("complete")

    def append_chunk(self, chunk: str) -> None:
        """
        Adiciona chunk de texto.

        Args:
            chunk: Texto a processar
        """
        if not self.is_streaming:
            return

        table = self._renderer.process_chunk(chunk)
        if table and self._content:
            self._content.update(table)
            self.row_count = len(self._renderer.state.rows)
            self.post_message(self.TableUpdated(
                self.row_count,
                len(self._renderer.state.columns),
            ))

    def end_stream(self) -> None:
        """Finaliza streaming."""
        self.is_streaming = False
        self.remove_class("streaming")
        self.add_class("complete")

        # Render final
        table = self._renderer.get_table()
        if table and self._content:
            self._content.update(table)

        self.post_message(self.TableComplete(
            len(self._renderer.state.rows),
            len(self._renderer.state.columns),
        ))

    def set_markdown_table(self, markdown: str) -> None:
        """
        Define tabela a partir de markdown (não streaming).

        Args:
            markdown: Tabela em formato markdown
        """
        self._renderer.reset()
        table = self._renderer.process_chunk(markdown + "\n\n")
        if table and self._content:
            self._content.update(table)
            self.row_count = len(self._renderer.state.rows)


def parse_markdown_table(markdown: str) -> Optional[Table]:
    """
    Parseia tabela markdown e retorna Rich Table.

    Args:
        markdown: Tabela em formato markdown

    Returns:
        Rich Table ou None
    """
    renderer = StreamingTableRenderer()
    return renderer.process_chunk(markdown + "\n\n")


def create_table_from_data(
    headers: List[str],
    rows: List[List[str]],
    alignments: Optional[List[str]] = None,
    title: Optional[str] = None,
) -> Table:
    """
    Cria tabela a partir de dados.

    Args:
        headers: Lista de headers
        rows: Lista de listas de células
        alignments: Lista de alinhamentos (left, center, right)
        title: Título opcional

    Returns:
        Rich Table
    """
    table = Table(
        title=title,
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        row_styles=["", "dim"],
        padding=(0, 1),
    )

    alignments = alignments or ["left"] * len(headers)

    for i, header in enumerate(headers):
        align = alignments[i] if i < len(alignments) else "left"
        table.add_column(header, justify=align)

    for row in rows:
        table.add_row(*row)

    return table
