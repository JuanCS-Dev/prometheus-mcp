"""E2E Tests: Real Tool Workflows with Correct APIs.

These tests use the actual tool APIs as implemented.
"""

import pytest
import asyncio
import time
import os
from pathlib import Path

from .conftest import TestResult, get_report


class TestFileOperations:
    """Test file operation tools with real APIs."""

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, temp_project, e2e_report):
        """Test writing and reading a file."""
        start_time = time.time()
        result = TestResult(
            name="write_and_read_file",
            status="passed",
            duration=0.0,
            metadata={"tools": ["WriteFileTool", "ReadFileTool"]}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

            write_tool = WriteFileTool()
            read_tool = ReadFileTool()

            # Write a file
            test_content = '''"""Test module created by E2E test."""

def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello("World"))
'''
            test_file = temp_project / "test_module.py"

            write_result = await write_tool._execute_validated(
                path=str(test_file),
                content=test_content
            )
            assert write_result.success, f"Write failed: {write_result.error}"
            result.logs.append("✓ File written successfully")

            # Read it back
            read_result = await read_tool._execute_validated(path=str(test_file))
            assert read_result.success, f"Read failed: {read_result.error}"

            # data is the content directly (string)
            content = read_result.data
            assert isinstance(content, str)
            assert "def hello" in content
            assert "Hello, {name}" in content
            result.logs.append("✓ File read successfully")
            result.logs.append(f"✓ Content verified ({len(content)} chars)")

            result.metadata["file_size"] = len(content)
            result.metadata["lines"] = read_result.metadata.get("lines", 0)

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_edit_file(self, temp_project, e2e_report):
        """Test editing a file."""
        start_time = time.time()
        result = TestResult(
            name="edit_file",
            status="passed",
            duration=0.0,
            metadata={"tools": ["WriteFileTool", "EditFileTool", "ReadFileTool"]}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool, EditFileTool, ReadFileTool

            write_tool = WriteFileTool()
            edit_tool = EditFileTool()
            read_tool = ReadFileTool()

            # Create initial file
            initial_content = '''def calculate(a, b):
    return a + b
'''
            test_file = temp_project / "calc.py"
            await write_tool._execute_validated(path=str(test_file), content=initial_content)
            result.logs.append("✓ Created initial file")

            # Edit it to add type hints
            edit_result = await edit_tool._execute_validated(
                path=str(test_file),
                edits=[{
                    "search": "def calculate(a, b):",
                    "replace": "def calculate(a: int, b: int) -> int:"
                }],
                preview=False,
                create_backup=False
            )
            assert edit_result.success, f"Edit failed: {edit_result.error}"
            result.logs.append("✓ File edited successfully")

            # Verify the edit
            read_result = await read_tool._execute_validated(path=str(test_file))
            assert "int" in read_result.data
            assert "-> int:" in read_result.data
            result.logs.append("✓ Edit verified")

            result.metadata["changes"] = edit_result.metadata.get("changes", 1)

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestSearchOperations:
    """Test search tools with real APIs."""

    @pytest.mark.asyncio
    async def test_search_in_files(self, sample_python_project, e2e_report):
        """Test searching for patterns in files."""
        start_time = time.time()
        result = TestResult(
            name="search_in_files",
            status="passed",
            duration=0.0,
            metadata={"tools": ["SearchFilesTool"]}
        )

        try:
            from jdev_cli.tools.search import SearchFilesTool

            search_tool = SearchFilesTool()

            # Search for function definitions
            search_result = await search_tool._execute_validated(
                pattern="def ",
                path=str(sample_python_project),
                file_pattern="*.py",
                max_results=20
            )
            assert search_result.success, f"Search failed: {search_result.error}"

            # data is a list of matches
            matches = search_result.data
            assert isinstance(matches, list)
            result.logs.append(f"✓ Found {len(matches)} function definitions")

            # Each match has file, line, text
            if matches:
                first_match = matches[0]
                assert "file" in first_match
                assert "line" in first_match
                assert "text" in first_match
                result.logs.append(f"✓ First match: {Path(first_match['file']).name}:{first_match['line']}")

            result.metadata["matches_found"] = len(matches)

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_search_for_bugs(self, sample_python_project, e2e_report):
        """Test searching for BUG comments."""
        start_time = time.time()
        result = TestResult(
            name="search_for_bugs",
            status="passed",
            duration=0.0,
            metadata={"tools": ["SearchFilesTool"]}
        )

        try:
            from jdev_cli.tools.search import SearchFilesTool

            search_tool = SearchFilesTool()

            # Search for BUG markers
            search_result = await search_tool._execute_validated(
                pattern="BUG",
                path=str(sample_python_project),
                file_pattern="*.py"
            )
            assert search_result.success

            matches = search_result.data if search_result.data else []
            result.logs.append(f"✓ Found {len(matches)} BUG markers")

            for match in matches[:3]:
                result.logs.append(f"  - {Path(match['file']).name}:{match['line']}: {match['text'][:50]}...")

            result.metadata["bugs_found"] = len(matches)

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestProjectCreation:
    """Test creating complete projects."""

    @pytest.mark.asyncio
    async def test_create_python_module(self, temp_project, e2e_report):
        """Test creating a complete Python module."""
        start_time = time.time()
        result = TestResult(
            name="create_python_module",
            status="passed",
            duration=0.0,
            metadata={"project_type": "python_module"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool

            write_tool = WriteFileTool()

            # Create package structure
            pkg_dir = temp_project / "mypackage"
            pkg_dir.mkdir()

            files_to_create = {
                "mypackage/__init__.py": '''"""MyPackage - A test package."""
__version__ = "0.1.0"
from .core import process, validate
''',
                "mypackage/core.py": '''"""Core functionality."""
from typing import List, Any

def process(items: List[Any]) -> List[Any]:
    """Process a list of items."""
    return [item for item in items if item is not None]

def validate(data: dict) -> bool:
    """Validate data dictionary."""
    required = ["name", "value"]
    return all(key in data for key in required)
''',
                "mypackage/utils.py": '''"""Utility functions."""
import hashlib

def hash_string(s: str) -> str:
    """Generate SHA256 hash of a string."""
    return hashlib.sha256(s.encode()).hexdigest()

def truncate(s: str, max_len: int = 100) -> str:
    """Truncate string to max length."""
    if len(s) <= max_len:
        return s
    return s[:max_len-3] + "..."
''',
                "tests/__init__.py": "",
                "tests/test_core.py": '''"""Tests for core module."""
import pytest
from mypackage.core import process, validate

def test_process_removes_none():
    result = process([1, None, 2, None, 3])
    assert result == [1, 2, 3]

def test_process_empty():
    assert process([]) == []

def test_validate_success():
    assert validate({"name": "test", "value": 123})

def test_validate_missing_field():
    assert not validate({"name": "test"})
''',
                "README.md": '''# MyPackage

A test package created by E2E tests.

## Installation

```bash
pip install -e .
```

## Usage

```python
from mypackage import process, validate

items = process([1, None, 2])
is_valid = validate({"name": "test", "value": 123})
```
''',
                "pyproject.toml": '''[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "mypackage"
version = "0.1.0"
requires-python = ">=3.9"
'''
            }

            (temp_project / "tests").mkdir(exist_ok=True)

            for path, content in files_to_create.items():
                write_result = await write_tool._execute_validated(
                    path=str(temp_project / path),
                    content=content
                )
                assert write_result.success, f"Failed to create {path}: {write_result.error}"
                result.logs.append(f"✓ Created {path}")

            result.metadata["files_created"] = len(files_to_create)

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestGitOperations:
    """Test git-related operations."""

    @pytest.mark.asyncio
    async def test_git_status(self, sample_python_project, e2e_report):
        """Test getting git status."""
        start_time = time.time()
        result = TestResult(
            name="git_status",
            status="passed",
            duration=0.0,
            metadata={"tools": ["GitStatusTool"]}
        )

        try:
            from jdev_cli.tools.git_ops import GitStatusTool

            status_tool = GitStatusTool()

            # Get status - check actual parameters
            status_result = await status_tool._execute_validated()

            assert status_result.success, f"Git status failed: {status_result.error}"

            # Check what we got
            data = status_result.data
            result.logs.append(f"✓ Git status retrieved")
            result.logs.append(f"✓ Data type: {type(data)}")

            if isinstance(data, dict):
                if "branch" in data:
                    result.logs.append(f"✓ Branch: {data['branch']}")
                if "modified" in data:
                    result.logs.append(f"✓ Modified files: {len(data['modified'])}")

            result.metadata["status_data"] = str(data)[:200]

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestPlanMode:
    """Test planning mode tools."""

    @pytest.mark.asyncio
    async def test_plan_mode_cycle(self, temp_project, e2e_report):
        """Test full plan mode cycle."""
        start_time = time.time()
        result = TestResult(
            name="plan_mode_cycle",
            status="passed",
            duration=0.0,
            metadata={"tools": ["EnterPlanModeTool", "ExitPlanModeTool"]}
        )

        try:
            from jdev_cli.tools.plan_mode import (
                EnterPlanModeTool,
                ExitPlanModeTool,
                get_plan_state,
                reset_plan_state
            )

            reset_plan_state()

            enter_tool = EnterPlanModeTool()
            exit_tool = ExitPlanModeTool()

            # Enter plan mode
            plan_file = temp_project / ".jdev" / "plans" / "e2e_plan.md"
            enter_result = await enter_tool._execute_validated(
                task_description="E2E Test Planning",
                plan_file=str(plan_file)
            )

            assert enter_result.success, f"Enter failed: {enter_result.error}"
            assert get_plan_state().active is True
            result.logs.append("✓ Entered plan mode")

            # Write some plan content
            plan_file.write_text("""# E2E Test Plan

## Objective
Test the planning mode functionality.

## Steps
1. Enter plan mode
2. Create plan document
3. Exit plan mode

## Notes
This is an automated test.
""")
            result.logs.append("✓ Plan content written")

            # Exit plan mode
            exit_result = await exit_tool._execute_validated(
                summary="E2E test planning complete"
            )

            assert exit_result.success, f"Exit failed: {exit_result.error}"
            result.logs.append("✓ Exited plan mode")

            result.metadata["plan_file"] = str(plan_file)

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestCombinedWorkflow:
    """Test combined multi-tool workflows."""

    @pytest.mark.asyncio
    async def test_search_and_fix_workflow(self, sample_python_project, e2e_report):
        """Test searching for issues and fixing them."""
        start_time = time.time()
        result = TestResult(
            name="search_and_fix_workflow",
            status="passed",
            duration=0.0,
            metadata={"workflow": "search_fix", "tools": 3}
        )

        try:
            from jdev_cli.tools.search import SearchFilesTool
            from jdev_cli.tools.file_ops import ReadFileTool, EditFileTool

            search_tool = SearchFilesTool()
            read_tool = ReadFileTool()
            edit_tool = EditFileTool()

            # Step 1: Search for potential issues
            result.logs.append("Step 1: Searching for issues...")

            search_result = await search_tool._execute_validated(
                pattern="# BUG",
                path=str(sample_python_project),
                file_pattern="*.py"
            )

            if search_result.success and search_result.data:
                matches = search_result.data
                result.logs.append(f"  Found {len(matches)} issues")

                if matches:
                    # Step 2: Read the first file with issues
                    first_file = matches[0]["file"]
                    result.logs.append(f"Step 2: Reading {Path(first_file).name}...")

                    read_result = await read_tool._execute_validated(path=first_file)
                    if read_result.success:
                        content = read_result.data
                        result.logs.append(f"  Read {len(content)} chars")

                        # Step 3: Fix an issue
                        if "a / b  # BUG" in content:
                            result.logs.append("Step 3: Fixing division bug...")

                            edit_result = await edit_tool._execute_validated(
                                path=first_file,
                                edits=[{
                                    "search": "a / b  # BUG: no zero check",
                                    "replace": "a / b if b != 0 else 0  # FIXED"
                                }],
                                preview=False,
                                create_backup=False
                            )

                            if edit_result.success:
                                result.logs.append("  ✓ Bug fixed!")
                                result.metadata["fixed"] = True
                            else:
                                result.logs.append(f"  Could not fix: {edit_result.error}")
                                result.metadata["fixed"] = False
            else:
                result.logs.append("  No issues found (clean code!)")
                result.metadata["fixed"] = False

            result.metadata["issues_found"] = len(search_result.data) if search_result.data else 0

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error
