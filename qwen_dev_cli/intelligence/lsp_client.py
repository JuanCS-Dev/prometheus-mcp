"""
LSP (Language Server Protocol) Client for Code Intelligence.

Provides:
- Hover documentation
- Go-to-definition
- Find references
- Code completion (basic)
- Diagnostics (errors/warnings)

Boris Cherny Implementation - Week 3 Day 3
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


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


class LSPClient:
    """
    Lightweight LSP client for Python code intelligence.
    
    Uses python-lsp-server (pylsp) as the backend.
    Communication via JSON-RPC over stdio.
    """

    def __init__(self, root_path: Path):
        """
        Initialize LSP client.
        
        Args:
            root_path: Project root directory
        """
        self.root_path = root_path.resolve()
        self.root_uri = f"file://{self.root_path}"
        
        self._process: Optional[subprocess.Popen] = None
        self._initialized = False
        self._message_id = 0
        self._diagnostics: Dict[str, List[Diagnostic]] = {}
        
        logger.info(f"LSP client initialized for {self.root_path}")

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

    async def start(self) -> bool:
        """
        Start LSP server.
        
        Returns:
            True if started successfully
        """
        if self._process is not None:
            logger.warning("LSP server already running")
            return True
        
        try:
            # Start pylsp
            self._process = subprocess.Popen(
                ["pylsp"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.root_path)
            )
            
            # Initialize
            await self._initialize()
            self._initialized = True
            
            logger.info("LSP server started successfully")
            return True
            
        except FileNotFoundError:
            logger.error("pylsp not found. Install: pip install python-lsp-server[all]")
            return False
        except Exception as e:
            logger.error(f"Failed to start LSP server: {e}")
            return False

    async def _initialize(self):
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
                        "completion": {},
                        "publishDiagnostics": {}
                    }
                }
            }
        }
        
        # Note: Full implementation would send/receive via stdin/stdout
        # For now, we'll use synchronous pylsp invocation
        logger.debug("LSP initialized")

    async def stop(self):
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

    async def open_file(self, file_path: Path):
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

    async def close_file(self, file_path: Path):
        """
        Notify LSP that file is closed.
        
        Args:
            file_path: Closed file
        """
        if not self._initialized:
            return
        
        # Would send textDocument/didClose notification
        logger.debug(f"File closed: {file_path}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        asyncio.run(self.stop())
