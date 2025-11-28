"""
Interactive Checklist - Checklist interativo com animação de strikethrough.

Features:
- Click para toggle checkbox
- Animação ease-out de 200ms para strikethrough
- Parsing de markdown checklists durante streaming
- Visual estilo Claude Code (badges coloridos)

Autor: JuanCS Dev
Data: 2025-11-25
"""

import re
import time
import asyncio
from typing import Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive
from textual.message import Message
from textual.app import ComposeResult
from textual.containers import Vertical

from rich.text import Text


class ChecklistItemStatus(Enum):
    """Status de um item do checklist."""
    UNCHECKED = "unchecked"
    CHECKED = "checked"
    IN_PROGRESS = "in_progress"


class AnimationState(Enum):
    """Estado da animação de strikethrough."""
    IDLE = "idle"
    ANIMATING_CHECK = "animating_check"
    ANIMATING_UNCHECK = "animating_uncheck"
    COMPLETE = "complete"


@dataclass
class ChecklistItem:
    """Item de checklist."""
    text: str
    checked: bool = False
    animation_state: AnimationState = AnimationState.IDLE
    animation_progress: float = 0.0  # 0.0 a 1.0
    priority: Optional[str] = None  # BLOCKER, IMPORTANTE, SUGESTAO
    indent_level: int = 0

    @property
    def display_text(self) -> str:
        """Texto formatado para display."""
        return self.text.strip()

    @property
    def priority_badge(self) -> Optional[tuple[str, str]]:
        """Retorna (emoji, cor) para badge de prioridade."""
        badges = {
            "BLOCKER": ("", "red"),
            "IMPORTANTE": ("", "yellow"),
            "SUGESTAO": ("", "green"),
            "HIGH": ("", "red"),
            "MEDIUM": ("", "yellow"),
            "LOW": ("", "green"),
        }

        if self.priority:
            key = self.priority.upper()
            return badges.get(key, None)
        return None


class StrikethroughAnimation:
    """
    Animação de strikethrough da esquerda para direita.

    Usa easing ease-out para movimento natural.
    """

    DURATION_MS = 200
    FRAME_INTERVAL = 0.016  # ~60 FPS

    @staticmethod
    def ease_out(t: float) -> float:
        """
        Função ease-out (deceleração).

        Args:
            t: Progresso (0.0 a 1.0)

        Returns:
            Valor eased
        """
        return 1 - (1 - t) ** 3

    @classmethod
    async def animate(
        cls,
        text: str,
        on_frame: Callable[[str, float], None],
        reverse: bool = False,
    ) -> None:
        """
        Anima strikethrough progressivamente.

        Args:
            text: Texto a animar
            on_frame: Callback com (texto_parcial_riscado, progresso)
            reverse: Se True, anima de riscado para normal
        """
        start_time = time.perf_counter()
        duration_s = cls.DURATION_MS / 1000

        while True:
            elapsed = time.perf_counter() - start_time
            raw_progress = min(elapsed / duration_s, 1.0)

            # Aplica easing
            progress = cls.ease_out(raw_progress)

            if reverse:
                progress = 1.0 - progress

            # Callback com progresso
            on_frame(text, progress)

            if raw_progress >= 1.0:
                break

            await asyncio.sleep(cls.FRAME_INTERVAL)

    @staticmethod
    def render_partial_strikethrough(text: str, progress: float) -> Text:
        """
        Renderiza texto com strikethrough parcial.

        Args:
            text: Texto completo
            progress: Progresso da animação (0.0 a 1.0)

        Returns:
            Rich Text com strikethrough parcial
        """
        if progress <= 0:
            return Text(text)
        if progress >= 1:
            return Text(text, style="strike dim")

        # Calcula posição do strike
        strike_end = int(len(text) * progress)

        result = Text()

        # Parte riscada
        if strike_end > 0:
            result.append(text[:strike_end], style="strike dim")

        # Parte normal
        if strike_end < len(text):
            result.append(text[strike_end:])

        return result


