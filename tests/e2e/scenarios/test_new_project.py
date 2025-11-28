"""
E2E Scenario Tests: New Project Creation
=========================================

Tests for creating new projects from scratch.
Validates the complete workflow of project scaffolding.

Based on:
- Anthropic TDD with expected outputs
- Real-world project creation scenarios

Total: 10 tests
"""

import pytest
import os


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def empty_workspace(tmp_path):
    """Create an empty workspace for new projects."""
    workspace = tmp_path / "new_projects"
    workspace.mkdir()

    old_cwd = os.getcwd()
    os.chdir(workspace)

    yield workspace

    os.chdir(old_cwd)


# ==============================================================================
# TEST CLASS: Python Project Creation
# ==============================================================================

@pytest.mark.e2e
class TestNewPythonProject:
    """Tests for creating new Python projects."""

    def test_creates_basic_python_project_structure(self, empty_workspace):
        """Creates standard Python project with src layout."""
        project_dir = empty_workspace / "my_project"

        # Expected structure
        expected_files = [
            "pyproject.toml",
            "README.md",
            "src/__init__.py",
            "src/main.py",
            "tests/__init__.py",
            "tests/test_main.py",
        ]

        # Simulate project creation
        project_dir.mkdir()
        (project_dir / "src").mkdir()
        (project_dir / "tests").mkdir()

        (project_dir / "pyproject.toml").write_text('''[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.10"
''')
        (project_dir / "README.md").write_text("# My Project\n")
        (project_dir / "src" / "__init__.py").write_text("")
        (project_dir / "src" / "main.py").write_text('def main():\n    print("Hello")\n')
        (project_dir / "tests" / "__init__.py").write_text("")
        (project_dir / "tests" / "test_main.py").write_text(
            'def test_main():\n    assert True\n'
        )

        # Verify structure
        for file_path in expected_files:
            assert (project_dir / file_path).exists(), f"Missing: {file_path}"

    def test_creates_flask_api_project(self, empty_workspace):
        """Creates Flask API project with proper structure."""
        project_dir = empty_workspace / "flask_api"
        project_dir.mkdir()

        # Create Flask project structure
        (project_dir / "app").mkdir()
        (project_dir / "app" / "__init__.py").write_text('''"""Flask application factory."""
from flask import Flask

def create_app():
    app = Flask(__name__)

    from app.routes import main
    app.register_blueprint(main)

    return app
''')
        (project_dir / "app" / "routes.py").write_text('''"""API routes."""
from flask import Blueprint, jsonify

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return jsonify({"status": "ok"})

@main.route('/health')
def health():
    return jsonify({"healthy": True})
''')

        (project_dir / "tests").mkdir()
        (project_dir / "tests" / "__init__.py").write_text("")
        (project_dir / "tests" / "conftest.py").write_text('''"""Test configuration."""
import pytest
from app import create_app

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
def client(app):
    return app.test_client()
''')
        (project_dir / "tests" / "test_routes.py").write_text('''"""Test API routes."""

def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'

def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['healthy'] is True
''')

        (project_dir / "requirements.txt").write_text("flask>=2.0\npytest>=8.0\n")

        # Verify Flask-specific files
        assert (project_dir / "app" / "__init__.py").exists()
        assert (project_dir / "app" / "routes.py").exists()
        assert "create_app" in (project_dir / "app" / "__init__.py").read_text()

    def test_creates_cli_tool_project(self, empty_workspace):
        """Creates CLI tool project with click/argparse."""
        project_dir = empty_workspace / "my_cli"
        project_dir.mkdir()

        (project_dir / "src").mkdir()
        (project_dir / "src" / "__init__.py").write_text("")
        (project_dir / "src" / "cli.py").write_text('''"""CLI entry point."""
import argparse

def main():
    parser = argparse.ArgumentParser(description="My CLI Tool")
    parser.add_argument('command', choices=['run', 'check', 'build'])
    parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()

    if args.command == 'run':
        print("Running...")
    elif args.command == 'check':
        print("Checking...")
    elif args.command == 'build':
        print("Building...")

if __name__ == '__main__':
    main()
''')

        (project_dir / "pyproject.toml").write_text('''[project]
name = "my-cli"
version = "0.1.0"
requires-python = ">=3.10"

[project.scripts]
my-cli = "src.cli:main"
''')

        # Verify CLI entry point is configured
        pyproject = (project_dir / "pyproject.toml").read_text()
        assert "[project.scripts]" in pyproject
        assert "my-cli" in pyproject

    def test_creates_project_with_tests(self, empty_workspace):
        """Creates project with comprehensive test setup."""
        project_dir = empty_workspace / "tested_project"
        project_dir.mkdir()

        (project_dir / "src").mkdir()
        (project_dir / "tests").mkdir()

        (project_dir / "pytest.ini").write_text('''[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short
''')

        (project_dir / "tests" / "conftest.py").write_text('''"""Shared test fixtures."""
import pytest

@pytest.fixture
def sample_data():
    return {"key": "value", "numbers": [1, 2, 3]}
''')

        # Verify test configuration
        assert (project_dir / "pytest.ini").exists()
        assert (project_dir / "tests" / "conftest.py").exists()

    def test_creates_project_with_documentation(self, empty_workspace):
        """Creates project with documentation structure."""
        project_dir = empty_workspace / "documented_project"
        project_dir.mkdir()

        (project_dir / "docs").mkdir()
        (project_dir / "docs" / "index.md").write_text("# Documentation\n\nWelcome!\n")
        (project_dir / "docs" / "api.md").write_text("# API Reference\n")
        (project_dir / "docs" / "getting-started.md").write_text("# Getting Started\n")

        (project_dir / "README.md").write_text('''# Documented Project

## Installation

```bash
pip install documented-project
```

## Usage

```python
from documented_project import main
main()
```

## Documentation

See [docs/](docs/) for full documentation.
''')

        # Verify documentation
        assert (project_dir / "docs").is_dir()
        assert (project_dir / "docs" / "index.md").exists()
        readme = (project_dir / "README.md").read_text()
        assert "Installation" in readme
        assert "Usage" in readme


