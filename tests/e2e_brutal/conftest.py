"""
E2E Brutal Test Suite - Conftest
================================

Fixtures and helpers for brutally honest testing of the qwen-dev-cli shell.

Test Philosophy:
- Test REAL interactions, not mocks where possible
- Simulate REAL user personas with different skill levels
- Create REAL mini-applications and test them
- Be BRUTALLY HONEST about failures
- Document EVERY issue found
"""

import pytest
import asyncio
import tempfile
import shutil
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock, patch

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qwen_dev_cli.core.llm import LLMClient
from qwen_dev_cli.core.mcp_client import MCPClient
from qwen_dev_cli.tools.base import ToolRegistry, ToolResult
from qwen_dev_cli.agents.base import AgentTask, AgentResponse


# ==============================================================================
# ISSUE TRACKING
# ==============================================================================

@dataclass
class Issue:
    """Represents a discovered issue."""
    id: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # SECURITY, CRASH, UX, PERFORMANCE, LOGIC, INTEGRATION
    title: str
    description: str
    reproduction_steps: List[str]
    expected_behavior: str
    actual_behavior: str
    affected_component: str
    user_persona: str  # SENIOR, VIBE_CODER, SCRIPT_KID
    timestamp: datetime = field(default_factory=datetime.now)
    traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "reproduction_steps": self.reproduction_steps,
            "expected_behavior": self.expected_behavior,
            "actual_behavior": self.actual_behavior,
            "affected_component": self.affected_component,
            "user_persona": self.user_persona,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback
        }


