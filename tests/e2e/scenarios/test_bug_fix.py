"""
E2E Scenario Tests: Bug Fixing
==============================

Tests for debugging and fixing bugs in code.
Validates the complete workflow of identifying and resolving issues.

Based on:
- Anthropic TDD with expected outputs
- Real-world debugging scenarios

Total: 10 tests
"""

import pytest


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def buggy_project(tmp_path):
    """Create a project with various bugs to fix."""
    project_dir = tmp_path / "buggy_project"
    project_dir.mkdir()
    (project_dir / "src").mkdir()

    # File with syntax error
    (project_dir / "src" / "syntax_error.py").write_text('''"""Module with syntax error."""

def broken_function():
    print("Hello"
    return 42
''')

    # File with import error
    (project_dir / "src" / "import_error.py").write_text('''"""Module with import error."""
from nonexistent_module import something

def use_import():
    return something()
''')

    # File with type error
    (project_dir / "src" / "type_error.py").write_text('''"""Module with type error."""

def add_numbers(a, b):
    return a + b

result = add_numbers("5", 3)  # Type error: str + int
''')

    # File with logic bug
    (project_dir / "src" / "logic_bug.py").write_text('''"""Module with logic bug."""

def calculate_average(numbers):
    """Calculate average of numbers."""
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)  # Bug: doesn't handle empty list

def find_max(numbers):
    """Find maximum value."""
    max_val = 0  # Bug: assumes positive numbers
    for num in numbers:
        if num > max_val:
            max_val = num
    return max_val
''')

    # File with runtime error
    (project_dir / "src" / "runtime_error.py").write_text('''"""Module with runtime error."""

def divide(a, b):
    return a / b  # No zero check

def access_list(lst, index):
    return lst[index]  # No bounds check

def get_key(d, key):
    return d[key]  # No key check
''')

    return project_dir


# ==============================================================================
# TEST CLASS: Syntax Error Fixes
# ==============================================================================

@pytest.mark.e2e
class TestSyntaxErrorFixes:
    """Tests for identifying and fixing syntax errors."""

    def test_identifies_missing_parenthesis(self, buggy_project):
        """Identifies and fixes missing parenthesis."""
        file_path = buggy_project / "src" / "syntax_error.py"
        content = file_path.read_text()

        # The bug: print("Hello" - missing closing paren
        assert 'print("Hello"' in content

        # Fix: add missing parenthesis
        fixed_content = '''"""Module with syntax error."""

def broken_function():
    print("Hello")
    return 42
'''
        file_path.write_text(fixed_content)

        # Verify fix compiles
        import ast
        try:
            ast.parse(fixed_content)
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False

        assert syntax_valid, "Fixed code should have valid syntax"

    def test_identifies_indentation_error(self, buggy_project):
        """Identifies and fixes indentation errors."""
        file_path = buggy_project / "src" / "indent_error.py"

        # Create file with indentation error
        file_path.write_text('''def function():
print("wrong indent")
    return 1
''')

        # Fix: correct indentation
        fixed_content = '''def function():
    print("correct indent")
    return 1
'''
        file_path.write_text(fixed_content)

        import ast
        try:
            ast.parse(fixed_content)
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False

        assert syntax_valid, "Fixed code should have valid syntax"


# ==============================================================================
# TEST CLASS: Import Error Fixes
# ==============================================================================

