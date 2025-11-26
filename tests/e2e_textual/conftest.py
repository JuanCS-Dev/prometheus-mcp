"""Pytest configuration for E2E Textual tests."""

import pytest
import asyncio
import tempfile
import shutil
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    status: str  # passed, failed, error, skipped
    duration: float
    screenshots: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class E2EReport:
    """Full E2E test report."""
    timestamp: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0
    results: List[TestResult] = field(default_factory=list)

    def add_result(self, result: TestResult):
        self.results.append(result)
        self.total_tests += 1
        if result.status == "passed":
            self.passed += 1
        elif result.status == "failed":
            self.failed += 1
        elif result.status == "error":
            self.errors += 1
        else:
            self.skipped += 1
        self.duration += result.duration

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total": self.total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "errors": self.errors,
                "skipped": self.skipped,
                "pass_rate": f"{(self.passed/self.total_tests*100):.1f}%" if self.total_tests > 0 else "N/A",
                "duration": f"{self.duration:.2f}s"
            },
            "results": [asdict(r) for r in self.results]
        }


# Global report instance
_report = None


def get_report() -> E2EReport:
    """Get or create the global report."""
    global _report
    if _report is None:
        _report = E2EReport(timestamp=datetime.now().isoformat())
    return _report


@pytest.fixture(scope="session")
def e2e_report():
    """Provide the E2E report to tests."""
    return get_report()


@pytest.fixture(scope="session")
def screenshots_dir():
    """Directory for screenshots."""
    path = Path(__file__).parent / "screenshots"
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    tmpdir = tempfile.mkdtemp(prefix="jdev_e2e_")

    # Initialize as git repo
    os.system(f"cd {tmpdir} && git init -q")

    yield Path(tmpdir)

    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_python_project(temp_project):
    """Create a sample Python project structure."""
    # Create basic structure
    (temp_project / "src").mkdir()
    (temp_project / "tests").mkdir()

    # Main module
    (temp_project / "src" / "__init__.py").write_text("")
    (temp_project / "src" / "main.py").write_text('''"""Main application module."""

def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    return a / b  # BUG: no zero check

class Calculator:
    """Simple calculator."""

    def __init__(self):
        self.history = []

    def calculate(self, op: str, a: float, b: float) -> float:
        """Perform calculation."""
        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        elif op == "*":
            result = a * b
        elif op == "/":
            result = a / b  # BUG: no zero check
        else:
            raise ValueError(f"Unknown op: {op}")
        self.history.append((op, a, b, result))
        return result
''')

    # Config file
    (temp_project / "config.py").write_text('''"""Configuration."""

DEBUG = True
API_KEY = "sk-1234567890"  # BUG: hardcoded secret
DATABASE_URL = "postgresql://user:pass@localhost/db"
''')

    # Test file
    (temp_project / "tests" / "__init__.py").write_text("")
    (temp_project / "tests" / "test_main.py").write_text('''"""Tests for main module."""

import pytest
from src.main import greet, add, Calculator

def test_greet():
    assert greet("World") == "Hello, World!"

def test_add():
    assert add(2, 3) == 5

def test_calculator():
    calc = Calculator()
    assert calc.calculate("+", 2, 3) == 5
''')

    # Requirements
    (temp_project / "requirements.txt").write_text('''pytest>=7.0.0
black>=23.0.0
ruff>=0.1.0
''')

    # README
    (temp_project / "README.md").write_text('''# Sample Project

A sample project for E2E testing.

## Features

- Greeting function
- Calculator class
- Basic math operations
''')

    # Commit initial state
    os.system(f"cd {temp_project} && git add -A && git commit -q -m 'Initial commit'")

    return temp_project


@pytest.fixture
def mock_llm_responses():
    """Provide mock LLM responses for deterministic testing."""
    return {
        "create_app": {
            "files": ["app.py", "requirements.txt", "README.md"],
            "description": "Created FastAPI application"
        },
        "refactor": {
            "changes": ["Added type hints", "Extracted functions", "Fixed bugs"],
            "files_modified": 2
        },
        "audit": {
            "issues": [
                {"severity": "high", "message": "Hardcoded API key"},
                {"severity": "medium", "message": "No input validation"},
                {"severity": "low", "message": "Missing docstrings"}
            ]
        },
        "plan": {
            "steps": [
                "Analyze requirements",
                "Design architecture",
                "Implement core features",
                "Add tests",
                "Document"
            ]
        }
    }


def pytest_sessionfinish(session, exitstatus):
    """Generate final report after all tests."""
    report = get_report()

    # Save JSON report
    report_path = Path(__file__).parent / "E2E_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    # Generate markdown report
    md_path = Path(__file__).parent / "E2E_REPORT.md"
    with open(md_path, "w") as f:
        f.write(f"# E2E Test Report - Juan-Dev-Code\n\n")
        f.write(f"**Generated:** {report.timestamp}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Tests | {report.total_tests} |\n")
        f.write(f"| Passed | {report.passed} |\n")
        f.write(f"| Failed | {report.failed} |\n")
        f.write(f"| Errors | {report.errors} |\n")
        f.write(f"| Pass Rate | {(report.passed/report.total_tests*100):.1f}% |\n" if report.total_tests > 0 else "| Pass Rate | N/A |\n")
        f.write(f"| Duration | {report.duration:.2f}s |\n")
        f.write(f"\n## Test Results\n\n")

        for result in report.results:
            status_emoji = {"passed": "✅", "failed": "❌", "error": "💥", "skipped": "⏭️"}.get(result.status, "❓")
            f.write(f"### {status_emoji} {result.name}\n\n")
            f.write(f"- **Status:** {result.status}\n")
            f.write(f"- **Duration:** {result.duration:.2f}s\n")

            if result.error:
                f.write(f"- **Error:** `{result.error}`\n")

            if result.screenshots:
                f.write(f"\n**Screenshots:**\n")
                for ss in result.screenshots:
                    f.write(f"![{ss}](screenshots/{ss})\n")

            if result.metadata:
                f.write(f"\n**Details:**\n```json\n{json.dumps(result.metadata, indent=2)}\n```\n")

            f.write("\n---\n\n")

    print(f"\n📊 E2E Report saved to: {md_path}")
