"""
Block Detector V2 - Scalable State Machine for Block Detection.

ARQUITETURA ESCALÁVEL:
Usa BlockRendererRegistry para detecção automática.
Adicionar novo tipo = criar renderer = detecção automática.

Autor: JuanCS Dev
Data: 2025-11-25
"""

from __future__ import annotations

import re
from typing import List, Optional
from dataclasses import dataclass, field

from .block_renderers import (
    BlockType, BlockInfo, BlockRendererRegistry,
    detect_block_type
)


class BlockDetectorV2:
    """
    State machine escalável para detecção de blocos durante streaming.

    Usa BlockRendererRegistry para detecção - zero config para novos tipos.

    Princípios:
    - Blocos finalizados NUNCA são re-parseados
    - Apenas o último bloco é re-avaliado a cada chunk
    - Optimistic rendering - detecta tipo antes de fechar
    """

    # Pattern para fechar code fence
    CODE_FENCE_CLOSE = re.compile(r'^(`{3,}|~{3,})\s*$')

    def __init__(self):
        self.blocks: List[BlockInfo] = []
        self.current_block: Optional[BlockInfo] = None
        self.line_number: int = 0
        self.in_code_fence: bool = False
        self.code_fence_marker: str = ""
        self._buffer: str = ""

    def reset(self) -> None:
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

        # Detecta tipo de bloco VIA REGISTRY
        block_type = detect_block_type(line)

        # Continua bloco atual ou inicia novo?
        if self._should_continue_block(block_type, line):
            self._extend_current_block(line)
        else:
            self._finalize_current_block()
            self._start_new_block(block_type, line)

    def _process_partial_line(self, partial: str) -> None:
        """Processa linha parcial (optimistic parsing)."""
        if not partial.strip():
            return

        if self.in_code_fence:
            if self.current_block:
                self.current_block.content += partial
            return

        block_type = detect_block_type(partial)

        if self._should_continue_block(block_type, partial):
            if self.current_block:
                self.current_block.content += partial
        else:
            self._start_new_block(block_type, partial, is_partial=True)

    def _should_continue_block(self, new_type: BlockType, line: str) -> bool:
        """Determina se deve continuar bloco atual ou iniciar novo."""
        if not self.current_block:
            return False

        current_type = self.current_block.block_type

        # Usa registry para verificar continuação
        renderer_cls = BlockRendererRegistry._renderers.get(current_type)
        if renderer_cls:
            return renderer_cls.should_continue(current_type, new_type, line)

        # Fallback: tipos iguais continuam
        return current_type == new_type

    def _start_new_block(self, block_type: BlockType, line: str, is_partial: bool = False) -> None:
        """Inicia um novo bloco."""
        # Caso especial: code fence
        if block_type == BlockType.CODE_FENCE:
            match = re.match(r'^(`{3,}|~{3,})(\w*)\s*$', line.strip())
            if match:
                self.in_code_fence = True
                self.code_fence_marker = match.group(1)[:3]
                language = match.group(2) or None

                self.current_block = BlockInfo(
                    block_type=BlockType.CODE_FENCE,
                    start_line=self.line_number,
                    language=language,
                    content="",
                    is_complete=False,
                )
                return

        # Extrai metadata via registry
        metadata = {}
        renderer_cls = BlockRendererRegistry._renderers.get(block_type)
        if renderer_cls and hasattr(renderer_cls, 'extract_metadata'):
            metadata = renderer_cls.extract_metadata(line)

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


# Alias para compatibilidade
BlockDetector = BlockDetectorV2


__all__ = [
    'BlockDetectorV2',
    'BlockDetector',  # Alias
]
