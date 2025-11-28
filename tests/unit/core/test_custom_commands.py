"""
Tests for CustomCommandsManager - Slash Command System
=======================================================

Comprehensive tests following Boris Cherny methodology:
- Unit tests for all public methods
- Edge cases and error handling
- Security tests (path traversal)
- Integration tests

Target: 95%+ coverage
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from jdev_tui.core.custom_commands import CustomCommandsManager


class TestCustomCommandsManagerInit:
    """Test initialization and configuration."""

    def test_init_default_paths(self):
        """Test default path configuration."""
        manager = CustomCommandsManager()

        assert manager._project_dir is None
        assert manager._global_dir == Path.home() / ".juancs" / "commands"
        assert manager._commands == {}
        assert manager._loaded is False

    def test_init_custom_paths(self, tmp_path):
        """Test custom path configuration."""
        project_dir = tmp_path / "project_commands"
        global_dir = tmp_path / "global_commands"

        manager = CustomCommandsManager(
            project_dir=project_dir,
            global_dir=global_dir
        )

        assert manager._project_dir == project_dir
        assert manager._global_dir == global_dir

    def test_get_project_commands_dir_with_custom(self, tmp_path):
        """Test project commands dir with custom path."""
        project_dir = tmp_path / "custom"
        manager = CustomCommandsManager(project_dir=project_dir)

        assert manager._get_project_commands_dir() == project_dir

    def test_get_project_commands_dir_default(self):
        """Test project commands dir with default (cwd)."""
        manager = CustomCommandsManager()

        expected = Path.cwd() / ".juancs" / "commands"
        assert manager._get_project_commands_dir() == expected

    def test_get_global_commands_dir(self, tmp_path):
        """Test global commands dir getter."""
        global_dir = tmp_path / "global"
        manager = CustomCommandsManager(global_dir=global_dir)

        assert manager._get_global_commands_dir() == global_dir

    def test_get_commands_dir_prefers_project(self, tmp_path):
        """Test that project dir takes priority when it exists."""
        project_dir = tmp_path / "project"
        global_dir = tmp_path / "global"
        project_dir.mkdir(parents=True)

        manager = CustomCommandsManager(
            project_dir=project_dir,
            global_dir=global_dir
        )

        assert manager._get_commands_dir() == project_dir

    def test_get_commands_dir_falls_back_to_global(self, tmp_path):
        """Test fallback to global when project doesn't exist."""
        project_dir = tmp_path / "project"  # Not created
        global_dir = tmp_path / "global"

        manager = CustomCommandsManager(
            project_dir=project_dir,
            global_dir=global_dir
        )

        assert manager._get_commands_dir() == global_dir


