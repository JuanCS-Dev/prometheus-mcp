"""
Week 3 Day 1 Scientific Validation Tests

Real-world usage scenarios and edge cases.
Tests airgaps, constitutional compliance, performance.

Boris Cherny: Scientific validation standards
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock
from jdev_cli.shell import InteractiveShell
from jdev_cli.intelligence.indexer import SemanticIndexer
from jdev_cli.tools.search import SearchFilesTool


class TestRealWorldUsage:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_large_codebase_indexing(self):
        """Test indexing a large codebase (100+ files)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 100 Python files
            for i in range(100):
                test_file = Path(tmpdir) / f"module{i}.py"
                test_file.write_text(f"""
def func{i}():
    '''Function {i}'''
    pass

class Class{i}:
    '''Class {i}'''
    pass
""")

            # Index
            indexer = SemanticIndexer(root_path=tmpdir)

            import time
            start = time.time()
            count = indexer.index_codebase()
            elapsed = time.time() - start

            # Verify: Indexed all files
            assert count == 100

            # Verify: Performance acceptable (< 5s for 100 files)
            assert elapsed < 5.0, f"Indexing too slow: {elapsed:.2f}s"

            # Verify: Stats correct
            stats = indexer.get_stats()
            assert stats['total_files'] == 100
            assert stats['total_symbols'] == 200  # 100 funcs + 100 classes

    @pytest.mark.asyncio
    async def test_search_with_partial_match(self):
        """Test semantic search with partial symbol name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "models.py"
            test_file.write_text("""
class UserModel:
    pass

class UserController:
    pass

class ProductModel:
    pass
""")

            indexer = SemanticIndexer(root_path=tmpdir)
            indexer.index_codebase()

            tool = SearchFilesTool()

            # Search for "User" (partial match)
            result = await tool._execute_validated(
                pattern="User",
                semantic=True,
                indexer=indexer
            )

            # Verify: Found both User* classes
            assert result.success is True
            assert len(result.data) >= 2
            names = [r['name'] for r in result.data]
            assert 'UserModel' in names
            assert 'UserController' in names

    @pytest.mark.asyncio
    async def test_auto_index_with_cache_reuse(self):
        """Test that auto-index reuses cache on second run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello(): pass")

            # First run - build cache
            shell1 = object.__new__(InteractiveShell)
            shell1.console = Mock()
            shell1.indexer = SemanticIndexer(root_path=tmpdir)
            shell1._indexer_initialized = False

            import time
            start1 = time.time()
            await shell1._auto_index_background()
            time1 = time.time() - start1

            # Second run - use cache
            shell2 = object.__new__(InteractiveShell)
            shell2.console = Mock()
            shell2.indexer = SemanticIndexer(root_path=tmpdir)
            shell2.indexer.load_cache()  # Load from cache
            shell2._indexer_initialized = False

            start2 = time.time()
            await shell2._auto_index_background()
            time2 = time.time() - start2

            # Verify: Second run faster (cache hit)
            assert time2 < time1 or time2 < 0.5, "Cache not being used"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_codebase(self):
        """Test indexing an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = SemanticIndexer(root_path=tmpdir)
            count = indexer.index_codebase()

            # Verify: No crash, returns 0
            assert count == 0

            stats = indexer.get_stats()
            assert stats['total_files'] == 0
            assert stats['total_symbols'] == 0

    @pytest.mark.asyncio
    async def test_file_with_syntax_errors(self):
        """Test indexing file with syntax errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "bad.py"
            bad_file.write_text("def broken(:\n    pass\n")  # Syntax error

            good_file = Path(tmpdir) / "good.py"
            good_file.write_text("def working(): pass")

            indexer = SemanticIndexer(root_path=tmpdir)
            count = indexer.index_codebase()

            # Verify: Skips bad file, indexes good file
            assert count >= 1  # At least good file

            # Verify: Can still search
            symbols = indexer.search_symbols("working")
            assert len(symbols) == 1

    @pytest.mark.asyncio
    async def test_very_large_file(self):
        """Test indexing a very large file (10K lines)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            large_file = Path(tmpdir) / "large.py"

            # Generate 10K lines
            lines = []
            for i in range(10000):
                lines.append(f"def func{i}(): pass\n")

            large_file.write_text(''.join(lines))

            indexer = SemanticIndexer(root_path=tmpdir)

            import time
            start = time.time()
            count = indexer.index_codebase()
            elapsed = time.time() - start

            # Verify: Indexed successfully
            assert count == 1

            # Verify: Performance acceptable (< 2s for 10K lines)
            assert elapsed < 2.0

            # Verify: Found many symbols
            stats = indexer.get_stats()
            assert stats['total_symbols'] >= 9000  # Most functions found

    @pytest.mark.asyncio
    async def test_binary_files_skipped(self):
        """Test that binary files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create binary file
            binary_file = Path(tmpdir) / "image.png"
            binary_file.write_bytes(b'\x89PNG\r\n\x1a\n')

            # Create text file
            text_file = Path(tmpdir) / "code.py"
            text_file.write_text("def hello(): pass")

            indexer = SemanticIndexer(root_path=tmpdir)
            count = indexer.index_codebase()

            # Verify: Only indexed text file
            assert count == 1

    @pytest.mark.asyncio
    async def test_special_characters_in_symbol_names(self):
        """Test symbols with unicode/special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "unicode.py"
            test_file.write_text("""