class ChecklistParser:
    """Parser para checklists markdown durante streaming."""

    # Pattern para checklist item
    CHECKLIST_PATTERN = re.compile(
        r'^(\s*)[-*+]\s+\[([xX ])\]\s+(.+)$'
    )

    # Pattern para prioridade no texto
    PRIORITY_PATTERN = re.compile(
        r'\[?(BLOCKER|IMPORTANTE|SUGESTAO|HIGH|MEDIUM|LOW)\]?',
        re.IGNORECASE
    )

    @classmethod
    def parse_line(cls, line: str) -> Optional[ChecklistItem]:
        """
        Parseia uma linha como checklist item.

        Args:
            line: Linha a parsear

        Returns:
            ChecklistItem ou None
        """
        match = cls.CHECKLIST_PATTERN.match(line)
        if not match:
            return None

        indent = len(match.group(1))
        check_char = match.group(2)
        text = match.group(3).strip()

        # Detecta prioridade
        priority = None
        priority_match = cls.PRIORITY_PATTERN.search(text)
        if priority_match:
            priority = priority_match.group(1).upper()
            # Remove prioridade do texto
            text = cls.PRIORITY_PATTERN.sub('', text).strip()

        return ChecklistItem(
            text=text,
            checked=(check_char.lower() == 'x'),
            indent_level=indent // 2,  # 2 espaços por nível
            priority=priority,
        )

    @classmethod
    def parse_markdown(cls, markdown: str) -> List[ChecklistItem]:
        """
        Parseia markdown completo.

        Args:
            markdown: Texto markdown

        Returns:
            Lista de ChecklistItems
        """
        items = []
        for line in markdown.split('\n'):
            item = cls.parse_line(line)
            if item:
                items.append(item)
        return items


