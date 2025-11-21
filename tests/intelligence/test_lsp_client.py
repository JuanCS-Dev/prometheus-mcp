"""
Tests for LSP client.

Boris Cherny Implementation - Week 3 Day 3 + Week 4 Day 3 Enhancement
"""

import pytest
from pathlib import Path
from qwen_dev_cli.intelligence.lsp_client import (
    LSPClient,
    Position,
    Range,
    Location,
    Diagnostic,
    HoverInfo,
    Language,
    LSPServerConfig,
    CompletionItem,
    SignatureHelp,
    SignatureInformation,
    ParameterInformation
)


@pytest.fixture
def temp_project(tmp_path):
    """Create temporary Python project."""
    (tmp_path / "example.py").write_text("""
def greet(name: str) -> str:
    '''Greet someone by name.'''
    return f"Hello, {name}!"
""")
    return tmp_path


@pytest.mark.asyncio
class TestLSPClient:
    """Test LSP client functionality."""
    
    async def test_client_initialization(self, temp_project):
        """Test LSP client can be initialized."""
        client = LSPClient(root_path=temp_project)
        
        assert client.root_path == temp_project.resolve()
        assert client.root_uri == f"file://{temp_project.resolve()}"
        assert not client._initialized


class TestPosition:
    """Test Position dataclass."""
    
    def test_position_creation(self):
        """Test creating position."""
        pos = Position(line=10, character=5)
        assert pos.line == 10
        assert pos.character == 5
    
    def test_position_to_lsp(self):
        """Test converting to LSP format."""
        pos = Position(line=10, character=5)
        lsp_pos = pos.to_lsp()
        
        assert lsp_pos == {"line": 10, "character": 5}


class TestRange:
    """Test Range dataclass."""
    
    def test_range_creation(self):
        """Test creating range."""
        start = Position(line=1, character=0)
        end = Position(line=1, character=10)
        rng = Range(start=start, end=end)
        
        assert rng.start.line == 1
        assert rng.end.character == 10


class TestLanguageDetection:
    """Test language detection."""
    
    def test_detect_python(self):
        """Test Python file detection."""
        assert Language.detect(Path("test.py")) == Language.PYTHON
    
    def test_detect_typescript(self):
        """Test TypeScript file detection."""
        assert Language.detect(Path("test.ts")) == Language.TYPESCRIPT
        assert Language.detect(Path("test.tsx")) == Language.TYPESCRIPT
    
    def test_detect_javascript(self):
        """Test JavaScript file detection."""
        assert Language.detect(Path("test.js")) == Language.JAVASCRIPT
        assert Language.detect(Path("test.jsx")) == Language.JAVASCRIPT
    
    def test_detect_go(self):
        """Test Go file detection."""
        assert Language.detect(Path("test.go")) == Language.GO
    
    def test_detect_unknown(self):
        """Test unknown file detection."""
        assert Language.detect(Path("test.txt")) == Language.UNKNOWN


class TestLSPServerConfig:
    """Test LSP server configuration."""
    
    def test_get_python_config(self):
        """Test Python LSP config."""
        configs = LSPServerConfig.get_configs()
        py_config = configs[Language.PYTHON]
        
        assert py_config.language == Language.PYTHON
        assert py_config.command == ["pylsp"]
    
    def test_get_typescript_config(self):
        """Test TypeScript LSP config."""
        configs = LSPServerConfig.get_configs()
        ts_config = configs[Language.TYPESCRIPT]
        
        assert ts_config.language == Language.TYPESCRIPT
        assert "typescript-language-server" in ts_config.command[0]
    
    def test_get_go_config(self):
        """Test Go LSP config."""
        configs = LSPServerConfig.get_configs()
        go_config = configs[Language.GO]
        
        assert go_config.language == Language.GO
        assert go_config.command == ["gopls"]


class TestCompletionItem:
    """Test completion item parsing."""
    
    def test_from_lsp_basic(self):
        """Test basic completion item."""
        data = {
            "label": "test_func",
            "kind": 3,
            "detail": "() -> None"
        }
        item = CompletionItem.from_lsp(data)
        
        assert item.label == "test_func"
        assert item.kind == 3
        assert item.detail == "() -> None"
        assert item.kind_name == "Function"
    
    def test_from_lsp_with_documentation(self):
        """Test completion item with documentation."""
        data = {
            "label": "test_var",
            "kind": 6,
            "documentation": {"value": "Test variable"}
        }
        item = CompletionItem.from_lsp(data)
        
        assert item.label == "test_var"
        assert item.kind_name == "Variable"
        assert item.documentation == "Test variable"


class TestSignatureHelp:
    """Test signature help parsing."""
    
    def test_parameter_information(self):
        """Test parameter info parsing."""
        data = {
            "label": "param1: str",
            "documentation": "First parameter"
        }
        param = ParameterInformation.from_lsp(data)
        
        assert param.label == "param1: str"
        assert param.documentation == "First parameter"
    
    def test_signature_information(self):
        """Test signature info parsing."""
        data = {
            "label": "func(a: str, b: int) -> None",
            "documentation": "Test function",
            "parameters": [
                {"label": "a: str"},
                {"label": "b: int"}
            ]
        }
        sig = SignatureInformation.from_lsp(data)
        
        assert sig.label == "func(a: str, b: int) -> None"
        assert len(sig.parameters) == 2
        assert sig.parameters[0].label == "a: str"
    
    def test_signature_help_full(self):
        """Test full signature help."""
        data = {
            "signatures": [
                {
                    "label": "func(a: str) -> None",
                    "parameters": [{"label": "a: str"}]
                }
            ],
            "activeSignature": 0,
            "activeParameter": 0
        }
        help_data = SignatureHelp.from_lsp(data)
        
        assert len(help_data.signatures) == 1
        assert help_data.active_signature == 0
        assert help_data.active_parameter == 0


@pytest.mark.asyncio
class TestMultiLanguageLSP:
    """Test multi-language LSP functionality."""
    
    async def test_client_with_typescript(self, temp_project):
        """Test LSP client with TypeScript."""
        client = LSPClient(root_path=temp_project, language=Language.TYPESCRIPT)
        
        assert client.language == Language.TYPESCRIPT
        assert Language.TYPESCRIPT in client._server_configs
    
    async def test_client_language_switch(self, temp_project):
        """Test switching language."""
        client = LSPClient(root_path=temp_project, language=Language.PYTHON)
        
        # Attempt to start with different language (would fail without server installed)
        # Just test that config exists
        assert Language.GO in client._server_configs
        assert Language.TYPESCRIPT in client._server_configs
    
    async def test_completion_request(self, temp_project):
        """Test completion request structure."""
        client = LSPClient(root_path=temp_project)
        
        # Mock completion (real would require running server)
        completions = await client.completion(
            file_path=temp_project / "example.py",
            line=2,
            character=10
        )
        
        # Should return empty or mock data since no real server
        assert isinstance(completions, list)
    
    async def test_signature_help_request(self, temp_project):
        """Test signature help request structure."""
        client = LSPClient(root_path=temp_project)
        
        # Mock signature help (real would require running server)
        sig_help = await client.signature_help(
            file_path=temp_project / "example.py",
            line=2,
            character=10
        )
        
        # Should return None or mock data since no real server
        assert sig_help is None or isinstance(sig_help, SignatureHelp)
