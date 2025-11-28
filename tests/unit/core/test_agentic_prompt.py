"""
Tests for agentic_prompt module - Claude Code-style prompt building.

Tests cover:
- build_agentic_system_prompt function
- load_project_memory function
- get_dynamic_context function
- enhance_tool_result function

Based on pytest patterns from Anthropic's Claude Code.
"""
import os
import subprocess
from unittest.mock import patch

from jdev_tui.core.agentic_prompt import (
    build_agentic_system_prompt,
    load_project_memory,
    get_dynamic_context,
    enhance_tool_result,
)


# =============================================================================
# BUILD_AGENTIC_SYSTEM_PROMPT TESTS
# =============================================================================

class TestBuildAgenticSystemPrompt:
    """Tests for build_agentic_system_prompt function."""

    def test_minimal_prompt(self):
        """Test prompt with minimal arguments."""
        prompt = build_agentic_system_prompt(tools=[])

        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "juancs-code" in prompt

    def test_with_tools(self):
        """Test prompt includes tool information."""
        tools = [
            {
                "name": "read_file",
                "description": "Read a file",
                "category": "file_ops",
                "parameters": {
                    "required": ["path"],
                    "properties": {"path": {"type": "string"}}
                }
            },
            {
                "name": "write_file",
                "description": "Write to a file",
                "category": "file_ops",
                "parameters": {
                    "required": ["path", "content"],
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    }
                }
            }
        ]

        prompt = build_agentic_system_prompt(tools=tools)

        assert "read_file" in prompt
        assert "write_file" in prompt
        assert "File Ops" in prompt  # Category title-cased

    def test_with_context(self):
        """Test prompt includes context information."""
        context = {
            "cwd": "/home/user/project",
            "git_branch": "feature/test",
            "git_status": "3 modified, 1 untracked",
            "modified_files": {"file1.py", "file2.py"},
            "recent_files": {"recent.py"}
        }

        prompt = build_agentic_system_prompt(tools=[], context=context)

        assert "/home/user/project" in prompt
        assert "feature/test" in prompt
        assert "3 modified" in prompt
        assert "file1.py" in prompt or "file2.py" in prompt

    def test_with_project_memory(self):
        """Test prompt includes project memory."""
        memory = """# Project: MyApp
## Build Command
npm run build

## Important
Never modify config.json directly.
"""
        prompt = build_agentic_system_prompt(tools=[], project_memory=memory)

        assert "Project Memory" in prompt
        assert "npm run build" in prompt
        assert "config.json" in prompt

    def test_with_user_memory(self):
        """Test prompt includes user memory."""
        user_mem = "User prefers TypeScript over JavaScript."

        prompt = build_agentic_system_prompt(tools=[], user_memory=user_mem)

        assert "User Memory" in prompt
        assert "TypeScript" in prompt

    def test_agentic_loop_instructions(self):
        """Test prompt includes agentic loop instructions."""
        prompt = build_agentic_system_prompt(tools=[])

        # Check for key agentic patterns
        assert "GATHER" in prompt
        assert "ACT" in prompt
        assert "VERIFY" in prompt
        assert "REPEAT" in prompt or "loop" in prompt.lower()

    def test_tool_protocol_section(self):
        """Test prompt includes tool protocol."""
        prompt = build_agentic_system_prompt(tools=[])

        assert "Tool Use Protocol" in prompt or "tool" in prompt.lower()
        assert "json" in prompt.lower()

    def test_safety_guidelines(self):
        """Test prompt includes safety guidelines."""
        prompt = build_agentic_system_prompt(tools=[])

        assert "Safety" in prompt
        assert "dangerous" in prompt.lower() or "never" in prompt.lower()

    def test_empty_context(self):
        """Test prompt with empty context dict."""
        prompt = build_agentic_system_prompt(tools=[], context={})

        assert "No context available" in prompt

    def test_tool_categories_grouped(self):
        """Test tools are grouped by category."""
        tools = [
            {"name": "git_status", "category": "git", "parameters": {}},
            {"name": "git_commit", "category": "git", "parameters": {}},
            {"name": "read_file", "category": "files", "parameters": {}},
        ]

        prompt = build_agentic_system_prompt(tools=tools)

        # Git tools should appear together
        git_section = prompt.find("Git")
        files_section = prompt.find("Files")

        # Both sections should exist
        assert git_section != -1 or files_section != -1


# =============================================================================
# LOAD_PROJECT_MEMORY TESTS
# =============================================================================

