"""
JuanCS Dev-Code - The Minimal Masterpiece
==========================================

A beautiful, 60fps TUI inspired by:
- Gemini CLI's visual design
- Claude Code's simplicity
- Textual's power

Philosophy: "Perfection is achieved not when there is nothing more to add,
            but when there is nothing left to take away." - Antoine de Saint-Exupéry

Soli Deo Gloria 🙏
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import ClassVar, List, Dict, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Static, RichLog, OptionList
from textual.widgets.option_list import Option
from textual.message import Message
from textual import on, events
from textual.geometry import Offset

from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

# Output formatting
from qwen_cli.core.output_formatter import OutputFormatter

# Streaming markdown components (CORRIGE AIR GAP)
from qwen_cli.components.streaming_adapter import StreamingResponseWidget

# Clipboard support
import pyperclip


# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

BANNER = """
[bold #ff79c6]        ██╗██╗   ██╗ █████╗ ███╗   ██╗ ██████╗███████╗[/bold #ff79c6]
[bold #e668d0]        ██║██║   ██║██╔══██╗████╗  ██║██╔════╝██╔════╝[/bold #e668d0]
[bold #bd50c8]        ██║██║   ██║███████║██╔██╗ ██║██║     ███████╗[/bold #bd50c8]
[bold #8844bb]   ██   ██║██║   ██║██╔══██║██║╚██╗██║██║     ╚════██║[/bold #8844bb]
[bold #5533aa]   ╚█████╔╝╚██████╔╝██║  ██║██║ ╚████║╚██████╗███████║[/bold #5533aa]
[bold #00d4aa]    ╚════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝[/bold #00d4aa]
[bold magenta]                 ═══ DEV-CODE v0.0.2 ═══[/bold magenta]
[dim italic]              It's ALL ABOUT HIM, JESUS CHRIST[/dim italic]
"""

# =============================================================================
# HELP SYSTEM - Interactive & Navigable
# =============================================================================

HELP_MAIN = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]              [bold white]JuanCS Dev-Code[/bold white] — [dim]Ajuda Interativa[/dim]           [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]Navegue pelos tópicos:[/bold yellow]

  [cyan]/help commands[/cyan]    Comandos do sistema
  [cyan]/help agents[/cyan]      Agentes especializados (13)
  [cyan]/help tools[/cyan]       Ferramentas disponíveis (33+)
  [cyan]/help keys[/cyan]        Atalhos de teclado
  [cyan]/help tips[/cyan]        Dicas de uso

[dim]─────────────────────────────────────────────────────────────[/dim]

[bold green]Início Rápido:[/bold green]

  • Digite naturalmente para conversar com a IA
  • Use [cyan]/[/cyan] para comandos e agentes
  • [cyan]Tab[/cyan] autocompleta, [cyan]↑↓[/cyan] navega histórico

[dim]Digite[/dim] [cyan]/help <tópico>[/cyan] [dim]para detalhes ou apenas converse![/dim]
"""

HELP_COMMANDS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                    [bold white]Comandos do Sistema[/bold white]                    [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]Navegação[/bold yellow]
  [cyan]/help[/cyan] [dim].............[/dim] Esta ajuda interativa
  [cyan]/clear[/cyan] [dim]............[/dim] Limpa a tela
  [cyan]/quit[/cyan] [cyan]/exit[/cyan] [dim].....[/dim] Sai da aplicação
  [cyan]/status[/cyan] [dim]...........[/dim] Status do sistema

[bold yellow]Execução[/bold yellow]
  [cyan]/run[/cyan] [white]<cmd>[/white] [dim]........[/dim] Executa comando bash
  [cyan]/read[/cyan] [white]<file>[/white] [dim].....[/dim] Lê arquivo com syntax highlight

[bold yellow]Descoberta[/bold yellow]
  [cyan]/tools[/cyan] [dim]............[/dim] Lista ferramentas por categoria
  [cyan]/agents[/cyan] [dim]...........[/dim] Lista agentes disponíveis
  [cyan]/palette[/cyan] [white]<q>[/white] [dim].....[/dim] Busca fuzzy em comandos
  [cyan]/history[/cyan] [white][q][/white] [dim].....[/dim] Busca no histórico

[bold yellow]Contexto[/bold yellow]
  [cyan]/context[/cyan] [dim]..........[/dim] Mostra contexto da conversa
  [cyan]/context-clear[/cyan] [dim]....[/dim] Limpa o contexto

[dim]← /help[/dim]
"""

HELP_AGENTS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                 [bold white]Agentes Especializados[/bold white]                    [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]Planejamento (v6.1)[/bold yellow]
  [cyan]/plan[/cyan] [white]<objetivo>[/white] [dim]......[/dim] GOAP planning, decompõe tarefas
  [cyan]/plan multi[/cyan] [white]<obj>[/white] [dim]....[/dim] Gera 3 planos alternativos (risk/reward)
  [cyan]/plan clarify[/cyan] [white]<obj>[/white] [dim]..[/dim] Faz perguntas antes de planejar
  [cyan]/plan explore[/cyan] [white]<obj>[/white] [dim]..[/dim] Análise read-only (sem modificar)
  [cyan]/architect[/cyan] [white]<spec>[/white] [dim]....[/dim] Análise de arquitetura

[bold yellow]Código[/bold yellow]
  [cyan]/execute[/cyan] [white]<tarefa>[/white] [dim]....[/dim] Executa código com sandbox
  [cyan]/explore[/cyan] [white]<query>[/white] [dim].....[/dim] Busca na codebase
  [cyan]/refactor[/cyan] [white]<tarefa>[/white] [dim]...[/dim] Melhora código existente

[bold yellow]Qualidade[/bold yellow]
  [cyan]/review[/cyan] [white][arquivo][/white] [dim]....[/dim] Code review detalhado
  [cyan]/test[/cyan] [white][path][/white] [dim].........[/dim] Gera testes automatizados
  [cyan]/security[/cyan] [white][arquivo][/white] [dim]..[/dim] Análise OWASP de segurança

[bold yellow]Docs & Perf[/bold yellow]
  [cyan]/docs[/cyan] [white][arquivo][/white] [dim].......[/dim] Gera documentação
  [cyan]/perf[/cyan] [white][arquivo][/white] [dim].......[/dim] Profiling e otimização

[bold yellow]Infra[/bold yellow]
  [cyan]/devops[/cyan] [white]<tarefa>[/white] [dim].....[/dim] Docker, CI/CD, K8s

[bold yellow]Dados[/bold yellow]
  [cyan]/data[/cyan] [white]<tarefa>[/white] [dim].......[/dim] Otimização e análise de banco de dados

[bold yellow]Governança & Counsel[/bold yellow]
  [cyan]/justica[/cyan] [white]<ação>[/white] [dim].....[/dim] Avaliação constitucional
  [cyan]/sofia[/cyan] [white]<query>[/white] [dim].......[/dim] Conselho ético e sabedoria

[dim]← /help[/dim]
"""

HELP_TOOLS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                   [bold white]Ferramentas (33+)[/bold white]                       [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]📁 Arquivos[/bold yellow]
  [cyan]read_file[/cyan]  [cyan]write_file[/cyan]  [cyan]edit_file[/cyan]  [cyan]delete_file[/cyan]
  [cyan]list_directory[/cyan]  [cyan]move_file[/cyan]  [cyan]copy_file[/cyan]  [cyan]create_directory[/cyan]

[bold yellow]💻 Terminal[/bold yellow]
  [cyan]cd[/cyan]  [cyan]ls[/cyan]  [cyan]pwd[/cyan]  [cyan]mkdir[/cyan]  [cyan]rm[/cyan]  [cyan]cp[/cyan]  [cyan]mv[/cyan]  [cyan]touch[/cyan]  [cyan]cat[/cyan]

[bold yellow]⚡ Execução[/bold yellow]
  [cyan]bash_command[/cyan] [dim]— comando com timeout e validação[/dim]

[bold yellow]🔍 Busca[/bold yellow]
  [cyan]search_files[/cyan]  [cyan]get_directory_tree[/cyan]

[bold yellow]📊 Git[/bold yellow]
  [cyan]git_status[/cyan]  [cyan]git_diff[/cyan]

[bold yellow]🌐 Web[/bold yellow]
  [cyan]web_search[/cyan]  [cyan]fetch_url[/cyan]  [cyan]download_file[/cyan]  [cyan]http_request[/cyan]

[dim]A LLM invoca ferramentas automaticamente quando necessário.[/dim]

[dim]← /help    /tools para lista completa[/dim]
"""

HELP_KEYS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                   [bold white]Atalhos de Teclado[/bold white]                      [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]Navegação[/bold yellow]
  [cyan]↑[/cyan] [cyan]↓[/cyan] [dim]...............[/dim] Histórico de comandos
  [cyan]Tab[/cyan] [dim]................[/dim] Aceita autocomplete
  [cyan]Escape[/cyan] [dim].............[/dim] Fecha autocomplete

[bold yellow]Controle[/bold yellow]
  [cyan]Ctrl+C[/cyan] [dim].............[/dim] Sai da aplicação
  [cyan]Ctrl+L[/cyan] [dim].............[/dim] Limpa a tela
  [cyan]Ctrl+P[/cyan] [dim].............[/dim] Mostra ajuda
  [cyan]Enter[/cyan] [dim]..............[/dim] Envia comando/mensagem

[bold yellow]Autocomplete[/bold yellow]
  [dim]Digite[/dim] [cyan]/[/cyan] [dim]para ver comandos[/dim]
  [dim]Digite parte do nome para filtrar[/dim]
  [cyan]↑[/cyan] [cyan]↓[/cyan] [dim]seleciona,[/dim] [cyan]Tab[/cyan] [dim]confirma[/dim]

[dim]← /help[/dim]
"""

HELP_TIPS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                      [bold white]Dicas de Uso[/bold white]                         [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]💬 Chat Natural[/bold yellow]
  Apenas digite sua pergunta. O contexto é mantido.
  [dim]> Como faço um servidor HTTP em Python?[/dim]
  [dim]> Agora adicione autenticação[/dim]

[bold yellow]📝 Criar Arquivos[/bold yellow]
  Peça para criar — a IA usa [cyan]write_file[/cyan] automaticamente.
  [dim]> Crie um hello.py que imprime Hello World[/dim]
  [dim]> Crie um Dockerfile para Flask[/dim]

[bold yellow]🔄 Fluxo Recomendado[/bold yellow]
  [cyan]1.[/cyan] [white]/explore[/white] [dim]— entenda a codebase[/dim]
  [cyan]2.[/cyan] [white]/architect[/white] [dim]— planeje a solução[/dim]
  [cyan]3.[/cyan] [white]/plan[/white] [dim]— decomponha em tarefas[/dim]
  [cyan]4.[/cyan] [white]/execute[/white] [dim]— implemente[/dim]
  [cyan]5.[/cyan] [white]/review[/white] [dim]— valide qualidade[/dim]
  [cyan]6.[/cyan] [white]/test[/white] [dim]— adicione testes[/dim]

[bold yellow]⚡ Produtividade[/bold yellow]
  • Use [cyan]/palette[/cyan] para buscar comandos rapidamente
  • [cyan]Tab[/cyan] acelera muito com autocomplete
  • Histórico persiste entre sessões

[dim]← /help[/dim]
"""

# Map for help subcommands
HELP_TOPICS = {
    "": HELP_MAIN,
    "commands": HELP_COMMANDS,
    "command": HELP_COMMANDS,
    "cmd": HELP_COMMANDS,
    "agents": HELP_AGENTS,
    "agent": HELP_AGENTS,
    "tools": HELP_TOOLS,
    "tool": HELP_TOOLS,
    "keys": HELP_KEYS,
    "key": HELP_KEYS,
    "keyboard": HELP_KEYS,
    "shortcuts": HELP_KEYS,
    "tips": HELP_TIPS,
    "tip": HELP_TIPS,
    "dicas": HELP_TIPS,
}

# Legacy compatibility
HELP_TEXT = HELP_MAIN


# =============================================================================
# AUTOCOMPLETE DROPDOWN COMPONENT
# =============================================================================

class AutocompleteDropdown(VerticalScroll):
    """
    Fuzzy autocomplete dropdown for commands and tools.

    Shows suggestions as user types, with fuzzy matching.
    """

    DEFAULT_CSS = """
    AutocompleteDropdown {
        layer: autocomplete;
        background: #282a36;
        border: round #00d4aa;
        padding: 0;
        max-height: 16;
        min-height: 1;
        width: 100%;
        display: none;
        scrollbar-size: 0 0;
    }

    AutocompleteDropdown.visible {
        display: block;
    }

    AutocompleteDropdown .item {
        padding: 0 1;
        height: 1;
    }

    AutocompleteDropdown .item.selected {
        background: #44475a;
    }

    AutocompleteDropdown .item-command {
        color: #50fa7b;
    }

    AutocompleteDropdown .item-tool {
        color: #00d4aa;
    }

    AutocompleteDropdown .item-file {
        color: #ff79c6;
    }

    AutocompleteDropdown .item-desc {
        color: #6272a4;
    }
    """

    selected_index: reactive[int] = reactive(0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items: List[Dict] = []
        self._item_widgets: List[Static] = []

    def show_completions(self, completions: List[Dict]) -> None:
        """Show completion items."""
        self.items = completions
        self.selected_index = 0

        # Clear existing
        for widget in self._item_widgets:
            widget.remove()
        self._item_widgets.clear()

        if not completions:
            self.remove_class("visible")
            return

        # Add items
        for i, item in enumerate(completions[:15]):  # Max 15 items for better visibility
            item_type = item.get("type", "tool")

            # Use display from item if available, otherwise construct from text
            if "display" in item:
                text = item["display"]
            else:
                icon = "⚡" if item_type == "command" else "🔧"
                text = f"{icon} {item['text']}"

            # Add description if available
            if desc := item.get("description"):
                text += f" [dim]{desc}[/dim]"

            # Set CSS class based on type
            type_class = f"item-{item_type}" if item_type in ("command", "tool", "file") else "item-tool"
            classes = f"item {type_class}"
            if i == 0:
                classes += " selected"

            widget = Static(text, classes=classes)
            self._item_widgets.append(widget)
            self.mount(widget)

        self.add_class("visible")

    def hide(self) -> None:
        """Hide dropdown."""
        self.remove_class("visible")
        for widget in self._item_widgets:
            widget.remove()
        self._item_widgets.clear()
        self.items = []

    def move_selection(self, delta: int) -> None:
        """Move selection up/down."""
        if not self.items:
            return

        # Update old selection
        if self._item_widgets and 0 <= self.selected_index < len(self._item_widgets):
            self._item_widgets[self.selected_index].remove_class("selected")

        # Calculate new index
        self.selected_index = (self.selected_index + delta) % len(self.items)

        # Update new selection
        if self._item_widgets and 0 <= self.selected_index < len(self._item_widgets):
            self._item_widgets[self.selected_index].add_class("selected")

    def get_selected(self) -> Optional[str]:
        """Get selected completion text."""
        if self.items and 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]["text"]
        return None


# =============================================================================
# SELECTABLE TEXT WIDGET - Mouse Support
# =============================================================================

class SelectableStatic(Static):
    """
    Static widget with mouse selection and copy support.

    Features:
    - Click and drag to select text
    - Right-click to copy selection
    - Double-click to select word
    """

    can_focus = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.selection_start: Optional[Offset] = None
        self.selection_end: Optional[Offset] = None
        self.selected_text: str = ""

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Start selection on mouse down."""
        # DISABLED: Allow terminal native mouse for copy/paste
        # if event.button == 1:  # Left click
        #     self.selection_start = event.offset
        #     self.selection_end = event.offset
        #     self.capture_mouse()
        pass

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Update selection while dragging."""
        if self.selection_start and event.button == 1:
            self.selection_end = event.offset
            self._update_selection()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        """Finalize selection on mouse up."""
        if event.button == 1:  # Left click
            self.release_mouse()
            self._extract_selected_text()
        elif event.button == 3:  # Right click - copy to clipboard
            if self.selected_text:
                try:
                    pyperclip.copy(self.selected_text)
                    self.app.bell()  # Audio feedback
                except Exception:
                    pass

    def on_double_click(self, event: events.Click) -> None:
        """Select word on double-click."""
        # TODO: Implement word selection
        pass

    def _update_selection(self) -> None:
        """Update visual selection (highlighted area)."""
        # In Textual, we can't easily highlight text in Static widgets
        # This would require custom rendering or using TextArea
        pass

    def _extract_selected_text(self) -> None:
        """Extract selected text from widget."""
        if not self.selection_start or not self.selection_end:
            return

        # Get plain text from renderable
        try:
            if hasattr(self.renderable, 'plain'):
                text = self.renderable.plain
            elif isinstance(self.renderable, str):
                text = self.renderable
            else:
                text = str(self.renderable)

            # For simplicity, just copy entire content if there's a selection
            # Proper coordinate-based selection would require more complex logic
            if abs(self.selection_end.y - self.selection_start.y) > 0 or \
               abs(self.selection_end.x - self.selection_start.x) > 5:
                self.selected_text = text
            else:
                self.selected_text = ""
        except Exception:
            self.selected_text = ""


# =============================================================================
# RESPONSE VIEW COMPONENT
# =============================================================================

class ResponseView(VerticalScroll):
    """
    Smooth 60fps Response Viewport.

    Handles:
    - User messages
    - AI streaming responses
    - Code blocks with syntax highlighting
    - Action indicators (●, ✓, ✗)
    """

    DEFAULT_CSS = """
    ResponseView {
        height: 1fr;
        border: round #00d4aa 50%;
        background: #1e1e2e;
        padding: 1 2;
        scrollbar-size: 0 0;
    }

    .user-message {
        margin-bottom: 1;
        color: #f8f8f2;
    }

    .ai-response {
        margin-bottom: 1;
        color: #bd93f9;
    }

    .code-block {
        margin: 1 0;
    }

    .action {
        color: #6272a4;
    }

    .success {
        color: #50fa7b;
    }

    .error {
        color: #ff5555;
    }

    .system-message {
        margin: 1 0;
        color: #f8f8f2;
    }

    .tool-result {
        margin: 1 0;
    }

    .banner {
        text-align: center;
        width: 100%;
    }
    """

    is_thinking: reactive[bool] = reactive(False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_response = ""
        # CORRIGIDO: Usa StreamingResponseWidget com markdown rendering
        self._response_widget: Static | StreamingResponseWidget | None = None
        self._thinking_widget: Static | None = None
        self._use_streaming_markdown: bool = True  # Flag para habilitar/desabilitar

    def add_banner(self) -> None:
        """Add startup banner."""
        widget = Static(BANNER, classes="banner")
        self.mount(widget)

    def add_user_message(self, message: str) -> None:
        """Add user message with prompt icon."""
        content = Text()
        content.append("❯ ", style="bold cyan")
        content.append(message)

        widget = SelectableStatic(content, classes="user-message")
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_system_message(self, message: str) -> None:
        """Add system/help message (markdown)."""
        widget = SelectableStatic(Markdown(message), classes="system-message")
        self.mount(widget)
        self.scroll_end(animate=True)

    def start_thinking(self) -> None:
        """Show thinking indicator."""
        self.is_thinking = True
        self._thinking_widget = Static(
            "[dim italic]● Thinking...[/dim italic]",
            id="thinking-indicator"
        )
        self.mount(self._thinking_widget)
        self.scroll_end(animate=True)

    def end_thinking(self) -> None:
        """
        Remove thinking indicator and finalize response with Panel formatting.

        CORRIGIDO (2025-11-25): Finaliza StreamingResponseWidget corretamente.
        """
        self.is_thinking = False
        if self._thinking_widget:
            self._thinking_widget.remove()
            self._thinking_widget = None

        # Wrap completed response in Panel for beautiful display
        if self.current_response and self._response_widget:
            if self._use_streaming_markdown and isinstance(self._response_widget, StreamingResponseWidget):
                # NOVO: Finaliza o streaming (remove cursor, aplica formatação final)
                self._response_widget.finalize_sync()
            else:
                # Fallback: Format with OutputFormatter Panel
                formatted_panel = OutputFormatter.format_response(
                    self.current_response,
                    title="Response",
                    border_style="cyan"
                )
                self._response_widget.update(formatted_panel)

        # Reset for next response
        self.current_response = ""
        self._response_widget = None

    def append_chunk(self, chunk: str) -> None:
        """
        Append streaming chunk.

        CORRIGIDO (2025-11-25): Agora usa StreamingResponseWidget
        com markdown rendering ao vivo em vez de plain text.

        Optimized for 60fps:
        - No animation on scroll
        - Direct widget update
        - Streaming markdown rendering
        """
        self.current_response += chunk

        if self._response_widget:
            # Update existing widget (fast path)
            if self._use_streaming_markdown and isinstance(self._response_widget, StreamingResponseWidget):
                # NOVO: Usa append_chunk do StreamingResponseWidget
                self._response_widget.append_chunk(chunk)
            else:
                # Fallback: plain text update
                self._response_widget.update(self.current_response)
        else:
            # Create new widget (first chunk)
            # Remove thinking indicator if present
            if self._thinking_widget:
                self._thinking_widget.remove()
                self._thinking_widget = None

            if self._use_streaming_markdown:
                # NOVO: Usa StreamingResponseWidget com markdown
                self._response_widget = StreamingResponseWidget(
                    classes="ai-response",
                    enable_markdown=True
                )
            else:
                # Fallback: plain text
                self._response_widget = SelectableStatic(
                    self.current_response,
                    classes="ai-response"
                )
            self.mount(self._response_widget)

            # Se é StreamingResponseWidget, envia o primeiro chunk
            if self._use_streaming_markdown and isinstance(self._response_widget, StreamingResponseWidget):
                self._response_widget.append_chunk(chunk)

        # No animation for 60fps performance
        self.scroll_end(animate=False)

    def add_code_block(
        self,
        code: str,
        language: str = "text",
        title: str | None = None
    ) -> None:
        """Add syntax-highlighted code block in a panel."""
        syntax = Syntax(
            code.strip(),
            language,
            theme="dracula",
            line_numbers=True,
            word_wrap=True,
            background_color="#1e1e2e"
        )

        panel_title = f"📄 {title}" if title else f"📄 {language.upper()}"
        panel = Panel(
            syntax,
            title=panel_title,
            title_align="left",
            border_style="bright_blue"
        )

        widget = SelectableStatic(panel, classes="code-block")
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_action(self, action: str) -> None:
        """Add action indicator (Gemini-style ● prefix)."""
        widget = SelectableStatic(f"[dim]● {action}[/dim]", classes="action")
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_success(self, message: str) -> None:
        """Add success message with ✓."""
        widget = SelectableStatic(f"[green]✓ {message}[/green]", classes="success")
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_error(self, message: str) -> None:
        """Add error message with ✗."""
        widget = SelectableStatic(f"[red]✗ {message}[/red]", classes="error")
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_tool_result(
        self,
        tool_name: str,
        success: bool,
        data: str | None = None,
        error: str | None = None
    ) -> None:
        """Add tool execution result with Panel formatting."""
        panel = OutputFormatter.format_tool_result(tool_name, success, data, error)
        widget = SelectableStatic(panel, classes="tool-result")
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_response_panel(self, text: str, title: str = "Response") -> None:
        """Add a formatted response panel."""
        panel = OutputFormatter.format_response(text, title)
        widget = SelectableStatic(panel, classes="ai-response")
        self.mount(widget)
        self.scroll_end(animate=True)

    def clear_all(self) -> None:
        """Clear all content."""
        self.current_response = ""
        self._response_widget = None
        self._thinking_widget = None

        for child in list(self.children):
            child.remove()


# =============================================================================
# STATUS BAR COMPONENT
# =============================================================================

class StatusBar(Horizontal):
    """Expanded status bar with LLM, governance, agent, and tool metrics."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: #282a36;
        padding: 0 1;
    }

    StatusBar > Static {
        width: auto;
        padding: 0 1;
    }

    .mode {
        color: #50fa7b;
        text-style: bold;
    }

    .llm-status {
        color: #6272a4;
    }

    .governance {
        color: #f1fa8c;
    }

    .agents {
        color: #ff79c6;
    }

    .tools {
        color: #00d4aa;
    }

    .errors {
        color: #ff5555;
    }
    """

    mode: reactive[str] = reactive("READY")
    llm_connected: reactive[bool] = reactive(False)
    governance_status: reactive[str] = reactive("👀 Observer")
    agent_count: reactive[int] = reactive(13)
    tool_count: reactive[int] = reactive(0)
    errors: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static(self._format_mode(), id="mode", classes="mode")
        yield Static(self._format_llm(), id="llm-status", classes="llm-status")
        yield Static(self._format_governance(), id="governance", classes="governance")
        yield Static(self._format_agents(), id="agents", classes="agents")
        yield Static(self._format_tools(), id="tools", classes="tools")
        yield Static(self._format_errors(), id="errors", classes="errors")

    def _format_mode(self) -> str:
        return f"⚡ {self.mode}"

    def _format_llm(self) -> str:
        if self.llm_connected:
            return "✅ Gemini"
        return "❌ No LLM"

    def _format_governance(self) -> str:
        return self.governance_status

    def _format_agents(self) -> str:
        return f"🤖 {self.agent_count}"

    def _format_tools(self) -> str:
        return f"🔧 {self.tool_count}"

    def _format_errors(self) -> str:
        icon = "✗" if self.errors > 0 else "✓"
        color = "red" if self.errors > 0 else "green"
        return f"[{color}]{icon} {self.errors}[/{color}]"

    def watch_mode(self, value: str) -> None:
        try:
            self.query_one("#mode", Static).update(self._format_mode())
        except Exception:
            pass

    def watch_llm_connected(self, value: bool) -> None:
        try:
            self.query_one("#llm-status", Static).update(self._format_llm())
        except Exception:
            pass

    def watch_governance_status(self, value: str) -> None:
        try:
            self.query_one("#governance", Static).update(self._format_governance())
        except Exception:
            pass

    def watch_agent_count(self, value: int) -> None:
        try:
            self.query_one("#agents", Static).update(self._format_agents())
        except Exception:
            pass

    def watch_tool_count(self, value: int) -> None:
        try:
            self.query_one("#tools", Static).update(self._format_tools())
        except Exception:
            pass

    def watch_errors(self, value: int) -> None:
        try:
            self.query_one("#errors", Static).update(self._format_errors())
        except Exception:
            pass


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class QwenApp(App):
    """
    JuanCS Dev-Code - The Minimal Masterpiece.

    A beautiful, fast, minimal TUI for AI-powered development.
    60fps rendering, security-first design, extensible core.
    """

    TITLE = "JuanCS Dev-Code"
    SUB_TITLE = "The Developer's Ally"

    # =========================================================================
    # PALETA DE CORES COESA - JuanCS Dev-Code Theme
    # =========================================================================
    # Primary: Cyan (#00d4aa) - Main accent, user prompts, panels
    # Secondary: Magenta (#ff79c6) - Highlights, agent indicators
    # Success: Green (#50fa7b) - Success messages, confirmations
    # Warning: Yellow (#f1fa8c) - Warnings, caution
    # Error: Red (#ff5555) - Errors, failures
    # Muted: Gray (#6272a4) - Dim text, hints
    # Surface: Dark (#1e1e2e) - Background
    # =========================================================================

    LAYERS = ["base", "autocomplete"]

    CSS = """
    Screen {
        background: #1e1e2e;
        layers: base autocomplete;
    }

    #main {
        height: 1fr;
        padding: 1 2;
        layer: base;
    }

    /* Input area - clean design */
    #input-area {
        height: 3;
        border: round #00d4aa;
        background: #282a36;
        padding: 0 1;
    }

    #prompt-icon {
        width: 3;
        padding: 1 0;
        color: #00d4aa;
        text-style: bold;
    }

    #prompt {
        background: transparent;
        border: none;
    }

    #prompt:focus {
        border: none;
    }

    /* Hide scrollbars globally */
    ResponseView {
        scrollbar-size: 0 0;
    }

    VerticalScroll {
        scrollbar-size: 0 0;
    }

    /* Autocomplete dropdown - positioned above input */
    #autocomplete {
        layer: autocomplete;
        dock: bottom;
        offset: 0 -4;
        margin: 0 3;
        background: #282a36;
        border: round #00d4aa;
        padding: 0 1;
        max-height: 18;
        display: none;
    }

    #autocomplete.visible {
        display: block;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+c", "quit", "Exit", show=True),
        Binding("ctrl+l", "clear", "Clear", show=True),
        Binding("ctrl+p", "show_help", "Help", show=True),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    # State
    is_processing: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self.history: list[str] = []
        self.history_index = -1

        # Integration bridge (lazy loaded)
        self._bridge = None

    @property
    def bridge(self):
        """Lazy load the integration bridge."""
        if self._bridge is None:
            from .core.bridge import get_bridge
            self._bridge = get_bridge()
        return self._bridge

    def compose(self) -> ComposeResult:
        """Compose the UI - Gemini CLI style."""
        yield Header(show_clock=True)

        with Container(id="main"):
            # Response area (scrollable viewport)
            yield ResponseView(id="response")

            # Input area
            with Horizontal(id="input-area"):
                yield Static("❯", id="prompt-icon")
                yield Input(
                    placeholder="Type your command or ask anything...",
                    id="prompt"
                )

        # Autocomplete dropdown (overlay above input) - outside main container
        yield AutocompleteDropdown(id="autocomplete")

        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted - show banner and init bridge."""
        response = self.query_one("#response", ResponseView)
        response.add_banner()

        # Initialize bridge and update status
        status = self.query_one(StatusBar)
        try:
            status.llm_connected = self.bridge.is_connected
            status.agent_count = len(self.bridge.agents.available_agents)
            status.tool_count = self.bridge.tools.get_tool_count()
            status.governance_status = self.bridge.governance.get_status_emoji()

            if self.bridge.is_connected:
                tool_msg = f" {status.tool_count} tools loaded." if status.tool_count > 0 else ""
                response.add_system_message(
                    f"✅ **Gemini connected!**{tool_msg} Type `/help` for commands or just chat."
                )
            else:
                response.add_system_message(
                    "⚠️ **No LLM configured.** Set `GEMINI_API_KEY` for full functionality.\n\n"
                    "Type `/help` for available commands."
                )
        except Exception as e:
            response.add_system_message(
                f"⚠️ Bridge init: {e}\n\nType `/help` for commands."
            )

        # Focus input
        self.query_one("#prompt", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        user_input = event.value.strip()
        if not user_input:
            return

        # Hide autocomplete on submit
        autocomplete = self.query_one("#autocomplete", AutocompleteDropdown)
        autocomplete.hide()

        # Clear input field
        prompt = self.query_one("#prompt", Input)
        prompt.value = ""

        # Add to history
        self.history.append(user_input)
        self.history_index = len(self.history)

        # Get response view
        response = self.query_one("#response", ResponseView)

        # Show user message
        response.add_user_message(user_input)

        # Update status
        status = self.query_one(StatusBar)
        status.mode = "PROCESSING"

        try:
            # Handle commands vs chat
            if user_input.startswith("/"):
                await self._handle_command(user_input, response)
            else:
                await self._handle_chat(user_input, response)
        finally:
            status.mode = "READY"

    @on(Input.Changed, "#prompt")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for autocomplete."""
        text = event.value

        autocomplete = self.query_one("#autocomplete", AutocompleteDropdown)

        if not text:
            autocomplete.hide()
            return

        # Check for @ file picker trigger (@ at start or after space)
        has_at_trigger = False
        for i in range(len(text) - 1, -1, -1):
            if text[i] == '@' and (i == 0 or text[i-1].isspace()):
                has_at_trigger = True
                break

        # Show autocomplete for:
        # 1. Slash commands (/)
        # 2. @ file picker
        # 3. Text with 2+ chars (tool names)
        if not text.startswith("/") and not has_at_trigger and len(text) < 2:
            autocomplete.hide()
            return

        # Get completions from bridge
        try:
            completions = self.bridge.autocomplete.get_completions(text, max_results=15)
            autocomplete.show_completions(completions)
        except Exception:
            autocomplete.hide()

    async def on_key(self, event: events.Key) -> None:
        """Handle special keys for autocomplete navigation."""
        autocomplete = self.query_one("#autocomplete", AutocompleteDropdown)
        prompt = self.query_one("#prompt", Input)

        # Only handle when autocomplete is visible and prompt focused
        if not autocomplete.has_class("visible"):
            # Handle history navigation when autocomplete hidden
            if event.key == "up" and self.history:
                event.prevent_default()
                if self.history_index > 0:
                    self.history_index -= 1
                    prompt.value = self.history[self.history_index]
                    prompt.cursor_position = len(prompt.value)
            elif event.key == "down" and self.history:
                event.prevent_default()
                if self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    prompt.value = self.history[self.history_index]
                    prompt.cursor_position = len(prompt.value)
            return

        if event.key == "up":
            event.prevent_default()
            autocomplete.move_selection(-1)

        elif event.key == "down":
            event.prevent_default()
            autocomplete.move_selection(1)

        elif event.key == "tab" or event.key == "enter":
            # Complete with selected item
            selected = autocomplete.get_selected()
            if selected:
                event.prevent_default()
                prompt.value = selected + " "
                prompt.cursor_position = len(prompt.value)
                autocomplete.hide()

        elif event.key == "escape":
            event.prevent_default()
            autocomplete.hide()

    async def _handle_command(
        self,
        cmd: str,
        view: ResponseView
    ) -> None:
        """Handle slash commands including agent invocations."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Basic commands
        if command == "/help":
            topic = args.lower().strip() if args else ""
            if topic in HELP_TOPICS:
                view.add_system_message(HELP_TOPICS[topic])
            else:
                # Fuzzy match topic
                matches = [k for k in HELP_TOPICS.keys() if k and topic in k]
                if matches:
                    view.add_system_message(HELP_TOPICS[matches[0]])
                else:
                    view.add_system_message(
                        f"❓ **Tópico não encontrado:** `{topic}`\n\n"
                        f"Tópicos disponíveis: `commands`, `agents`, `tools`, `keys`, `tips`\n\n"
                        f"Use `/help` para ver o menu principal."
                    )

        elif command == "/clear":
            view.clear_all()
            view.add_banner()

        elif command == "/quit" or command == "/exit":
            self.exit()

        elif command == "/run":
            if not args:
                view.add_error("Usage: /run <command>")
                return
            await self._execute_bash(args, view)

        elif command == "/read":
            if not args:
                view.add_error("Usage: /read <file>")
                return
            await self._read_file(args, view)

        elif command == "/agents":
            # List available agents
            agents_list = "\n".join([
                f"- **{name}**: {info.description}"
                for name, info in self.bridge.agents.AGENT_REGISTRY.items()
            ]) if hasattr(self.bridge.agents, 'AGENT_REGISTRY') else "13 agents available"
            view.add_system_message(f"## 🤖 Available Agents\n\n{agents_list}")

        elif command == "/status":
            # Show current status
            status_msg = (
                f"## 📊 Status\n\n"
                f"- **LLM:** {'✅ Gemini connected' if self.bridge.is_connected else '❌ Not connected'}\n"
                f"- **Governance:** {self.bridge.governance.get_status_emoji()}\n"
                f"- **Agents:** {len(self.bridge.agents.available_agents)} available\n"
                f"- **Tools:** {self.bridge.tools.get_tool_count()} loaded\n"
                f"- **Context:** {len(self.bridge.history.context)} messages\n"
            )
            view.add_system_message(status_msg)

        elif command == "/tools":
            # List all tools
            view.add_system_message(self.bridge.get_tool_list())

        elif command == "/palette":
            # Fuzzy search commands
            if args:
                results = self.bridge.palette.search(args)
                if results:
                    lines = ["## 🔍 Command Search Results\n"]
                    for r in results:
                        kb = f" `{r.get('keybinding', '')}`" if r.get('keybinding') else ""
                        lines.append(f"- **{r['command']}**{kb}: {r['description']}")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_system_message(f"No commands found for: `{args}`")
            else:
                # Show popular commands
                results = self.bridge.palette.search("", max_results=15)
                lines = ["## ⚡ Command Palette\n", "Type `/palette <query>` to search.\n"]
                for r in results:
                    kb = f" `{r.get('keybinding', '')}`" if r.get('keybinding') else ""
                    lines.append(f"- **{r['command']}**{kb}: {r['description']}")
                view.add_system_message("\n".join(lines))

        elif command == "/history":
            # Search command history
            if args:
                results = self.bridge.history.search_history(args)
            else:
                results = self.bridge.history.get_recent(15)

            if results:
                lines = ["## 📜 Command History\n"]
                for i, cmd in enumerate(results, 1):
                    lines.append(f"{i}. `{cmd}`")
                view.add_system_message("\n".join(lines))
            else:
                view.add_system_message("No history found.")

        elif command == "/context":
            # Show conversation context
            context = self.bridge.history.get_context()
            if context:
                lines = [f"## 💬 Conversation Context ({len(context)} messages)\n"]
                for i, msg in enumerate(context[-10:], 1):  # Show last 10
                    role = "👤 User" if msg["role"] == "user" else "🤖 Assistant"
                    content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                    lines.append(f"**{role}:** {content}\n")
                view.add_system_message("\n".join(lines))
            else:
                view.add_system_message("No conversation context yet. Start chatting!")

        elif command == "/context-clear":
            # Clear conversation context
            self.bridge.history.clear_context()
            view.add_success("Conversation context cleared.")

        # Agent commands - map to agents
        # =====================================================================
        # PLANNER v6.1 COMMANDS (multi, clarify, explore)
        # =====================================================================
        elif command == "/plan":
            # Check for v6.1 sub-commands
            if args:
                args_lower = args.lower().strip()
                if args_lower.startswith("multi ") or args_lower == "multi":
                    # Multi-Plan Generation
                    task = args[6:].strip() if args_lower.startswith("multi ") else ""
                    await self._invoke_planner_v61("multi", task or "Generate multiple plans", view)
                elif args_lower.startswith("clarify ") or args_lower == "clarify":
                    # Clarification Mode
                    task = args[8:].strip() if args_lower.startswith("clarify ") else ""
                    await self._invoke_planner_v61("clarify", task or "Clarify requirements", view)
                elif args_lower.startswith("explore ") or args_lower == "explore":
                    # Exploration Mode (read-only)
                    task = args[8:].strip() if args_lower.startswith("explore ") else ""
                    await self._invoke_planner_v61("explore", task or "Explore codebase", view)
                else:
                    # Regular planning
                    await self._invoke_agent("planner", args, view)
            else:
                await self._invoke_agent("planner", "Create a plan", view)

        elif command == "/execute":
            await self._invoke_agent("executor", args or "Execute task", view)

        elif command == "/architect":
            await self._invoke_agent("architect", args or "Analyze architecture", view)

        elif command == "/review":
            await self._invoke_agent("reviewer", args or "Review code", view)

        elif command == "/explore":
            await self._invoke_agent("explorer", args or "Explore codebase", view)

        elif command == "/refactor":
            await self._invoke_agent("refactorer", args or "Refactor code", view)

        elif command == "/test":
            await self._invoke_agent("testing", args or "Generate tests", view)

        elif command == "/security":
            await self._invoke_agent("security", args or "Security scan", view)

        elif command == "/docs":
            await self._invoke_agent("documentation", args or "Generate documentation", view)

        elif command == "/perf":
            await self._invoke_agent("performance", args or "Profile performance", view)

        elif command == "/devops":
            await self._invoke_agent("devops", args or "DevOps task", view)

        # Governance & Counsel Agents
        elif command == "/justica":
            await self._invoke_agent("justica", args or "Evaluate governance", view)

        elif command == "/sofia":
            await self._invoke_agent("sofia", args or "Provide counsel", view)

        # Data Agent
        elif command == "/data":
            await self._invoke_agent("data", args or "Database analysis", view)

        # =====================================================================
        # Claude Code Parity Commands
        # =====================================================================

        # /compact - Compact context with optional focus
        elif command == "/compact":
            focus = args if args else None
            try:
                result = self.bridge.compact_context(focus)
                view.add_system_message(
                    f"## 📦 Context Compacted\n\n"
                    f"- **Messages before:** {result.get('before', '?')}\n"
                    f"- **Messages after:** {result.get('after', '?')}\n"
                    f"- **Tokens saved:** ~{result.get('tokens_saved', '?')}\n"
                    f"{'- **Focus:** ' + focus if focus else ''}"
                )
            except Exception as e:
                view.add_error(f"Compact failed: {e}")

        # /cost - Show token usage statistics
        elif command == "/cost":
            try:
                stats = self.bridge.get_token_stats()
                view.add_system_message(
                    f"## 💰 Token Usage\n\n"
                    f"- **Session tokens:** {stats.get('session_tokens', 0):,}\n"
                    f"- **Total tokens:** {stats.get('total_tokens', 0):,}\n"
                    f"- **Input tokens:** {stats.get('input_tokens', 0):,}\n"
                    f"- **Output tokens:** {stats.get('output_tokens', 0):,}\n"
                    f"- **Estimated cost:** ${stats.get('cost', 0):.4f}\n"
                )
            except Exception as e:
                view.add_system_message(f"## 💰 Token Usage\n\nToken tracking not available: {e}")

        # /tokens - Alias for /cost
        elif command == "/tokens":
            try:
                stats = self.bridge.get_token_stats()
                view.add_system_message(
                    f"## 📊 Token Stats\n\n"
                    f"**Session:** {stats.get('session_tokens', 0):,} tokens\n"
                    f"**Context:** {stats.get('context_tokens', 0):,} / {stats.get('max_tokens', 128000):,}"
                )
            except Exception as e:
                view.add_system_message(f"## 📊 Token Stats\n\nNot available: {e}")

        # /todos - List current todos
        elif command == "/todos":
            try:
                todos = self.bridge.get_todos()
                if todos:
                    lines = ["## 📋 Todo List\n"]
                    for i, todo in enumerate(todos, 1):
                        status_icon = "✅" if todo.get('done') else "⬜"
                        lines.append(f"{status_icon} {i}. {todo.get('text', '?')}")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_system_message("## 📋 Todo List\n\nNo todos yet. Use `/todo <task>` to add one.")
            except Exception as e:
                view.add_system_message(f"## 📋 Todo List\n\nNot available: {e}")

        # /todo - Add a todo
        elif command == "/todo":
            if not args:
                view.add_error("Usage: /todo <task description>")
            else:
                try:
                    self.bridge.add_todo(args)
                    view.add_system_message(f"✅ Added todo: {args}")
                except Exception as e:
                    view.add_error(f"Failed to add todo: {e}")

        # /model - Select or show model
        elif command == "/model":
            if args:
                try:
                    self.bridge.set_model(args)
                    view.add_system_message(f"✅ Model changed to: **{args}**")
                except Exception as e:
                    view.add_error(f"Failed to change model: {e}")
            else:
                current = self.bridge.get_current_model()
                available = self.bridge.get_available_models()
                view.add_system_message(
                    f"## 🤖 Model Selection\n\n"
                    f"**Current:** {current}\n\n"
                    f"**Available:**\n" +
                    "\n".join(f"- `{m}`" for m in available)
                )

        # /init - Initialize project with JUANCS.md
        elif command == "/init":
            try:
                result = self.bridge.init_project()
                view.add_system_message(
                    f"## 🚀 Project Initialized\n\n"
                    f"Created **JUANCS.md** with project context.\n\n"
                    f"{result.get('summary', 'Project ready!')}"
                )
            except Exception as e:
                view.add_error(f"Init failed: {e}")

        # /resume - Resume previous session
        elif command == "/resume":
            session_id = args if args else None
            try:
                result = self.bridge.resume_session(session_id)
                view.add_system_message(
                    f"## 🔄 Session Resumed\n\n"
                    f"**Session:** {result.get('session_id', 'latest')}\n"
                    f"**Timestamp:** {result.get('timestamp', 'unknown')}\n"
                    f"**Messages:** {result.get('message_count', 0)}\n"
                    f"**Context:** Restored ✓"
                )
            except Exception as e:
                view.add_system_message(f"## 🔄 Resume Session\n\nNo previous session found: {e}\n\nUse `/sessions` to list available sessions.")

        # /save - Save current session
        elif command == "/save":
            session_id = args if args else None
            try:
                saved_id = self.bridge.save_session(session_id)
                view.add_system_message(
                    f"## 💾 Session Saved\n\n"
                    f"**Session ID:** `{saved_id}`\n"
                    f"**Location:** `~/.juancs/sessions/{saved_id}.json`\n\n"
                    f"Use `/resume {saved_id}` to restore later."
                )
            except Exception as e:
                view.add_error(f"Save failed: {e}")

        # /sessions - List available sessions
        elif command == "/sessions":
            try:
                sessions = self.bridge.list_sessions(10)
                if sessions:
                    lines = ["## 📚 Available Sessions\n"]
                    for s in sessions:
                        lines.append(f"- `{s['session_id']}` ({s['message_count']} msgs) - {s.get('timestamp', '?')[:16]}")
                    lines.append("\nUse `/resume <session_id>` to restore.")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_system_message("## 📚 Sessions\n\nNo saved sessions found.\n\nUse `/save` to save current session.")
            except Exception as e:
                view.add_error(f"List sessions failed: {e}")

        # /checkpoint - Create a checkpoint
        elif command == "/checkpoint":
            label = args if args else None
            try:
                cp = self.bridge.create_checkpoint(label)
                view.add_system_message(
                    f"## 📌 Checkpoint Created\n\n"
                    f"**Index:** {cp['index']}\n"
                    f"**Label:** {cp['label']}\n"
                    f"**Messages:** {cp['message_count']}\n\n"
                    f"Use `/rewind {cp['index']}` to return to this point."
                )
            except Exception as e:
                view.add_error(f"Checkpoint failed: {e}")

        # /rewind - Rewind to previous checkpoint
        elif command == "/rewind":
            try:
                checkpoints = self.bridge.get_checkpoints()
                if args and args.isdigit():
                    # Rewind to specific checkpoint
                    idx = int(args)
                    result = self.bridge.rewind_to(idx)
                    view.add_system_message(
                        f"## ⏪ Rewound\n\n"
                        f"**Checkpoint:** {result.get('rewound_to', idx)}\n"
                        f"**Messages:** {result.get('message_count', '?')}\n"
                        f"**Status:** Conversation state restored ✓"
                    )
                elif checkpoints:
                    # Show available checkpoints
                    lines = ["## ⏪ Available Checkpoints\n"]
                    for cp in checkpoints[-10:]:
                        lines.append(f"- `{cp['index']}`: {cp['label']} ({cp['message_count']} msgs)")
                    lines.append("\nUse `/rewind <index>` to restore.")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_system_message(
                        "## ⏪ Checkpoints\n\n"
                        "No checkpoints available.\n\n"
                        "Use `/checkpoint [label]` to create one."
                    )
            except Exception as e:
                view.add_system_message(f"## ⏪ Rewind\n\nError: {e}")

        # /export - Export conversation
        elif command == "/export":
            try:
                filepath = self.bridge.export_conversation(args or "conversation.md")
                view.add_system_message(f"✅ Conversation exported to: **{filepath}**")
            except Exception as e:
                view.add_error(f"Export failed: {e}")

        # /doctor - Check installation health
        elif command == "/doctor":
            try:
                health = self.bridge.check_health()
                lines = ["## 🏥 Health Check\n"]
                for check, status in health.items():
                    icon = "✅" if status.get('ok') else "❌"
                    lines.append(f"{icon} **{check}:** {status.get('message', 'OK')}")
                view.add_system_message("\n".join(lines))
            except Exception as e:
                view.add_system_message(f"## 🏥 Health Check\n\n❌ Check failed: {e}")

        # /permissions - Show/manage permissions
        elif command == "/permissions":
            try:
                perms = self.bridge.get_permissions()
                lines = ["## 🔐 Permissions\n"]
                for perm, value in perms.items():
                    icon = "✅" if value else "❌"
                    lines.append(f"{icon} **{perm}**")
                view.add_system_message("\n".join(lines))
            except Exception as e:
                view.add_system_message(f"## 🔐 Permissions\n\nNot available: {e}")

        # /sandbox - Enable/disable sandbox
        elif command == "/sandbox":
            try:
                if args == "off":
                    self.bridge.set_sandbox(False)
                    view.add_system_message("🔓 Sandbox **disabled**")
                else:
                    self.bridge.set_sandbox(True)
                    view.add_system_message("🔒 Sandbox **enabled** - commands run in isolation")
            except Exception as e:
                view.add_error(f"Sandbox toggle failed: {e}")

        # /hooks - Manage hooks (Claude Code parity)
        elif command == "/hooks":
            try:
                # Parse subcommand
                parts = args.split(maxsplit=2) if args else []
                subcommand = parts[0].lower() if parts else ""

                if subcommand == "enable" and len(parts) >= 2:
                    # /hooks enable <hook_name>
                    hook_name = parts[1]
                    if self.bridge.enable_hook(hook_name, True):
                        view.add_system_message(f"✅ Hook **{hook_name}** enabled")
                    else:
                        view.add_error(f"Unknown hook: {hook_name}")

                elif subcommand == "disable" and len(parts) >= 2:
                    # /hooks disable <hook_name>
                    hook_name = parts[1]
                    if self.bridge.enable_hook(hook_name, False):
                        view.add_system_message(f"⬜ Hook **{hook_name}** disabled")
                    else:
                        view.add_error(f"Unknown hook: {hook_name}")

                elif subcommand == "add" and len(parts) >= 3:
                    # /hooks add <hook_name> <command>
                    hook_name = parts[1]
                    command_str = parts[2]
                    if self.bridge.add_hook_command(hook_name, command_str):
                        view.add_system_message(f"✅ Added command to **{hook_name}**: `{command_str}`")
                    else:
                        view.add_error(f"Failed to add command to hook: {hook_name}")

                elif subcommand == "remove" and len(parts) >= 3:
                    # /hooks remove <hook_name> <command>
                    hook_name = parts[1]
                    command_str = parts[2]
                    if self.bridge.remove_hook_command(hook_name, command_str):
                        view.add_system_message(f"✅ Removed command from **{hook_name}**: `{command_str}`")
                    else:
                        view.add_error(f"Failed to remove command from hook: {hook_name}")

                elif subcommand == "set" and len(parts) >= 3:
                    # /hooks set <hook_name> <command1,command2,...>
                    hook_name = parts[1]
                    commands = [c.strip() for c in parts[2].split(",")]
                    if self.bridge.set_hook(hook_name, commands):
                        view.add_system_message(f"✅ Hook **{hook_name}** configured with {len(commands)} command(s)")
                    else:
                        view.add_error(f"Failed to set hook: {hook_name}")

                elif subcommand == "stats":
                    # /hooks stats - Show execution statistics
                    stats = self.bridge.get_hook_stats()
                    lines = ["## 📊 Hook Statistics\n"]
                    for key, value in stats.items():
                        lines.append(f"- **{key}:** {value}")
                    view.add_system_message("\n".join(lines))

                else:
                    # Default: Show all hooks with details
                    hooks = self.bridge.get_hooks()
                    if hooks:
                        lines = [
                            "## 🪝 Hooks Configuration\n",
                            "*Hooks run shell commands after file operations*\n",
                        ]
                        for hook_name, hook_info in hooks.items():
                            status = "✅" if hook_info.get('enabled') else "⬜"
                            lines.append(f"\n### {status} {hook_name}")
                            lines.append(f"*{hook_info.get('description', '')}*")
                            commands = hook_info.get('commands', [])
                            if commands:
                                lines.append("**Commands:**")
                                for cmd in commands:
                                    lines.append(f"  - `{cmd}`")
                            else:
                                lines.append("*No commands configured*")

                        lines.append("\n**Usage:**")
                        lines.append("- `/hooks enable <hook>` - Enable a hook")
                        lines.append("- `/hooks disable <hook>` - Disable a hook")
                        lines.append("- `/hooks add <hook> <cmd>` - Add command to hook")
                        lines.append("- `/hooks remove <hook> <cmd>` - Remove command")
                        lines.append("- `/hooks set <hook> <cmd1,cmd2>` - Set commands")
                        lines.append("- `/hooks stats` - Show execution stats")
                        lines.append("\n**Variables:** `{file}`, `{dir}`, `{file_name}`, `{file_extension}`")
                        view.add_system_message("\n".join(lines))
                    else:
                        view.add_system_message("## 🪝 Hooks\n\nNo hooks configured.")
            except Exception as e:
                view.add_system_message(f"## 🪝 Hooks\n\nNot available: {e}")

        # /mcp - MCP server management
        elif command == "/mcp":
            try:
                mcp_status = self.bridge.get_mcp_status()
                lines = ["## 🔌 MCP Servers\n"]
                if mcp_status.get('servers'):
                    for server in mcp_status['servers']:
                        status = "🟢" if server.get('connected') else "🔴"
                        lines.append(f"{status} **{server.get('name')}**")
                else:
                    lines.append("No MCP servers configured.")
                view.add_system_message("\n".join(lines))
            except Exception as e:
                view.add_system_message(f"## 🔌 MCP Servers\n\nNot available: {e}")

        # =====================================================================
        # AGENT ROUTER COMMANDS (Claude Code Parity - Subagent System)
        # =====================================================================

        # /router - Toggle auto-routing
        elif command == "/router":
            try:
                enabled = self.bridge.toggle_auto_routing()
                status_emoji = "🟢" if enabled else "🔴"
                view.add_system_message(
                    f"## 🎯 Agent Router\n\n"
                    f"{status_emoji} Auto-routing is now **{'ENABLED' if enabled else 'DISABLED'}**\n\n"
                    f"When enabled, messages are automatically routed to specialized agents based on intent."
                )
            except Exception as e:
                view.add_error(f"Router toggle failed: {e}")

        # /router-status - Show routing configuration
        elif command == "/router-status":
            try:
                status = self.bridge.get_router_status()
                lines = [
                    "## 🎯 Agent Router Status\n",
                    f"- **Enabled:** {'Yes' if status['enabled'] else 'No'}",
                    f"- **Min Confidence:** {int(status['min_confidence']*100)}%",
                    f"- **Agents:** {status['agents_configured']}",
                    f"- **Patterns:** {status['pattern_count']}",
                    "\n**Available Agents:**",
                ]
                for agent in status['available_agents']:
                    lines.append(f"  - `/{agent}`")
                view.add_system_message("\n".join(lines))
            except Exception as e:
                view.add_error(f"Router status failed: {e}")

        # /route [message] - Test routing without execution
        elif command == "/route":
            if not args:
                view.add_error("Usage: `/route <message>` - Test how a message would be routed")
            else:
                try:
                    analysis = self.bridge.test_routing(args)
                    lines = [
                        "## 🎯 Routing Analysis\n",
                        f"**Message:** `{analysis['message'][:50]}...`" if len(analysis['message']) > 50 else f"**Message:** `{analysis['message']}`",
                        f"**Should Route:** {'Yes' if analysis['should_route'] else 'No'}",
                    ]

                    if analysis['detected_intents']:
                        lines.append("\n**Detected Intents:**")
                        for intent in analysis['detected_intents'][:5]:
                            lines.append(f"  - `{intent['agent']}`: {intent['confidence']}")

                    if analysis['selected_route']:
                        route = analysis['selected_route']
                        lines.append(f"\n**Would Route To:** `{route['agent']}` ({route['confidence']})")
                    else:
                        lines.append("\n**Would Route To:** None (general LLM chat)")

                    if analysis['suggestion']:
                        lines.append(f"\n**Suggestion:**\n{analysis['suggestion']}")

                    view.add_system_message("\n".join(lines))
                except Exception as e:
                    view.add_error(f"Route test failed: {e}")

        # =====================================================================
        # BACKGROUND TASKS (Claude Code /bashes parity)
        # =====================================================================

        # /bashes - List background tasks
        elif command == "/bashes":
            try:
                from qwen_dev_cli.tools.claude_parity_tools import BackgroundTaskTool
                import asyncio

                tool = BackgroundTaskTool()
                result = asyncio.get_event_loop().run_until_complete(
                    tool._execute_validated(action="list")
                )

                if result.success:
                    tasks = result.data.get("tasks", [])
                    if tasks:
                        lines = ["## 🔄 Background Tasks\n"]
                        for t in tasks:
                            status_icon = "🟢" if t["status"] == "running" else "✅" if t["status"] == "completed" else "❌"
                            lines.append(f"{status_icon} `{t['id']}` - {t['command']} ({t['status']})")
                        view.add_system_message("\n".join(lines))
                    else:
                        view.add_system_message("## 🔄 Background Tasks\n\nNo background tasks running.")
                else:
                    view.add_error(f"Failed: {result.error}")
            except Exception as e:
                view.add_error(f"Background tasks error: {e}")

        # /bg <command> - Start background task
        elif command == "/bg":
            if not args:
                view.add_error("Usage: `/bg <command>` - Run command in background")
            else:
                try:
                    from qwen_dev_cli.tools.claude_parity_tools import BackgroundTaskTool
                    import asyncio

                    tool = BackgroundTaskTool()
                    result = asyncio.get_event_loop().run_until_complete(
                        tool._execute_validated(action="start", command=args)
                    )

                    if result.success:
                        task_id = result.data.get("task_id")
                        view.add_system_message(
                            f"## 🚀 Background Task Started\n\n"
                            f"**Task ID:** `{task_id}`\n"
                            f"**Command:** `{args}`\n\n"
                            f"Use `/bashes` to check status, `/kill {task_id}` to stop."
                        )
                    else:
                        view.add_error(f"Failed to start: {result.error}")
                except Exception as e:
                    view.add_error(f"Background task error: {e}")

        # /kill <task_id> - Kill background task
        elif command == "/kill":
            if not args:
                view.add_error("Usage: `/kill <task_id>` - Kill a background task")
            else:
                try:
                    from qwen_dev_cli.tools.claude_parity_tools import BackgroundTaskTool
                    import asyncio

                    tool = BackgroundTaskTool()
                    result = asyncio.get_event_loop().run_until_complete(
                        tool._execute_validated(action="kill", task_id=args)
                    )

                    if result.success:
                        view.add_system_message(f"✅ Task `{args}` killed.")
                    else:
                        view.add_error(f"Failed: {result.error}")
                except Exception as e:
                    view.add_error(f"Kill error: {e}")

        # =====================================================================
        # NOTEBOOK TOOLS (Claude Code parity)
        # =====================================================================

        # /notebook <path> - Read notebook file
        elif command == "/notebook":
            if not args:
                view.add_error("Usage: `/notebook <path.ipynb>` - Read Jupyter notebook")
            else:
                try:
                    from qwen_dev_cli.tools.claude_parity_tools import NotebookReadTool
                    import asyncio

                    tool = NotebookReadTool()
                    result = asyncio.get_event_loop().run_until_complete(
                        tool._execute_validated(file_path=args)
                    )

                    if result.success:
                        data = result.data
                        lines = [
                            f"## 📓 Notebook: {args}\n",
                            f"**Kernel:** {data.get('kernel', 'Unknown')}",
                            f"**Language:** {data.get('language', 'unknown')}",
                            f"**Cells:** {data.get('total_cells', 0)}\n",
                        ]

                        for cell in data.get("cells", [])[:10]:  # Limit to 10 cells
                            cell_type = cell.get("type", "unknown")
                            icon = "📝" if cell_type == "code" else "📄"
                            source = cell.get("source", "")[:200]
                            if len(cell.get("source", "")) > 200:
                                source += "..."

                            lines.append(f"\n### {icon} Cell {cell.get('index')} ({cell_type})")
                            lines.append(f"```\n{source}\n```")

                            if cell.get("outputs"):
                                lines.append(f"*Outputs: {len(cell['outputs'])} items*")

                        if data.get("total_cells", 0) > 10:
                            lines.append(f"\n*... and {data['total_cells'] - 10} more cells*")

                        view.add_system_message("\n".join(lines))
                    else:
                        view.add_error(f"Failed: {result.error}")
                except Exception as e:
                    view.add_error(f"Notebook error: {e}")

        # =====================================================================
        # TASK/SUBAGENT TOOLS (Claude Code parity)
        # =====================================================================

        # /task - Launch a subagent
        elif command == "/task":
            if not args:
                # Show help
                view.add_system_message(
                    "## 🤖 Task Tool - Launch Subagents\n\n"
                    "**Usage:** `/task <type> <prompt>`\n\n"
                    "**Agent Types:**\n"
                    "- `explore` - Fast codebase exploration\n"
                    "- `plan` - Task planning and breakdown\n"
                    "- `general-purpose` - Complex multi-step tasks\n"
                    "- `code-reviewer` - Review code quality\n"
                    "- `test-runner` - Execute tests\n"
                    "- `security` - Security analysis\n"
                    "- `documentation` - Generate docs\n"
                    "- `refactor` - Code refactoring\n\n"
                    "**Examples:**\n"
                    "- `/task explore Find all API endpoints`\n"
                    "- `/task plan Implement user authentication`\n"
                    "- `/task code-reviewer Review the auth module`"
                )
            else:
                try:
                    from qwen_dev_cli.tools.claude_parity_tools import TaskTool

                    # Parse args: first word is type, rest is prompt
                    parts = args.split(maxsplit=1)
                    subagent_type = parts[0] if parts else "general-purpose"
                    prompt = parts[1] if len(parts) > 1 else args

                    tool = TaskTool()
                    result = await tool._execute_validated(
                        prompt=prompt,
                        subagent_type=subagent_type,
                        description=f"Task: {prompt[:30]}"
                    )

                    if result.success:
                        data = result.data
                        view.add_system_message(
                            f"## 🤖 Subagent Launched\n\n"
                            f"**ID:** `{data['subagent_id']}`\n"
                            f"**Type:** {data['type']}\n"
                            f"**Description:** {data['description']}\n\n"
                            f"**Result:**\n"
                            f"```json\n{json.dumps(data['result'], indent=2)}\n```\n\n"
                            f"Use `/subagents` to see all running subagents."
                        )
                    else:
                        view.add_error(f"Task failed: {result.error}")
                except Exception as e:
                    view.add_error(f"Task error: {e}")

        # /subagents - List all subagents
        elif command == "/subagents":
            try:
                from qwen_dev_cli.tools.claude_parity_tools import TaskTool

                subagents = TaskTool.list_subagents()
                if subagents:
                    lines = ["## 🤖 Running Subagents\n"]
                    for s in subagents:
                        status_icon = "🟢" if s["status"] == "running" else "✅" if s["status"] == "completed" else "❌"
                        lines.append(
                            f"{status_icon} `{s['id']}` - **{s['type']}** ({s['status']})\n"
                            f"   {s['description']} | {s['prompts_count']} prompt(s)"
                        )
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_system_message(
                        "## 🤖 Subagents\n\n"
                        "No subagents running.\n\n"
                        "Use `/task <type> <prompt>` to launch one."
                    )
            except Exception as e:
                view.add_error(f"Subagents error: {e}")

        # /ask - Interactive question (Claude Code AskUserQuestion parity)
        elif command == "/ask":
            if not args:
                view.add_system_message(
                    "## ❓ Ask User Question\n\n"
                    "This command is used by the AI to ask clarifying questions.\n\n"
                    "The AI can use this tool to:\n"
                    "- Gather user preferences\n"
                    "- Clarify requirements\n"
                    "- Get decisions on implementation choices"
                )
            else:
                # Show pending questions
                try:
                    from qwen_dev_cli.tools.claude_parity_tools import AskUserQuestionTool
                    pending = AskUserQuestionTool.get_pending_questions()
                    if pending:
                        lines = ["## ❓ Pending Questions\n"]
                        for q in pending:
                            lines.append(f"**Question ID:** `{q['id']}`")
                            for question in q["questions"]:
                                lines.append(f"\n**{question['header']}:** {question['question']}")
                                for i, opt in enumerate(question["options"], 1):
                                    label = opt.get("label", opt) if isinstance(opt, dict) else opt
                                    lines.append(f"  {i}. {label}")
                        view.add_system_message("\n".join(lines))
                    else:
                        view.add_system_message("No pending questions.")
                except Exception as e:
                    view.add_error(f"Ask error: {e}")

        # =====================================================================
        # CUSTOM SLASH COMMANDS (Claude Code parity)
        # =====================================================================

        # /commands - List custom commands
        elif command == "/commands":
            try:
                commands = self.bridge.get_custom_commands()
                if commands:
                    lines = ["## 📜 Custom Commands\n"]
                    for name, cmd in commands.items():
                        scope = "🏠" if cmd["type"] == "project" else "🌍"
                        lines.append(f"{scope} **/{name}** - {cmd['description']}")
                    lines.append("\n**Usage:**")
                    lines.append("- `/commands refresh` - Reload commands")
                    lines.append("- `/command-create <name>` - Create new command")
                    lines.append("- `/command-delete <name>` - Delete command")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_system_message(
                        "## 📜 Custom Commands\n\n"
                        "No custom commands found.\n\n"
                        "**Create commands in:**\n"
                        "- `.juancs/commands/<name>.md` (project)\n"
                        "- `~/.juancs/commands/<name>.md` (global)\n\n"
                        "**Example:**\n"
                        "Create `.juancs/commands/review-pr.md`:\n"
                        "```markdown\n"
                        "# Review a pull request\n"
                        "Review PR $1 focusing on code quality and security.\n"
                        "```\n"
                        "Then use: `/review-pr 123`"
                    )
            except Exception as e:
                view.add_error(f"Commands error: {e}")

        # /commands refresh - Reload custom commands
        elif command == "/commands" and args == "refresh":
            try:
                commands = self.bridge.refresh_custom_commands()
                view.add_system_message(f"✅ Reloaded {len(commands)} custom commands")
            except Exception as e:
                view.add_error(f"Refresh error: {e}")

        # /command-create <name> <prompt> - Create a custom command
        elif command == "/command-create":
            if not args:
                view.add_system_message(
                    "## 📜 Create Custom Command\n\n"
                    "**Usage:** `/command-create <name> <prompt>`\n\n"
                    "**Variables:**\n"
                    "- `$ARGUMENTS` or `{args}` - All arguments\n"
                    "- `$1`, `$2`, etc. - Positional arguments\n\n"
                    "**Example:**\n"
                    "`/command-create fix-bugs Find and fix bugs in $ARGUMENTS`"
                )
            else:
                parts = args.split(maxsplit=1)
                name = parts[0]
                prompt = parts[1] if len(parts) > 1 else f"Execute {name} command"

                try:
                    cmd = self.bridge.create_custom_command(name, prompt)
                    view.add_system_message(
                        f"## ✅ Command Created\n\n"
                        f"**Name:** `/{name}`\n"
                        f"**Path:** `{cmd['path']}`\n\n"
                        f"Now you can use `/{name} <args>` to run this command."
                    )
                except Exception as e:
                    view.add_error(f"Create failed: {e}")

        # /command-delete <name> - Delete a custom command
        elif command == "/command-delete":
            if not args:
                view.add_error("Usage: `/command-delete <name>`")
            else:
                try:
                    if self.bridge.delete_custom_command(args):
                        view.add_system_message(f"✅ Command `/{args}` deleted")
                    else:
                        view.add_error(f"Command not found: {args}")
                except Exception as e:
                    view.add_error(f"Delete failed: {e}")

        # =====================================================================
        # PLAN MODE (Claude Code parity)
        # =====================================================================

        # /plan-mode - Enter plan mode
        elif command == "/plan-mode":
            try:
                result = self.bridge.enter_plan_mode(args)
                if result.get("success"):
                    view.add_system_message(
                        f"## 📋 Plan Mode Activated\n\n"
                        f"**Task:** {result.get('task', 'No task specified')}\n"
                        f"**Plan file:** `{result.get('plan_file')}`\n\n"
                        f"⚠️ **Restrictions:** {result.get('restrictions')}\n\n"
                        f"**Commands:**\n"
                        f"- `/plan-note <note>` - Add exploration note\n"
                        f"- `/plan-status` - Check plan status\n"
                        f"- `/plan-exit` - Exit without approval\n"
                        f"- `/plan-approve` - Approve and exit"
                    )
                else:
                    view.add_error(result.get("error", "Failed to enter plan mode"))
            except Exception as e:
                view.add_error(f"Plan mode failed: {e}")

        # /plan-status - Check plan mode status
        elif command == "/plan-status":
            try:
                state = self.bridge.get_plan_mode_state()
                if state.get("active"):
                    view.add_system_message(
                        f"## 📋 Plan Mode Status\n\n"
                        f"**Active:** ✅ Yes\n"
                        f"**Task:** {state.get('task', 'N/A')}\n"
                        f"**Plan file:** `{state.get('plan_file')}`\n"
                        f"**Started:** {state.get('started_at')}\n"
                        f"**Notes:** {len(state.get('exploration_log', []))} entries"
                    )
                else:
                    view.add_system_message(
                        "## 📋 Plan Mode Status\n\n"
                        "**Active:** ❌ No\n\n"
                        "Use `/plan-mode <task>` to enter plan mode."
                    )
            except Exception as e:
                view.add_error(f"Status check failed: {e}")

        # /plan-note - Add note to plan
        elif command == "/plan-note":
            if not args:
                view.add_error("Usage: `/plan-note <note>`")
            else:
                try:
                    if self.bridge.add_plan_note(args):
                        view.add_system_message(f"✅ Note added: {args[:50]}...")
                    else:
                        view.add_error("Not in plan mode. Use `/plan-mode` first.")
                except Exception as e:
                    view.add_error(f"Failed to add note: {e}")

        # /plan-exit - Exit plan mode without approval
        elif command == "/plan-exit":
            try:
                result = self.bridge.exit_plan_mode(approved=False)
                if result.get("success"):
                    view.add_system_message(
                        f"## 📋 Plan Mode Exited\n\n"
                        f"**Approved:** ❌ No\n"
                        f"**Plan file:** `{result.get('plan_file')}`\n"
                        f"**Notes collected:** {result.get('exploration_count', 0)}"
                    )
                else:
                    view.add_error(result.get("error", "Not in plan mode"))
            except Exception as e:
                view.add_error(f"Exit failed: {e}")

        # /plan-approve - Approve plan and exit
        elif command == "/plan-approve":
            try:
                result = self.bridge.exit_plan_mode(approved=True)
                if result.get("success"):
                    view.add_system_message(
                        f"## ✅ Plan Approved!\n\n"
                        f"**Plan file:** `{result.get('plan_file')}`\n"
                        f"**Notes collected:** {result.get('exploration_count', 0)}\n\n"
                        f"Write operations are now enabled. Ready to implement!"
                    )
                else:
                    view.add_error(result.get("error", "Not in plan mode"))
            except Exception as e:
                view.add_error(f"Approval failed: {e}")

        # =====================================================================
        # PR CREATION (Claude Code parity)
        # =====================================================================

        # /pr - Create pull request
        elif command == "/pr":
            if not args:
                view.add_system_message(
                    "## 🔀 Create Pull Request\n\n"
                    "**Usage:** `/pr <title>`\n\n"
                    "**Options:**\n"
                    "- `/pr <title>` - Create PR with title\n"
                    "- `/pr-draft <title>` - Create draft PR\n\n"
                    "**Requirements:**\n"
                    "- GitHub CLI (gh) installed\n"
                    "- Authenticated with `gh auth login`\n"
                    "- Changes committed and pushed"
                )
            else:
                try:
                    view.add_system_message("🔄 Creating pull request...")
                    result = await self.bridge.create_pull_request(title=args)
                    if result.get("success"):
                        view.add_system_message(
                            f"## ✅ Pull Request Created!\n\n"
                            f"**URL:** {result.get('url')}\n"
                            f"**Branch:** {result.get('branch')} → {result.get('base')}"
                        )
                    else:
                        view.add_error(f"PR creation failed: {result.get('error')}")
                except Exception as e:
                    view.add_error(f"PR error: {e}")

        # /pr-draft - Create draft PR
        elif command == "/pr-draft":
            if not args:
                view.add_error("Usage: `/pr-draft <title>`")
            else:
                try:
                    view.add_system_message("🔄 Creating draft pull request...")
                    result = await self.bridge.create_pull_request(title=args, draft=True)
                    if result.get("success"):
                        view.add_system_message(
                            f"## ✅ Draft PR Created!\n\n"
                            f"**URL:** {result.get('url')}\n"
                            f"**Branch:** {result.get('branch')} → {result.get('base')}\n"
                            f"**Status:** Draft"
                        )
                    else:
                        view.add_error(f"PR creation failed: {result.get('error')}")
                except Exception as e:
                    view.add_error(f"PR error: {e}")

        # =====================================================================
        # AUTH MANAGEMENT - /login, /logout, /auth (Claude Code Parity - WAVE 5)
        # =====================================================================

        # /login - Login to API provider
        elif command == "/login":
            if not args:
                # Show status and help
                status = self.bridge.get_auth_status()
                lines = ["## 🔐 Authentication Status\n"]
                for provider, info in status.get("providers", {}).items():
                    if info["logged_in"]:
                        sources = ", ".join(info["sources"])
                        lines.append(f"✅ **{provider}**: logged in ({sources})")
                    else:
                        lines.append(f"⬚ **{provider}**: not configured")
                lines.append("\n**Usage:**")
                lines.append("- `/login <provider> <api_key>` - Login globally")
                lines.append("- `/login <provider> <api_key> project` - Login for this project only")
                lines.append("\n**Providers:** gemini, openai, anthropic, nebius, groq")
                view.add_system_message("\n".join(lines))
            else:
                parts = args.split(maxsplit=2)
                provider = parts[0]
                api_key = parts[1] if len(parts) > 1 else None
                scope = parts[2] if len(parts) > 2 else "global"

                result = self.bridge.login(provider, api_key, scope)
                if result.get("success"):
                    view.add_system_message(
                        f"## ✅ Logged in to {provider}\n\n"
                        f"**Scope:** {result.get('scope', 'global')}\n"
                        f"**File:** `{result.get('file', 'environment')}`"
                    )
                else:
                    view.add_error(result.get("error", "Login failed"))

        # /logout - Logout from provider
        elif command == "/logout":
            if not args:
                # Logout all
                result = self.bridge.logout()
            else:
                result = self.bridge.logout(provider=args)

            if result.get("success"):
                removed = result.get("removed", [])
                if removed:
                    view.add_system_message(
                        f"## 🔓 Logged Out\n\n"
                        f"**Removed:** {', '.join(removed)}"
                    )
                else:
                    view.add_system_message("No credentials found to remove.")
            else:
                view.add_error(result.get("error", "Logout failed"))

        # /auth - Show auth status
        elif command == "/auth":
            status = self.bridge.get_auth_status()
            lines = ["## 🔐 Authentication Status\n"]

            for provider, info in status.get("providers", {}).items():
                if info["logged_in"]:
                    sources = ", ".join(info["sources"])
                    lines.append(f"✅ **{provider}**: `{info['env_var']}` ({sources})")
                else:
                    lines.append(f"⬚ **{provider}**: not configured")

            lines.append(f"\n**Global config:** `{status.get('global_file')}`")
            lines.append(f"**Project config:** `{status.get('project_file')}`")
            view.add_system_message("\n".join(lines))

        # =====================================================================
        # MEMORY - /memory, /remember (Claude Code Parity - WAVE 5)
        # =====================================================================

        # /memory - View/manage memory
        elif command == "/memory":
            if not args:
                # Show memory content
                project_mem = self.bridge.read_memory(scope="project")
                global_mem = self.bridge.read_memory(scope="global")

                lines = ["## 🧠 Memory\n"]

                if project_mem.get("exists"):
                    lines.append(f"### Project Memory (`{project_mem.get('file')}`)")
                    lines.append(f"*{project_mem.get('lines', 0)} lines, {project_mem.get('size', 0)} bytes*\n")
                    content = project_mem.get("content", "")[:500]
                    if content:
                        lines.append(f"```\n{content}\n```")
                else:
                    lines.append("*No project memory (MEMORY.md not found)*\n")

                if global_mem.get("exists"):
                    lines.append(f"\n### Global Memory (`{global_mem.get('file')}`)")
                    lines.append(f"*{global_mem.get('lines', 0)} lines*")
                else:
                    lines.append("\n*No global memory*")

                lines.append("\n**Commands:**")
                lines.append("- `/remember <note>` - Add note to memory")
                lines.append("- `/memory edit` - Open memory file in editor")
                view.add_system_message("\n".join(lines))

            elif args == "edit":
                import subprocess
                import shutil

                mem_file = self.bridge._get_memory_file(scope="project")
                editor = os.environ.get("EDITOR", "nano")

                if not mem_file.exists():
                    # Create with template
                    self.bridge.write_memory(
                        "# Project Memory\n\nAdd persistent notes and context here.\n",
                        scope="project"
                    )

                try:
                    subprocess.run([editor, str(mem_file)])
                    view.add_system_message(f"Memory file edited: `{mem_file}`")
                except Exception as e:
                    view.add_error(f"Could not open editor: {e}")

            elif args == "clear":
                import os
                mem_file = self.bridge._get_memory_file(scope="project")
                if mem_file.exists():
                    mem_file.unlink()
                    view.add_system_message("Project memory cleared.")
                else:
                    view.add_system_message("No memory file to clear.")

        # /remember - Add note to memory
        elif command == "/remember":
            if not args:
                view.add_error("Usage: `/remember <note>` or `/remember preferences: <note>`")
            else:
                # Parse category from note
                category = "general"
                note = args

                if ":" in args and args.split(":")[0].strip() in ["preferences", "patterns", "todos", "context"]:
                    category, note = args.split(":", 1)
                    category = category.strip()
                    note = note.strip()

                result = self.bridge.add_memory_note(note, category=category)
                if result.get("success"):
                    view.add_system_message(
                        f"📝 Note added to **{category}** in `{result.get('file')}`"
                    )
                else:
                    view.add_error(result.get("error", "Failed to add note"))

        # =====================================================================
        # IMAGE/PDF READING (Claude Code Parity - WAVE 5)
        # =====================================================================

        # /image - Read image
        elif command == "/image":
            if not args:
                view.add_system_message(
                    "## 🖼️ Image Reading\n\n"
                    "**Usage:** `/image <path>`\n\n"
                    "Reads an image and makes it available for AI analysis.\n"
                    "Supports: PNG, JPEG, GIF, WebP\n\n"
                    "*Note: Install Pillow for automatic resizing: `pip install Pillow`*"
                )
            else:
                result = self.bridge.read_image(args)
                if result.get("success"):
                    size_info = ""
                    if result.get("resized"):
                        size_info = f" (resized from {result.get('original_size')} to {result.get('final_size')})"
                    view.add_system_message(
                        f"## 🖼️ Image Loaded\n\n"
                        f"**File:** `{result.get('file')}`\n"
                        f"**Type:** {result.get('mime_type')}{size_info}\n\n"
                        f"Image data is ready for AI analysis."
                    )
                    # Store for next AI request
                    self._pending_image = result
                else:
                    view.add_error(result.get("error", "Failed to read image"))

        # /pdf - Read PDF
        elif command == "/pdf":
            if not args:
                view.add_system_message(
                    "## 📄 PDF Reading\n\n"
                    "**Usage:** `/pdf <path>`\n\n"
                    "Extracts text from PDF for AI analysis.\n\n"
                    "*Note: Install PyMuPDF or pypdf: `pip install PyMuPDF`*"
                )
            else:
                result = self.bridge.read_pdf(args)
                if result.get("success"):
                    pages = result.get("pages", [])
                    preview = pages[0]["text"][:300] if pages else "No text extracted"
                    view.add_system_message(
                        f"## 📄 PDF Loaded\n\n"
                        f"**File:** `{result.get('file')}`\n"
                        f"**Pages:** {result.get('total_pages')}\n"
                        f"**Extractor:** {result.get('extractor')}\n\n"
                        f"**Preview:**\n```\n{preview}...\n```"
                    )
                    # Store for next AI request
                    self._pending_pdf = result
                else:
                    view.add_error(result.get("error", "Failed to read PDF"))

        # =====================================================================
        # WAVE 6: AUDIT LOGGING
        # =====================================================================

        elif command == "/audit":
            if not args:
                result = self.bridge.get_audit_log(limit=20)
                if result.get("success"):
                    entries = result.get("entries", [])
                    lines = [f"## 📋 Audit Log ({result.get('total', 0)} total)\n"]
                    if entries:
                        for e in entries[:15]:
                            ts = e.get("timestamp", "")[:19]
                            action = e.get("action", "?")
                            result_status = e.get("result", "")
                            lines.append(f"- `{ts}` **{action}** [{result_status}]")
                    else:
                        lines.append("*No audit entries yet*")
                    lines.append(f"\n**Log file:** `{result.get('file')}`")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_error(result.get("error"))
            elif args == "clear":
                log_file = self.bridge._get_audit_log_file()
                if log_file.exists():
                    log_file.unlink()
                    view.add_system_message("Audit log cleared.")
                else:
                    view.add_system_message("No audit log to clear.")
            elif args in ("on", "enable"):
                self.bridge.set_audit_enabled(True)
                view.add_system_message("✅ Audit logging enabled")
            elif args in ("off", "disable"):
                self.bridge.set_audit_enabled(False)
                view.add_system_message("⏸️ Audit logging disabled")

        # =====================================================================
        # WAVE 6: DIFF PREVIEW
        # =====================================================================

        elif command == "/diff":
            view.add_system_message(
                "## 📝 Diff Preview\n\n"
                "Use diff preview programmatically via `bridge.preview_diff(file, old, new)`\n"
                "This shows unified diff before applying edits."
            )

        # =====================================================================
        # WAVE 6: BACKUP MANAGEMENT
        # =====================================================================

        elif command == "/backup":
            if not args:
                result = self.bridge.list_backups(limit=20)
                if result.get("success"):
                    backups = result.get("backups", [])
                    lines = [f"## 💾 Backups ({result.get('total', 0)} total)\n"]
                    if backups:
                        for b in backups[:15]:
                            lines.append(f"- `{b.get('timestamp')}` {b.get('original_name')} ({b.get('reason')})")
                    else:
                        lines.append("*No backups yet*")
                    lines.append(f"\n**Backup dir:** `{result.get('backup_dir')}`")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_error(result.get("error"))
            else:
                # Create backup
                result = self.bridge.create_backup(args, reason="manual")
                if result.get("success"):
                    view.add_system_message(
                        f"## 💾 Backup Created\n\n"
                        f"**Original:** `{result.get('original')}`\n"
                        f"**Backup:** `{result.get('backup')}`"
                    )
                else:
                    view.add_error(result.get("error"))

        elif command == "/restore":
            if not args:
                view.add_error("Usage: `/restore <backup_path>` or `/restore <backup_path> <target_path>`")
            else:
                parts = args.split(maxsplit=1)
                backup_path = parts[0]
                target_path = parts[1] if len(parts) > 1 else None
                result = self.bridge.restore_backup(backup_path, target_path)
                if result.get("success"):
                    view.add_system_message(
                        f"## ✅ Restored\n\n"
                        f"**From:** `{result.get('restored_from')}`\n"
                        f"**To:** `{result.get('restored_to')}`"
                    )
                else:
                    view.add_error(result.get("error"))

        # =====================================================================
        # WAVE 6: UNDO/REDO
        # =====================================================================

        elif command == "/undo":
            result = self.bridge.undo()
            if result.get("success"):
                view.add_system_message(
                    f"## ↩️ Undone\n\n"
                    f"**Operation:** {result.get('undone')}\n"
                    f"**File:** `{result.get('file')}`\n"
                    f"**Remaining undos:** {result.get('remaining_undos')}"
                )
            else:
                view.add_error(result.get("error"))

        elif command == "/redo":
            result = self.bridge.redo()
            if result.get("success"):
                view.add_system_message(
                    f"## ↪️ Redone\n\n"
                    f"**Operation:** {result.get('redone')}\n"
                    f"**File:** `{result.get('file')}`\n"
                    f"**Remaining redos:** {result.get('remaining_redos')}"
                )
            else:
                view.add_error(result.get("error"))

        elif command == "/undo-stack":
            result = self.bridge.get_undo_stack()
            lines = [f"## ↩️ Undo Stack\n"]
            lines.append(f"**Undo available:** {result.get('undo_count', 0)}")
            lines.append(f"**Redo available:** {result.get('redo_count', 0)}\n")

            if result.get("undo_operations"):
                lines.append("**Recent operations (undoable):**")
                for op in result.get("undo_operations", [])[:5]:
                    lines.append(f"- {op.get('operation')} on `{op.get('file')}`")
            view.add_system_message("\n".join(lines))

        # =====================================================================
        # WAVE 6: SECRETS SCANNER
        # =====================================================================

        elif command == "/secrets":
            if not args:
                args = "."

            view.add_system_message(f"🔍 Scanning `{args}` for secrets...")
            result = self.bridge.scan_secrets(args)

            if result.get("success"):
                findings = result.get("findings", [])
                severity = result.get("severity", "CLEAN")

                if severity == "CLEAN":
                    view.add_system_message(
                        f"## ✅ No Secrets Found\n\n"
                        f"**Files scanned:** {result.get('files_scanned')}\n"
                        f"**Status:** CLEAN"
                    )
                else:
                    lines = [f"## 🚨 Secrets Found!\n"]
                    lines.append(f"**Findings:** {result.get('findings_count')}")
                    lines.append(f"**Files scanned:** {result.get('files_scanned')}\n")

                    for f in findings[:10]:
                        lines.append(f"- **{f.get('type')}** in `{f.get('file')}` line {f.get('line')}")

                    if len(findings) > 10:
                        lines.append(f"\n*...and {len(findings) - 10} more*")

                    view.add_system_message("\n".join(lines))
            else:
                view.add_error(result.get("error"))

        elif command == "/secrets-staged":
            view.add_system_message("🔍 Scanning staged files for secrets...")
            result = self.bridge.scan_staged_secrets()

            if result.get("success"):
                if result.get("can_commit", True):
                    view.add_system_message(
                        f"## ✅ Safe to Commit\n\n"
                        f"**Staged files:** {result.get('files_scanned')}\n"
                        f"**Secrets found:** 0"
                    )
                else:
                    findings = result.get("findings", [])
                    lines = [f"## 🚨 DO NOT COMMIT!\n"]
                    lines.append(f"**Secrets found:** {result.get('findings_count')}\n")
                    for f in findings[:5]:
                        lines.append(f"- **{f.get('type')}** in `{f.get('file')}`")
                    view.add_system_message("\n".join(lines))
            else:
                view.add_error(result.get("error"))

        else:
            # Check if it's a custom command
            custom_cmd_name = command.lstrip("/")
            custom_prompt = self.bridge.execute_custom_command(custom_cmd_name, args)

            if custom_prompt:
                # Execute the custom command as a chat message
                view.add_system_message(f"📜 *Running custom command: `/{custom_cmd_name}`*")
                await self._handle_chat(custom_prompt, view)
            else:
                view.add_error(f"Unknown command: {command}")
                view.add_system_message("Type `/help` for available commands.")

    async def _handle_chat(
        self,
        message: str,
        view: ResponseView
    ) -> None:
        """
        Handle natural language chat via Gemini streaming.

        Uses the bridge to connect to Gemini API with 60fps streaming.
        """
        self.is_processing = True
        view.start_thinking()

        # Update status
        status = self.query_one(StatusBar)
        status.mode = "THINKING"

        try:
            # Stream from Gemini via bridge
            async for chunk in self.bridge.chat(message):
                view.append_chunk(chunk)
                await asyncio.sleep(0)  # Yield for UI

            view.add_success("✓ Response complete")

            # Update governance status
            status.governance_status = self.bridge.governance.get_status_emoji()

        except Exception as e:
            view.add_error(f"Chat error: {e}")
            status.errors += 1
        finally:
            self.is_processing = False
            status.mode = "READY"
            view.end_thinking()

    async def _invoke_agent(
        self,
        agent_name: str,
        task: str,
        view: ResponseView
    ) -> None:
        """
        Invoke a specific agent with streaming response.

        Routes to the appropriate agent via bridge.
        """
        self.is_processing = True
        view.start_thinking()

        # Update status
        status = self.query_one(StatusBar)
        status.mode = f"🤖 {agent_name.upper()}"

        try:
            # Stream from agent via bridge
            async for chunk in self.bridge.invoke_agent(agent_name, task):
                view.append_chunk(chunk)
                await asyncio.sleep(0)  # Yield for UI

            view.add_success(f"✓ {agent_name.title()}Agent complete")

            # Update governance status
            status.governance_status = self.bridge.governance.get_status_emoji()

        except Exception as e:
            view.add_error(f"Agent error: {e}")
            status.errors += 1
        finally:
            self.is_processing = False
            status.mode = "READY"
            view.end_thinking()

    async def _invoke_planner_v61(
        self,
        mode: str,
        task: str,
        view: ResponseView
    ) -> None:
        """
        Invoke Planner v6.1 with specific mode.

        Modes:
            - multi: Generate 3 alternative plans with risk/reward
            - clarify: Ask clarifying questions before planning
            - explore: Read-only analysis mode
        """
        self.is_processing = True
        view.start_thinking()

        status = self.query_one(StatusBar)
        mode_labels = {
            "multi": "MULTI-PLAN",
            "clarify": "CLARIFY",
            "explore": "EXPLORE"
        }
        status.mode = f"🎯 PLANNER:{mode_labels.get(mode, mode.upper())}"

        try:
            if mode == "multi":
                async for chunk in self.bridge.invoke_planner_multi(task):
                    view.append_chunk(chunk)
                    await asyncio.sleep(0)
            elif mode == "clarify":
                async for chunk in self.bridge.invoke_planner_clarify(task):
                    view.append_chunk(chunk)
                    await asyncio.sleep(0)
            elif mode == "explore":
                async for chunk in self.bridge.invoke_planner_explore(task):
                    view.append_chunk(chunk)
                    await asyncio.sleep(0)
            else:
                view.add_error(f"Unknown planner mode: {mode}")
                return

            view.add_success(f"✓ Planner v6.1 ({mode}) complete")
            status.governance_status = self.bridge.governance.get_status_emoji()

        except Exception as e:
            view.add_error(f"Planner v6.1 error: {e}")
            status.errors += 1
        finally:
            self.is_processing = False
            status.mode = "READY"
            view.end_thinking()

    async def _execute_bash(
        self,
        command: str,
        view: ResponseView
    ) -> None:
        """
        Execute bash command SECURELY via whitelist.

        Uses SafeCommandExecutor to prevent shell injection.
        Only whitelisted commands are allowed.

        Security: OWASP compliant - no shell=True, no user input in shell
        """
        from qwen_cli.core.safe_executor import get_safe_executor

        executor = get_safe_executor()

        # Check if command is allowed BEFORE execution
        is_allowed, reason = executor.is_command_allowed(command)

        if not is_allowed:
            view.add_error(f"🚫 Command blocked: {reason}")
            view.add_action("Allowed commands:")

            # Show allowed commands by category
            allowed_by_cat = executor.get_allowed_commands_by_category()
            for category, commands in allowed_by_cat.items():
                view.add_action(f"  [{category}]")
                for cmd in commands[:3]:  # Show first 3 per category
                    view.add_action(f"    • {cmd}")
            return

        view.add_action(f"🔒 Executing (whitelisted): {command}")

        # Execute securely
        result = await executor.execute(command)

        if result.success:
            if result.stdout:
                view.add_code_block(result.stdout, language="bash", title=command)
            view.add_success(f"✓ Command completed (exit code: {result.exit_code})")
        else:
            error_msg = result.error_message or result.stderr or "Unknown error"
            view.add_error(f"Command failed: {error_msg}")
            if result.stderr:
                view.add_code_block(result.stderr, language="text", title="stderr")

    async def _read_file(
        self,
        path_str: str,
        view: ResponseView
    ) -> None:
        """Read and display file with syntax highlighting."""
        path = Path(path_str).expanduser()

        view.add_action(f"Reading: {path}")

        if not path.exists():
            view.add_error(f"File not found: {path}")
            return

        if not path.is_file():
            view.add_error(f"Not a file: {path}")
            return

        try:
            content = path.read_text()
            language = self._detect_language(path.suffix)

            view.add_code_block(
                content,
                language=language,
                title=str(path.name)
            )
            view.add_success(f"Read {len(content):,} characters")

        except Exception as e:
            view.add_error(f"Read error: {e}")

    def _detect_language(self, suffix: str) -> str:
        """Detect language from file extension."""
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".toml": "toml",
            ".ini": "ini",
            ".xml": "xml",
        }
        return lang_map.get(suffix.lower(), "text")

    # Actions
    def action_quit(self) -> None:
        """Exit the application."""
        self.exit()

    def action_clear(self) -> None:
        """Clear the response view."""
        response = self.query_one("#response", ResponseView)
        response.clear_all()
        response.add_banner()

    def action_show_help(self) -> None:
        """Show help."""
        response = self.query_one("#response", ResponseView)
        response.add_system_message(HELP_TEXT)

    def action_cancel(self) -> None:
        """Cancel current operation."""
        if self.is_processing:
            self.is_processing = False
            response = self.query_one("#response", ResponseView)
            response.end_thinking()
            response.add_error("Operation cancelled")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main() -> None:
    """Run the QWEN CLI application."""
    app = QwenApp()
    # mouse=False allows terminal native mouse for copy/paste/select
    app.run(mouse=False)


if __name__ == "__main__":
    main()
