"""Refactoring Engine - Week 4 Day 2 - Boris Cherny"""
import ast, re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class RefactoringResult:
    success: bool
    message: str
    files_modified: List[Path]
    changes_preview: str
    error: Optional[str] = None

class RefactoringEngine:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    def rename_symbol(self, file_path: Path, old: str, new: str) -> RefactoringResult:
        try:
            content = file_path.read_text()
            count = len(re.findall(r'\b' + re.escape(old) + r'\b', content))
            new_content = re.sub(r'\b' + re.escape(old) + r'\b', new, content)
            file_path.write_text(new_content)
            return RefactoringResult(True, f"Renamed {count} occurrences", [file_path], f"{old}→{new}: {count}")
        except Exception as e:
            return RefactoringResult(False, "Failed", [], "", str(e))

    def organize_imports(self, file_path: Path) -> RefactoringResult:
        try:
            content = file_path.read_text()
            if not content.strip():
                return RefactoringResult(False, "Empty file", [], "", "Cannot organize imports in empty file")
            tree = ast.parse(content)
            imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
            other = [n for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom))]
            sorted_imp = sorted(imports, key=lambda n: ast.unparse(n))
            new_content = '\n'.join([ast.unparse(i) for i in sorted_imp] + ([''] if imports and other else []) + [ast.unparse(o) for o in other])
            file_path.write_text(new_content)
            return RefactoringResult(True, f"Organized {len(imports)} imports", [file_path], f"Sorted {len(imports)}")
        except Exception as e:
            return RefactoringResult(False, "Failed", [], "", str(e))