class TestLoadCommands:
    """Test command loading functionality."""

    def test_load_commands_empty_directory(self, tmp_path):
        """Test loading from empty directory."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert commands == {}
        assert manager._loaded is True

    def test_load_commands_nonexistent_directory(self, tmp_path):
        """Test loading from non-existent directories."""
        manager = CustomCommandsManager(
            project_dir=tmp_path / "nonexistent_project",
            global_dir=tmp_path / "nonexistent_global"
        )

        commands = manager.load_commands()
        assert commands == {}

    def test_load_single_command(self, tmp_path):
        """Test loading a single command file."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        # Create command file
        (commands_dir / "review.md").write_text("Review this code: $ARGUMENTS")

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert "review" in commands
        assert commands["review"]["name"] == "review"
        assert commands["review"]["prompt"] == "Review this code: $ARGUMENTS"
        assert commands["review"]["type"] == "project"

    def test_load_multiple_commands(self, tmp_path):
        """Test loading multiple command files."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        (commands_dir / "review.md").write_text("Review code")
        (commands_dir / "test.md").write_text("Run tests")
        (commands_dir / "deploy.md").write_text("Deploy app")

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert len(commands) == 3
        assert "review" in commands
        assert "test" in commands
        assert "deploy" in commands

    def test_load_commands_with_description_header(self, tmp_path):
        """Test extraction of description from markdown header."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        content = "# Code Review Helper\n\nReview this code: $ARGUMENTS"
        (commands_dir / "review.md").write_text(content)

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert commands["review"]["description"] == "Code Review Helper"

    def test_load_commands_with_html_comment_description(self, tmp_path):
        """Test extraction of description from HTML comment."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        content = "<!-- Deployment automation -->\nDeploy the app"
        (commands_dir / "deploy.md").write_text(content)

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert commands["deploy"]["description"] == "Deployment automation"

    def test_load_commands_no_description(self, tmp_path):
        """Test default description when none provided."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        (commands_dir / "simple.md").write_text("Just a simple command")

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert commands["simple"]["description"] == "Custom command: simple"

    def test_load_commands_caching(self, tmp_path):
        """Test that commands are cached after first load."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text("Test command")

        manager = CustomCommandsManager(project_dir=commands_dir)

        # First load
        commands1 = manager.load_commands()
        assert len(commands1) == 1

        # Add another file
        (commands_dir / "new.md").write_text("New command")

        # Second load should return cached
        commands2 = manager.load_commands()
        assert len(commands2) == 1  # Still 1 because cached

    def test_load_commands_force_reload(self, tmp_path):
        """Test force reload bypasses cache."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text("Test command")

        manager = CustomCommandsManager(project_dir=commands_dir)

        # First load
        commands1 = manager.load_commands()
        assert len(commands1) == 1

        # Add another file
        (commands_dir / "new.md").write_text("New command")

        # Force reload
        commands2 = manager.load_commands(force_reload=True)
        assert len(commands2) == 2

    def test_load_commands_project_priority_over_global(self, tmp_path):
        """Test that project commands take priority over global."""
        project_dir = tmp_path / "project"
        global_dir = tmp_path / "global"
        project_dir.mkdir()
        global_dir.mkdir()

        # Same command name in both
        (project_dir / "review.md").write_text("Project review")
        (global_dir / "review.md").write_text("Global review")
        (global_dir / "deploy.md").write_text("Global deploy")

        manager = CustomCommandsManager(
            project_dir=project_dir,
            global_dir=global_dir
        )
        commands = manager.load_commands()

        # Project version should win
        assert commands["review"]["prompt"] == "Project review"
        assert commands["review"]["type"] == "project"

        # Global-only command should be loaded
        assert commands["deploy"]["prompt"] == "Global deploy"
        assert commands["deploy"]["type"] == "global"

    def test_load_commands_skips_non_md_files(self, tmp_path):
        """Test that only .md files are loaded."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        (commands_dir / "valid.md").write_text("Valid command")
        (commands_dir / "invalid.txt").write_text("Invalid file")
        (commands_dir / "also_invalid.json").write_text("{}")

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert len(commands) == 1
        assert "valid" in commands

    def test_load_commands_handles_read_error(self, tmp_path):
        """Test graceful handling of file read errors."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        (commands_dir / "good.md").write_text("Good command")

        manager = CustomCommandsManager(project_dir=commands_dir)

        # Create a file that will fail to read
        bad_file = commands_dir / "bad.md"
        bad_file.write_text("Bad command")

        with patch.object(Path, 'read_text', side_effect=[
            "Good command",  # First file works
            IOError("Permission denied")  # Second file fails
        ]):
            # Should not raise, just skip bad file
            commands = manager.load_commands(force_reload=True)


class TestExtractDescription:
    """Test description extraction from content."""

    def test_extract_markdown_heading(self):
        """Test extraction from markdown heading."""
        manager = CustomCommandsManager()

        content = "# My Command Description\n\nCommand content here"
        assert manager._extract_description(content) == "My Command Description"

    def test_extract_multiple_hash_heading(self):
        """Test extraction from ## or ### headings."""
        manager = CustomCommandsManager()

        content = "## Secondary Heading\n\nContent"
        assert manager._extract_description(content) == "Secondary Heading"

    def test_extract_html_comment(self):
        """Test extraction from HTML comment."""
        manager = CustomCommandsManager()

        content = "<!-- Command for testing -->\n\nContent"
        assert manager._extract_description(content) == "Command for testing"

    def test_extract_no_description(self):
        """Test empty result when no description marker."""
        manager = CustomCommandsManager()

        content = "Just plain content without description"
        assert manager._extract_description(content) == ""

    def test_extract_empty_content(self):
        """Test empty result for empty content."""
        manager = CustomCommandsManager()

        assert manager._extract_description("") == ""
        assert manager._extract_description("   ") == ""


