"""
Semantic Codebase Indexer - Cursor-style intelligence.

Provides blazing-fast semantic search and context awareness.
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import re


@dataclass
class Symbol:
    """Represents a code symbol (class, function, variable)."""
    name: str
    type: str  # 'class', 'function', 'method', 'variable', 'import'
    file_path: str
    line_number: int
    docstring: Optional[str] = None
    signature: Optional[str] = None
    parent: Optional[str] = None  # Parent class/function
    references: Set[str] = field(default_factory=set)


@dataclass
class FileIndex:
    """Index data for a single file."""
    path: str
    hash: str
    symbols: List[Symbol]
    imports: List[str]
    dependencies: Set[str] = field(default_factory=set)
    last_modified: float = 0.0


class SemanticIndexer:
    """
    Cursor-style semantic codebase indexer.
    
    Features:
    - Instant symbol lookup
    - Error → Source mapping
    - Dependency graph
    - Smart context collection
    """

    def __init__(self, root_path: str, cache_dir: Optional[str] = None):
        self.root_path = Path(root_path).resolve()
        self.cache_dir = Path(cache_dir or self.root_path / ".qwen" / "index")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory indexes
        self.file_index: Dict[str, FileIndex] = {}
        self.symbol_index: Dict[str, List[Symbol]] = defaultdict(list)
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)

        # Exclude patterns
        self.exclude_patterns = {
            '__pycache__', '.git', '.venv', 'venv', 'node_modules',
            '.pytest_cache', '.mypy_cache', '.tox', 'dist', 'build',
            '*.pyc', '*.pyo', '*.so', '*.egg-info'
        }

    def should_index(self, path: Path) -> bool:
        """Check if file should be indexed."""
        # Check exclude patterns
        parts = path.parts
        for pattern in self.exclude_patterns:
            if pattern.startswith('*.'):
                if path.suffix == pattern[1:]:
                    return False
            else:
                if pattern in parts:
                    return False

        # Only Python files for now
        return path.suffix == '.py'

    def compute_file_hash(self, path: Path) -> str:
        """Compute hash of file content."""
        try:
            with open(path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception:
            return ""

    def parse_file(self, path: Path) -> Optional[FileIndex]:
        """Parse Python file and extract symbols."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(path))

            symbols = []
            imports = []

            for node in ast.walk(tree):
                # Classes
                if isinstance(node, ast.ClassDef):
                    symbols.append(Symbol(
                        name=node.name,
                        type='class',
                        file_path=str(path.relative_to(self.root_path)),
                        line_number=node.lineno,
                        docstring=ast.get_docstring(node)
                    ))

                # Functions
                elif isinstance(node, ast.FunctionDef):
                    parent = None
                    # Check if it's a method
                    for parent_node in ast.walk(tree):
                        if isinstance(parent_node, ast.ClassDef):
                            if node in ast.walk(parent_node):
                                parent = parent_node.name
                                break

                    # Build signature
                    args = [arg.arg for arg in node.args.args]
                    signature = f"{node.name}({', '.join(args)})"

                    symbols.append(Symbol(
                        name=node.name,
                        type='method' if parent else 'function',
                        file_path=str(path.relative_to(self.root_path)),
                        line_number=node.lineno,
                        docstring=ast.get_docstring(node),
                        signature=signature,
                        parent=parent
                    ))

                # Imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            file_hash = self.compute_file_hash(path)

            return FileIndex(
                path=str(path.relative_to(self.root_path)),
                hash=file_hash,
                symbols=symbols,
                imports=imports,
                last_modified=path.stat().st_mtime
            )

        except Exception as e:
            # Silently skip files that can't be parsed
            return None

    def index_codebase(self, force: bool = False) -> int:
        """
        Index entire codebase.
        
        Returns number of files indexed.
        """
        indexed_count = 0

        for path in self.root_path.rglob('*.py'):
            if not self.should_index(path):
                continue

            # Check if file needs reindexing
            rel_path = str(path.relative_to(self.root_path))

            if not force and rel_path in self.file_index:
                existing = self.file_index[rel_path]
                current_hash = self.compute_file_hash(path)

                if existing.hash == current_hash:
                    continue  # Skip unchanged files

            # Parse and index
            file_idx = self.parse_file(path)
            if file_idx:
                self.file_index[rel_path] = file_idx

                # Update symbol index
                for symbol in file_idx.symbols:
                    self.symbol_index[symbol.name].append(symbol)

                # Update import graph
                for imp in file_idx.imports:
                    self.import_graph[rel_path].add(imp)

                indexed_count += 1

        # Save to cache
        self._save_cache()

        return indexed_count

    def find_symbol(self, name: str, type: Optional[str] = None) -> List[Symbol]:
        """Find symbols by name and optional type."""
        symbols = self.symbol_index.get(name, [])

        if type:
            symbols = [s for s in symbols if s.type == type]

        return symbols

    def find_definition(self, error_trace: str) -> Optional[Tuple[str, int]]:
        """
        Map error trace to source location (Cursor magic).
        
        Parses traceback and finds the exact file + line.
        """
        # Parse traceback format
        # Example: File "/path/to/file.py", line 42, in function_name
        pattern = r'File "([^"]+)", line (\d+)'
        matches = re.findall(pattern, error_trace)

        if not matches:
            return None

        # Return first match from our codebase
        for file_path, line_num in matches:
            path = Path(file_path)

            # Check if it's in our codebase
            try:
                rel_path = path.relative_to(self.root_path)
                if str(rel_path) in self.file_index:
                    return (str(rel_path), int(line_num))
            except ValueError:
                continue

        return None

    def get_file_context(self, file_path: str, line_number: int,
                        context_lines: int = 10) -> Optional[str]:
        """Get code context around a line number."""
        full_path = self.root_path / file_path

        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()

            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)

            context = []
            for i in range(start, end):
                marker = "→" if i == line_number - 1 else " "
                context.append(f"{marker} {i+1:4d} | {lines[i].rstrip()}")

            return "\n".join(context)

        except Exception:
            return None

    def get_dependencies(self, file_path: str) -> Set[str]:
        """Get all dependencies for a file."""
        if file_path not in self.file_index:
            return set()

        deps = set()
        to_process = [file_path]
        processed = set()

        while to_process:
            current = to_process.pop()
            if current in processed:
                continue

            processed.add(current)

            if current in self.import_graph:
                for imp in self.import_graph[current]:
                    # Try to resolve import to file
                    resolved = self._resolve_import(imp)
                    if resolved and resolved not in processed:
                        deps.add(resolved)
                        to_process.append(resolved)

        return deps

    def _resolve_import(self, import_name: str) -> Optional[str]:
        """Resolve import to file path."""
        # Simple resolution: convert module.path to file/path.py
        parts = import_name.split('.')

        # Try direct match
        possible_path = '/'.join(parts) + '.py'
        if possible_path in self.file_index:
            return possible_path

        # Try as package
        possible_path = '/'.join(parts) + '/__init__.py'
        if possible_path in self.file_index:
            return possible_path

        return None

    def search_symbols(self, query: str, limit: int = 10) -> List[Symbol]:
        """Fuzzy search symbols."""
        query_lower = query.lower()
        results = []

        for name, symbols in self.symbol_index.items():
            if query_lower in name.lower():
                results.extend(symbols)

        # Sort by relevance (exact match first, then prefix, then contains)
        def sort_key(symbol: Symbol) -> Tuple[int, str]:
            name_lower = symbol.name.lower()
            if name_lower == query_lower:
                return (0, symbol.name)
            elif name_lower.startswith(query_lower):
                return (1, symbol.name)
            else:
                return (2, symbol.name)

        results.sort(key=sort_key)

        return results[:limit]

    def get_stats(self) -> Dict:
        """Get indexer statistics."""
        total_symbols = sum(len(syms) for syms in self.symbol_index.values())

        symbol_types = defaultdict(int)
        for symbols in self.symbol_index.values():
            for symbol in symbols:
                symbol_types[symbol.type] += 1

        return {
            'files_indexed': len(self.file_index),
            'total_symbols': total_symbols,
            'symbol_types': dict(symbol_types),
            'unique_symbols': len(self.symbol_index)
        }

    def _save_cache(self):
        """Save index to cache."""
        cache_file = self.cache_dir / "index.json"

        try:
            data = {
                'file_index': {
                    path: {
                        'path': idx.path,
                        'hash': idx.hash,
                        'symbols': [
                            {
                                'name': s.name,
                                'type': s.type,
                                'file_path': s.file_path,
                                'line_number': s.line_number,
                                'docstring': s.docstring,
                                'signature': s.signature,
                                'parent': s.parent
                            }
                            for s in idx.symbols
                        ],
                        'imports': idx.imports,
                        'last_modified': idx.last_modified
                    }
                    for path, idx in self.file_index.items()
                }
            }

            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception:
            pass  # Silently fail cache save

    def load_cache(self) -> bool:
        """Load index from cache."""
        cache_file = self.cache_dir / "index.json"

        if not cache_file.exists():
            return False

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)

            # Reconstruct indexes
            for path, idx_data in data['file_index'].items():
                symbols = [
                    Symbol(**s) for s in idx_data['symbols']
                ]

                file_idx = FileIndex(
                    path=idx_data['path'],
                    hash=idx_data['hash'],
                    symbols=symbols,
                    imports=idx_data['imports'],
                    last_modified=idx_data['last_modified']
                )

                self.file_index[path] = file_idx

                # Rebuild symbol index
                for symbol in symbols:
                    self.symbol_index[symbol.name].append(symbol)

                # Rebuild import graph
                for imp in file_idx.imports:
                    self.import_graph[path].add(imp)

            return True

        except Exception:
            return False
