"""
REAL INTEGRATION TEST - Context Suggestions.

Tests with actual project files to verify it WORKS.

Scientific Validation - Boris Cherny
"""

from pathlib import Path
from jdev_cli.intelligence.context_suggestions import ContextSuggestionEngine


class TestRealProjectIntegration:
    """Test with actual qwen-dev-cli codebase."""

    def test_suggest_for_shell_py(self):
        """Test suggestions on shell.py (our main file)."""
        project_root = Path(__file__).parent.parent.parent
        engine = ContextSuggestionEngine(project_root=project_root)

        shell_py = project_root / "jdev_cli" / "shell.py"
        assert shell_py.exists(), "shell.py not found"

        # Get recommendations
        recommendations = engine.suggest_related_files(shell_py, max_suggestions=10)

        # Validation
        assert len(recommendations) > 0, "No recommendations found"

        # Should suggest test file
        test_files = [r for r in recommendations if 'test' in str(r.file_path).lower()]
        print(f"Found {len(test_files)} test file recommendations")

        # Should suggest imported files
        import_recs = [r for r in recommendations if r.relationship_type == 'import']
        print(f"Found {len(import_recs)} import recommendations")
        assert len(import_recs) > 0, "Should suggest imported files"

        # Check relevance scores are valid
        for rec in recommendations:
            assert 0.0 <= rec.relevance_score <= 1.0, f"Invalid score: {rec.relevance_score}"
            assert rec.file_path.exists(), f"Recommended non-existent file: {rec.file_path}"

    def test_suggest_for_lsp_client(self):
        """Test suggestions on lsp_client.py."""
        project_root = Path(__file__).parent.parent.parent
        engine = ContextSuggestionEngine(project_root=project_root)

        lsp_client = project_root / "jdev_cli" / "intelligence" / "lsp_client.py"
        assert lsp_client.exists(), "lsp_client.py not found"

        recommendations = engine.suggest_related_files(lsp_client, max_suggestions=10)

        # Should suggest test file
        test_file_path = project_root / "tests" / "intelligence" / "test_lsp_client.py"
        if test_file_path.exists():
            test_recs = [r for r in recommendations if r.file_path == test_file_path]
            assert len(test_recs) > 0, "Should suggest its test file"

    def test_code_suggestions_on_real_file(self):
        """Test code suggestions on actual project file."""
        project_root = Path(__file__).parent.parent.parent
        engine = ContextSuggestionEngine(project_root=project_root)

        # Pick a file that might have issues
        shell_py = project_root / "jdev_cli" / "shell.py"

        suggestions = engine.suggest_edits(shell_py)

        # Validation (might be empty if code is clean)
        print(f"Found {len(suggestions)} code suggestions")

        for sug in suggestions[:3]:  # Check first 3
            assert sug.line_number > 0, "Invalid line number"
            assert sug.impact in ['high', 'medium', 'low'], f"Invalid impact: {sug.impact}"
            assert sug.category in ['refactor', 'bug', 'performance', 'style'], "Invalid category"
            print(f"  Line {sug.line_number}: {sug.suggestion}")

    def test_analyze_context_real_file(self):
        """Test context analysis on real Python file."""
        project_root = Path(__file__).parent.parent.parent
        engine = ContextSuggestionEngine(project_root=project_root)

        shell_py = project_root / "jdev_cli" / "shell.py"
        context = engine.analyze_file_context(shell_py)

        # Validate context structure
        assert 'language' in context, "Missing language"
        assert context['language'] == 'python', "Wrong language detected"
        assert 'imports' in context, "Missing imports"
        assert 'definitions' in context, "Missing definitions"

        # shell.py should have many imports
        assert len(context['imports']) > 10, f"Too few imports: {len(context['imports'])}"

        # shell.py should have class definitions
        assert len(context['definitions']) > 0, "No definitions found"

        print(f"✓ Analyzed shell.py: {len(context['imports'])} imports, {len(context['definitions'])} definitions")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_file(self):
        """Test with non-existent file."""
        project_root = Path(__file__).parent.parent.parent
        engine = ContextSuggestionEngine(project_root=project_root)

        fake_file = project_root / "does_not_exist.py"
        recommendations = engine.suggest_related_files(fake_file)

        # Should return empty, not crash
        assert recommendations == []

    def test_binary_file(self):
        """Test with binary file (should not crash)."""
        project_root = Path(__file__).parent.parent.parent
        engine = ContextSuggestionEngine(project_root=project_root)

        # Try with pyproject.toml (not Python)
        toml_file = project_root / "pyproject.toml"
        if toml_file.exists():
            context = engine.analyze_file_context(toml_file)
            # Should fallback to text analysis
            assert 'language' in context

    def test_empty_file(self, tmp_path):
        """Test with empty file."""
        engine = ContextSuggestionEngine(project_root=tmp_path)

        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        context = engine.analyze_file_context(empty_file)
        assert context['import_count'] == 0
        assert context['definition_count'] == 0

    def test_syntax_error_file(self, tmp_path):
        """Test with file containing syntax errors."""
        engine = ContextSuggestionEngine(project_root=tmp_path)

        broken_file = tmp_path / "broken.py"
        broken_file.write_text("def broken(\n  # Missing closing paren")

        # Should fallback to text analysis, not crash
        context = engine.analyze_file_context(broken_file)
        assert 'language' in context  # Should still return something