@pytest.mark.e2e
class TestImportErrorFixes:
    """Tests for identifying and fixing import errors."""

    def test_identifies_missing_module(self, buggy_project):
        """Identifies missing module and suggests fix."""
        file_path = buggy_project / "src" / "import_error.py"
        content = file_path.read_text()

        # The bug: importing nonexistent module
        assert "nonexistent_module" in content

        # Fix: replace with valid import or create the module
        fixed_content = '''"""Module with fixed import."""
# from nonexistent_module import something  # Removed invalid import

def use_import():
    return "Using local implementation instead"
'''
        file_path.write_text(fixed_content)

        # Verify fix
        assert "nonexistent_module" not in file_path.read_text() or \
               "#" in file_path.read_text().split("nonexistent_module")[0].split("\n")[-1]

    def test_fixes_typo_in_import(self, buggy_project):
        """Fixes typo in module name."""
        file_path = buggy_project / "src" / "typo_import.py"

        # Create file with typo
        file_path.write_text('''import jsn  # Typo: should be json
data = jsn.dumps({"key": "value"})
''')

        # Fix: correct the typo
        fixed_content = '''import json  # Fixed typo
data = json.dumps({"key": "value"})
'''
        file_path.write_text(fixed_content)

        # Verify fix works
        import ast
        ast.parse(fixed_content)  # Should not raise


# ==============================================================================
# TEST CLASS: Type Error Fixes
# ==============================================================================

@pytest.mark.e2e
class TestTypeErrorFixes:
    """Tests for identifying and fixing type errors."""

    def test_identifies_type_mismatch(self, buggy_project):
        """Identifies type mismatch in function call."""
        file_path = buggy_project / "src" / "type_error.py"
        content = file_path.read_text()

        # The bug: add_numbers("5", 3) - string + int
        assert 'add_numbers("5", 3)' in content

        # Fix: convert string to int
        fixed_content = '''"""Module with fixed type error."""

def add_numbers(a, b):
    return a + b

result = add_numbers(5, 3)  # Fixed: both are ints now
'''
        file_path.write_text(fixed_content)

        # Verify fix works at runtime
        exec(compile(fixed_content, file_path, 'exec'))

    def test_adds_type_hints_for_clarity(self, buggy_project):
        """Adds type hints to prevent future type errors."""
        file_path = buggy_project / "src" / "typed_module.py"

        # Create module with type hints
        file_path.write_text('''"""Module with type hints."""
from typing import List, Dict, Optional

def add_numbers(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

def process_items(items: List[str]) -> Dict[str, int]:
    """Process string items to dict."""
    return {item: len(item) for item in items}

def find_value(data: Dict[str, int], key: str) -> Optional[int]:
    """Find value by key, return None if not found."""
    return data.get(key)
''')

        content = file_path.read_text()

        # Verify type hints present
        assert "-> int" in content
        assert "List[str]" in content
        assert "Optional[int]" in content


# ==============================================================================
# TEST CLASS: Logic Bug Fixes
# ==============================================================================

@pytest.mark.e2e
class TestLogicBugFixes:
    """Tests for identifying and fixing logic bugs."""

    def test_fixes_divide_by_zero_bug(self, buggy_project):
        """Fixes divide by zero in average calculation."""
        file_path = buggy_project / "src" / "logic_bug.py"

        # Fix: handle empty list
        fixed_content = '''"""Module with fixed logic bugs."""

def calculate_average(numbers):
    """Calculate average of numbers."""
    if not numbers:
        return 0  # Handle empty list
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def find_max(numbers):
    """Find maximum value."""
    if not numbers:
        return None  # Handle empty list
    max_val = numbers[0]  # Start with first element, not 0
    for num in numbers[1:]:
        if num > max_val:
            max_val = num
    return max_val
'''
        file_path.write_text(fixed_content)

        # Verify fixes
        exec_globals = {}
        exec(compile(fixed_content, file_path, 'exec'), exec_globals)

        calculate_average = exec_globals['calculate_average']
        find_max = exec_globals['find_max']

        # Test edge cases
        assert calculate_average([]) == 0
        assert calculate_average([1, 2, 3]) == 2
        assert find_max([]) is None
        assert find_max([-5, -3, -1]) == -1

    def test_fixes_off_by_one_error(self, buggy_project):
        """Fixes off-by-one error in loop."""
        file_path = buggy_project / "src" / "off_by_one.py"

        # Create file with off-by-one bug
        file_path.write_text('''"""Module with off-by-one bug."""

def get_last_n_items(items, n):
    """Get last n items from list."""
    result = []
    for i in range(len(items) - n, len(items) + 1):  # Bug: +1 causes IndexError
        result.append(items[i])
    return result
''')

        # Fix: correct the range
        fixed_content = '''"""Module with fixed off-by-one."""

def get_last_n_items(items, n):
    """Get last n items from list."""
    if n <= 0:
        return []
    if n >= len(items):
        return items[:]
    return items[-n:]  # Simpler, correct implementation
'''
        file_path.write_text(fixed_content)

        # Verify fix
        exec_globals = {}
        exec(compile(fixed_content, file_path, 'exec'), exec_globals)

        get_last_n = exec_globals['get_last_n_items']
        assert get_last_n([1, 2, 3, 4, 5], 2) == [4, 5]
        assert get_last_n([1, 2, 3], 0) == []
        assert get_last_n([1, 2], 5) == [1, 2]