class TestGetCommands:
    """Test get_commands and get_command methods."""

    def test_get_commands_triggers_load(self, tmp_path):
        """Test that get_commands triggers load if not loaded."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text("Test")

        manager = CustomCommandsManager(project_dir=commands_dir)
        assert manager._loaded is False

        commands = manager.get_commands()

        assert manager._loaded is True
        assert "test" in commands

    def test_get_command_existing(self, tmp_path):
        """Test getting an existing command."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "review.md").write_text("# Code Review\n\nReview $ARGUMENTS")

        manager = CustomCommandsManager(project_dir=commands_dir)
        command = manager.get_command("review")

        assert command is not None
        assert command["name"] == "review"
        assert command["description"] == "Code Review"

    def test_get_command_nonexistent(self, tmp_path):
        """Test getting a non-existent command."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        manager = CustomCommandsManager(project_dir=commands_dir)
        command = manager.get_command("nonexistent")

        assert command is None


class TestExecuteCommand:
    """Test command execution and argument substitution."""

    def test_execute_basic(self, tmp_path):
        """Test basic command execution."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "hello.md").write_text("Hello, world!")

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.execute_command("hello")

        assert result == "Hello, world!"

    def test_execute_with_arguments_substitution(self, tmp_path):
        """Test $ARGUMENTS substitution."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "review.md").write_text("Review this file: $ARGUMENTS")

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.execute_command("review", "main.py")

        assert result == "Review this file: main.py"

    def test_execute_with_args_braces_substitution(self, tmp_path):
        """Test {args} substitution."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text("Run tests for: {args}")

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.execute_command("test", "unit integration")

        assert result == "Run tests for: unit integration"

    def test_execute_with_positional_args(self, tmp_path):
        """Test $1, $2, etc. positional argument substitution."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "compare.md").write_text("Compare $1 with $2")

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.execute_command("compare", "file1.py file2.py")

        assert result == "Compare file1.py with file2.py"

    def test_execute_with_mixed_substitutions(self, tmp_path):
        """Test multiple substitution types together."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        content = "Full: $ARGUMENTS | First: $1 | Second: $2 | Alt: {args}"
        (commands_dir / "multi.md").write_text(content)

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.execute_command("multi", "foo bar")

        assert result == "Full: foo bar | First: foo | Second: bar | Alt: foo bar"

    def test_execute_nonexistent_command(self, tmp_path):
        """Test executing non-existent command returns None."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.execute_command("nonexistent")

        assert result is None

    def test_execute_no_args_keeps_placeholders(self, tmp_path):
        """Test that placeholders remain if no args provided."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text("Value: $ARGUMENTS")

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.execute_command("test", "")

        # No substitution when args is empty
        assert result == "Value: $ARGUMENTS"


class TestSanitizeCommandName:
    """Test command name sanitization for security."""

    def test_sanitize_valid_name(self):
        """Test valid names pass through."""
        manager = CustomCommandsManager()

        assert manager._sanitize_command_name("review") == "review"
        assert manager._sanitize_command_name("code_review") == "code_review"
        assert manager._sanitize_command_name("code-review") == "code-review"
        assert manager._sanitize_command_name("Review123") == "Review123"

    def test_sanitize_removes_special_chars(self):
        """Test special characters are removed."""
        manager = CustomCommandsManager()

        assert manager._sanitize_command_name("review!@#$%") == "review"
        assert manager._sanitize_command_name("code.review") == "codereview"
        assert manager._sanitize_command_name("test/cmd") == "testcmd"

    def test_sanitize_path_traversal_attempt(self):
        """Test path traversal attempts are sanitized."""
        manager = CustomCommandsManager()

        # Path traversal attempts should be sanitized
        assert manager._sanitize_command_name("../../../etc/passwd") == "etcpasswd"
        assert manager._sanitize_command_name("..\\..\\secrets") == "secrets"

    def test_sanitize_empty_becomes_unnamed(self):
        """Test empty name becomes 'unnamed_command'."""
        manager = CustomCommandsManager()

        assert manager._sanitize_command_name("") == "unnamed_command"
        assert manager._sanitize_command_name("!@#$%") == "unnamed_command"

    def test_sanitize_truncates_long_names(self):
        """Test names are truncated to 50 chars."""
        manager = CustomCommandsManager()

        long_name = "a" * 100
        result = manager._sanitize_command_name(long_name)

        assert len(result) == 50
        assert result == "a" * 50


