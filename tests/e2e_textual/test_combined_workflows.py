"""E2E Tests: Combined Multi-Tool and Multi-Agent Workflows.

Tests complex scenarios that combine multiple tools and agents.
"""

import pytest
import asyncio
import time
from pathlib import Path

from .conftest import TestResult, get_report


class TestMultiToolWorkflows:
    """Test workflows combining multiple tools."""

    @pytest.mark.asyncio
    async def test_search_read_edit_workflow(self, sample_python_project, e2e_report):
        """Test: Search -> Read -> Edit workflow."""
        start_time = time.time()
        result = TestResult(
            name="search_read_edit_workflow",
            status="passed",
            duration=0.0,
            metadata={"workflow": "search_read_edit", "tools_used": 3}
        )

        try:
            from jdev_cli.tools.search import SearchFilesTool
            from jdev_cli.tools.file_ops import ReadFileTool, EditFileTool

            search_tool = SearchFilesTool()
            read_tool = ReadFileTool()
            edit_tool = EditFileTool()

            # Step 1: Search for "BUG" comments
            result.logs.append("Step 1: Searching for BUG comments...")
            search_result = await search_tool._execute_validated(
                pattern="BUG",
                path=str(sample_python_project),
                file_pattern="*.py"
            )

            assert search_result.success
            matches = search_result.data.get("matches", [])
            result.logs.append(f"  ✓ Found {len(matches)} files with BUG comments")

            if matches:
                bug_file = matches[0]["file"]

                # Step 2: Read the file
                result.logs.append(f"Step 2: Reading {Path(bug_file).name}...")
                read_result = await read_tool._execute_validated(path=bug_file)
                assert read_result.success
                content = read_result.data["content"]
                result.logs.append(f"  ✓ Read {len(content)} characters")

                # Step 3: Fix a BUG
                result.logs.append("Step 3: Fixing BUG...")
                if "return a / b  # BUG: no zero check" in content:
                    edit_result = await edit_tool._execute_validated(
                        path=bug_file,
                        edits=[{
                            "search": "return a / b  # BUG: no zero check",
                            "replace": "if b == 0:\n        raise ZeroDivisionError('Cannot divide by zero')\n    return a / b"
                        }],
                        preview=False,
                        create_backup=False
                    )
                    assert edit_result.success
                    result.logs.append("  ✓ Fixed division by zero bug")

            result.metadata["bugs_found"] = len(matches)
            result.metadata["bugs_fixed"] = 1 if matches else 0

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_create_test_run_workflow(self, temp_project, e2e_report):
        """Test: Create code -> Create tests -> Verify workflow."""
        start_time = time.time()
        result = TestResult(
            name="create_test_run_workflow",
            status="passed",
            duration=0.0,
            metadata={"workflow": "create_test_verify", "tools_used": 3}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

            write_tool = WriteFileTool()
            read_tool = ReadFileTool()

            # Step 1: Create a module
            result.logs.append("Step 1: Creating calculator module...")
            calc_code = '''"""Calculator module."""

class Calculator:
    """A simple calculator."""

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b
'''
            await write_tool._execute_validated(
                path=str(temp_project / "calculator.py"),
                content=calc_code
            )
            result.logs.append("  ✓ Created calculator.py")

            # Step 2: Create tests
            result.logs.append("Step 2: Creating tests...")
            test_code = '''"""Tests for calculator module."""

import pytest
from calculator import Calculator

@pytest.fixture
def calc():
    """Create calculator instance."""
    return Calculator()

class TestCalculator:
    """Test Calculator class."""

    def test_add(self, calc):
        assert calc.add(2, 3) == 5
        assert calc.add(-1, 1) == 0
        assert calc.add(0.1, 0.2) == pytest.approx(0.3)

    def test_subtract(self, calc):
        assert calc.subtract(5, 3) == 2
        assert calc.subtract(1, 1) == 0

    def test_multiply(self, calc):
        assert calc.multiply(3, 4) == 12
        assert calc.multiply(-2, 3) == -6

    def test_divide(self, calc):
        assert calc.divide(10, 2) == 5
        assert calc.divide(7, 2) == 3.5

    def test_divide_by_zero(self, calc):
        with pytest.raises(ZeroDivisionError):
            calc.divide(1, 0)
'''
            (temp_project / "tests").mkdir(exist_ok=True)
            await write_tool._execute_validated(
                path=str(temp_project / "tests" / "test_calculator.py"),
                content=test_code
            )
            result.logs.append("  ✓ Created test_calculator.py")

            # Step 3: Verify both files exist and have correct content
            result.logs.append("Step 3: Verifying files...")
            read_result = await read_tool._execute_validated(
                path=str(temp_project / "calculator.py")
            )
            assert read_result.success
            assert "class Calculator" in read_result.data["content"]

            read_result = await read_tool._execute_validated(
                path=str(temp_project / "tests" / "test_calculator.py")
            )
            assert read_result.success
            assert "def test_add" in read_result.data["content"]
            assert "def test_divide_by_zero" in read_result.data["content"]
            result.logs.append("  ✓ All files verified")

            result.metadata["files_created"] = 2
            result.metadata["test_count"] = 5

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_git_workflow(self, sample_python_project, e2e_report):
        """Test: Edit -> Git status -> Git diff workflow."""
        start_time = time.time()
        result = TestResult(
            name="git_workflow",
            status="passed",
            duration=0.0,
            metadata={"workflow": "git_operations", "tools_used": 4}
        )

        try:
            from jdev_cli.tools.file_ops import EditFileTool
            from jdev_cli.tools.git_ops import GitStatusTool, GitDiffTool

            edit_tool = EditFileTool()
            status_tool = GitStatusTool()
            diff_tool = GitDiffTool()

            # Step 1: Check initial git status
            result.logs.append("Step 1: Checking initial git status...")
            status_result = await status_tool._execute_validated(
                path=str(sample_python_project)
            )
            assert status_result.success
            result.logs.append(f"  ✓ Branch: {status_result.data.get('branch', 'unknown')}")

            # Step 2: Make a change
            result.logs.append("Step 2: Making a change...")
            readme_file = sample_python_project / "README.md"
            original_content = readme_file.read_text()
            new_content = original_content + "\n\n## Updated by E2E Test\n\nThis section was added by the E2E test suite.\n"

            edit_result = await edit_tool._execute_validated(
                path=str(readme_file),
                edits=[{"search": original_content, "replace": new_content}],
                preview=False,
                create_backup=False
            )
            assert edit_result.success
            result.logs.append("  ✓ Modified README.md")

            # Step 3: Check git status again
            result.logs.append("Step 3: Checking modified status...")
            status_result = await status_tool._execute_validated(
                path=str(sample_python_project)
            )
            assert status_result.success
            modified_files = status_result.data.get("modified", [])
            result.logs.append(f"  ✓ Modified files: {len(modified_files)}")

            # Step 4: Get diff
            result.logs.append("Step 4: Getting diff...")
            diff_result = await diff_tool._execute_validated(
                path=str(sample_python_project)
            )
            assert diff_result.success
            diff_content = diff_result.data.get("diff", "")
            has_changes = "Updated by E2E Test" in diff_content or len(diff_content) > 0
            result.logs.append(f"  ✓ Diff shows changes: {has_changes}")

            result.metadata["files_modified"] = len(modified_files)
            result.metadata["has_diff"] = has_changes

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    @pytest.mark.asyncio
    async def test_full_feature_implementation(self, temp_project, e2e_report):
        """Test implementing a complete feature from scratch."""
        start_time = time.time()
        result = TestResult(
            name="full_feature_implementation",
            status="passed",
            duration=0.0,
            metadata={"scenario": "feature_implementation"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

            write_tool = WriteFileTool()

            # Simulate implementing a "User Authentication" feature

            # Step 1: Create models
            result.logs.append("Phase 1: Creating data models...")
            models = '''"""User authentication models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib
import secrets

@dataclass
class User:
    """User model."""
    id: int
    username: str
    email: str
    password_hash: str
    created_at: datetime
    is_active: bool = True
    last_login: Optional[datetime] = None

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password securely."""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256', password.encode(), salt.encode(), 100000
        )
        return f"{salt}${hash_obj.hex()}"

    def verify_password(self, password: str) -> bool:
        """Verify a password against the hash."""
        salt, hash_val = self.password_hash.split('$')
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256', password.encode(), salt.encode(), 100000
        )
        return hash_obj.hex() == hash_val

@dataclass
class Session:
    """User session model."""
    id: str
    user_id: int
    created_at: datetime
    expires_at: datetime
    is_valid: bool = True
'''
            (temp_project / "app" / "models").mkdir(parents=True, exist_ok=True)
            await write_tool._execute_validated(
                path=str(temp_project / "app" / "models" / "auth.py"),
                content=models
            )
            result.logs.append("  ✓ Created auth models")

            # Step 2: Create service layer
            result.logs.append("Phase 2: Creating service layer...")
            service = '''"""Authentication service."""

from datetime import datetime, timedelta
from typing import Optional
import secrets
from .models.auth import User, Session

class AuthService:
    """Handle user authentication."""

    def __init__(self):
        self._users: dict[int, User] = {}
        self._sessions: dict[str, Session] = {}
        self._next_user_id = 1

    def register(self, username: str, email: str, password: str) -> User:
        """Register a new user."""
        # Check if username exists
        for user in self._users.values():
            if user.username == username:
                raise ValueError("Username already exists")
            if user.email == email:
                raise ValueError("Email already exists")

        user = User(
            id=self._next_user_id,
            username=username,
            email=email,
            password_hash=User.hash_password(password),
            created_at=datetime.now()
        )
        self._users[user.id] = user
        self._next_user_id += 1
        return user

    def login(self, username: str, password: str) -> Optional[Session]:
        """Authenticate user and create session."""
        user = self._get_user_by_username(username)
        if not user or not user.verify_password(password):
            return None

        if not user.is_active:
            return None

        # Create session
        session = Session(
            id=secrets.token_urlsafe(32),
            user_id=user.id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24)
        )
        self._sessions[session.id] = session
        user.last_login = datetime.now()
        return session

    def logout(self, session_id: str) -> bool:
        """Invalidate a session."""
        if session_id in self._sessions:
            self._sessions[session_id].is_valid = False
            return True
        return False

    def validate_session(self, session_id: str) -> Optional[User]:
        """Validate session and return user."""
        session = self._sessions.get(session_id)
        if not session or not session.is_valid:
            return None
        if session.expires_at < datetime.now():
            session.is_valid = False
            return None
        return self._users.get(session.user_id)

    def _get_user_by_username(self, username: str) -> Optional[User]:
        """Find user by username."""
        for user in self._users.values():
            if user.username == username:
                return user
        return None
'''
            await write_tool._execute_validated(
                path=str(temp_project / "app" / "auth_service.py"),
                content=service
            )
            result.logs.append("  ✓ Created auth service")

            # Step 3: Create API endpoints
            result.logs.append("Phase 3: Creating API endpoints...")
            api = '''"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from .auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    token: str
    expires_in: int

@router.post("/register")
async def register(req: RegisterRequest):
    """Register a new user."""
    try:
        user = auth_service.register(req.username, req.email, req.password)
        return {"id": user.id, "username": user.username}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Login and get session token."""
    session = auth_service.login(req.username, req.password)
    if not session:
        raise HTTPException(401, "Invalid credentials")
    return TokenResponse(token=session.id, expires_in=86400)

@router.post("/logout")
async def logout(token: str):
    """Logout and invalidate session."""
    if auth_service.logout(token):
        return {"message": "Logged out"}
    raise HTTPException(400, "Invalid session")
'''
            (temp_project / "app" / "api").mkdir(exist_ok=True)
            await write_tool._execute_validated(
                path=str(temp_project / "app" / "api" / "auth.py"),
                content=api
            )
            result.logs.append("  ✓ Created API endpoints")

            # Step 4: Create tests
            result.logs.append("Phase 4: Creating tests...")
            tests = '''"""Tests for authentication feature."""

import pytest
from app.auth_service import AuthService

@pytest.fixture
def auth_service():
    return AuthService()

class TestAuthService:

    def test_register_user(self, auth_service):
        user = auth_service.register("testuser", "test@example.com", "password123")
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.id == 1

    def test_register_duplicate_username(self, auth_service):
        auth_service.register("testuser", "test1@example.com", "password123")
        with pytest.raises(ValueError, match="Username already exists"):
            auth_service.register("testuser", "test2@example.com", "password456")

    def test_login_success(self, auth_service):
        auth_service.register("testuser", "test@example.com", "password123")
        session = auth_service.login("testuser", "password123")
        assert session is not None
        assert session.user_id == 1

    def test_login_wrong_password(self, auth_service):
        auth_service.register("testuser", "test@example.com", "password123")
        session = auth_service.login("testuser", "wrongpassword")
        assert session is None

    def test_validate_session(self, auth_service):
        auth_service.register("testuser", "test@example.com", "password123")
        session = auth_service.login("testuser", "password123")
        user = auth_service.validate_session(session.id)
        assert user is not None
        assert user.username == "testuser"

    def test_logout(self, auth_service):
        auth_service.register("testuser", "test@example.com", "password123")
        session = auth_service.login("testuser", "password123")
        assert auth_service.logout(session.id)
        assert auth_service.validate_session(session.id) is None
'''
            (temp_project / "tests").mkdir(exist_ok=True)
            await write_tool._execute_validated(
                path=str(temp_project / "tests" / "test_auth.py"),
                content=tests
            )
            result.logs.append("  ✓ Created tests")

            # Count what was created
            all_files = list(temp_project.rglob("*.py"))
            result.logs.append(f"\nTotal: Created {len(all_files)} Python files")

            result.metadata["phases_completed"] = 4
            result.metadata["files_created"] = len(all_files)
            result.metadata["feature"] = "User Authentication"

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_codebase_analysis_and_fix(self, sample_python_project, e2e_report):
        """Test analyzing a codebase and fixing issues."""
        start_time = time.time()
        result = TestResult(
            name="codebase_analysis_and_fix",
            status="passed",
            duration=0.0,
            metadata={"scenario": "analysis_and_fix"}
        )

        try:
            from jdev_cli.tools.search import SearchFilesTool
            from jdev_cli.tools.file_ops import ReadFileTool, EditFileTool

            search_tool = SearchFilesTool()
            read_tool = ReadFileTool()
            edit_tool = EditFileTool()

            issues_found = []
            issues_fixed = []

            # Phase 1: Find all issues
            result.logs.append("Phase 1: Scanning for issues...")

            # Check for hardcoded secrets
            search_result = await search_tool._execute_validated(
                pattern="API_KEY.*=.*['\"]sk-",
                path=str(sample_python_project),
                file_pattern="*.py"
            )
            if search_result.success and search_result.data.get("matches"):
                issues_found.append({
                    "type": "hardcoded_secret",
                    "count": len(search_result.data["matches"])
                })
                result.logs.append(f"  ⚠️ Found {len(search_result.data['matches'])} hardcoded secrets")

            # Check for BUG comments
            search_result = await search_tool._execute_validated(
                pattern="# BUG",
                path=str(sample_python_project),
                file_pattern="*.py"
            )
            if search_result.success and search_result.data.get("matches"):
                issues_found.append({
                    "type": "marked_bugs",
                    "count": len(search_result.data["matches"])
                })
                result.logs.append(f"  ⚠️ Found {len(search_result.data['matches'])} marked BUGs")

            # Check for TODO comments
            search_result = await search_tool._execute_validated(
                pattern="# TODO",
                path=str(sample_python_project),
                file_pattern="*.py"
            )
            if search_result.success and search_result.data.get("matches"):
                issues_found.append({
                    "type": "todos",
                    "count": len(search_result.data["matches"])
                })
                result.logs.append(f"  ℹ️ Found {len(search_result.data['matches'])} TODOs")

            # Phase 2: Fix critical issues
            result.logs.append("\nPhase 2: Fixing critical issues...")

            # Fix hardcoded secrets in config.py
            config_file = sample_python_project / "config.py"
            if config_file.exists():
                read_result = await read_tool._execute_validated(path=str(config_file))
                if read_result.success:
                    content = read_result.data["content"]
                    if "sk-1234567890" in content:
                        fixed_content = content.replace(
                            'API_KEY = "sk-1234567890"',
                            'API_KEY = os.getenv("API_KEY")  # Fixed: Use env var'
                        )
                        fixed_content = 'import os\n' + fixed_content

                        edit_result = await edit_tool._execute_validated(
                            path=str(config_file),
                            edits=[{"search": content, "replace": fixed_content}],
                            preview=False,
                            create_backup=False
                        )
                        if edit_result.success:
                            issues_fixed.append("hardcoded_secret")
                            result.logs.append("  ✓ Fixed hardcoded API key in config.py")

            # Summary
            result.logs.append(f"\nSummary:")
            result.logs.append(f"  Issues found: {len(issues_found)}")
            result.logs.append(f"  Issues fixed: {len(issues_fixed)}")

            result.metadata["issues_found"] = issues_found
            result.metadata["issues_fixed"] = issues_fixed

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error