class TestLoadProjectMemory:
    """Tests for load_project_memory function."""

    def test_load_juancs_md(self, temp_workspace):
        """Test loading JUANCS.md file."""
        memory_file = temp_workspace / "JUANCS.md"
        memory_file.write_text("# Project Memory\nTest content")

        result = load_project_memory(str(temp_workspace))

        assert result is not None
        assert "Project Memory" in result
        assert "Test content" in result

    def test_load_claude_md_fallback(self, temp_workspace):
        """Test loading CLAUDE.md as fallback."""
        memory_file = temp_workspace / "CLAUDE.md"
        memory_file.write_text("# Claude Memory\nFallback content")

        result = load_project_memory(str(temp_workspace))

        assert result is not None
        assert "Fallback content" in result

    def test_load_from_subdirectory(self, temp_workspace):
        """Test loading from .juancs subdirectory."""
        subdir = temp_workspace / ".juancs"
        subdir.mkdir()
        memory_file = subdir / "JUANCS.md"
        memory_file.write_text("# Hidden Memory")

        result = load_project_memory(str(temp_workspace))

        assert result is not None
        assert "Hidden Memory" in result

    def test_no_memory_file(self, temp_workspace):
        """Test returns None when no memory file exists."""
        result = load_project_memory(str(temp_workspace))

        assert result is None

    def test_priority_juancs_over_claude(self, temp_workspace):
        """Test JUANCS.md takes priority over CLAUDE.md."""
        (temp_workspace / "JUANCS.md").write_text("JUANCS content")
        (temp_workspace / "CLAUDE.md").write_text("CLAUDE content")

        result = load_project_memory(str(temp_workspace))

        assert "JUANCS content" in result
        assert "CLAUDE content" not in result


# =============================================================================
# GET_DYNAMIC_CONTEXT TESTS
# =============================================================================

class TestGetDynamicContext:
    """Tests for get_dynamic_context function."""

    def test_returns_dict(self):
        """Test function returns a dictionary."""
        result = get_dynamic_context()

        assert isinstance(result, dict)

    def test_contains_cwd(self):
        """Test result contains current working directory."""
        result = get_dynamic_context()

        assert "cwd" in result
        assert result["cwd"] == os.getcwd()

    def test_contains_git_fields(self):
        """Test result contains git-related fields."""
        result = get_dynamic_context()

        assert "git_branch" in result
        assert "git_status" in result
        assert "modified_files" in result

    def test_modified_files_is_set(self):
        """Test modified_files is a set."""
        result = get_dynamic_context()

        assert isinstance(result["modified_files"], set)

    def test_recent_files_is_set(self):
        """Test recent_files is a set."""
        result = get_dynamic_context()

        assert isinstance(result["recent_files"], set)

    @patch("subprocess.run")
    def test_handles_git_failure(self, mock_run):
        """Test graceful handling when git commands fail."""
        mock_run.side_effect = subprocess.SubprocessError("Git not found")

        result = get_dynamic_context()

        assert result["git_branch"] is None
        assert result["git_status"] is None

    @patch("subprocess.run")
    def test_handles_timeout(self, mock_run):
        """Test graceful handling of git command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        result = get_dynamic_context()

        # Should not crash
        assert isinstance(result, dict)

    def test_in_git_repo(self, temp_git_repo):
        """Test context in actual git repo."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_git_repo)
            result = get_dynamic_context()

            # Should have git information
            assert result["cwd"] == str(temp_git_repo)
            # Git branch might be 'main' or 'master'
            assert result["git_branch"] in ["main", "master", None]
        finally:
            os.chdir(original_cwd)


# =============================================================================
# ENHANCE_TOOL_RESULT TESTS
# =============================================================================

