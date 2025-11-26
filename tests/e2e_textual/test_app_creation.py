"""E2E Tests: Application Creation Workflows.

Tests the ability to create complete applications from scratch.
"""

import pytest
import asyncio
import time
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from .conftest import TestResult, get_report


class TestAppCreation:
    """Test application creation workflows."""

    @pytest.mark.asyncio
    async def test_create_fastapi_app(self, temp_project, e2e_report, screenshots_dir):
        """Test creating a complete FastAPI application."""
        start_time = time.time()
        result = TestResult(
            name="create_fastapi_app",
            status="passed",
            duration=0.0,
            metadata={"project_type": "FastAPI", "path": str(temp_project)}
        )

        try:
            # Import tools
            from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool
            from jdev_cli.tools.search import SearchFilesTool

            write_tool = WriteFileTool()
            read_tool = ReadFileTool()

            # 1. Create main.py
            main_content = '''"""FastAPI Application - Created by Juan-Dev-Code E2E Test."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
    title="E2E Test API",
    description="API created during E2E testing",
    version="1.0.0"
)

class Item(BaseModel):
    """Item model."""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    quantity: int = 0

# In-memory database
items_db: List[Item] = []
next_id = 1

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to E2E Test API", "status": "operational"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "items_count": len(items_db)}

@app.get("/items", response_model=List[Item])
async def list_items():
    """List all items."""
    return items_db

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    """Get item by ID."""
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items", response_model=Item)
async def create_item(item: Item):
    """Create new item."""
    global next_id
    item.id = next_id
    next_id += 1
    items_db.append(item)
    return item

@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, updated: Item):
    """Update existing item."""
    for i, item in enumerate(items_db):
        if item.id == item_id:
            updated.id = item_id
            items_db[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    """Delete item."""
    for i, item in enumerate(items_db):
        if item.id == item_id:
            items_db.pop(i)
            return {"message": "Item deleted"}
    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
            write_result = await write_tool._execute_validated(
                path=str(temp_project / "main.py"),
                content=main_content
            )
            assert write_result.success, f"Failed to write main.py: {write_result.error}"
            result.logs.append("✓ Created main.py")

            # 2. Create requirements.txt
            requirements = '''fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
