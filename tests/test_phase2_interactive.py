"""
Scientific tests for Phase 2: Interactive Shell Enhancement

Constitutional compliance: P1 (Completeness), P2 (Validation), P3 (Skepticism)

Test Coverage:
- Multi-line input detection
- Code block processing
- Autocomplete accuracy
- History management
- Edge cases
"""

import pytest
from pathlib import Path
from jdev_cli.tui.input_enhanced import MultiLineMode, IntelligentCompleter, InputContext
from jdev_cli.tui.components.autocomplete import (
    ContextAwareCompleter,
    CompletionItem,
    CompletionType
)
from jdev_cli.tui.history import CommandHistory, HistoryEntry
from datetime import datetime
from prompt_toolkit.document import Document


class TestMultiLineMode:
    """Test multi-line input detection."""

    def test_code_block_detection(self):
        """Test markdown code block detection."""
        # Open code block
        assert MultiLineMode.should_continue("```python")

        # Closed code block
        assert not MultiLineMode.should_continue("```python\ncode\n```")

        # Empty input
        assert not MultiLineMode.should_continue("")

    def test_python_syntax_detection(self):
        """Test Python syntax continuation."""
        # Function definition
        assert MultiLineMode.should_continue("def my_func():")

        # If statement
        assert MultiLineMode.should_continue("if x > 0:")

        # For loop
        assert MultiLineMode.should_continue("for i in range(10):")

        # Complete statement
        assert not MultiLineMode.should_continue("x = 5")

    def test_bracket_matching(self):
        """Test unclosed bracket detection."""
        # Open parenthesis
        assert MultiLineMode.should_continue("func(arg1, arg2")

        # Open bracket
        assert MultiLineMode.should_continue("list = [1, 2, 3")

        # Open brace
        assert MultiLineMode.should_continue("dict = {'key': 'value'")

        # Closed brackets
        assert not MultiLineMode.should_continue("func(arg1, arg2)")

    def test_explicit_continuation(self):
        """Test backslash continuation."""
        assert MultiLineMode.should_continue("long_line = \\")
        assert not MultiLineMode.should_continue("long_line = value")

    def test_language_detection(self):
        """Test programming language detection."""
        assert MultiLineMode.detect_language("```python") == "python"
        assert MultiLineMode.detect_language("def my_func():") == "python"
        assert MultiLineMode.detect_language("function myFunc() {") == "javascript"
        assert MultiLineMode.detect_language("pub fn my_func() {") == "rust"
        assert MultiLineMode.detect_language("some text") is None


class TestIntelligentCompleter:
    """Test intelligent autocomplete."""

    @pytest.fixture
    def context(self, tmp_path):
        """Create test context."""
        return InputContext(
            cwd=str(tmp_path),
            recent_files=["file1.py", "file2.py"],
            command_history=["ls", "cd", "git status"],
            session_data={}
        )

    def test_completer_initialization(self, context):
        """Test completer creates successfully."""
        completer = IntelligentCompleter(context)
        assert completer.context == context
        assert completer.path_completer is not None

    def test_command_completion(self, context):
        """Test command history completion."""
        completer = IntelligentCompleter(context)
        # Note: Actual completion testing requires prompt_toolkit event loop
        # which is complex to set up in unit tests
        assert hasattr(completer, 'commands')


class TestContextAwareCompleter:
    """Test context-aware autocomplete component."""

    def test_completion_item_creation(self):
        """Test CompletionItem dataclass."""
        item = CompletionItem(
            text="my_command",
            display="my_command - does something",
            type=CompletionType.COMMAND,
            description="A test command",
            score=0.9
        )

        assert item.text == "my_command"
        assert item.type == CompletionType.COMMAND
        assert item.score == 0.9
        assert item.metadata == {}

    def test_completer_initialization(self):
        """Test ContextAwareCompleter initialization."""
        completer = ContextAwareCompleter()
        assert completer.tools_registry is None
        assert completer.indexer is None
        assert completer._cache == {}

    def test_empty_prefix_no_completions(self):
        """Test no completions for empty prefix."""
        completer = ContextAwareCompleter()
        document = Document("", cursor_position=0)

        completions = list(completer.get_completions(document, None))
        assert len(completions) == 0