class ChecklistItemWidget(Widget):
    """Widget para um item individual do checklist."""

    DEFAULT_CSS = """
    ChecklistItemWidget {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    ChecklistItemWidget:hover {
        background: #44475a;
    }

    ChecklistItemWidget.checked {
        opacity: 0.7;
    }

    ChecklistItemWidget.animating {
        background: #00d4aa 10%;
    }
    """

    checked = reactive(False)

    class ItemToggled(Message):
        """Item foi toggled."""
        def __init__(self, item: ChecklistItem, new_state: bool):
            self.item = item
            self.new_state = new_state
            super().__init__()

    def __init__(
        self,
        item: ChecklistItem,
        animate_on_toggle: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        """
        Inicializa widget.

        Args:
            item: ChecklistItem
            animate_on_toggle: Animar ao toggle
            name: Nome
            id: ID
            classes: Classes
        """
        super().__init__(name=name, id=id, classes=classes)

        self.item = item
        self.checked = item.checked
        self.animate_on_toggle = animate_on_toggle
        self._animation_task: Optional[asyncio.Task] = None
        self._content: Optional[Static] = None

    def compose(self) -> ComposeResult:
        """Compõe widget."""
        self._content = Static(self._render_item())
        yield self._content

    def _render_item(self) -> Text:
        """Renderiza item."""
        result = Text()

        # Indent
        if self.item.indent_level > 0:
            result.append("  " * self.item.indent_level)

        # Checkbox
        checkbox = "" if self.item.checked else ""
        checkbox_style = "green" if self.item.checked else "dim"
        result.append(f"{checkbox} ", style=checkbox_style)

        # Badge de prioridade
        badge = self.item.priority_badge
        if badge:
            emoji, color = badge
            result.append(f"{emoji} ", style=color)

        # Texto com animação
        if self.item.animation_state in (
            AnimationState.ANIMATING_CHECK,
            AnimationState.ANIMATING_UNCHECK
        ):
            # Durante animação
            text_rendered = StrikethroughAnimation.render_partial_strikethrough(
                self.item.display_text,
                self.item.animation_progress
            )
            result.append_text(text_rendered)
        elif self.item.checked:
            # Checked - strikethrough completo
            result.append(self.item.display_text, style="strike dim")
        else:
            # Unchecked - normal
            result.append(self.item.display_text)

        return result

    async def _animate_toggle(self, checking: bool) -> None:
        """
        Anima toggle do checkbox.

        Args:
            checking: True se está marcando, False se desmarcando
        """
        self.add_class("animating")
        self.item.animation_state = (
            AnimationState.ANIMATING_CHECK if checking
            else AnimationState.ANIMATING_UNCHECK
        )

        def on_frame(text: str, progress: float) -> None:
            self.item.animation_progress = progress
            if self._content:
                self._content.update(self._render_item())

        await StrikethroughAnimation.animate(
            self.item.display_text,
            on_frame,
            reverse=not checking,
        )

        self.item.animation_state = AnimationState.COMPLETE
        self.item.animation_progress = 1.0 if checking else 0.0
        self.remove_class("animating")

    async def toggle(self) -> None:
        """Toggle estado do checkbox."""
        new_state = not self.item.checked

        if self.animate_on_toggle:
            # Cancela animação anterior se existir
            if self._animation_task and not self._animation_task.done():
                self._animation_task.cancel()
                try:
                    await self._animation_task
                except asyncio.CancelledError:
                    pass

            # Inicia nova animação
            self._animation_task = asyncio.create_task(
                self._animate_toggle(new_state)
            )
            await self._animation_task

        # Atualiza estado
        self.item.checked = new_state
        self.checked = new_state

        if new_state:
            self.add_class("checked")
        else:
            self.remove_class("checked")

        # Update display
        if self._content:
            self._content.update(self._render_item())

        # Emite evento
        self.post_message(self.ItemToggled(self.item, new_state))

    async def on_click(self) -> None:
        """Handler de click."""
        await self.toggle()


class InteractiveChecklist(Widget):
    """
    Checklist interativo com múltiplos items.

    Features:
    - Toggle por click
    - Animação de strikethrough
    - Badges de prioridade
    - Parsing de markdown streaming
    """

    DEFAULT_CSS = """
    InteractiveChecklist {
        width: 100%;
        height: auto;
        min-height: 3;
        border: solid #bd93f9;
        padding: 1;
    }

    InteractiveChecklist.streaming {
        border: solid #00d4aa;
    }

    InteractiveChecklist .checklist-header {
        background: #282a36;
        padding: 0 1;
        margin-bottom: 1;
    }

    InteractiveChecklist .checklist-items {
        width: 100%;
    }
    """

    is_streaming = reactive(False)
    total_items = reactive(0)
    checked_items = reactive(0)

    class ChecklistUpdated(Message):
        """Checklist foi atualizado."""
        def __init__(self, total: int, checked: int):
            self.total = total
            self.checked = checked
            super().__init__()

    class AllItemsChecked(Message):
        """Todos os items foram marcados."""
        pass

    def __init__(
        self,
        title: Optional[str] = None,
        show_progress: bool = True,
        animate_toggles: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ):
        """
        Inicializa checklist.

        Args:
            title: Título opcional
            show_progress: Mostrar progresso
            animate_toggles: Animar toggles
            name: Nome
            id: ID
            classes: Classes
        """
        super().__init__(name=name, id=id, classes=classes)

        self.title = title
        self.show_progress = show_progress
        self.animate_toggles = animate_toggles

        self._items: List[ChecklistItem] = []
        self._buffer = ""
        self._header: Optional[Static] = None
        self._items_container: Optional[Vertical] = None

    def compose(self) -> ComposeResult:
        """Compõe widget."""
        if self.title or self.show_progress:
            header_text = self._get_header_text()
            self._header = Static(header_text, classes="checklist-header")
            yield self._header

        self._items_container = Vertical(classes="checklist-items")
        yield self._items_container

    def _get_header_text(self) -> Text:
        """Gera texto do header."""
        result = Text()

        if self.title:
            result.append(f" {self.title}", style="bold")

        if self.show_progress and self.total_items > 0:
            if self.title:
                result.append(" | ")
            progress = f"{self.checked_items}/{self.total_items}"
            percentage = (self.checked_items / self.total_items) * 100
            result.append(f"{progress} ({percentage:.0f}%)", style="cyan")

        return result

    def _update_header(self) -> None:
        """Atualiza header."""
        if self._header:
            self._header.update(self._get_header_text())

    def _update_counts(self) -> None:
        """Atualiza contadores."""
        self.total_items = len(self._items)
        self.checked_items = sum(1 for item in self._items if item.checked)
        self._update_header()

        self.post_message(self.ChecklistUpdated(self.total_items, self.checked_items))

        if self.total_items > 0 and self.checked_items == self.total_items:
            self.post_message(self.AllItemsChecked())

    def start_stream(self) -> None:
        """Inicia streaming."""
        self.is_streaming = True
        self._items = []
        self._buffer = ""
        self.add_class("streaming")

        if self._items_container:
            self._items_container.remove_children()

        self._update_counts()

    def append_chunk(self, chunk: str) -> None:
        """
        Adiciona chunk de texto.

        Args:
            chunk: Texto a processar
        """
        if not self.is_streaming:
            return

        self._buffer += chunk

        # Processa linhas completas
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            self._process_line(line)

    def _process_line(self, line: str) -> None:
        """Processa uma linha."""
        item = ChecklistParser.parse_line(line)
        if item:
            self._add_item(item)

    def _add_item(self, item: ChecklistItem) -> None:
        """Adiciona item ao checklist."""
        self._items.append(item)

        if self._items_container:
            widget = ChecklistItemWidget(
                item,
                animate_on_toggle=self.animate_toggles,
            )
            self._items_container.mount(widget)

        self._update_counts()

    def end_stream(self) -> None:
        """Finaliza streaming."""
        # Processa buffer restante
        if self._buffer.strip():
            self._process_line(self._buffer)
            self._buffer = ""

        self.is_streaming = False
        self.remove_class("streaming")

    def set_items(self, items: List[ChecklistItem]) -> None:
        """
        Define items diretamente.

        Args:
            items: Lista de items
        """
        self._items = items

        if self._items_container:
            self._items_container.remove_children()
            for item in items:
                widget = ChecklistItemWidget(
                    item,
                    animate_on_toggle=self.animate_toggles,
                )
                self._items_container.mount(widget)

        self._update_counts()

    def set_markdown(self, markdown: str) -> None:
        """
        Define checklist a partir de markdown.

        Args:
            markdown: Markdown com checklist
        """
        items = ChecklistParser.parse_markdown(markdown)
        self.set_items(items)

    def on_checklist_item_widget_item_toggled(
        self, event: ChecklistItemWidget.ItemToggled
    ) -> None:
        """Handler quando item é toggled."""
        self._update_counts()

    def get_items(self) -> List[ChecklistItem]:
        """Retorna items."""
        return self._items.copy()

    def get_checked_items(self) -> List[ChecklistItem]:
        """Retorna items marcados."""
        return [item for item in self._items if item.checked]

    def get_unchecked_items(self) -> List[ChecklistItem]:
        """Retorna items não marcados."""
        return [item for item in self._items if not item.checked]


def parse_checklist_markdown(markdown: str) -> List[ChecklistItem]:
    """
    Parseia checklist de markdown.

    Args:
        markdown: Texto markdown

    Returns:
        Lista de ChecklistItems
    """
    return ChecklistParser.parse_markdown(markdown)


def render_checklist_text(
    items: List[ChecklistItem],
    show_badges: bool = True,
) -> Text:
    """
    Renderiza checklist como Rich Text.

    Args:
        items: Lista de items
        show_badges: Mostrar badges de prioridade

    Returns:
        Rich Text
    """
    result = Text()

    for i, item in enumerate(items):
        if i > 0:
            result.append("\n")

        # Indent
        if item.indent_level > 0:
            result.append("  " * item.indent_level)

        # Checkbox
        checkbox = "" if item.checked else ""
        checkbox_style = "green" if item.checked else "dim"
        result.append(f"{checkbox} ", style=checkbox_style)

        # Badge
        if show_badges:
            badge = item.priority_badge
            if badge:
                emoji, color = badge
                result.append(f"{emoji} ", style=color)

        # Texto
        if item.checked:
            result.append(item.display_text, style="strike dim")
        else:
            result.append(item.display_text)

    return result
