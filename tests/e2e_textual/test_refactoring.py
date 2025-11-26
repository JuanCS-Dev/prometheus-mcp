"""E2E Tests: Code Refactoring Workflows.

Tests the ability to refactor and improve existing code.
"""

import pytest
import asyncio
import time
from pathlib import Path

from .conftest import TestResult, get_report


class TestCodeRefactoring:
    """Test code refactoring capabilities."""

    @pytest.mark.asyncio
    async def test_add_type_hints(self, sample_python_project, e2e_report):
        """Test adding type hints to untyped code."""
        start_time = time.time()
        result = TestResult(
            name="add_type_hints",
            status="passed",
            duration=0.0,
            metadata={"refactor_type": "type_hints"}
        )

        try:
            from jdev_cli.tools.file_ops import ReadFileTool, EditFileTool

            read_tool = ReadFileTool()
            edit_tool = EditFileTool()

            # Create untyped code
            untyped_code = '''def process_data(items):
    results = []
    for item in items:
        if item > 0:
            results.append(item * 2)
    return results

def find_max(numbers):
    if not numbers:
        return None
    max_val = numbers[0]
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val

class DataProcessor:
    def __init__(self, name):
        self.name = name
        self.data = []

    def add(self, item):
        self.data.append(item)

    def get_all(self):
        return self.data.copy()
'''
            test_file = sample_python_project / "untyped.py"
            test_file.write_text(untyped_code)

            # Apply type hints via edit
            typed_code = '''from typing import List, Optional

def process_data(items: List[int]) -> List[int]:
    results: List[int] = []
    for item in items:
        if item > 0:
            results.append(item * 2)
    return results

def find_max(numbers: List[int]) -> Optional[int]:
    if not numbers:
        return None
    max_val: int = numbers[0]
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val

class DataProcessor:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self.data: List[any] = []

    def add(self, item: any) -> None:
        self.data.append(item)

    def get_all(self) -> List[any]:
        return self.data.copy()
'''
            edit_result = await edit_tool._execute_validated(
                path=str(test_file),
                edits=[{"search": untyped_code, "replace": typed_code}],
                preview=False,
                create_backup=False
            )
            assert edit_result.success, f"Edit failed: {edit_result.error}"

            # Verify changes
            read_result = await read_tool._execute_validated(path=str(test_file))
            content = read_result.data["content"]

            assert "List[int]" in content
            assert "Optional[int]" in content
            assert "-> None" in content
            assert "from typing import" in content

            result.logs.append("✓ Added type hints to functions")
            result.logs.append("✓ Added type hints to class methods")
            result.logs.append("✓ Added typing imports")
            result.metadata["type_hints_added"] = 8

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_extract_function(self, sample_python_project, e2e_report):
        """Test extracting repeated code into a function."""
        start_time = time.time()
        result = TestResult(
            name="extract_function",
            status="passed",
            duration=0.0,
            metadata={"refactor_type": "extract_function"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool, EditFileTool

            write_tool = WriteFileTool()
            edit_tool = EditFileTool()

            # Code with duplication
            duplicated_code = '''def process_users(users):
    # Validate and transform users
    valid_users = []
    for user in users:
        if user.get("name") and user.get("email"):
            if "@" in user["email"]:
                valid_users.append({
                    "name": user["name"].strip().title(),
                    "email": user["email"].strip().lower()
                })
    return valid_users

def process_admins(admins):
    # Validate and transform admins (same logic!)
    valid_admins = []
    for admin in admins:
        if admin.get("name") and admin.get("email"):
            if "@" in admin["email"]:
                valid_admins.append({
                    "name": admin["name"].strip().title(),
                    "email": admin["email"].strip().lower()
                })
    return valid_admins

def process_guests(guests):
    # Validate and transform guests (same logic again!)
    valid_guests = []
    for guest in guests:
        if guest.get("name") and guest.get("email"):
            if "@" in guest["email"]:
                valid_guests.append({
                    "name": guest["name"].strip().title(),
                    "email": guest["email"].strip().lower()
                })
    return valid_guests
'''
            test_file = sample_python_project / "duplicated.py"
            test_file.write_text(duplicated_code)

            # Refactored code with extracted function
            refactored_code = '''from typing import List, Dict, Any


def validate_and_transform(item: Dict[str, Any]) -> Dict[str, str] | None:
    """Validate and transform a user/admin/guest item."""
    if not item.get("name") or not item.get("email"):
        return None
    if "@" not in item["email"]:
        return None
    return {
        "name": item["name"].strip().title(),
        "email": item["email"].strip().lower()
    }


def process_items(items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Process a list of items with validation."""
    return [
        transformed
        for item in items
        if (transformed := validate_and_transform(item)) is not None
    ]


def process_users(users: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Process users."""
    return process_items(users)


def process_admins(admins: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Process admins."""
    return process_items(admins)


def process_guests(guests: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Process guests."""
    return process_items(guests)
'''
            await write_tool._execute_validated(
                path=str(test_file),
                content=refactored_code
            )

            # Verify refactoring
            content = test_file.read_text()
            assert "validate_and_transform" in content
            assert "process_items" in content
            assert content.count("for") < duplicated_code.count("for")

            result.logs.append("✓ Extracted validate_and_transform function")
            result.logs.append("✓ Extracted process_items function")
            result.logs.append("✓ Reduced code duplication")
            result.metadata["lines_before"] = len(duplicated_code.splitlines())
            result.metadata["lines_after"] = len(refactored_code.splitlines())
            result.metadata["reduction_percent"] = round(
                (1 - len(refactored_code) / len(duplicated_code)) * 100, 1
            )

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_fix_security_issues(self, sample_python_project, e2e_report):
        """Test fixing security vulnerabilities."""
        start_time = time.time()
        result = TestResult(
            name="fix_security_issues",
            status="passed",
            duration=0.0,
            metadata={"refactor_type": "security_fix"}
        )

        try:
            from jdev_cli.tools.file_ops import ReadFileTool, EditFileTool

            read_tool = ReadFileTool()
            edit_tool = EditFileTool()

            # Read the config file with hardcoded secrets
            config_file = sample_python_project / "config.py"
            read_result = await read_tool._execute_validated(path=str(config_file))
            original_content = read_result.data["content"]

            assert "API_KEY = \"sk-" in original_content, "Test file should have hardcoded secret"

            # Fix by using environment variables
            fixed_config = '''"""Configuration - Secure version."""
import os
from typing import Optional

def get_env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value

# Configuration from environment
DEBUG = get_env("DEBUG", "false").lower() == "true"
API_KEY = get_env("API_KEY", required=True)  # No hardcoded value!
DATABASE_URL = get_env("DATABASE_URL", "postgresql://localhost/db")

# Validate on import
if not API_KEY:
    raise ValueError("API_KEY environment variable must be set")
'''
            edit_result = await edit_tool._execute_validated(
                path=str(config_file),
                edits=[{"search": original_content, "replace": fixed_config}],
                preview=False,
                create_backup=False
            )

            # Verify fix
            read_result = await read_tool._execute_validated(path=str(config_file))
            new_content = read_result.data["content"]

            assert "sk-1234567890" not in new_content, "Hardcoded secret should be removed"
            assert "os.getenv" in new_content, "Should use environment variables"
            assert "required=True" in new_content, "Should mark required vars"

            result.logs.append("✓ Removed hardcoded API key")
            result.logs.append("✓ Added environment variable lookup")
            result.logs.append("✓ Added validation for required vars")
            result.metadata["issues_fixed"] = ["hardcoded_secret", "missing_validation"]

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_add_error_handling(self, sample_python_project, e2e_report):
        """Test adding proper error handling to code."""
        start_time = time.time()
        result = TestResult(
            name="add_error_handling",
            status="passed",
            duration=0.0,
            metadata={"refactor_type": "error_handling"}
        )

        try:
            from jdev_cli.tools.file_ops import ReadFileTool, EditFileTool

            read_tool = ReadFileTool()
            edit_tool = EditFileTool()

            # Read main.py which has divide without zero check
            main_file = sample_python_project / "src" / "main.py"
            read_result = await read_tool._execute_validated(path=str(main_file))
            original = read_result.data["content"]

            # Find and fix the divide function
            old_divide = '''def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    return a / b  # BUG: no zero check'''

            new_divide = '''def divide(a: float, b: float) -> float:
    """Divide two numbers safely.

    Args:
        a: Dividend
        b: Divisor

    Returns:
        Result of division

    Raises:
        ZeroDivisionError: If b is zero
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b'''

            edit_result = await edit_tool._execute_validated(
                path=str(main_file),
                edits=[{"search": old_divide, "replace": new_divide}],
                preview=False,
                create_backup=False
            )
            assert edit_result.success

            # Also fix Calculator.calculate
            read_result = await read_tool._execute_validated(path=str(main_file))
            content = read_result.data["content"]

            old_calc = '''elif op == "/":
            result = a / b  # BUG: no zero check'''

            new_calc = '''elif op == "/":
            if b == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            result = a / b'''

            edit_result = await edit_tool._execute_validated(
                path=str(main_file),
                edits=[{"search": old_calc, "replace": new_calc}],
                preview=False,
                create_backup=False
            )
            assert edit_result.success

            # Verify fixes
            read_result = await read_tool._execute_validated(path=str(main_file))
            final_content = read_result.data["content"]

            assert "if b == 0:" in final_content
            assert "ZeroDivisionError" in final_content
            assert "# BUG" not in final_content

            result.logs.append("✓ Fixed divide function")
            result.logs.append("✓ Fixed Calculator.calculate method")
            result.logs.append("✓ Added ZeroDivisionError handling")
            result.metadata["bugs_fixed"] = 2

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestBulkRefactoring:
    """Test refactoring across multiple files."""

    @pytest.mark.asyncio
    async def test_rename_across_files(self, sample_python_project, e2e_report):
        """Test renaming a function across multiple files."""
        start_time = time.time()
        result = TestResult(
            name="rename_across_files",
            status="passed",
            duration=0.0,
            metadata={"refactor_type": "rename"}
        )

        try:
            from jdev_cli.tools.file_ops import EditFileTool
            from jdev_cli.tools.search import SearchFilesTool

            edit_tool = EditFileTool()
            search_tool = SearchFilesTool()

            # Search for 'greet' function usage
            search_result = await search_tool._execute_validated(
                pattern="greet",
                path=str(sample_python_project),
                file_pattern="*.py"
            )

            files_with_greet = []
            if search_result.success and search_result.data.get("matches"):
                files_with_greet = list(set(m["file"] for m in search_result.data["matches"]))

            # Rename greet -> say_hello in main.py
            main_file = sample_python_project / "src" / "main.py"
            edit_result = await edit_tool._execute_validated(
                path=str(main_file),
                edits=[{"search": "def greet(", "replace": "def say_hello("}],
                preview=False,
                create_backup=False,
                replace_all=True
            )

            # Rename in test file too
            test_file = sample_python_project / "tests" / "test_main.py"
            edit_result = await edit_tool._execute_validated(
                path=str(test_file),
                edits=[
                    {"search": "from src.main import greet", "replace": "from src.main import say_hello"},
                    {"search": "greet(", "replace": "say_hello("}
                ],
                preview=False,
                create_backup=False,
                replace_all=True
            )

            # Verify
            main_content = main_file.read_text()
            test_content = test_file.read_text()

            assert "def say_hello(" in main_content
            assert "def greet(" not in main_content
            assert "say_hello(" in test_content
            assert "import say_hello" in test_content

            result.logs.append(f"✓ Found {len(files_with_greet)} files with 'greet'")
            result.logs.append("✓ Renamed function in main.py")
            result.logs.append("✓ Updated imports in test_main.py")
            result.logs.append("✓ Updated function calls")
            result.metadata["files_modified"] = 2

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error
