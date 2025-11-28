"""
Comprehensive E2E Tests: Integration Workflows
===============================================

Tests complete end-to-end workflows combining multiple tools, agents, and operations.
Real world scenarios without mocks.

Author: JuanCS Dev
Date: 2025-11-27
"""

import pytest
import subprocess


class TestCompleteFeatureImplementation:
    """Test implementing complete features from scratch."""

    @pytest.mark.asyncio
    async def test_implement_crud_api(self, temp_project):
        """Test implementing complete CRUD API."""
        from jdev_cli.tools.file_ops import WriteFileTool
        from jdev_cli.tools.search import SearchFilesTool

        write_tool = WriteFileTool()
        search_tool = SearchFilesTool()

        # Step 1: Create main API file
        api_code = '''"""CRUD API for products."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

class Product(BaseModel):
    id: int
    name: str
    price: float

# In-memory storage
products = {}
next_id = 1

@app.post("/products", response_model=Product)
async def create_product(product: Product):
    global next_id
    product.id = next_id
    products[next_id] = product
    next_id += 1
    return product

@app.get("/products", response_model=List[Product])
async def list_products():
    return list(products.values())

@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    return products[product_id]

@app.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, product: Product):
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    product.id = product_id
    products[product_id] = product
    return product

@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    del products[product_id]
    return {"message": "Product deleted"}
'''

        result = await write_tool._execute_validated(
            path=str(temp_project / "api.py"),
            content=api_code
        )
        assert result.success

        # Step 2: Create tests
        test_code = '''"""Tests for CRUD API."""
import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_create_product():
    response = client.post("/products", json={"name": "Test", "price": 9.99})
    assert response.status_code == 200
    assert response.json()["name"] == "Test"

def test_list_products():
    response = client.get("/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_product():
    create_resp = client.post("/products", json={"name": "Test", "price": 9.99})
    product_id = create_resp.json()["id"]

    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test"

def test_update_product():
    create_resp = client.post("/products", json={"name": "Test", "price": 9.99})
    product_id = create_resp.json()["id"]

    response = client.put(f"/products/{product_id}", json={"name": "Updated", "price": 19.99})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"

def test_delete_product():
    create_resp = client.post("/products", json={"name": "Test", "price": 9.99})
    product_id = create_resp.json()["id"]

    response = client.delete(f"/products/{product_id}")
    assert response.status_code == 200
'''

        result = await write_tool._execute_validated(
            path=str(temp_project / "test_api.py"),
            content=test_code
        )
        assert result.success

        # Step 3: Verify structure
        search_result = await search_tool._execute_validated(
            pattern="@app\\.",
            path=str(temp_project)
        )
        assert search_result.success
        assert len(search_result.data.get("matches", [])) >= 5  # 5 endpoints

    @pytest.mark.asyncio
    async def test_refactor_duplicate_code(self, temp_project):
        """Test complete refactoring workflow."""
        from jdev_cli.tools.file_ops import WriteFileTool, EditFileTool, ReadFileTool

        write_tool = WriteFileTool()
        edit_tool = EditFileTool()
        read_tool = ReadFileTool()

        # Step 1: Create file with duplicated code
        duplicated = '''def process_users(users):
    valid = []
    for user in users:
        if user.get("email") and "@" in user["email"]:
            valid.append(user)
    return valid

def process_admins(admins):
    valid = []
    for admin in admins:
        if admin.get("email") and "@" in admin["email"]:
            valid.append(admin)
    return valid
'''

        await write_tool._execute_validated(
            path=str(temp_project / "duplicate.py"),
            content=duplicated
        )

        # Step 2: Refactor to extract common function
        refactored = '''def validate_email_items(items):
    """Extract common validation logic."""
    valid = []
    for item in items:
        if item.get("email") and "@" in item["email"]:
            valid.append(item)
    return valid

def process_users(users):
    return validate_email_items(users)

def process_admins(admins):
    return validate_email_items(admins)
'''

        (temp_project / "duplicate.py").write_text(refactored)

        # Step 3: Verify refactoring
        read_result = await read_tool._execute_validated(
            path=str(temp_project / "duplicate.py")
        )
        assert read_result.success
        assert "validate_email_items" in read_result.data["content"]
        assert read_result.data["content"].count("for item in items") == 1  # Only once now