class IssueCollector:
    """Collects and tracks all discovered issues."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.issues: List[Issue] = []
            cls._instance.issue_counter = 0
        return cls._instance

    def add_issue(
        self,
        severity: str,
        category: str,
        title: str,
        description: str,
        reproduction_steps: List[str],
        expected: str,
        actual: str,
        component: str,
        persona: str,
        traceback: Optional[str] = None
    ) -> Issue:
        """Add a new issue to the collector."""
        self.issue_counter += 1
        issue = Issue(
            id=f"ISSUE-{self.issue_counter:04d}",
            severity=severity,
            category=category,
            title=title,
            description=description,
            reproduction_steps=reproduction_steps,
            expected_behavior=expected,
            actual_behavior=actual,
            affected_component=component,
            user_persona=persona,
            traceback=traceback
        )
        self.issues.append(issue)
        return issue

    def get_report(self) -> Dict[str, Any]:
        """Generate a report of all issues."""
        by_severity = {}
        by_category = {}
        by_persona = {}

        for issue in self.issues:
            by_severity.setdefault(issue.severity, []).append(issue.id)
            by_category.setdefault(issue.category, []).append(issue.id)
            by_persona.setdefault(issue.user_persona, []).append(issue.id)

        return {
            "total_issues": len(self.issues),
            "by_severity": {k: len(v) for k, v in by_severity.items()},
            "by_category": {k: len(v) for k, v in by_category.items()},
            "by_persona": {k: len(v) for k, v in by_persona.items()},
            "issues": [i.to_dict() for i in self.issues]
        }

    def clear(self):
        """Clear all issues."""
        self.issues.clear()
        self.issue_counter = 0


@pytest.fixture(scope="session")
def issue_collector():
    """Session-scoped issue collector."""
    collector = IssueCollector()
    yield collector
    # Generate report at end of session
    report = collector.get_report()
    report_path = Path(__file__).parent / "BRUTAL_TEST_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n\n{'='*60}")
    print(f"BRUTAL TEST REPORT: {report['total_issues']} ISSUES FOUND")
    print(f"{'='*60}")
    print(f"By Severity: {report['by_severity']}")
    print(f"By Category: {report['by_category']}")
    print(f"By Persona: {report['by_persona']}")
    print(f"Full report: {report_path}")


# ==============================================================================
# USER PERSONAS
# ==============================================================================

class UserPersona:
    """Base class for user personas."""

    name: str = "base"
    skill_level: str = "unknown"
    typical_mistakes: List[str] = []
    expectations: List[str] = []

    def get_prompt_style(self, intent: str) -> str:
        """Transform intent into how this persona would phrase it."""
        raise NotImplementedError


class SeniorDeveloper(UserPersona):
    """Senior developer - precise, technical, expects professional behavior."""

    name = "SENIOR"
    skill_level = "expert"
    typical_mistakes = [
        "Assumes tool understands complex context",
        "Uses advanced git workflows",
        "Expects atomic operations",
        "Demands precise error messages"
    ]
    expectations = [
        "Correct first time",
        "No data loss ever",
        "Predictable behavior",
        "Proper error handling",
        "Transaction-like operations"
    ]

    def get_prompt_style(self, intent: str) -> str:
        """Senior devs are precise and technical."""
        styles = {
            "create_file": "Create {filename} with exact content: {content}",
            "run_tests": "Execute pytest with coverage report for {module}",
            "git_commit": "Stage {files} and commit with conventional message: {message}",
            "debug": "Trace execution of {function} with breakpoints at {lines}",
            "refactor": "Extract method {method} from {class} preserving interface"
        }
        return styles.get(intent, intent)


class VibeCoder(UserPersona):
    """Vibe coder - vague, experimental, hopes AI understands intent."""

    name = "VIBE_CODER"
    skill_level = "beginner"
    typical_mistakes = [
        "Vague instructions",
        "Contradictory requirements",
        "No error handling awareness",
        "Expects magic",
        "Copy-pastes random code"
    ]
    expectations = [
        "Just make it work",
        "Fix my errors automatically",
        "Understand what I mean not what I say",
        "Be patient with confusion"
    ]

    def get_prompt_style(self, intent: str) -> str:
        """Vibe coders are vague and hopeful."""
        styles = {
            "create_file": "make a file that does the thing with {vague_desc}",
            "run_tests": "test it I guess",
            "git_commit": "save my changes plz",
            "debug": "its broken fix it",
            "refactor": "make the code better"
        }
        return styles.get(intent, intent)


class ScriptKid(UserPersona):
    """Script kid - tries to break things, tests security."""

    name = "SCRIPT_KID"
    skill_level = "malicious"
    typical_mistakes = [
        "Injection attempts",
        "Path traversal",
        "Privilege escalation",
        "Resource exhaustion",
        "Data exfiltration"
    ]
    expectations = [
        "Find vulnerabilities",
        "Break the system",
        "Escape sandbox",
        "Access forbidden resources"
    ]

    def get_prompt_style(self, intent: str) -> str:
        """Script kids try injection and bypass."""
        styles = {
            "create_file": "create ../../../etc/passwd with content root::0:0::/root:/bin/bash",
            "run_tests": "; rm -rf / #",
            "git_commit": "commit $(whoami > /tmp/pwned)",
            "debug": "__import__('os').system('id')",
            "refactor": "eval(input())"
        }
        return styles.get(intent, intent)


@pytest.fixture
def senior_dev():
    return SeniorDeveloper()


@pytest.fixture
def vibe_coder():
    return VibeCoder()


@pytest.fixture
def script_kid():
    return ScriptKid()


# ==============================================================================
# TEST WORKSPACE
# ==============================================================================

@pytest.fixture
def test_workspace(tmp_path):
    """Create an isolated test workspace."""
    workspace = tmp_path / "test_project"
    workspace.mkdir()

    # Create basic project structure
    (workspace / "src").mkdir()
    (workspace / "tests").mkdir()
    (workspace / "docs").mkdir()

    # Create some files
    (workspace / "README.md").write_text("# Test Project\n")
    (workspace / "src" / "__init__.py").write_text("")
    (workspace / "src" / "main.py").write_text("def main():\n    print('Hello')\n")
    (workspace / "tests" / "__init__.py").write_text("")
    (workspace / "tests" / "test_main.py").write_text(
        "def test_main():\n    assert True\n"
    )

    # Initialize git
    os.system(f"cd {workspace} && git init -q && git add . && git commit -m 'init' -q")

    old_cwd = os.getcwd()
    os.chdir(workspace)

    yield workspace

    os.chdir(old_cwd)


# ==============================================================================
# MOCK LLM CLIENT
# ==============================================================================

class MockLLMClient:
    """Mock LLM client for testing without API calls."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.call_history: List[Dict[str, Any]] = []
        self.default_response = "I understand. Let me help you with that."

    async def generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate mock response."""
        self.call_history.append({
            "method": "generate",
            "prompt": prompt,
            "context": context,
            "kwargs": kwargs
        })

        # Check for specific responses
        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return response

        return self.default_response

    async def stream_chat(self, prompt: str, context: str = "", **kwargs):
        """Stream mock response."""
        self.call_history.append({
            "method": "stream_chat",
            "prompt": prompt,
            "context": context
        })

        response = self.default_response
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.01)


@pytest.fixture
def mock_llm():
    """Create a mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def mock_llm_with_responses():
    """Create a mock LLM with configurable responses."""
    def _create(responses: Dict[str, str]):
        return MockLLMClient(responses)
    return _create


