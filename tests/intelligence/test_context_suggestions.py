"""
Tests for Context Suggestions Engine.

Boris Cherny Implementation - Week 4 Day 1
"""

import pytest
from pathlib import Path
from qwen_dev_cli.intelligence.context_suggestions import (
    ContextSuggestionEngine,
    FileRecommendation,
    CodeSuggestion
)


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure."""
    # Main module
    (tmp_path / "myapp.py").write_text("""
import os
from pathlib import Path

def main():
    '''Main function.'''
    print("Hello, World!")

class MyClass:
    '''Sample class.'''
    pass
""")
    
    # Test file
    (tmp_path / "test_myapp.py").write_text("""
from myapp import main, MyClass

def test_main():
    main()
""")
    
    # Dependency
    (tmp_path / "utils.py").write_text("""
def helper():
    '''Helper function.'''
    pass
""")
    
    return tmp_path


class TestContextSuggestionEngine:
    """Test context suggestion engine."""
    
    def test_initialization(self, temp_project):
        """Test engine can be initialized."""
        engine = ContextSuggestionEngine(project_root=temp_project)
        
        assert engine.project_root == temp_project.resolve()
        assert engine.indexer is not None
    
    def test_analyze_python_context(self, temp_project):
        """Test Python file context analysis."""
        engine = ContextSuggestionEngine(project_root=temp_project)
        
        file_path = temp_project / "myapp.py"
        context = engine.analyze_file_context(file_path)
        
        assert context['language'] == 'python'
        assert context['import_count'] > 0
        assert context['definition_count'] == 2  # main + MyClass
    
    def test_suggest_test_file(self, temp_project):
        """Test finding related test file."""
        engine = ContextSuggestionEngine(project_root=temp_project)
        
        file_path = temp_project / "myapp.py"
        recommendations = engine.suggest_related_files(file_path)
        
        # Should suggest test_myapp.py
        test_recs = [r for r in recommendations if r.relationship_type == 'test']
        assert len(test_recs) > 0
        assert test_recs[0].file_path.name == 'test_myapp.py'
        assert test_recs[0].relevance_score >= 0.9
    
    def test_code_suggestions(self, temp_project):
        """Test code improvement suggestions."""
        # Create file with issues
        problem_file = temp_project / "problems.py"
        problem_file.write_text("""
# TODO: Fix this
def foo():
    try:
        x = 1
    except:  # Bare except!
        pass

# Very long line that exceeds 120 characters and should trigger a warning about line length issues in the code
""")
        
        engine = ContextSuggestionEngine(project_root=temp_project)
        suggestions = engine.suggest_edits(problem_file)
        
        assert len(suggestions) > 0
        
        # Should detect bare except
        bare_except = [s for s in suggestions if 'except' in s.suggestion.lower()]
        assert len(bare_except) > 0
        assert bare_except[0].impact == 'high'


class TestFileRecommendation:
    """Test FileRecommendation dataclass."""
    
    def test_recommendation_creation(self):
        """Test creating recommendation."""
        rec = FileRecommendation(
            file_path=Path("test.py"),
            reason="Test file",
            relevance_score=0.95,
            relationship_type="test"
        )
        
        assert rec.file_path == Path("test.py")
        assert rec.relevance_score == 0.95
        assert rec.relationship_type == "test"


class TestCodeSuggestion:
    """Test CodeSuggestion dataclass."""
    
    def test_suggestion_creation(self):
        """Test creating suggestion."""
        sug = CodeSuggestion(
            file_path=Path("test.py"),
            line_number=10,
            suggestion="Fix this",
            impact="high",
            category="bug"
        )
        
        assert sug.line_number == 10
        assert sug.impact == "high"
        assert sug.category == "bug"
