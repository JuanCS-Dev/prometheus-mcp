"""
Tests for LSP client.

Boris Cherny Implementation - Week 3 Day 3
"""

import pytest
from pathlib import Path
from qwen_dev_cli.intelligence.lsp_client import (
    LSPClient,
    Position,
    Range,
    Location,
    Diagnostic,
    HoverInfo
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