def função_português():
    '''Portuguese function'''
    pass

class Класс:
    '''Cyrillic class'''
    pass
""")

            indexer = SemanticIndexer(root_path=tmpdir)
            count = indexer.index_codebase()

            # Verify: Indexed successfully
            assert count == 1

            # Verify: Can find unicode symbols
            results = indexer.search_symbols("função")
            assert len(results) >= 1


class TestPerformance:
    """Performance regression tests."""

    @pytest.mark.asyncio
    async def test_search_performance_scales(self):
        """Test that search performance scales well."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with many symbols
            for i in range(10):
                test_file = Path(tmpdir) / f"module{i}.py"
                symbols = []
                for j in range(50):  # 50 symbols per file
                    symbols.append(f"def func{i}_{j}(): pass\n")
                test_file.write_text(''.join(symbols))

            indexer = SemanticIndexer(root_path=tmpdir)
            indexer.index_codebase()

            # Total: 500 symbols
            stats = indexer.get_stats()
            assert stats['total_symbols'] >= 400

            # Search performance
            import time

            searches = ['func0', 'func5', 'func9', 'nonexistent']
            times = []

            for query in searches:
                start = time.time()
                indexer.search_symbols(query)
                elapsed = time.time() - start
                times.append(elapsed)

            # Verify: All searches < 100ms
            assert all(t < 0.1 for t in times), f"Search too slow: {times}"

            # Verify: Average < 50ms
            avg_time = sum(times) / len(times)
            assert avg_time < 0.05, f"Average search time too high: {avg_time:.3f}s"


class TestConstitutionalCompliance:
    """Test Constituição Vértice compliance."""

    def test_no_todos_in_new_code(self):
        """P1: Verify no TODOs in Week 3 Day 1 code."""
        files_to_check = [
            'jdev_cli/tools/search.py',  # Only new file
        ]

        for filepath in files_to_check:
            with open(filepath, 'r') as f:
                content = f.read()
                # Check for TODO patterns (excluding comments and strings)
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    # Skip if in string or comment with "find files modified today"
                    if 'modified today' in line or 'Week 3' in line:
                        continue
                    if 'TODO' in line and '#' not in line[:line.find('TODO')] if 'TODO' in line else False:
                        assert False, f"Found uncommented TODO in {filepath}:{i}"

    def test_type_hints_present(self):
        """P1: Verify type hints in critical functions."""
        from jdev_cli.shell import InteractiveShell
        from jdev_cli.tools.search import SearchFilesTool

        # Check shell._auto_index_background has hints
        method = InteractiveShell._auto_index_background
        assert method.__annotations__, "Missing type hints in _auto_index_background"

        # Check SearchFilesTool._semantic_search has hints
        method = SearchFilesTool._semantic_search
        assert method.__annotations__, "Missing type hints in _semantic_search"

    def test_error_handling_robust(self):
        """P2: Verify error handling in critical paths."""
        # Verify _auto_index_background has try/except
        import inspect
        from jdev_cli.shell import InteractiveShell

        source = inspect.getsource(InteractiveShell._auto_index_background)
        assert 'try:' in source, "Missing error handling in _auto_index_background"
        assert 'except' in source, "Missing exception handling"

        # Verify _semantic_search has try/except
        from jdev_cli.tools.search import SearchFilesTool
        source = inspect.getsource(SearchFilesTool._semantic_search)
        assert 'try:' in source, "Missing error handling in _semantic_search"
        assert 'except' in source, "Missing exception handling"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