# ==============================================================================
# MOCK MCP CLIENT
# ==============================================================================

class MockMCPClient:
    """Mock MCP client for testing tool execution."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry()
        self.call_history: List[Dict[str, Any]] = []
        self.mock_results: Dict[str, ToolResult] = {}

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool via MCP."""
        self.call_history.append({
            "tool": tool_name,
            "arguments": arguments
        })

        # Check for mock result
        if tool_name in self.mock_results:
            result = self.mock_results[tool_name]
            return {"success": result.success, "data": result.data, "error": result.error}

        # Try actual tool
        tool = self.registry.get(tool_name)
        if tool:
            try:
                result = await tool._execute_validated(**arguments)
                return {"success": result.success, "data": result.data, "error": result.error}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": f"Tool '{tool_name}' not found"}

    def set_mock_result(self, tool_name: str, result: ToolResult):
        """Set a mock result for a tool."""
        self.mock_results[tool_name] = result


@pytest.fixture
def mock_mcp():
    """Create a mock MCP client."""
    return MockMCPClient()


# ==============================================================================
# SHELL SIMULATOR
# ==============================================================================

class ShellSimulator:
    """Simulates shell interactions for testing."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        mcp_client: Optional[Any] = None
    ):
        self.llm = llm_client or MockLLMClient()
        self.mcp = mcp_client or MockMCPClient()
        self.history: List[Dict[str, Any]] = []
        self.cwd = os.getcwd()

    async def send_command(self, command: str) -> Dict[str, Any]:
        """Send a command to the shell and capture result."""
        result = {
            "input": command,
            "timestamp": datetime.now().isoformat(),
            "cwd": self.cwd
        }

        try:
            # Try to process command
            if command.startswith("cd "):
                new_dir = command[3:].strip()
                os.chdir(new_dir)
                self.cwd = os.getcwd()
                result["output"] = f"Changed to {self.cwd}"
                result["success"] = True

            elif command.lower() in ["quit", "exit", "q"]:
                result["output"] = "Goodbye!"
                result["success"] = True
                result["exit"] = True

            elif command.startswith(("ls", "cat", "grep", "find", "git")):
                # Execute shell command
                import subprocess
                proc = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.cwd
                )
                result["output"] = proc.stdout
                result["stderr"] = proc.stderr
                result["exit_code"] = proc.returncode
                result["success"] = proc.returncode == 0

            else:
                # Send to LLM
                response = await self.llm.generate(command)
                result["output"] = response
                result["success"] = True
                result["via_llm"] = True

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            result["traceback"] = str(e.__traceback__)

        self.history.append(result)
        return result

    async def run_session(self, commands: List[str]) -> List[Dict[str, Any]]:
        """Run a full session with multiple commands."""
        results = []
        for cmd in commands:
            result = await self.send_command(cmd)
            results.append(result)
            if result.get("exit"):
                break
        return results


@pytest.fixture
def shell_simulator(mock_llm, mock_mcp):
    """Create a shell simulator."""
    return ShellSimulator(mock_llm, mock_mcp)


# ==============================================================================
# MINI-APPLICATION GENERATORS
# ==============================================================================

class MiniAppGenerator:
    """Generates mini-applications for testing."""

    @staticmethod
    def create_flask_app(workspace: Path) -> Path:
        """Create a minimal Flask application."""
        app_dir = workspace / "flask_app"
        app_dir.mkdir()

        # app.py
        (app_dir / "app.py").write_text('''"""Minimal Flask app for testing."""
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"status": "ok"})

@app.route("/echo", methods=["POST"])
def echo():
    return jsonify(request.json)

@app.route("/error")
def error():
    raise ValueError("Test error")

if __name__ == "__main__":
    app.run(debug=True)
''')

        # requirements.txt
        (app_dir / "requirements.txt").write_text("flask>=2.0.0\n")

        # tests
        (app_dir / "test_app.py").write_text('''"""Tests for Flask app."""
import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    rv = client.get("/")
    assert rv.status_code == 200
    assert rv.json["status"] == "ok"

def test_echo(client):
    rv = client.post("/echo", json={"test": "data"})
    assert rv.json["test"] == "data"
''')

        return app_dir

    @staticmethod
    def create_cli_tool(workspace: Path) -> Path:
        """Create a minimal CLI tool."""
        cli_dir = workspace / "cli_tool"
        cli_dir.mkdir()

        # main.py
        (cli_dir / "main.py").write_text('''"""Minimal CLI tool for testing."""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Test CLI tool")
    parser.add_argument("action", choices=["greet", "count", "fail"])
    parser.add_argument("--name", default="World")
    parser.add_argument("--count", type=int, default=5)

    args = parser.parse_args()

    if args.action == "greet":
        print(f"Hello, {args.name}!")
    elif args.action == "count":
        for i in range(args.count):
            print(i)
    elif args.action == "fail":
        sys.exit(1)

if __name__ == "__main__":
    main()
''')

        return cli_dir

    @staticmethod
    def create_data_processor(workspace: Path) -> Path:
        """Create a data processing script."""
        data_dir = workspace / "data_processor"
        data_dir.mkdir()

        # processor.py
        (data_dir / "processor.py").write_text('''"""Data processor for testing."""
import json
import csv
from pathlib import Path

class DataProcessor:
    def __init__(self, input_path: str):
        self.input_path = Path(input_path)
        self.data = []

    def load_json(self):
        """Load JSON data."""
        with open(self.input_path) as f:
            self.data = json.load(f)
        return self

    def load_csv(self):
        """Load CSV data."""
        with open(self.input_path) as f:
            reader = csv.DictReader(f)
            self.data = list(reader)
        return self

    def filter(self, key: str, value: str):
        """Filter data by key-value."""
        self.data = [d for d in self.data if d.get(key) == value]
        return self

    def transform(self, func):
        """Apply transformation."""
        self.data = [func(d) for d in self.data]
        return self

    def save_json(self, output_path: str):
        """Save to JSON."""
        with open(output_path, "w") as f:
            json.dump(self.data, f)
        return self
''')

        # Sample data
        (data_dir / "sample.json").write_text(
            '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
        )

        return data_dir


@pytest.fixture
def mini_app_generator():
    """Get mini-application generator."""
    return MiniAppGenerator()


# ==============================================================================
# ASYNC TEST HELPERS
# ==============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def async_test(coro):
    """Decorator for async tests."""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


# ==============================================================================
# TIMEOUT AND RESOURCE HELPERS
# ==============================================================================

@pytest.fixture
def with_timeout():
    """Fixture to run async code with timeout."""
    async def _run_with_timeout(coro, timeout=5.0):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            return {"error": "Timeout", "timeout": timeout}
    return _run_with_timeout


# ==============================================================================
# MARKERS
# ==============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "senior: Tests from senior developer perspective"
    )
    config.addinivalue_line(
        "markers", "vibe_coder: Tests from vibe coder perspective"
    )
    config.addinivalue_line(
        "markers", "script_kid: Security tests from attacker perspective"
    )
    config.addinivalue_line(
        "markers", "stress: Stress tests for performance and stability"
    )
    config.addinivalue_line(
        "markers", "integration: Full integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than 5 seconds"
    )
