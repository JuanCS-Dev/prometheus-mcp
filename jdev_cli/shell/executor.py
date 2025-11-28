"""
Shell Executor - Processa comandos e executa ferramentas.
Versão LIMPA sem code smells.
"""
import json
import re
from typing import Dict, Any
from rich.console import Console

from jdev_cli.plugins.tools_plugin import ToolRegistry


class ShellExecutor:
    """
    Executor limpo que:
    1. Recebe input do usuário
    2. Chama LLM com ferramentas
    3. Parse resposta (JSON ou texto)
    4. Executa ferramentas se necessário
    """

    def __init__(self, llm, console: Console):
        self.llm = llm
        self.console = console
        self.registry = ToolRegistry()
        self.history = []

        # System prompt: Instruções claras
        self.system_prompt = """You are a helpful AI assistant with access to tools.

Available tools:
{tools}

When you need to use a tool, respond with JSON:
{{"tool": "tool_name", "args": {{"param": "value"}}}}

For multiple tools, use array:
[{{"tool": "write_file", "args": {{"path": "/tmp/test.txt", "content": "hello"}}}}, ...]

For conversation, respond normally in text.
"""

    def _build_system_prompt(self) -> str:
        """Constrói system prompt com lista de ferramentas."""
        tools_list = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.registry.tools.items()
        ])
        return self.system_prompt.format(tools=tools_list)

    async def execute(self, user_input: str):
        """
        Loop principal de execução:
        1. Atualiza Histórico
        2. Stream do LLM
        3. Parse de JSON
        4. Execução de Ferramenta
        """
        self.history.append({"role": "user", "content": user_input})

        # Mantém janela de contexto deslizante para eficiência
        messages = self.history[-10:]

        full_response = ""
        is_collecting_json = False

        self.console.print("[bold cyan]Qwen:[/bold cyan] ", end="")

        # --- STREAMING ---
        # Passamos o system prompt a cada turno para garantir obediência
        try:
            async for chunk in self.llm.stream_chat(messages, system_prompt=self._build_system_prompt()):
                full_response += chunk
        except Exception as e:
            self.console.print(f"[red]LLM Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            return

            # Lógica de UI: Ocultar o JSON bruto enquanto ele é gerado
            if "{" in chunk or "[" in chunk:
                is_collecting_json = True

            if not is_collecting_json:
                self.console.print(chunk, end="")

        self.console.print()  # Newline após streaming

        # --- PARSE DE TOOL CALLS ---
        tool_calls = self._extract_tool_calls(full_response)

        if tool_calls:
            # Executa ferramentas
            await self._execute_tools(tool_calls)

        # Adiciona resposta ao histórico
        self.history.append({"role": "assistant", "content": full_response})

    def _extract_tool_calls(self, text: str) -> list[Dict[str, Any]]:
        """
        Extrai tool calls do formato JSON da resposta.
        Suporta:
        - Single: {"tool": "...", "args": {...}}
        - Multiple: [{"tool": "...", "args": {...}}, ...]
        """
        # Tenta encontrar JSON no texto
        json_pattern = r'(\{[^{}]*"tool"[^{}]*\}|\[[^\]]*"tool"[^\]]*\])'
        matches = re.findall(json_pattern, text, re.DOTALL)

        if not matches:
            return []

        # Parse o JSON encontrado
        try:
            json_str = matches[0]
            parsed = json.loads(json_str)

            # Normaliza para lista
            if isinstance(parsed, dict):
                return [parsed]
            elif isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            self.console.print("[yellow]Warning: Failed to parse tool JSON[/yellow]")
            return []

        return []

    async def _execute_tools(self, tool_calls: list[Dict[str, Any]]):
        """Executa lista de ferramentas sequencialmente."""
        for call in tool_calls:
            tool_name = call.get("tool", "")
            args = call.get("args", {})

            self.console.print(f"\n[dim]→ Executing {tool_name}...[/dim]")

            tool = self.registry.get(tool_name)
            if not tool:
                self.console.print(f"[red]✗ Unknown tool: {tool_name}[/red]")
                continue

            # Executa a ferramenta
            try:
                result = await tool.execute(**args)

                if result.success:
                    self.console.print(f"[green]✓ {tool_name} completed[/green]")
                    if result.data:
                        self.console.print(f"[dim]{result.data}[/dim]")
                else:
                    self.console.print(f"[red]✗ {tool_name} failed: {result.error}[/red]")

            except Exception as e:
                self.console.print(f"[red]✗ Error executing {tool_name}: {e}[/red]")