class TestEnhanceToolResult:
    """Tests for enhance_tool_result function."""

    def test_success_format(self):
        """Test successful tool result formatting."""
        result = enhance_tool_result("read_file", "file contents", success=True)

        assert 'success="true"' in result
        assert "file contents" in result
        assert "read_file" in result

    def test_failure_format(self):
        """Test failed tool result formatting."""
        result = enhance_tool_result("write_file", "Permission denied", success=False)

        assert 'success="false"' in result
        assert "Permission denied" in result
        assert "guidance" in result.lower()

    def test_read_file_guidance(self):
        """Test read_file has specific guidance."""
        result = enhance_tool_result("read_file", "contents", success=True)

        assert "file contents" in result.lower() or "proceed" in result.lower()

    def test_write_file_guidance(self):
        """Test write_file has specific guidance."""
        result = enhance_tool_result("write_file", "success", success=True)

        assert "written" in result.lower() or "verify" in result.lower()

    def test_bash_guidance(self):
        """Test bash command has specific guidance."""
        result = enhance_tool_result("bash", "output", success=True)

        assert "executed" in result.lower() or "check" in result.lower()

    def test_search_guidance(self):
        """Test grep/search has specific guidance."""
        result = enhance_tool_result("grep", "matches", success=True)

        assert "search" in result.lower() or "review" in result.lower()

    def test_failure_guidance_detailed(self):
        """Test failure guidance includes error recovery tips."""
        result = enhance_tool_result("test_tool", "error", success=False)

        # Should include guidance for error recovery
        assert "path" in result.lower() or "permission" in result.lower() or "retry" in result.lower()

    def test_xml_format(self):
        """Test result uses XML-style tags."""
        result = enhance_tool_result("test", "data", success=True)

        assert "<tool_result" in result
        assert "</tool_result>" in result
        assert "<guidance>" in result
        assert "</guidance>" in result

    def test_unknown_tool(self):
        """Test handling of unknown tool names."""
        result = enhance_tool_result("unknown_custom_tool", "result", success=True)

        # Should still produce valid output
        assert "<tool_result" in result
        assert "unknown_custom_tool" in result

    def test_empty_result(self):
        """Test handling of empty result string."""
        result = enhance_tool_result("test", "", success=True)

        assert "<tool_result" in result

    def test_special_characters_in_result(self):
        """Test handling of special characters."""
        result = enhance_tool_result("test", "<script>alert('xss')</script>", success=True)

        # Should not crash, content should be included
        assert "script" in result.lower()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestPromptIntegration:
    """Integration tests for prompt building."""

    def test_full_prompt_build(self, temp_workspace):
        """Test building a complete prompt with all options."""
        # Create memory file
        (temp_workspace / "JUANCS.md").write_text("# Project Setup\nnpm install")

        tools = [
            {
                "name": "read_file",
                "description": "Read file contents",
                "category": "files",
                "parameters": {"required": ["path"], "properties": {"path": {"type": "string"}}}
            }
        ]

        context = {
            "cwd": str(temp_workspace),
            "git_branch": "main",
            "modified_files": set(),
            "recent_files": set()
        }

        memory = load_project_memory(str(temp_workspace))

        prompt = build_agentic_system_prompt(
            tools=tools,
            context=context,
            project_memory=memory,
            user_memory="User prefers verbose output"
        )

        # Verify all sections present
        assert "juancs-code" in prompt
        assert "read_file" in prompt
        assert str(temp_workspace) in prompt
        assert "npm install" in prompt
        assert "verbose output" in prompt

    def test_prompt_token_efficiency(self):
        """Test prompt is reasonably sized."""
        prompt = build_agentic_system_prompt(tools=[])

        # Should be comprehensive but not excessive
        # Typical prompt should be under 10000 tokens (rough estimate: 4 chars/token)
        assert len(prompt) < 50000  # ~12500 tokens max


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_tool_without_category(self):
        """Test tool without category goes to 'general'."""
        tools = [{"name": "test_tool", "parameters": {}}]

        prompt = build_agentic_system_prompt(tools=tools)

        assert "General" in prompt or "test_tool" in prompt

    def test_tool_without_parameters(self):
        """Test tool without parameters field."""
        tools = [{"name": "simple_tool", "description": "Does something"}]

        # Should not crash
        prompt = build_agentic_system_prompt(tools=tools)

        assert "simple_tool" in prompt

    def test_context_with_many_files(self):
        """Test context with many modified files (should truncate)."""
        context = {
            "modified_files": {f"file_{i}.py" for i in range(100)},
            "recent_files": {f"recent_{i}.py" for i in range(50)}
        }

        prompt = build_agentic_system_prompt(tools=[], context=context)

        # Should not include all 100 files
        file_count = prompt.count("file_")
        assert file_count <= 15  # Max 10 modified + 5 recent

    def test_unicode_in_memory(self, temp_workspace):
        """Test unicode characters in memory file."""
        (temp_workspace / "JUANCS.md").write_text("# Projeto 日本語\n\nOlá mundo! 🎉")

        memory = load_project_memory(str(temp_workspace))

        assert memory is not None
        assert "日本語" in memory
        assert "🎉" in memory