class TestSecurityWorkflows:
    """Test security-related workflows."""

    @pytest.mark.asyncio
    async def test_find_and_fix_hardcoded_secrets(self, sample_python_project):
        """Test finding and fixing hardcoded secrets."""
        from jdev_cli.tools.search import SearchFilesTool
        from jdev_cli.tools.file_ops import ReadFileTool, EditFileTool

        search_tool = SearchFilesTool()
        read_tool = ReadFileTool()
        edit_tool = EditFileTool()

        # Step 1: Find hardcoded secrets
        search_result = await search_tool._execute_validated(
            pattern='API_KEY.*=.*"sk-',
            path=str(sample_python_project)
        )

        assert search_result.success
        matches = search_result.data.get("matches", [])
        assert len(matches) > 0

        # Step 2: Read the file
        config_file = matches[0]["file"]
        read_result = await read_tool._execute_validated(path=config_file)
        assert read_result.success

        # Step 3: Fix by using environment variables
        edit_result = await edit_tool._execute_validated(
            path=config_file,
            edits=[{
                "search": 'API_KEY = "sk-test123456789"',
                "replace": 'API_KEY = os.getenv("API_KEY", "")'
            }],
            preview=False,
            create_backup=True
        )

        assert edit_result.success

    @pytest.mark.asyncio
    async def test_add_input_validation(self, temp_project):
        """Test adding input validation to unsafe code."""
        from jdev_cli.tools.file_ops import WriteFileTool, EditFileTool

        write_tool = WriteFileTool()
        edit_tool = EditFileTool()

        # Step 1: Create unsafe code
        unsafe_code = '''def process_user_input(user_input):
    # Unsafe - no validation
    result = eval(user_input)
    return result
'''

        await write_tool._execute_validated(
            path=str(temp_project / "unsafe.py"),
            content=unsafe_code
        )

        # Step 2: Add validation
        edit_result = await edit_tool._execute_validated(
            path=str(temp_project / "unsafe.py"),
            edits=[{
                "search": "def process_user_input(user_input):\n    # Unsafe - no validation\n    result = eval(user_input)\n    return result",
                "replace": '''def process_user_input(user_input):
    # Added validation
    if not isinstance(user_input, str):
        raise ValueError("Input must be string")
    if len(user_input) > 1000:
        raise ValueError("Input too long")
    # Still unsafe, but now commented
    # result = eval(user_input)  # UNSAFE: arbitrary code execution
    result = str(user_input)
    return result'''
            }],
            preview=False,
            create_backup=False
        )

        assert edit_result.success


class TestGitWorkflows:
    """Test complete git workflows."""

    @pytest.mark.asyncio
    async def test_complete_git_workflow(self, temp_project):
        """Test: init -> add -> commit -> status -> diff."""
        from jdev_cli.tools.git_ops import GitStatusTool, GitDiffTool
        from jdev_cli.tools.file_ops import WriteFileTool

        # Setup git
        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        write_tool = WriteFileTool()
        status_tool = GitStatusTool()
        diff_tool = GitDiffTool()

        # Step 1: Create and commit initial file
        await write_tool._execute_validated(
            path=str(temp_project / "file.txt"),
            content="version 1"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=temp_project)

        # Step 2: Check status (should be clean)
        status_result = await status_tool._execute_validated(path=str(temp_project))
        assert status_result.success
        assert len(status_result.data["modified"]) == 0

        # Step 3: Modify file
        (temp_project / "file.txt").write_text("version 2")

        # Step 4: Check status (should show modification)
        status_result = await status_tool._execute_validated(path=str(temp_project))
        assert status_result.success
        assert len(status_result.data["modified"]) > 0

        # Step 5: Check diff
        diff_result = await diff_tool._execute_validated(path=str(temp_project))
        assert diff_result.success
        assert diff_result.data["has_changes"]
        assert "version 1" in diff_result.data["diff"]
        assert "version 2" in diff_result.data["diff"]


class TestProjectGenerationWorkflows:
    """Test complete project generation."""

    @pytest.mark.asyncio
    async def test_generate_python_package(self, temp_project):
        """Test generating complete Python package structure."""
        from jdev_cli.tools.file_ops import WriteFileTool

        write_tool = WriteFileTool()

        # Create package structure
        files_to_create = [
            ("mypackage/__init__.py", '"""My package."""\n__version__ = "0.1.0"'),
            ("mypackage/core.py", "def main():\n    pass"),
            ("mypackage/utils.py", "def helper():\n    pass"),
            ("tests/__init__.py", ""),
            ("tests/test_core.py", "def test_main():\n    assert True"),
            ("README.md", "# My Package\n\nDescription here."),
            ("pyproject.toml", '[tool.poetry]\nname = "mypackage"\nversion = "0.1.0"'),
        ]

        for filepath, content in files_to_create:
            result = await write_tool._execute_validated(
                path=str(temp_project / filepath),
                content=content
            )
            assert result.success

        # Verify all files created
        assert (temp_project / "mypackage" / "__init__.py").exists()
        assert (temp_project / "tests" / "test_core.py").exists()
        assert (temp_project / "README.md").exists()
        assert (temp_project / "pyproject.toml").exists()

    @pytest.mark.asyncio
    async def test_generate_fastapi_project(self, temp_project):
        """Test generating FastAPI project."""
        from jdev_cli.tools.file_ops import WriteFileTool

        write_tool = WriteFileTool()

        files = [
            ("main.py", '''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
'''),
            ("models.py", '''from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
'''),
            ("requirements.txt", "fastapi>=0.104.0\nuvicorn>=0.24.0\npydantic>=2.5.0"),
            ("README.md", "# FastAPI Project\n\nRun with: `uvicorn main:app --reload`"),
        ]

        for filepath, content in files:
            result = await write_tool._execute_validated(
                path=str(temp_project / filepath),
                content=content
            )
            assert result.success

        # Verify structure
        assert (temp_project / "main.py").exists()
        assert (temp_project / "models.py").exists()
        assert (temp_project / "requirements.txt").exists()


