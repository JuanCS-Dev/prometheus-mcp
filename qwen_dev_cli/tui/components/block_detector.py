"""
Block Detector - State machine para detecção de blocos durante streaming.

Identifica code fences, tabelas, checklists enquanto tokens chegam.
Parte do sistema de renderização estilo Claude Code Web.

Autor: JuanCS Dev
Data: 2025-11-25
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import re


class BlockType(Enum):
    """Tipos de blocos markdown suportados."""
    UNKNOWN = "unknown"
    PARAGRAPH = "paragraph"
    CODE_FENCE = "code_fence"
    TABLE = "table"
    CHECKLIST = "checklist"
    HEADING = "heading"
    LIST = "list"
    BLOCKQUOTE = "blockquote"
    HORIZONTAL_RULE = "horizontal_rule"
    EMPTY = "empty"
    # Claude Code Web style
    TOOL_CALL = "tool_call"
    DIFF_BLOCK = "diff_block"
    STATUS_BADGE = "status_badge"


@dataclass
class BlockInfo:
    """Informação sobre um bloco detectado."""
    block_type: BlockType
    start_line: int
    end_line: Optional[int] = None
    language: Optional[str] = None  # Para code fences
    is_complete: bool = False
    content: str = ""
    metadata: dict = field(default_factory=dict)


class BlockDetector:
    """
    State machine para detecção de blocos durante streaming.

    Princípios:
    - Blocos finalizados NUNCA são re-parseados
    - Apenas o último bloco é re-avaliado a cada chunk
    - Optimistic rendering - detecta tipo antes de fechar
    """

    # Patterns para detecção de início de bloco
    PATTERNS = {
        BlockType.CODE_FENCE: re.compile(r'^(`{3,}|~{3,})(\w*)\s*$'),
        BlockType.TABLE: re.compile(r'^\|.*\|'),
        BlockType.CHECKLIST: re.compile(r'^[-*+]\s+\[[ xX]\]'),
        BlockType.HEADING: re.compile(r'^(#{1,6})\s+(.*)'),
        BlockType.BLOCKQUOTE: re.compile(r'^>\s*'),
        BlockType.HORIZONTAL_RULE: re.compile(r'^([-*_]){3,}\s*$'),
        # Claude Code Web style patterns
        BlockType.TOOL_CALL: re.compile(r'^[•●]\s+(Read|Write|Bash|Update Todos|Edit|Glob|Grep|Task|WebFetch|WebSearch)\b'),
        BlockType.STATUS_BADGE: re.compile(r'^[🔴🟡🟢⚪🟠]\s*\w+'),
        # Diff block detection (unified diff format)
        BlockType.DIFF_BLOCK: re.compile(r'^(diff --git|@@\s*-\d+.*\+\d+.*@@|[+-]{3}\s+[ab]/)'),
    }

    # Additional patterns (not in BlockType enum)
    EXTRA_PATTERNS = {
        'TABLE_SEPARATOR': re.compile(r'^\|[\s\-:|]+\|'),
        'LIST_BULLET': re.compile(r'^[-*+]\s+(?!\[[ xX]\])'),
        'LIST_NUMBERED': re.compile(r'^\d+\.\s+'),
        # Tool output patterns
        'TOOL_OUTPUT': re.compile(r'^[└├│┌┐]\s*'),
        'DIFF_LINE': re.compile(r'^[+-]\s'),
        'SHOW_MORE': re.compile(r'^Show full diff \(\d+ more lines\)'),
    }

    # Pattern para fechar code fence
    CODE_FENCE_CLOSE = re.compile(r'^(`{3,}|~{3,})\s*$')

    def __init__(self):
        self.blocks: List[BlockInfo] = []
        self.current_block: Optional[BlockInfo] = None
        self.line_number: int = 0
        self.in_code_fence: bool = False
        self.code_fence_marker: str = ""  # ``` ou ~~~
        self._buffer: str = ""

    def reset(self):
        """Reseta o detector para novo documento."""
        self.blocks = []
        self.current_block = None
        self.line_number = 0
        self.in_code_fence = False
        self.code_fence_marker = ""
        self._buffer = ""

    def process_chunk(self, chunk: str) -> List[BlockInfo]:
        """
        Processa um chunk de texto e retorna blocos atualizados.

        Args:
            chunk: Texto novo a processar

        Returns:
            Lista de blocos (finalizados + atual em progresso)
        """
        self._buffer += chunk

        # Processa linha por linha
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            self._process_line(line)

        # Processa última linha incompleta (optimistic)
        if self._buffer:
            self._process_partial_line(self._buffer)

        return self.get_all_blocks()

    def _process_line(self, line: str) -> None:
        """Processa uma linha completa."""
        self.line_number += 1

        # Dentro de code fence?
        if self.in_code_fence:
            self._handle_code_fence_content(line)
            return

        # Linha vazia
        if not line.strip():
            self._finalize_current_block()
            return

        # Detecta tipo de bloco
        block_type = self._detect_block_type(line)

        # Continua bloco atual ou inicia novo?
        if self._should_continue_block(block_type, line):
            self._extend_current_block(line)
        else:
            self._finalize_current_block()
            self._start_new_block(block_type, line)

    def _process_partial_line(self, partial: str) -> None:
        """
        Processa linha parcial (optimistic parsing).
        Detecta tipo mas não finaliza.
        """
        if not partial.strip():
            return

        if self.in_code_fence:
            # Adiciona ao bloco atual sem finalizar
            if self.current_block:
                self.current_block.content += partial
            return

        block_type = self._detect_block_type(partial)

        if self._should_continue_block(block_type, partial):
            if self.current_block:
                self.current_block.content += partial
        else:
            # Inicia novo bloco (sem finalizar anterior ainda)
            self._start_new_block(block_type, partial, is_partial=True)

    def _detect_block_type(self, line: str) -> BlockType:
        """Detecta o tipo de bloco a partir de uma linha."""
        stripped = line.strip()

        # Tool call (Claude Code Web style) - prioridade alta
        if self.PATTERNS[BlockType.TOOL_CALL].match(stripped):
            return BlockType.TOOL_CALL

        # Status badge (🔴 BLOCKER, etc)
        if self.PATTERNS[BlockType.STATUS_BADGE].match(stripped):
            return BlockType.STATUS_BADGE

        # Diff block (unified diff format)
        if self.PATTERNS[BlockType.DIFF_BLOCK].match(stripped):
            return BlockType.DIFF_BLOCK

        # Code fence
        match = self.PATTERNS[BlockType.CODE_FENCE].match(stripped)
        if match:
            return BlockType.CODE_FENCE

        # Heading
        if self.PATTERNS[BlockType.HEADING].match(stripped):
            return BlockType.HEADING

        # Horizontal rule
        if self.PATTERNS[BlockType.HORIZONTAL_RULE].match(stripped):
            return BlockType.HORIZONTAL_RULE

        # Checklist (antes de list para prioridade)
        if self.PATTERNS[BlockType.CHECKLIST].match(stripped):
            return BlockType.CHECKLIST

        # Table
        if self.PATTERNS[BlockType.TABLE].match(stripped):
            return BlockType.TABLE

        # Blockquote
        if self.PATTERNS[BlockType.BLOCKQUOTE].match(stripped):
            return BlockType.BLOCKQUOTE

        # List bullet (using EXTRA_PATTERNS)
        if self.EXTRA_PATTERNS['LIST_BULLET'].match(stripped):
            return BlockType.LIST

        # List numbered (using EXTRA_PATTERNS)
        if self.EXTRA_PATTERNS['LIST_NUMBERED'].match(stripped):
            return BlockType.LIST

        return BlockType.PARAGRAPH

    def _should_continue_block(self, new_type: BlockType, line: str) -> bool:
        """Determina se deve continuar bloco atual ou iniciar novo."""
        if not self.current_block:
            return False

        current_type = self.current_block.block_type

        # Table continua com mais rows
        if current_type == BlockType.TABLE and new_type == BlockType.TABLE:
            return True

        # Lista continua com mais items
        if current_type == BlockType.LIST and new_type == BlockType.LIST:
            return True

        # Checklist continua
        if current_type == BlockType.CHECKLIST and new_type == BlockType.CHECKLIST:
            return True

        # Blockquote continua
        if current_type == BlockType.BLOCKQUOTE and new_type == BlockType.BLOCKQUOTE:
            return True

        # Paragraph continua com paragraph (texto corrido)
        if current_type == BlockType.PARAGRAPH and new_type == BlockType.PARAGRAPH:
            return True

        # Diff block continua com linhas +/- ou contexto (espaço no início)
        if current_type == BlockType.DIFF_BLOCK:
            # Linhas que fazem parte de um diff (não stripped - espaço inicial importa!)
            if (line.startswith('+') or line.startswith('-') or
                line.startswith('@@') or line.startswith('diff ') or
                line.startswith(' ') or  # Linha de contexto em diffs
                new_type == BlockType.DIFF_BLOCK):
                return True

        return False

    def _start_new_block(self, block_type: BlockType, line: str, is_partial: bool = False) -> None:
        """Inicia um novo bloco."""
        # Caso especial: code fence
        if block_type == BlockType.CODE_FENCE:
            match = self.PATTERNS[BlockType.CODE_FENCE].match(line.strip())
            if match:
                self.in_code_fence = True
                self.code_fence_marker = match.group(1)[:3]  # ``` ou ~~~
                language = match.group(2) or None

                self.current_block = BlockInfo(
                    block_type=BlockType.CODE_FENCE,
                    start_line=self.line_number,
                    language=language,
                    content="",  # Não inclui a fence marker
                    is_complete=False,
                )
                return

        # Extrai metadata para heading
        metadata = {}
        if block_type == BlockType.HEADING:
            match = self.PATTERNS[BlockType.HEADING].match(line.strip())
            if match:
                metadata['level'] = len(match.group(1))
                metadata['text'] = match.group(2)

        self.current_block = BlockInfo(
            block_type=block_type,
            start_line=self.line_number,
            content=line + ("\n" if not is_partial else ""),
            is_complete=False,
            metadata=metadata,
        )

        # Headings e horizontal rules são completos em uma linha
        if block_type in (BlockType.HEADING, BlockType.HORIZONTAL_RULE):
            self._finalize_current_block()

    def _extend_current_block(self, line: str) -> None:
        """Estende o bloco atual com mais conteúdo."""
        if self.current_block:
            self.current_block.content += line + "\n"

    def _handle_code_fence_content(self, line: str) -> None:
        """Processa conteúdo dentro de code fence."""
        # Verifica se é o fechamento
        if self.CODE_FENCE_CLOSE.match(line.strip()):
            marker = line.strip()[:3]
            if marker == self.code_fence_marker:
                self.in_code_fence = False
                self.code_fence_marker = ""
                self._finalize_current_block()
                return

        # Adiciona conteúdo
        if self.current_block:
            self.current_block.content += line + "\n"

    def _finalize_current_block(self) -> None:
        """Finaliza o bloco atual e o adiciona à lista."""
        if self.current_block:
            self.current_block.is_complete = True
            self.current_block.end_line = self.line_number

            # Remove trailing newline do content
            self.current_block.content = self.current_block.content.rstrip('\n')

            self.blocks.append(self.current_block)
            self.current_block = None

    def get_all_blocks(self) -> List[BlockInfo]:
        """Retorna todos os blocos (finalizados + atual em progresso)."""
        result = self.blocks.copy()
        if self.current_block:
            result.append(self.current_block)
        return result

    def get_finalized_blocks(self) -> List[BlockInfo]:
        """Retorna apenas blocos finalizados (completos)."""
        return [b for b in self.blocks if b.is_complete]

    def get_current_block(self) -> Optional[BlockInfo]:
        """Retorna o bloco atual em progresso."""
        return self.current_block

    def is_in_code_fence(self) -> bool:
        """Verifica se está dentro de um code fence."""
        return self.in_code_fence


class OptimisticInlineParser:
    """
    Parser otimista para formatação inline durante streaming.

    Renderiza **bold mesmo sem ** de fechamento.
    """

    # Padrões inline
    BOLD = re.compile(r'\*\*(.+?)(\*\*|$)')
    ITALIC = re.compile(r'\*([^*]+?)(\*|$)')
    CODE = re.compile(r'`([^`]+?)(`|$)')
    STRIKETHROUGH = re.compile(r'~~(.+?)(~~|$)')
    LINK = re.compile(r'\[([^\]]+)\]\(([^)]*)\)?')

    @classmethod
    def detect_incomplete(cls, text: str) -> List[Tuple[str, int, int]]:
        """
        Detecta formatação inline incompleta.

        Returns:
            Lista de (tipo, start, end) para cada formatação detectada
        """
        results = []

        # Bold incompleto: **texto sem fechamento
        if '**' in text:
            idx = text.rfind('**')
            remaining = text[idx+2:]
            if '**' not in remaining and remaining.strip():
                results.append(('bold_incomplete', idx, len(text)))

        # Code incompleto: `code sem fechamento
        backticks = [i for i, c in enumerate(text) if c == '`']
        if len(backticks) % 2 == 1:
            results.append(('code_incomplete', backticks[-1], len(text)))

        # Strikethrough incompleto
        if '~~' in text:
            idx = text.rfind('~~')
            remaining = text[idx+2:]
            if '~~' not in remaining and remaining.strip():
                results.append(('strike_incomplete', idx, len(text)))

        return results


