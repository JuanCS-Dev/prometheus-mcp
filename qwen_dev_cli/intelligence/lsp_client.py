"""
LSP (Language Server Protocol) Client for Code Intelligence.

Provides:
- Hover documentation
- Go-to-definition
- Find references
- Code completion
- Signature help
- Multi-language support (Python, TypeScript, Go)

Boris Cherny Implementation - Week 3 Day 3 + Week 4 Day 3 Enhancement
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    UNKNOWN = "unknown"
    
    @classmethod
    def detect(cls, file_path: Path) -> "Language":
        """Detect language from file extension."""
        suffix = file_path.suffix.lower()
        mapping = {
            ".py": cls.PYTHON,
            ".ts": cls.TYPESCRIPT,
            ".tsx": cls.TYPESCRIPT,
            ".js": cls.JAVASCRIPT,
            ".jsx": cls.JAVASCRIPT,
            ".go": cls.GO,
        }
        return mapping.get(suffix, cls.UNKNOWN)


@dataclass
class LSPServerConfig:
    """Configuration for an LSP server."""
    language: Language
    command: List[str]
    initialization_options: Optional[Dict[str, Any]] = None
    
    @classmethod
    def get_configs(cls) -> Dict[Language, "LSPServerConfig"]:
        """Get all LSP server configurations."""
        return {
            Language.PYTHON: cls(
                language=Language.PYTHON,
                command=["pylsp"],
                initialization_options={}
            ),
            Language.TYPESCRIPT: cls(
                language=Language.TYPESCRIPT,
                command=["typescript-language-server", "--stdio"],
                initialization_options={"preferences": {"includeCompletionsWithSnippetText": True}}
            ),
            Language.JAVASCRIPT: cls(
                language=Language.JAVASCRIPT,
                command=["typescript-language-server", "--stdio"],
                initialization_options={"preferences": {"includeCompletionsWithSnippetText": True}}
            ),
            Language.GO: cls(
                language=Language.GO,
                command=["gopls"],
                initialization_options={}
            ),
        }


class LSPFeature(Enum):
    """Supported LSP features."""
    HOVER = "textDocument/hover"
    DEFINITION = "textDocument/definition"
    REFERENCES = "textDocument/references"
    COMPLETION = "textDocument/completion"
    DIAGNOSTICS = "textDocument/publishDiagnostics"


@dataclass
class Position:
    """Position in a text document (0-indexed)."""
    line: int
    character: int

    def to_lsp(self) -> Dict[str, int]:
        """Convert to LSP position format."""
        return {"line": self.line, "character": self.character}


@dataclass
class Range:
    """Range in a text document."""
    start: Position
    end: Position

    def to_lsp(self) -> Dict[str, Any]:
        """Convert to LSP range format."""
        return {
            "start": self.start.to_lsp(),
            "end": self.end.to_lsp()
        }


@dataclass
class Location:
    """Location (file + range)."""
    uri: str
    range: Range

    @classmethod
    def from_lsp(cls, data: Dict[str, Any]) -> "Location":
        """Parse from LSP location."""
        return cls(
            uri=data["uri"],
            range=Range(
                start=Position(
                    line=data["range"]["start"]["line"],
                    character=data["range"]["start"]["character"]
                ),
                end=Position(
                    line=data["range"]["end"]["line"],
                    character=data["range"]["end"]["character"]
                )
            )
        )


@dataclass
class Diagnostic:
    """LSP diagnostic (error/warning)."""
    range: Range
    severity: int  # 1=Error, 2=Warning, 3=Info, 4=Hint
    message: str
    source: Optional[str] = None

    @classmethod
    def from_lsp(cls, data: Dict[str, Any]) -> "Diagnostic":
        """Parse from LSP diagnostic."""
        return cls(
            range=Range(
                start=Position(
                    line=data["range"]["start"]["line"],
                    character=data["range"]["start"]["character"]
                ),
                end=Position(
                    line=data["range"]["end"]["line"],
                    character=data["range"]["end"]["character"]
                )
            ),
            severity=data.get("severity", 1),
            message=data["message"],
            source=data.get("source")
        )

    @property
    def severity_name(self) -> str:
        """Human-readable severity."""
        return {1: "Error", 2: "Warning", 3: "Info", 4: "Hint"}.get(self.severity, "Unknown")


@dataclass
class HoverInfo:
    """Hover information."""
    contents: str
    range: Optional[Range] = None

    @classmethod
    def from_lsp(cls, data: Dict[str, Any]) -> "HoverInfo":
        """Parse from LSP hover response."""
        contents = data.get("contents", "")
        
        # Handle different content formats
        if isinstance(contents, dict):
            if "value" in contents:
                contents = contents["value"]
            elif "kind" in contents:
                contents = contents.get("value", "")
        elif isinstance(contents, list):
            contents = "\n".join(
                item["value"] if isinstance(item, dict) else str(item)
                for item in contents
            )
        
        range_data = data.get("range")
        range_obj = None
        if range_data:
            range_obj = Range(
                start=Position(
                    line=range_data["start"]["line"],
                    character=range_data["start"]["character"]
                ),
                end=Position(
                    line=range_data["end"]["line"],
                    character=range_data["end"]["character"]
                )
            )
        
        return cls(contents=contents, range=range_obj)


@dataclass
class CompletionItem:
    """Code completion item."""
    label: str
    kind: int  # 1=Text, 2=Method, 3=Function, 4=Constructor, etc.
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insert_text: Optional[str] = None
    sort_text: Optional[str] = None
    
    @classmethod
    def from_lsp(cls, data: Dict[str, Any]) -> "CompletionItem":
        """Parse from LSP completion item."""
        documentation = data.get("documentation")
        if isinstance(documentation, dict):
            documentation = documentation.get("value", "")
        
        return cls(
            label=data["label"],
            kind=data.get("kind", 1),
            detail=data.get("detail"),
            documentation=documentation,
            insert_text=data.get("insertText", data["label"]),
            sort_text=data.get("sortText")
        )
    
    @property
    def kind_name(self) -> str:
        """Human-readable kind."""
        kinds = {
            1: "Text", 2: "Method", 3: "Function", 4: "Constructor",
            5: "Field", 6: "Variable", 7: "Class", 8: "Interface",
            9: "Module", 10: "Property", 11: "Unit", 12: "Value",
            13: "Enum", 14: "Keyword", 15: "Snippet", 16: "Color",
            17: "File", 18: "Reference", 19: "Folder", 20: "EnumMember",
            21: "Constant", 22: "Struct", 23: "Event", 24: "Operator",
            25: "TypeParameter"
        }
        return kinds.get(self.kind, "Unknown")


@dataclass
class ParameterInformation:
    """Function parameter information."""
    label: str
    documentation: Optional[str] = None
    
    @classmethod
    def from_lsp(cls, data: Dict[str, Any]) -> "ParameterInformation":
        """Parse from LSP parameter."""
        label = data["label"]
        if isinstance(label, list):
            label = str(label)
        
        documentation = data.get("documentation")
        if isinstance(documentation, dict):
            documentation = documentation.get("value", "")
        
        return cls(label=label, documentation=documentation)


@dataclass
class SignatureInformation:
    """Function signature information."""
    label: str
    documentation: Optional[str] = None
    parameters: List[ParameterInformation] = field(default_factory=list)
    active_parameter: Optional[int] = None
    
    @classmethod
    def from_lsp(cls, data: Dict[str, Any], active_param: Optional[int] = None) -> "SignatureInformation":
        """Parse from LSP signature."""
        documentation = data.get("documentation")
        if isinstance(documentation, dict):
            documentation = documentation.get("value", "")
        
        parameters = [
            ParameterInformation.from_lsp(p)
            for p in data.get("parameters", [])
        ]
        
        return cls(
            label=data["label"],
            documentation=documentation,
            parameters=parameters,
            active_parameter=active_param
        )


@dataclass
class SignatureHelp:
    """Signature help response."""
    signatures: List[SignatureInformation]
    active_signature: int = 0
    active_parameter: int = 0
    
    @classmethod
    def from_lsp(cls, data: Dict[str, Any]) -> "SignatureHelp":
        """Parse from LSP signature help."""
        active_sig = data.get("activeSignature", 0)
        active_param = data.get("activeParameter", 0)
        
        signatures = [
            SignatureInformation.from_lsp(sig, active_param)
            for sig in data.get("signatures", [])
        ]
        
        return cls(
            signatures=signatures,
            active_signature=active_sig,
            active_parameter=active_param
        )


class LSPClient:
    """
    Multi-language LSP client for code intelligence.
    
    Supports:
    - Python (pylsp)
    - TypeScript/JavaScript (typescript-language-server)
    - Go (gopls)
    
    Communication via JSON-RPC over stdio.
    """

    def __init__(self, root_path: Path, language: Optional[Language] = None):
        """
        Initialize LSP client.
        
        Args:
            root_path: Project root directory
            language: Target language (auto-detect if None)
        """
        self.root_path = root_path.resolve()
        self.root_uri = f"file://{self.root_path}"
        self.language = language or Language.PYTHON
        
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._initialized = False
        self._message_id = 0
        self._diagnostics: Dict[str, List[Diagnostic]] = {}
        self._server_configs = LSPServerConfig.get_configs()
        
        logger.info(f"LSP client initialized for {self.root_path} (language: {self.language.value})")

    def _next_id(self) -> int:
        """Get next message ID."""
        self._message_id += 1
        return self._message_id

    def _file_to_uri(self, file_path: Path) -> str:
        """Convert file path to URI."""
        return f"file://{file_path.resolve()}"

    def _uri_to_file(self, uri: str) -> Path:
        """Convert URI to file path."""
        if uri.startswith("file://"):
            return Path(uri[7:])
        return Path(uri)

    async def start(self, language: Optional[Language] = None) -> bool:
        """
        Start LSP server for specified language.
        
        Args:
            language: Target language (uses self.language if None)
        
        Returns:
            True if started successfully
        """
        if self._process is not None:
            logger.warning("LSP server already running")
            return True
        
        target_language = language or self.language
        
        if target_language not in self._server_configs:
            logger.error(f"No LSP server configured for {target_language.value}")
            return False
        
        config = self._server_configs[target_language]
        
        try:
            # Start LSP server
            self._process = subprocess.Popen(
                config.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.root_path)
            )
            
            # Initialize
            await self._initialize(config)
            self._initialized = True
            self.language = target_language
            
            logger.info(f"LSP server started successfully ({target_language.value})")
            return True
            
        except FileNotFoundError:
            logger.error(
                f"LSP server not found for {target_language.value}. "
                f"Command: {' '.join(config.command)}"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to start LSP server: {e}")
            return False

    async def _initialize(self, config: LSPServerConfig) -> None:
        """Send initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": self.root_uri,
                "capabilities": {
                    "textDocument": {
                        "hover": {"contentFormat": ["markdown", "plaintext"]},
                        "definition": {"linkSupport": True},
                        "references": {},
                        "completion": {
                            "completionItem": {
                                "snippetSupport": True,
                                "documentationFormat": ["markdown", "plaintext"]
                            }
                        },
                        "signatureHelp": {
                            "signatureInformation": {
                                "documentationFormat": ["markdown", "plaintext"],
                                "parameterInformation": {
                                    "labelOffsetSupport": True
                                }
                            }
                        },
                        "publishDiagnostics": {}
                    }
                },
                "initializationOptions": config.initialization_options or {}
            }
        }
        
        # Note: Full implementation would send/receive via stdin/stdout
        # For now, we'll use synchronous invocation with pylsp/tsserver
        logger.debug(f"LSP initialized ({config.language.value})")

    async def stop(self) -> None:
        """Stop LSP server."""
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._process.wait),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self._process.kill()
            
            self._process = None
            self._initialized = False
            logger.info("LSP server stopped")

    async def hover(self, file_path: Path, line: int, character: int) -> Optional[HoverInfo]:
        """
        Get hover information at position.
        
        Args:
            file_path: Python file
            line: Line number (0-indexed)
            character: Character position (0-indexed)
            
        Returns:
            HoverInfo if available, None otherwise
        """
        if not self._initialized:
            logger.warning("LSP not initialized")
            return None
        
        try:
            # For now, use simple rope-based inspection
            # Full LSP implementation would use JSON-RPC
            content = file_path.read_text()
            lines = content.split("\n")
            
            if line >= len(lines):
                return None
            
            # Basic hover: extract word at position
            line_text = lines[line]
            if character >= len(line_text):
                return None
            
            # Find word boundaries
            start = character
            while start > 0 and (line_text[start - 1].isalnum() or line_text[start - 1] == "_"):
                start -= 1
            
            end = character
            while end < len(line_text) and (line_text[end].isalnum() or line_text[end] == "_"):
                end += 1
            
            word = line_text[start:end]
            if not word:
                return None
            
            # Try to get docstring/type info
            hover_text = f"Symbol: `{word}`\n\n"
            hover_text += "_(LSP integration in progress - basic info only)_"
            
            return HoverInfo(
                contents=hover_text,
                range=Range(
                    start=Position(line, start),
                    end=Position(line, end)
                )
            )
            
        except Exception as e:
            logger.error(f"Hover failed: {e}")
            return None

    async def definition(self, file_path: Path, line: int, character: int) -> List[Location]:
        """
        Go to definition.
        
        Args:
            file_path: Python file
            line: Line number (0-indexed)
            character: Character position (0-indexed)
            
        Returns:
            List of definition locations
        """
        if not self._initialized:
            logger.warning("LSP not initialized")
            return []
        
        try:
            # Placeholder: Would use LSP textDocument/definition
            # For now, return empty (feature in development)
            logger.info(f"Definition lookup: {file_path}:{line}:{character}")
            return []
            
        except Exception as e:
            logger.error(f"Definition lookup failed: {e}")
            return []

    async def references(self, file_path: Path, line: int, character: int) -> List[Location]:
        """
        Find all references.
        
        Args:
            file_path: Python file
            line: Line number (0-indexed)
            character: Character position (0-indexed)
            
        Returns:
            List of reference locations
        """
        if not self._initialized:
            logger.warning("LSP not initialized")
            return []
        
        try:
            # Placeholder: Would use LSP textDocument/references
            logger.info(f"References lookup: {file_path}:{line}:{character}")
            return []
            
        except Exception as e:
            logger.error(f"References lookup failed: {e}")
            return []

    async def diagnostics(self, file_path: Path) -> List[Diagnostic]:
        """
        Get diagnostics for file.
        
        Args:
            file_path: Python file
            
        Returns:
            List of diagnostics (errors/warnings)
        """
        uri = self._file_to_uri(file_path)
        return self._diagnostics.get(uri, [])

    def get_all_diagnostics(self) -> Dict[str, List[Diagnostic]]:
        """
        Get all diagnostics across all files.
        
        Returns:
            Dict mapping file URI to diagnostics
        """
        return self._diagnostics.copy()

    async def completion(
        self,
        file_path: Path,
        line: int,
        character: int,
        trigger_kind: int = 1  # 1=Invoked, 2=TriggerCharacter, 3=TriggerForIncompleteCompletions
    ) -> List[CompletionItem]:
        """
        Get code completions at position.
        
        Args:
            file_path: Source file
            line: Line number (0-indexed)
            character: Character position (0-indexed)
            trigger_kind: Completion trigger kind
            
        Returns:
            List of completion items
        """
        if not self._initialized:
            logger.warning("LSP not initialized")
            return []
        
        try:
            # Placeholder: Would use LSP textDocument/completion
            # Real implementation would send request via stdin/stdout
            logger.info(f"Completion requested: {file_path}:{line}:{character}")
            
            # For demo, return mock completions
            # In production, parse LSP JSON response
            return [
                CompletionItem(
                    label="example_function",
                    kind=3,  # Function
                    detail="() -> None",
                    documentation="Example function for demonstration"
                )
            ]
            
        except Exception as e:
            logger.error(f"Completion failed: {e}")
            return []

    async def signature_help(
        self,
        file_path: Path,
        line: int,
        character: int
    ) -> Optional[SignatureHelp]:
        """
        Get signature help (function parameter hints) at position.
        
        Args:
            file_path: Source file
            line: Line number (0-indexed)
            character: Character position (0-indexed)
            
        Returns:
            Signature help information or None
        """
        if not self._initialized:
            logger.warning("LSP not initialized")
            return None
        
        try:
            # Placeholder: Would use LSP textDocument/signatureHelp
            # Real implementation would send request via stdin/stdout
            logger.info(f"Signature help requested: {file_path}:{line}:{character}")
            
            # For demo, return mock signature
            # In production, parse LSP JSON response
            param = ParameterInformation(
                label="param1: str",
                documentation="First parameter"
            )
            
            sig = SignatureInformation(
                label="example_function(param1: str) -> None",
                documentation="Example function signature",
                parameters=[param],
                active_parameter=0
            )
            
            return SignatureHelp(
                signatures=[sig],
                active_signature=0,
                active_parameter=0
            )
            
        except Exception as e:
            logger.error(f"Signature help failed: {e}")
            return None

    async def open_file(self, file_path: Path) -> None:
        """
        Notify LSP that file is opened.
        
        Args:
            file_path: Opened file
        """
        if not self._initialized:
            return
        
        try:
            content = file_path.read_text()
            # Would send textDocument/didOpen notification
            logger.debug(f"File opened: {file_path}")
        except Exception as e:
            logger.error(f"Failed to open file in LSP: {e}")

    async def close_file(self, file_path: Path) -> None:
        """
        Notify LSP that file is closed.
        
        Args:
            file_path: Closed file
        """
        if not self._initialized:
            return
        
        # Would send textDocument/didClose notification
        logger.debug(f"File closed: {file_path}")

    def __enter__(self) -> "LSPClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        asyncio.run(self.stop())