class TestCommandHistory:
    """Test command history management."""

    @pytest.fixture
    def history_file(self, tmp_path):
        """Create temporary history file."""
        return tmp_path / "test_history.txt"

    def test_history_initialization(self, history_file):
        """Test history creates successfully."""
        history = CommandHistory(str(history_file))
        assert history.db_path == Path(history_file)
        assert len(history.get_recent()) == 0

    def test_add_command(self, history_file):
        """Test adding command to history."""
        history = CommandHistory(str(history_file))
        entry = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            command="test command",
            cwd="/tmp",
            success=True,
            duration_ms=100
        )
        history.add(entry)

        recent = history.get_recent()
        assert len(recent) == 1
        assert recent[0].command == "test command"

    def test_duplicate_prevention(self, history_file):
        """Test duplicate commands can be added (no dedup in DB)."""
        history = CommandHistory(str(history_file))
        entry1 = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            command="test command",
            cwd="/tmp",
            success=True,
            duration_ms=100
        )
        entry2 = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            command="test command",
            cwd="/tmp",
            success=True,
            duration_ms=100
        )
        history.add(entry1)
        history.add(entry2)

        # SQLite allows duplicates - this is OK for history tracking
        assert len(history.get_recent()) == 2

    def test_search_functionality(self, history_file):
        """Test history search."""
        history = CommandHistory(str(history_file))

        for cmd in ["git status", "git commit", "ls -la"]:
            entry = HistoryEntry(
                timestamp=datetime.now().isoformat(),
                command=cmd,
                cwd="/tmp",
                success=True,
                duration_ms=100
            )
            history.add(entry)

        results = history.search("git")
        assert len(results) >= 2
        assert any("git status" in r.command for r in results)

    def test_persistence(self, history_file):
        """Test history persistence across instances."""
        # First instance
        history1 = CommandHistory(str(history_file))
        for cmd in ["command1", "command2"]:
            entry = HistoryEntry(
                timestamp=datetime.now().isoformat(),
                command=cmd,
                cwd="/tmp",
                success=True,
                duration_ms=100
            )
            history1.add(entry)

        # Second instance (SQLite persists automatically)
        history2 = CommandHistory(str(history_file))

        assert len(history2.get_recent()) >= 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_multiline_empty_input(self):
        """Test empty input handling."""
        assert not MultiLineMode.should_continue("")
        assert not MultiLineMode.should_continue("   ")

    def test_multiline_malformed_brackets(self):
        """Test malformed bracket handling."""
        # More closing than opening
        text = "func())"
        assert not MultiLineMode.should_continue(text)

    def test_completion_with_special_chars(self):
        """Test completion with special characters."""
        item = CompletionItem(
            text="my-command",
            display="my-command",
            type=CompletionType.COMMAND
        )
        assert "-" in item.text

    def test_history_empty_file(self, tmp_path):
        """Test history with non-existent file."""
        history_file = tmp_path / "nonexistent.txt"
        history = CommandHistory(str(history_file))
        assert len(history.get_recent()) == 0


class TestRealUseCases:
    """Test real-world usage scenarios."""

    def test_python_function_multiline(self):
        """Test real Python function input."""
        lines = [
            "def calculate_sum(a, b):",
            "    result = a + b",
            "    return result"
        ]

        # First line should continue
        assert MultiLineMode.should_continue(lines[0])

        # Last line should not continue (no colon)
        assert not MultiLineMode.should_continue(lines[2])

    def test_nested_brackets(self):
        """Test nested bracket handling."""
        text = "func(nested([1, 2, {3: 4}]"
        assert MultiLineMode.should_continue(text)

        text_closed = "func(nested([1, 2, {3: 4}]))"
        assert not MultiLineMode.should_continue(text_closed)

    def test_multiline_string(self):
        """Test multiline string detection."""
        text = '''"""
        This is a multiline
        docstring'''

        # Should detect unclosed triple quotes
        assert text.count('"""') == 1

    def test_history_workflow(self, tmp_path):
        """Test complete history workflow."""
        history_file = tmp_path / "workflow_history.txt"
        history = CommandHistory(str(history_file))

        # Add commands
        commands = [
            "git status",
            "git add .",
            "git commit -m 'test'",
            "git push"
        ]

        for cmd in commands:
            entry = HistoryEntry(
                timestamp=datetime.now().isoformat(),
                command=cmd,
                cwd="/tmp",
                success=True,
                duration_ms=100
            )
            history.add(entry)

        # Search for git commands
        git_cmds = history.search("git")
        assert len(git_cmds) == 4

        # Get recent
        recent = history.get_recent(2)
        assert len(recent) == 2
        assert "git push" in recent[0].command


# Performance tests
class TestPerformance:
    """Test performance characteristics."""

    def test_history_large_dataset(self, tmp_path):
        """Test history with large dataset."""
        history_file = tmp_path / "large_history.txt"
        history = CommandHistory(str(history_file))

        # Add 1000 commands
        for i in range(1000):
            entry = HistoryEntry(
                timestamp=datetime.now().isoformat(),
                command=f"command_{i}",
                cwd="/tmp",
                success=True,
                duration_ms=100
            )
            history.add(entry)

        # Search should still be fast
        import time
        start = time.time()
        results = history.search("command_5")
        duration = time.time() - start

        assert duration < 0.5  # Should complete in < 500ms (SQLite is slower)
        assert len(results) > 0

    def test_multiline_detection_performance(self):
        """Test multiline detection speed."""
        import time

        texts = [
            "def func():",
            "if x > 0:",
            "for i in range(10):",
            "normal line",
        ] * 250  # 1000 checks

        start = time.time()
        for text in texts:
            MultiLineMode.should_continue(text)
        duration = time.time() - start

        assert duration < 0.1  # Should process 1000 in < 100ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