class TestCreateCommand:
    """Test command creation."""

    def test_create_basic_command(self, tmp_path):
        """Test creating a basic command."""
        commands_dir = tmp_path / "commands"

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.create_command("test", "Test prompt")

        assert result["name"] == "test"
        assert result["prompt"] == "Test prompt"
        assert result["type"] == "project"

        # Verify file was created
        assert (commands_dir / "test.md").exists()

    def test_create_command_with_description(self, tmp_path):
        """Test creating command with description."""
        commands_dir = tmp_path / "commands"

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.create_command(
            "review",
            "Review the code",
            description="Code Review Helper"
        )

        assert result["description"] == "Code Review Helper"

        # Verify file content has description header
        content = (commands_dir / "review.md").read_text()
        assert content.startswith("# Code Review Helper")

    def test_create_global_command(self, tmp_path):
        """Test creating a global scope command."""
        global_dir = tmp_path / "global"

        manager = CustomCommandsManager(
            project_dir=tmp_path / "project",
            global_dir=global_dir
        )
        result = manager.create_command("test", "Test", scope="global")

        assert result["type"] == "global"
        assert (global_dir / "test.md").exists()

    def test_create_command_sanitizes_name(self, tmp_path):
        """Test that command name is sanitized."""
        commands_dir = tmp_path / "commands"

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.create_command("test!@#$%", "Test prompt")

        assert result["name"] == "test"
        assert (commands_dir / "test.md").exists()

    def test_create_command_updates_cache(self, tmp_path):
        """Test that cache is updated after creation."""
        commands_dir = tmp_path / "commands"

        manager = CustomCommandsManager(project_dir=commands_dir)
        manager.create_command("new_cmd", "New command")

        # Should be in cache without needing reload
        assert "new_cmd" in manager._commands
        assert manager.get_command("new_cmd") is not None

    def test_create_command_creates_directory(self, tmp_path):
        """Test that directory is created if needed."""
        commands_dir = tmp_path / "nested" / "commands"

        manager = CustomCommandsManager(project_dir=commands_dir)
        manager.create_command("test", "Test")

        assert commands_dir.exists()
        assert (commands_dir / "test.md").exists()

    def test_create_command_path_traversal_raises(self, tmp_path):
        """Test that path traversal in name raises ValueError."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        manager = CustomCommandsManager(project_dir=commands_dir)

        # The sanitize function will clean this, but we test the security check
        # by mocking to bypass sanitization
        with patch.object(manager, '_sanitize_command_name', return_value="../../../etc/passwd"):
            with pytest.raises(ValueError, match="path traversal"):
                manager.create_command("malicious", "Evil content")


class TestDeleteCommand:
    """Test command deletion."""

    def test_delete_existing_command(self, tmp_path):
        """Test deleting an existing command."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text("Test")

        manager = CustomCommandsManager(project_dir=commands_dir)
        manager.load_commands()

        result = manager.delete_command("test")

        assert result is True
        assert not (commands_dir / "test.md").exists()
        assert "test" not in manager._commands

    def test_delete_nonexistent_command(self, tmp_path):
        """Test deleting non-existent command returns False."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.delete_command("nonexistent")

        assert result is False

    def test_delete_handles_file_error(self, tmp_path):
        """Test graceful handling of file deletion error."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text("Test")

        manager = CustomCommandsManager(project_dir=commands_dir)
        manager.load_commands()

        with patch.object(Path, 'unlink', side_effect=PermissionError("Denied")):
            result = manager.delete_command("test")
            assert result is False


class TestRefreshAndList:
    """Test refresh and list methods."""

    def test_refresh_clears_and_reloads(self, tmp_path):
        """Test refresh clears cache and reloads."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text("Test")

        manager = CustomCommandsManager(project_dir=commands_dir)
        manager.load_commands()

        # Add new file
        (commands_dir / "new.md").write_text("New")

        # Refresh should pick up new file
        commands = manager.refresh()

        assert len(commands) == 2
        assert "new" in commands

    def test_list_commands(self, tmp_path):
        """Test listing commands as list of dicts."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "a.md").write_text("A")
        (commands_dir / "b.md").write_text("B")

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.list_commands()

        assert isinstance(result, list)
        assert len(result) == 2

        names = [c["name"] for c in result]
        assert "a" in names
        assert "b" in names

    def test_command_exists_true(self, tmp_path):
        """Test command_exists returns True for existing."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text("Test")

        manager = CustomCommandsManager(project_dir=commands_dir)

        assert manager.command_exists("test") is True

    def test_command_exists_false(self, tmp_path):
        """Test command_exists returns False for non-existing."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        manager = CustomCommandsManager(project_dir=commands_dir)

        assert manager.command_exists("nonexistent") is False

    def test_get_command_names(self, tmp_path):
        """Test getting list of command names."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "alpha.md").write_text("A")
        (commands_dir / "beta.md").write_text("B")

        manager = CustomCommandsManager(project_dir=commands_dir)
        names = manager.get_command_names()

        assert isinstance(names, list)
        assert "alpha" in names
        assert "beta" in names


class TestGetStats:
    """Test statistics gathering."""

    def test_get_stats_empty(self, tmp_path):
        """Test stats with no commands."""
        manager = CustomCommandsManager(
            project_dir=tmp_path / "project",
            global_dir=tmp_path / "global"
        )

        stats = manager.get_stats()

        assert stats["total_commands"] == 0
        assert stats["project_commands"] == 0
        assert stats["global_commands"] == 0
        assert stats["loaded"] is True  # load_commands was called

    def test_get_stats_with_commands(self, tmp_path):
        """Test stats with mixed commands."""
        project_dir = tmp_path / "project"
        global_dir = tmp_path / "global"
        project_dir.mkdir()
        global_dir.mkdir()

        (project_dir / "p1.md").write_text("P1")
        (project_dir / "p2.md").write_text("P2")
        (global_dir / "g1.md").write_text("G1")

        manager = CustomCommandsManager(
            project_dir=project_dir,
            global_dir=global_dir
        )

        stats = manager.get_stats()

        assert stats["total_commands"] == 3
        assert stats["project_commands"] == 2
        assert stats["global_commands"] == 1
        assert str(project_dir) in stats["project_dir"]
        assert str(global_dir) in stats["global_dir"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unicode_in_command_content(self, tmp_path):
        """Test handling of unicode content."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        content = "# Revisão de Código 🔍\n\nRevisando: $ARGUMENTS"
        (commands_dir / "revisar.md").write_text(content, encoding="utf-8")

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert "revisar" in commands
        assert "Revisão de Código 🔍" in commands["revisar"]["description"]

    def test_multiline_command_content(self, tmp_path):
        """Test multiline command content."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        content = """# Multi-step Review