class TestDataTransformationWorkflows:
    """Test data transformation workflows."""

    @pytest.mark.asyncio
    async def test_search_and_transform(self, sample_python_project):
        """Test searching and transforming code patterns."""
        from jdev_cli.tools.search import SearchFilesTool
        from jdev_cli.tools.file_ops import ReadFileTool

        search_tool = SearchFilesTool()
        read_tool = ReadFileTool()

        # Step 1: Find "def " pattern (simple, will match Python files)
        search_result = await search_tool._execute_validated(
            pattern="def ",
            path=str(sample_python_project)
        )

        assert search_result.success
        matches = search_result.data.get("matches", [])

        # If matches found, verify they're valid
        if len(matches) > 0:
            first_match = matches[0]
            read_result = await read_tool._execute_validated(path=first_match["file"])
            assert read_result.success

    @pytest.mark.asyncio
    async def test_batch_file_processing(self, temp_project):
        """Test processing multiple files in batch."""
        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool, EditFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()
        edit_tool = EditFileTool()

        # Step 1: Create multiple files
        for i in range(10):
            await write_tool._execute_validated(
                path=str(temp_project / f"file{i}.txt"),
                content=f"content {i}\nstatus: draft"
            )

        # Step 2: Batch update all files
        for i in range(10):
            filepath = str(temp_project / f"file{i}.txt")
            await edit_tool._execute_validated(
                path=filepath,
                edits=[{"search": "status: draft", "replace": "status: published"}],
                preview=False,
                create_backup=False
            )

        # Step 3: Verify all updated
        for i in range(10):
            read_result = await read_tool._execute_validated(
                path=str(temp_project / f"file{i}.txt")
            )
            assert read_result.success
            assert "status: published" in read_result.data["content"]


class TestComplexDependencyChains:
    """Test complex tool dependency chains."""

    @pytest.mark.asyncio
    async def test_multi_stage_pipeline(self, temp_project):
        """Test multi-stage data processing pipeline."""
        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool, EditFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()
        edit_tool = EditFileTool()

        # Stage 1: Create raw data
        await write_tool._execute_validated(
            path=str(temp_project / "data.txt"),
            content="raw,data,here\n1,2,3\n4,5,6"
        )

        # Stage 2: Read and process
        read_result = await read_tool._execute_validated(
            path=str(temp_project / "data.txt")
        )
        assert read_result.success

        # Stage 3: Transform
        await edit_tool._execute_validated(
            path=str(temp_project / "data.txt"),
            edits=[{"search": "raw", "replace": "processed"}],
            preview=False,
            create_backup=False
        )

        # Stage 4: Create derived file
        processed_content = (temp_project / "data.txt").read_text()
        await write_tool._execute_validated(
            path=str(temp_project / "summary.txt"),
            content=f"Summary of:\n{processed_content}"
        )

        # Verify pipeline output
        assert (temp_project / "data.txt").exists()
        assert (temp_project / "summary.txt").exists()
        assert "processed" in (temp_project / "summary.txt").read_text()


class TestErrorRecoveryWorkflows:
    """Test workflows with error handling and recovery."""

    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self, temp_project):
        """Test recovering from partial failures."""
        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()

        # Try to process 5 files, where some fail
        results = []
        for i in range(5):
            if i == 2:
                # Intentionally fail this one (invalid path)
                result = await write_tool._execute_validated(
                    path="/invalid/path/file.txt",
                    content="fail"
                )
            else:
                result = await write_tool._execute_validated(
                    path=str(temp_project / f"file{i}.txt"),
                    content=f"data{i}"
                )
            results.append(result)

        # 4 should succeed, 1 should fail
        successes = sum(1 for r in results if r.success)
        assert successes == 4

        # Retry failed operations
        failed_indices = [i for i, r in enumerate(results) if not r.success]
        for i in failed_indices:
            # Retry with valid path
            result = await write_tool._execute_validated(
                path=str(temp_project / f"file{i}_retry.txt"),
                content=f"retry{i}"
            )
            assert result.success
