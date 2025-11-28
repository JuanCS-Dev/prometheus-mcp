"""
Context-Aware Suggestions Engine.

Analyzes current context and suggests related files, potential edits,
and optimization opportunities.

Boris Cherny Implementation - Week 4 Day 1
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..intelligence.indexer import SemanticIndexer


@dataclass
class FileRecommendation:
    """Recommendation for a related file."""
    file_path: Path
    reason: str
    relevance_score: float
    relationship_type: str  # 'import', 'test', 'dependency', 'similar'


@dataclass
class CodeSuggestion:
    """Suggestion for code modification."""
    file_path: Path
    line_number: int
    suggestion: str
    impact: str  # 'high', 'medium', 'low'
    category: str  # 'refactor', 'bug', 'performance', 'style'


class ContextSuggestionEngine:
    """
    Analyzes code context and provides intelligent suggestions.
    
    Features:
    - Smart file recommendations
    - Cross-file dependency detection
    - Impact analysis
    - Related code suggestions
    """

    def __init__(self, project_root: Path, indexer: Optional[SemanticIndexer] = None):
        """Initialize context suggestion engine."""
        self.project_root = Path(project_root).resolve() if isinstance(project_root, str) else project_root.resolve()
        self.indexer = indexer or SemanticIndexer(project_root)

    def analyze_file_context(self, file_path: Path) -> Dict[str, any]:
        """
        Analyze a file's context.
        
        Args:
            file_path: File to analyze
            
        Returns:
            Context analysis dict with imports, definitions, etc.
        """
        if not file_path.exists():
            return {}

        try:
            content = file_path.read_text()

            # Python AST analysis
            if file_path.suffix == '.py':
                return self._analyze_python_context(content, file_path)

            # Fallback: text-based analysis
            return self._analyze_text_context(content, file_path)

        except Exception as e:
            return {'error': str(e)}

    def _analyze_python_context(self, content: str, file_path: Path) -> Dict[str, any]:
        """Analyze Python file using AST."""
        try:
            tree = ast.parse(content)

            imports = []
            definitions = []

            for node in ast.walk(tree):
                # Imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'name': alias.name,
                            'type': 'import',
                            'line': node.lineno
                        })

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    # Mark relative imports
                    is_relative = node.level > 0
                    relative_prefix = '.' * node.level if is_relative else ''

                    for alias in node.names:
                        full_name = f"{relative_prefix}{module}.{alias.name}" if module else f"{relative_prefix}{alias.name}"
                        imports.append({
                            'name': full_name,
                            'type': 'from_import',
                            'line': node.lineno,
                            'module': module,
                            'relative': is_relative
                        })

                # Definitions
                elif isinstance(node, ast.FunctionDef):
                    definitions.append({
                        'name': node.name,
                        'type': 'function',
                        'line': node.lineno
                    })

                elif isinstance(node, ast.ClassDef):
                    definitions.append({
                        'name': node.name,
                        'type': 'class',
                        'line': node.lineno
                    })

            return {
                'file_path': file_path,
                'language': 'python',
                'imports': imports,
                'definitions': definitions,
                'import_count': len(imports),
                'definition_count': len(definitions)
            }

        except SyntaxError:
            return self._analyze_text_context(content, file_path)

    def _analyze_text_context(self, content: str, file_path: Path) -> Dict[str, any]:
        """Fallback text-based analysis."""
        # Simple pattern matching
        imports = re.findall(r'^(?:from|import)\s+(\S+)', content, re.MULTILINE)
        functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)

        return {
            'file_path': file_path,
            'language': 'text',
            'imports': [{'name': imp, 'type': 'detected'} for imp in imports],
            'functions': functions,
            'classes': classes
        }

    def suggest_related_files(
        self,
        file_path: Path,
        max_suggestions: int = 10
    ) -> List[FileRecommendation]:
        """
        Suggest files related to the given file.
        
        Args:
            file_path: Current file
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of file recommendations
        """
        recommendations = []
        context = self.analyze_file_context(file_path)

        if not context or 'error' in context:
            return []

        # 1. Imported files (only internal project imports)
        for imp in context.get('imports', []):
            # Skip stdlib and external packages
            import_name = imp['name']
            if self._is_internal_import(import_name):
                imported_file = self._resolve_import(import_name, file_path)
                if imported_file and imported_file.exists():
                    recommendations.append(FileRecommendation(
                        file_path=imported_file,
                        reason=f"Imported as '{import_name}'",
                        relevance_score=0.9,
                        relationship_type='import'
                    ))

        # 2. Test files
        test_file = self._find_test_file(file_path)
        if test_file and test_file.exists():
            recommendations.append(FileRecommendation(
                file_path=test_file,
                reason="Test file for this module",
                relevance_score=0.95,
                relationship_type='test'
            ))

        # 3. Files that import this file
        importers = self._find_importers(file_path)
        for importer in importers[:3]:  # Top 3
            recommendations.append(FileRecommendation(
                file_path=importer,
                reason="Imports this file",
                relevance_score=0.8,
                relationship_type='dependency'
            ))

        # 4. Similar files (same directory, similar names)
        similar = self._find_similar_files(file_path)
        for similar_file in similar[:3]:
            recommendations.append(FileRecommendation(
                file_path=similar_file,
                reason="Similar file in same directory",
                relevance_score=0.6,
                relationship_type='similar'
            ))

        # Sort by relevance and deduplicate
        seen = set()
        unique_recommendations = []

        for rec in sorted(recommendations, key=lambda r: r.relevance_score, reverse=True):
            if rec.file_path not in seen:
                seen.add(rec.file_path)
                unique_recommendations.append(rec)

                if len(unique_recommendations) >= max_suggestions:
                    break

        return unique_recommendations

    def _is_internal_import(self, import_name: str) -> bool:
        """Check if import is internal to project."""
        # Relative imports are always internal
        if import_name.startswith('.'):
            return True

        # Check if starts with known project modules
        first_part = import_name.split('.')[0]

        # Common stdlib modules to skip
        stdlib_modules = {
            'os', 'sys', 'time', 'json', 'asyncio', 'pathlib', 'typing',
            'dataclasses', 'enum', 're', 'logging', 'datetime', 'collections',
            'functools', 'itertools', 'subprocess', 'shutil', 'tempfile',
            'argparse', 'configparser', 'io', 'abc', 'contextlib'
        }

        if first_part in stdlib_modules:
            return False

        # Common third-party packages to skip
        third_party = {
            'rich', 'pytest', 'prompt_toolkit', 'google', 'openai',
            'huggingface_hub', 'docker', 'httpx', 'pydantic', 'fastapi',
            'gradio', 'typer', 'click', 'requests', 'numpy', 'pandas'
        }

        if first_part in third_party:
            return False

        # If it starts with project name, it's internal
        project_modules = {'jdev_cli', 'tests'}
        if first_part in project_modules:
            return True

        # Check if file exists in project
        parts = import_name.split('.')
        candidate = self.project_root / Path('/'.join(parts)).with_suffix('.py')
        return candidate.exists()

    def _resolve_import(self, import_name: str, current_file: Path) -> Optional[Path]:
        """Resolve import to file path."""
        # Handle relative imports
        if import_name.startswith('.'):
            base_dir = current_file.parent
            # Strip leading dots and last component (which is the symbol name)
            parts = import_name.lstrip('.').split('.')

            if len(parts) > 1:
                # e.g., .core.context.ContextBuilder -> try core/context.py
                module_parts = parts[:-1]  # All but last
                candidate = base_dir / Path('/'.join(module_parts)).with_suffix('.py')
                if candidate.exists():
                    return candidate

                # Try as package
                candidate = base_dir / '/'.join(module_parts) / '__init__.py'
                if candidate.exists():
                    return candidate

            return None

        # Handle absolute imports (simplified)
        parts = import_name.split('.')

        # Try as file
        candidate = self.project_root / Path('/'.join(parts)).with_suffix('.py')
        if candidate.exists():
            return candidate

        # Try as package
        candidate = self.project_root / '/'.join(parts) / '__init__.py'
        if candidate.exists():
            return candidate

        return None

    def _find_test_file(self, file_path: Path) -> Optional[Path]:
        """Find corresponding test file."""
        # Pattern: file.py -> test_file.py or file_test.py

        # Same directory
        test_file = file_path.parent / f"test_{file_path.name}"
        if test_file.exists():
            return test_file

        test_file = file_path.parent / f"{file_path.stem}_test.py"
        if test_file.exists():
            return test_file

        # tests/ directory
        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            relative = file_path.relative_to(self.project_root)
            test_file = tests_dir / f"test_{relative}"
            if test_file.exists():
                return test_file

        return None

    def _find_importers(self, file_path: Path) -> List[Path]:
        """Find files that import the given file."""
        importers = []

        # Get module name
        try:
            relative = file_path.relative_to(self.project_root)
            module_name = str(relative.with_suffix('')).replace('/', '.')
        except ValueError:
            return []

        # Search for imports
        for py_file in self.project_root.rglob('*.py'):
            if py_file == file_path:
                continue

            try:
                content = py_file.read_text()
                if module_name in content:
                    # Verify it's an actual import
                    if re.search(rf'\b(?:from|import)\s+.*{re.escape(module_name)}', content):
                        importers.append(py_file)
            except Exception:
                continue

        return importers

    def _find_similar_files(self, file_path: Path) -> List[Path]:
        """Find similar files."""
        similar = []
        directory = file_path.parent
        stem = file_path.stem

        # Files in same directory with similar names
        for sibling in directory.glob('*.py'):
            if sibling == file_path:
                continue

            # Calculate name similarity (simple)
            sibling_stem = sibling.stem
            common = len(set(stem.split('_')) & set(sibling_stem.split('_')))

            if common > 0:
                similar.append(sibling)

        return similar

    def suggest_edits(self, file_path: Path) -> List[CodeSuggestion]:
        """
        Suggest potential code improvements.
        
        Args:
            file_path: File to analyze
            
        Returns:
            List of code suggestions
        """
        suggestions = []

        if not file_path.exists():
            return suggestions

        try:
            content = file_path.read_text()
            lines = content.split('\n')

            # Simple heuristics
            for i, line in enumerate(lines, 1):
                # Long lines
                if len(line) > 120:
                    suggestions.append(CodeSuggestion(
                        file_path=file_path,
                        line_number=i,
                        suggestion="Consider breaking this line (>120 chars)",
                        impact='low',
                        category='style'
                    ))

                # TODO/FIXME comments
                if 'TODO' in line or 'FIXME' in line:
                    suggestions.append(CodeSuggestion(
                        file_path=file_path,
                        line_number=i,
                        suggestion="Address this TODO/FIXME",
                        impact='medium',
                        category='refactor'
                    ))

                # Bare except
                if re.search(r'except\s*:', line):
                    suggestions.append(CodeSuggestion(
                        file_path=file_path,
                        line_number=i,
                        suggestion="Avoid bare except, specify exception type",
                        impact='high',
                        category='bug'
                    ))

        except Exception:
            pass

        return suggestions