1. Check syntax: $1
2. Review logic
3. Test coverage for $ARGUMENTS
4. Final approval
"""
        (commands_dir / "full_review.md").write_text(content)

        manager = CustomCommandsManager(project_dir=commands_dir)
        result = manager.execute_command("full_review", "main.py tests/")

        assert "1. Check syntax: main.py" in result
        assert "3. Test coverage for main.py tests/" in result

    def test_empty_command_file(self, tmp_path):
        """Test handling of empty command file."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "empty.md").write_text("")

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert "empty" in commands
        assert commands["empty"]["prompt"] == ""

    def test_command_with_only_whitespace(self, tmp_path):
        """Test handling of whitespace-only content."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "spaces.md").write_text("   \n\n   ")

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert "spaces" in commands

    def test_special_filenames(self, tmp_path):
        """Test handling of special but valid filenames."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        (commands_dir / "123-numbers.md").write_text("Numbers")
        (commands_dir / "_underscore_start.md").write_text("Underscore")
        (commands_dir / "UPPERCASE.md").write_text("Upper")

        manager = CustomCommandsManager(project_dir=commands_dir)
        commands = manager.load_commands()

        assert "123-numbers" in commands
        assert "_underscore_start" in commands
        assert "UPPERCASE" in commands


class TestIntegration:
    """Integration tests for full workflows."""

    def test_full_workflow_create_execute_delete(self, tmp_path):
        """Test complete workflow: create, execute, delete."""
        commands_dir = tmp_path / "commands"

        manager = CustomCommandsManager(project_dir=commands_dir)

        # Create (without description to keep prompt clean)
        manager.create_command(
            "greet",
            "Hello, $ARGUMENTS! Welcome."
        )

        # Verify creation
        assert manager.command_exists("greet")
        assert (commands_dir / "greet.md").exists()

        # Execute
        result = manager.execute_command("greet", "World")
        assert result == "Hello, World! Welcome."

        # Delete
        assert manager.delete_command("greet")
        assert not manager.command_exists("greet")
        assert not (commands_dir / "greet.md").exists()

    def test_project_overrides_global(self, tmp_path):
        """Test project commands override global commands."""
        project_dir = tmp_path / "project"
        global_dir = tmp_path / "global"
        project_dir.mkdir()
        global_dir.mkdir()

        # Same command in both
        (global_dir / "status.md").write_text("Global: git status")
        (project_dir / "status.md").write_text("Project: npm status")

        manager = CustomCommandsManager(
            project_dir=project_dir,
            global_dir=global_dir
        )

        result = manager.execute_command("status")
        assert result == "Project: npm status"

    def test_refresh_picks_up_external_changes(self, tmp_path):
        """Test refresh picks up external file changes."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()

        manager = CustomCommandsManager(project_dir=commands_dir)

        # Initial load
        commands = manager.load_commands()
        assert len(commands) == 0

        # External change (simulating another process)
        (commands_dir / "external.md").write_text("Added externally")

        # Normal get won't see it
        assert "external" not in manager.get_commands()

        # Refresh will
        manager.refresh()
        assert "external" in manager.get_commands()
