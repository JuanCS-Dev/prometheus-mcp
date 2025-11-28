"""Tests for Refactoring Engine - Week 4 Day 2"""
from jdev_cli.refactoring.engine import RefactoringEngine

def test_rename(tmp_path):
    file = tmp_path / "test.py"
    file.write_text("old_name = 1\nprint(old_name)")
    engine = RefactoringEngine(tmp_path)
    result = engine.rename_symbol(file, "old_name", "new_name")
    assert result.success
    assert "new_name" in file.read_text()

def test_organize_imports(tmp_path):
    file = tmp_path / "test.py"
    file.write_text("import sys\nimport os\nprint(1)")
    engine = RefactoringEngine(tmp_path)
    result = engine.organize_imports(file)
    assert result.success