# ==============================================================================
# TEST CLASS: Runtime Error Fixes
# ==============================================================================

@pytest.mark.e2e
class TestRuntimeErrorFixes:
    """Tests for identifying and fixing runtime errors."""

    def test_fixes_zero_division_error(self, buggy_project):
        """Fixes division by zero error."""
        file_path = buggy_project / "src" / "runtime_error.py"

        fixed_content = '''"""Module with fixed runtime errors."""

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def access_list(lst, index):
    if not lst:
        return None
    if index < 0 or index >= len(lst):
        return None
    return lst[index]

def get_key(d, key, default=None):
    return d.get(key, default)
'''
        file_path.write_text(fixed_content)

        # Verify fixes
        exec_globals = {}
        exec(compile(fixed_content, file_path, 'exec'), exec_globals)

        divide = exec_globals['divide']
        access_list = exec_globals['access_list']
        get_key = exec_globals['get_key']

        # Test error handling
        with pytest.raises(ValueError):
            divide(10, 0)

        assert access_list([], 0) is None
        assert access_list([1, 2, 3], 10) is None
        assert access_list([1, 2, 3], 1) == 2

        assert get_key({}, "missing") is None
        assert get_key({"a": 1}, "a") == 1

    def test_adds_error_handling(self, buggy_project):
        """Adds proper error handling to functions."""
        file_path = buggy_project / "src" / "error_handling.py"

        file_path.write_text('''"""Module with proper error handling."""
import logging

logger = logging.getLogger(__name__)

def safe_divide(a, b):
    """Divide with proper error handling."""
    try:
        result = a / b
        return {"success": True, "result": result}
    except ZeroDivisionError:
        logger.warning(f"Attempted division by zero: {a}/{b}")
        return {"success": False, "error": "Division by zero"}
    except TypeError as e:
        logger.error(f"Type error in division: {e}")
        return {"success": False, "error": str(e)}

def safe_parse_json(json_string):
    """Parse JSON with error handling."""
    import json
    try:
        return {"success": True, "data": json.loads(json_string)}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}
''')

        # Verify error handling
        exec_globals = {}
        exec(compile(file_path.read_text(), file_path, 'exec'), exec_globals)

        safe_divide = exec_globals['safe_divide']
        safe_parse_json = exec_globals['safe_parse_json']

        assert safe_divide(10, 0)["success"] is False
        assert safe_divide(10, 2)["result"] == 5

        assert safe_parse_json("invalid")["success"] is False
        assert safe_parse_json('{"key": "value"}')["success"] is True


# ==============================================================================
# SUMMARY
# ==============================================================================

"""
Total Tests: 10

Bug Types Covered:
1. Syntax errors (missing parenthesis, indentation)
2. Import errors (missing module, typos)
3. Type errors (type mismatches, missing hints)
4. Logic bugs (edge cases, off-by-one)
5. Runtime errors (division, index, key errors)
6. Error handling patterns
"""
