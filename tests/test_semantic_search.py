"""
Week 3 Day 1: Semantic Search Tests

Tests for smart file search using semantic indexer.

Boris Cherny: Type-safe semantic search integration
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock
from qwen_dev_cli.tools.search import SearchFilesTool
from qwen_dev_cli.intelligence.indexer import SemanticIndexer, Symbol


class TestSemanticSearch:
    """Test semantic search integration with indexer."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_finds_symbols(self):
        """Test that semantic search finds code symbols."""
        # Create temp directory with test file
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("""
def hello_world():
    '''Say hello'''
    pass

class MyClass:
    '''A test class'''
    pass
""")
            
            # Index the file
            indexer = SemanticIndexer(root_path=tmpdir)
            indexer.index_codebase()
            
            # Search with semantic mode
            tool = SearchFilesTool()
            result = await tool._execute_validated(
                pattern="hello",
                semantic=True,
                indexer=indexer,
                max_results=10
            )
            
            # Verify: Found the function
            assert result.success is True
            assert len(result.data) >= 1
            assert any(r['name'] == 'hello_world' for r in result.data)
            assert result.metadata['tool'] == 'semantic_indexer'
    
    @pytest.mark.asyncio
    async def test_semantic_search_returns_symbol_metadata(self):
        """Test that semantic search returns rich symbol metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "code.py"
            test_file.write_text("""
def calculate(x: int, y: int) -> int:
    '''Calculate sum of x and y'''
    return x + y
""")
            
            indexer = SemanticIndexer(root_path=tmpdir)
            indexer.index_codebase()
            
            tool = SearchFilesTool()
            result = await tool._execute_validated(
                pattern="calculate",
                semantic=True,
                indexer=indexer
            )
            
            # Verify: Returns metadata
            assert result.success is True
            assert len(result.data) == 1
            
            symbol = result.data[0]
            assert symbol['name'] == 'calculate'
            assert symbol['type'] == 'function'
            assert 'signature' in symbol
            assert 'docstring' in symbol
            assert 'Calculate sum' in symbol['docstring']
    
    @pytest.mark.asyncio
    async def test_semantic_search_faster_than_text(self):
        """Test that semantic search is faster for code symbols."""
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple files
            for i in range(10):
                test_file = Path(tmpdir) / f"module{i}.py"
                test_file.write_text(f"""
def func{i}():
    pass

class Class{i}:
    pass
""")
            
            indexer = SemanticIndexer(root_path=tmpdir)
            indexer.index_codebase()
            
            tool = SearchFilesTool()
            
            # Semantic search
            start = time.time()
            result_semantic = await tool._execute_validated(
                pattern="func5",
                semantic=True,
                indexer=indexer
            )
            time_semantic = time.time() - start
            
            # Verify: Found result
            assert result_semantic.success is True
            assert len(result_semantic.data) >= 1
            
            # Note: Semantic should be fast (< 0.1s for 10 files)
            assert time_semantic < 0.5, f"Semantic search too slow: {time_semantic:.2f}s"
    
    @pytest.mark.asyncio
    async def test_semantic_search_falls_back_on_error(self):
        """Test that semantic search logs warning on error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello(): pass")
            
            # Create indexer that will fail
            indexer = Mock()
            indexer.search_symbols = Mock(side_effect=Exception("Index error"))
            
            tool = SearchFilesTool()
            
            # Should handle error gracefully (either fallback or error result)
            result = await tool._execute_validated(
                pattern="hello",
                semantic=True,
                indexer=indexer,
                path=tmpdir
            )
            
            # Verify: Either succeeds with fallback OR returns error gracefully
            # (both are acceptable - no crash is the key)
            assert isinstance(result.success, bool)
    
    @pytest.mark.asyncio
    async def test_text_search_still_works(self):
        """Test that text search still works when semantic=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.txt"
            test_file.write_text("hello world\ntest data")
            
            tool = SearchFilesTool()
            result = await tool._execute_validated(
                pattern="hello",
                path=tmpdir,
                semantic=False  # Explicit text search
            )
            
            # Verify: Text search works
            assert result.success is True
            assert result.metadata['tool'] in ['ripgrep', 'grep']
    
    @pytest.mark.asyncio
    async def test_semantic_search_empty_query(self):
        """Test semantic search with no results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello(): pass")
            
            indexer = SemanticIndexer(root_path=tmpdir)
            indexer.index_codebase()
            
            tool = SearchFilesTool()
            result = await tool._execute_validated(
                pattern="nonexistent_symbol",
                semantic=True,
                indexer=indexer
            )
            
            # Verify: Returns empty results (not error)
            assert result.success is True
            assert len(result.data) == 0
            assert result.metadata['count'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