pytest>=7.4.0
httpx>=0.25.0
'''
            write_result = await write_tool._execute_validated(
                path=str(temp_project / "requirements.txt"),
                content=requirements
            )
            assert write_result.success
            result.logs.append("✓ Created requirements.txt")

            # 3. Create tests
            test_content = '''"""Tests for FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_item():
    """Test item creation."""
    item = {"name": "Test Item", "price": 9.99, "quantity": 5}
    response = client.post("/items", json=item)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["id"] is not None

def test_list_items():
    """Test listing items."""
    response = client.get("/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_nonexistent_item():
    """Test getting nonexistent item."""
    response = client.get("/items/99999")
    assert response.status_code == 404
'''
            (temp_project / "tests").mkdir(exist_ok=True)
            write_result = await write_tool._execute_validated(
                path=str(temp_project / "tests" / "test_api.py"),
                content=test_content
            )
            assert write_result.success
            result.logs.append("✓ Created tests/test_api.py")

            # 4. Create README
            readme = '''# E2E Test API

FastAPI application created during E2E testing of Juan-Dev-Code.

## Features

- CRUD operations for items
- Health check endpoint
- OpenAPI documentation at `/docs`

## Running

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Testing

```bash
pytest tests/
```

---
🤖 Generated by Juan-Dev-Code E2E Test Suite
'''
            write_result = await write_tool._execute_validated(
                path=str(temp_project / "README.md"),
                content=readme
            )
            assert write_result.success
            result.logs.append("✓ Created README.md")

            # 5. Verify all files exist
            files_created = list(temp_project.glob("**/*.py")) + list(temp_project.glob("*.txt")) + list(temp_project.glob("*.md"))
            result.metadata["files_created"] = [str(f.relative_to(temp_project)) for f in files_created]
            result.metadata["total_files"] = len(files_created)

            # 6. Read back and verify content
            read_result = await read_tool._execute_validated(path=str(temp_project / "main.py"))
            assert read_result.success
            assert "FastAPI" in read_result.data["content"]
            assert "@app.get" in read_result.data["content"]
            result.logs.append("✓ Verified main.py content")

            result.status = "passed"
            result.metadata["success"] = True

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.metadata["success"] = False

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_create_cli_tool(self, temp_project, e2e_report):
        """Test creating a CLI tool with Typer."""
        start_time = time.time()
        result = TestResult(
            name="create_cli_tool",
            status="passed",
            duration=0.0,
            metadata={"project_type": "CLI Tool"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool

            write_tool = WriteFileTool()

            # Create CLI app
            cli_content = '''"""CLI Tool - Created by Juan-Dev-Code."""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="E2E Test CLI Tool")
console = Console()

@app.command()
def hello(name: str = typer.Argument("World", help="Name to greet")):
    """Say hello to someone."""
    console.print(f"[green]Hello, {name}![/green]")

@app.command()
def list_files(
    path: Path = typer.Argument(".", help="Directory path"),
    pattern: str = typer.Option("*", "-p", "--pattern", help="Glob pattern")
):
    """List files in directory."""
    table = Table(title=f"Files in {path}")
    table.add_column("Name", style="cyan")
    table.add_column("Size", style="green")
    table.add_column("Type", style="yellow")

    for file in path.glob(pattern):
        size = file.stat().st_size if file.is_file() else "-"
        ftype = "📁" if file.is_dir() else "📄"
        table.add_row(file.name, str(size), ftype)

    console.print(table)

@app.command()
def count(
    path: Path = typer.Argument(".", help="Directory to count"),
    recursive: bool = typer.Option(False, "-r", "--recursive", help="Count recursively")
):
    """Count files in directory."""
    pattern = "**/*" if recursive else "*"
    files = list(path.glob(pattern))
    dirs = sum(1 for f in files if f.is_dir())
    regular = sum(1 for f in files if f.is_file())

    console.print(f"[cyan]Directories:[/cyan] {dirs}")
    console.print(f"[green]Files:[/green] {regular}")
    console.print(f"[yellow]Total:[/yellow] {len(files)}")

if __name__ == "__main__":
    app()
'''
            write_result = await write_tool._execute_validated(
                path=str(temp_project / "cli.py"),
                content=cli_content
            )
            assert write_result.success
            result.logs.append("✓ Created cli.py")

            # Verify
            assert (temp_project / "cli.py").exists()
            content = (temp_project / "cli.py").read_text()
            assert "typer" in content
            assert "@app.command" in content

            result.metadata["lines_of_code"] = len(content.splitlines())

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_create_python_package(self, temp_project, e2e_report):
        """Test creating a complete Python package structure."""
        start_time = time.time()
        result = TestResult(
            name="create_python_package",
            status="passed",
            duration=0.0,
            metadata={"project_type": "Python Package"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool

            write_tool = WriteFileTool()

            # Package structure
            pkg_name = "mypackage"
            (temp_project / pkg_name).mkdir()
            (temp_project / pkg_name / "core").mkdir()
            (temp_project / pkg_name / "utils").mkdir()
            (temp_project / "tests").mkdir(exist_ok=True)

            # __init__.py files
            await write_tool._execute_validated(
                path=str(temp_project / pkg_name / "__init__.py"),
                content=f'"""Package {pkg_name}."""\n\n__version__ = "0.1.0"\n'
            )
            await write_tool._execute_validated(
                path=str(temp_project / pkg_name / "core" / "__init__.py"),
                content='"""Core module."""\n'
            )
            await write_tool._execute_validated(
                path=str(temp_project / pkg_name / "utils" / "__init__.py"),
                content='"""Utilities module."""\n'
            )

            # pyproject.toml
            pyproject = f'''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{pkg_name}"
version = "0.1.0"
description = "A test package created by Juan-Dev-Code"
readme = "README.md"
requires-python = ">=3.9"
license = {{text = "MIT"}}
authors = [
    {{name = "E2E Test", email = "test@example.com"}}
]
dependencies = [
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[tool.ruff]
line-length = 100
target-version = "py39"

[tool.black]
line-length = 100
target-version = ["py39"]
'''
            await write_tool._execute_validated(
                path=str(temp_project / "pyproject.toml"),
                content=pyproject
            )
            result.logs.append("✓ Created pyproject.toml")

            # Core module
            core_content = '''"""Core functionality."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Config:
    """Configuration class."""
    debug: bool = False
    verbose: bool = False
    max_items: int = 100