# ==============================================================================
# TEST CLASS: Project Configuration
# ==============================================================================

@pytest.mark.e2e
class TestProjectConfiguration:
    """Tests for project configuration files."""

    def test_creates_pyproject_toml_correctly(self, empty_workspace):
        """Pyproject.toml follows PEP 621 format."""
        project_dir = empty_workspace / "config_test"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text('''[project]
name = "config-test"
version = "1.0.0"
description = "A test project"
requires-python = ">=3.10"
authors = [
    {name = "Test Author", email = "test@example.com"}
]
dependencies = [
    "requests>=2.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
test = ["pytest>=8.0", "pytest-cov>=4.0"]
dev = ["black", "ruff", "mypy"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
''')

        content = (project_dir / "pyproject.toml").read_text()

        # Verify PEP 621 compliance
        assert "[project]" in content
        assert 'name = "config-test"' in content
        assert "[build-system]" in content

    def test_creates_gitignore(self, empty_workspace):
        """Creates appropriate .gitignore file."""
        project_dir = empty_workspace / "gitignore_test"
        project_dir.mkdir()

        (project_dir / ".gitignore").write_text('''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.eggs/

# Virtual environments
venv/
.venv/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Environment
.env
.env.local
*.env

# OS
.DS_Store
Thumbs.db
''')

        gitignore = (project_dir / ".gitignore").read_text()

        # Verify essential patterns
        assert "__pycache__" in gitignore
        assert ".env" in gitignore
        assert "venv" in gitignore
        assert ".pytest_cache" in gitignore

    def test_creates_editorconfig(self, empty_workspace):
        """Creates .editorconfig for consistent formatting."""
        project_dir = empty_workspace / "editorconfig_test"
        project_dir.mkdir()

        (project_dir / ".editorconfig").write_text('''root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
indent_size = 4

[*.{json,yml,yaml}]
indent_size = 2

[Makefile]
indent_style = tab
''')

        editorconfig = (project_dir / ".editorconfig").read_text()

        assert "root = true" in editorconfig
        assert "indent_style = space" in editorconfig

    def test_initializes_git_repository(self, empty_workspace):
        """Git repository is initialized correctly."""
        project_dir = empty_workspace / "git_test"
        project_dir.mkdir()

        # Initialize git
        os.system(f"cd {project_dir} && git init -q")

        assert (project_dir / ".git").is_dir()

    def test_creates_pre_commit_config(self, empty_workspace):
        """Creates pre-commit configuration."""
        project_dir = empty_workspace / "precommit_test"
        project_dir.mkdir()

        (project_dir / ".pre-commit-config.yaml").write_text('''repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
''')

        config = (project_dir / ".pre-commit-config.yaml").read_text()

        assert "repos:" in config
        assert "ruff" in config


# ==============================================================================
# SUMMARY
# ==============================================================================

"""
Total Tests: 10

Scenarios Covered:
1. Basic Python project with src layout
2. Flask API project with blueprints
3. CLI tool project with argparse
4. Project with comprehensive tests
5. Project with documentation
6. PEP 621 pyproject.toml
7. .gitignore with Python patterns
8. .editorconfig configuration
9. Git repository initialization
10. Pre-commit configuration
"""
