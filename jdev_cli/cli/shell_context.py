"""
Shell Context Manager para MAX-CODE REPL

Mantém contexto entre comandos para permitir referências como:
- "that file"
- "the config"
- "it"
- "there"

Exemplo de uso:
> Read config.json
> Change line 5 to timeout=30     (sabe qual arquivo é)
> Write it back                   (sabe qual arquivo)

Soli Deo Gloria 🙏
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileContext:
    """Contexto de um arquivo manipulado"""
    path: str
    content: Optional[str] = None
    last_operation: str = "read"  # read, write, edit
    line_number: Optional[int] = None


@dataclass
class CommandContext:
    """Contexto de um comando executado"""
    command: str
    tool: str
    result: Dict
    timestamp: str


class ShellContext:
    """
    Mantém contexto da sessão shell para permitir comandos contextuais.

    Features:
    - Remember last file read/written
    - Resolve references ("that file", "it", "the config")
    - Track command history
    - Maintain conversation memory
    """

    def __init__(self):
        self.last_file: Optional[FileContext] = None
        self.file_history: List[FileContext] = []
        self.command_history: List[CommandContext] = []
        self.variables: Dict[str, str] = {}

    def remember_file(self, path: str, content: Optional[str] = None, operation: str = "read"):
        """Remember file that was just accessed"""
        file_ctx = FileContext(
            path=path,
            content=content,
            last_operation=operation
        )
        self.last_file = file_ctx
        self.file_history.append(file_ctx)

    def remember_command(self, command: str, tool: str, result: Dict):
        """Remember command that was executed"""
        import datetime
        cmd_ctx = CommandContext(
            command=command,
            tool=tool,
            result=result,
            timestamp=datetime.datetime.now().isoformat()
        )
        self.command_history.append(cmd_ctx)

    def resolve_reference(self, text: str) -> str:
        """
        Resolve pronoun references to actual file paths.

        Examples:
        - "edit that file" → "edit config.json"
        - "write it back" → "write config.json"
        - "show the config" → "show config.json"
        """
        if not self.last_file:
            return text

        import re

        # Common references (ordered by specificity - longer first)
        references = [
            "that file",
            "the file",
            "that",
            "there",
            "it",
        ]

        result = text
        for ref in references:
            # Use word boundaries to avoid replacing parts of words
            # Example: "Edit" won't match "it", but "edit it" will
            pattern = re.compile(r'\b' + re.escape(ref) + r'\b', re.IGNORECASE)
            result = pattern.sub(self.last_file.path, result)

        return result

    def get_last_file_content(self) -> Optional[str]:
        """Get content of last file accessed"""
        if self.last_file:
            return self.last_file.content
        return None

    def get_working_directory(self) -> str:
        """Get current working directory from context"""
        if self.last_file:
            return str(Path(self.last_file.path).parent)
        return "."

    def set_variable(self, name: str, value: str):
        """Set a context variable (like $file, $dir, etc)"""
        self.variables[name] = value

    def get_variable(self, name: str) -> Optional[str]:
        """Get a context variable"""
        return self.variables.get(name)

    def clear(self):
        """Clear all context (reset session)"""
        self.last_file = None
        self.file_history.clear()
        self.command_history.clear()
        self.variables.clear()

    def get_summary(self) -> str:
        """Get a summary of current context for display"""
        lines = []

        if self.last_file:
            lines.append(f"📄 Last file: {self.last_file.path} ({self.last_file.last_operation})")

        if self.command_history:
            lines.append(f"📜 Commands: {len(self.command_history)} executed")

        if self.variables:
            lines.append(f"🔤 Variables: {', '.join(self.variables.keys())}")

        return "\n".join(lines) if lines else "No context"