class Engine:
    """Main engine class."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the engine."""
        self._initialized = True
        return True

    def process(self, items: List[str]) -> List[str]:
        """Process items."""
        if not self._initialized:
            raise RuntimeError("Engine not initialized")
        return [item.upper() for item in items[:self.config.max_items]]
'''
            await write_tool._execute_validated(
                path=str(temp_project / pkg_name / "core" / "engine.py"),
                content=core_content
            )

            # Utils module
            utils_content = '''"""Utility functions."""

import hashlib
from typing import Any


def hash_string(s: str) -> str:
    """Hash a string using SHA256."""
    return hashlib.sha256(s.encode()).hexdigest()


def safe_get(d: dict, key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary."""
    try:
        return d.get(key, default)
    except (AttributeError, TypeError):
        return default


def chunk_list(lst: list, size: int) -> list:
    """Split a list into chunks."""
    return [lst[i:i + size] for i in range(0, len(lst), size)]
'''
            await write_tool._execute_validated(
                path=str(temp_project / pkg_name / "utils" / "helpers.py"),
                content=utils_content
            )

            # Count created files
            all_files = list(temp_project.rglob("*.py")) + list(temp_project.rglob("*.toml"))
            result.metadata["files_created"] = len(all_files)
            result.metadata["package_structure"] = [
                str(f.relative_to(temp_project)) for f in all_files
            ]
            result.logs.append(f"✓ Created {len(all_files)} files")

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestMultiFileCreation:
    """Test creating multiple related files."""

    @pytest.mark.asyncio
    async def test_create_microservice(self, temp_project, e2e_report):
        """Test creating a microservice with multiple components."""
        start_time = time.time()
        result = TestResult(
            name="create_microservice",
            status="passed",
            duration=0.0,
            metadata={"project_type": "Microservice"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool

            write_tool = WriteFileTool()

            # Create directory structure
            for dir_name in ["app", "app/api", "app/models", "app/services", "tests"]:
                (temp_project / dir_name).mkdir(exist_ok=True)

            files_to_create = {
                "app/__init__.py": '"""Microservice app."""\n',
                "app/api/__init__.py": '"""API routes."""\n',
                "app/models/__init__.py": '"""Data models."""\n',
                "app/services/__init__.py": '"""Business services."""\n',
                "app/config.py": '''"""Configuration."""
import os

class Settings:
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

settings = Settings()
''',
                "app/models/user.py": '''"""User model."""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: bool = True
    role: str = "user"
''',
                "app/services/user_service.py": '''"""User service."""
from typing import List, Optional
from ..models.user import User
from datetime import datetime

class UserService:
    def __init__(self):
        self._users = {}
        self._next_id = 1

    def create(self, username: str, email: str) -> User:
        user = User(
            id=self._next_id,
            username=username,
            email=email,
            created_at=datetime.now()
        )
        self._users[user.id] = user
        self._next_id += 1
        return user

    def get(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def list_all(self) -> List[User]:
        return list(self._users.values())
''',
                "app/api/users.py": '''"""User API routes."""
from fastapi import APIRouter, HTTPException
from ..services.user_service import UserService
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])
service = UserService()

class CreateUserRequest(BaseModel):
    username: str
    email: str

@router.post("/")
def create_user(req: CreateUserRequest):
    user = service.create(req.username, req.email)
    return {"id": user.id, "username": user.username}

@router.get("/{user_id}")
def get_user(user_id: int):
    user = service.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
''',
                "Dockerfile": '''FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
''',
                "docker-compose.yml": '''version: "3.8"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=true
    volumes:
      - .:/app
'''
            }

            for path, content in files_to_create.items():
                await write_tool._execute_validated(
                    path=str(temp_project / path),
                    content=content
                )
                result.logs.append(f"✓ Created {path}")

            result.metadata["files_created"] = len(files_to_create)
            result.metadata["has_docker"] = True
            result.metadata["has_tests_dir"] = True

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error
