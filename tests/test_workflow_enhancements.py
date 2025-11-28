"""Tests for Day 7 workflow enhancements.

Tests:
- GitRollback (checkpoint creation, rollback functionality)
- PartialRollback (operation tracking, granular rollback)
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from jdev_cli.core.workflow import (
    GitRollback,
    PartialRollback
)


class TestGitRollback:
    """Test git-based rollback functionality."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create temporary git repository."""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)

        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=temp_dir,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=temp_dir,
            capture_output=True
        )

        # Create initial commit
        (temp_path / "README.md").write_text("# Test Repo")
        subprocess.run(["git", "add", "README.md"], cwd=temp_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=temp_dir,
            capture_output=True
        )

        yield temp_path

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test git rollback initialization."""
        rollback = GitRollback()

        assert rollback.commits_made == []
        assert rollback.checkpoints == {}

    @pytest.mark.asyncio
    async def test_create_checkpoint_commit(self, temp_git_repo, monkeypatch):
        """Test creating checkpoint commit."""
        monkeypatch.chdir(temp_git_repo)

        rollback = GitRollback()

        # Make some changes
        (temp_git_repo / "test.py").write_text("print('hello')")

        # Create checkpoint
        sha = await rollback.create_checkpoint_commit("Test checkpoint")

        assert sha is not None
        assert len(sha) == 40  # Git SHA length
        assert sha in rollback.commits_made

    @pytest.mark.asyncio
    async def test_create_checkpoint_no_changes(self, temp_git_repo, monkeypatch):
        """Test checkpoint creation with no changes."""
        monkeypatch.chdir(temp_git_repo)

        rollback = GitRollback()

        # No changes
        sha = await rollback.create_checkpoint_commit("No changes")

        assert sha is None

    @pytest.mark.asyncio
    async def test_create_checkpoint_not_in_repo(self, tmp_path, monkeypatch):
        """Test checkpoint creation outside git repo."""
        monkeypatch.chdir(tmp_path)

        rollback = GitRollback()

        # Not in git repo
        (tmp_path / "test.txt").write_text("test")
        sha = await rollback.create_checkpoint_commit("Outside repo")

        assert sha is None

    @pytest.mark.asyncio
    async def test_rollback_to_checkpoint(self, temp_git_repo, monkeypatch):
        """Test rolling back to checkpoint."""
        monkeypatch.chdir(temp_git_repo)

        rollback = GitRollback()

        # Create checkpoint 1
        (temp_git_repo / "file1.txt").write_text("version 1")
        sha1 = await rollback.create_checkpoint_commit("Checkpoint 1")

        # Make more changes
        (temp_git_repo / "file1.txt").write_text("version 2")
        (temp_git_repo / "file2.txt").write_text("new file")
        sha2 = await rollback.create_checkpoint_commit("Checkpoint 2")

        assert (temp_git_repo / "file1.txt").read_text() == "version 2"
        assert (temp_git_repo / "file2.txt").exists()

        # Rollback to checkpoint 1
        success = await rollback.rollback_to_checkpoint(sha1)
        assert success is True

        # Verify rollback
        assert (temp_git_repo / "file1.txt").read_text() == "version 1"
        assert not (temp_git_repo / "file2.txt").exists()

    @pytest.mark.asyncio
    async def test_rollback_last_checkpoint(self, temp_git_repo, monkeypatch):
        """Test rolling back to last checkpoint."""
        monkeypatch.chdir(temp_git_repo)

        rollback = GitRollback()

        # Create checkpoints
        (temp_git_repo / "file.txt").write_text("v1")
        sha1 = await rollback.create_checkpoint_commit("CP1")

        (temp_git_repo / "file.txt").write_text("v2")
        sha2 = await rollback.create_checkpoint_commit("CP2")

        assert len(rollback.commits_made) == 2

        # Rollback last
        success = await rollback.rollback_last_checkpoint()
        assert success is True
        assert len(rollback.commits_made) == 1

    def test_get_checkpoints(self):
        """Test getting checkpoint list."""
        rollback = GitRollback()
        rollback.commits_made = ["abc123", "def456"]

        checkpoints = rollback.get_checkpoints()
        assert checkpoints == ["abc123", "def456"]

        # Should be a copy
        checkpoints.append("ghi789")
        assert len(rollback.commits_made) == 2

    def test_clear_checkpoints(self):
        """Test clearing checkpoints."""
        rollback = GitRollback()
        rollback.commits_made = ["abc123", "def456"]
        rollback.checkpoints = {"cp1": "abc123"}

        rollback.clear_checkpoints()

        assert rollback.commits_made == []
        assert rollback.checkpoints == {}


class TestPartialRollback:
    """Test granular operation rollback."""

    def test_initialization(self):
        """Test partial rollback initialization."""
        rollback = PartialRollback()

        assert rollback.operations == []

    def test_add_operation(self):
        """Test adding operation to stack."""
        rollback = PartialRollback()

        rollback.add_operation(
            op_type="file_write",
            data={"file_path": "test.txt", "backup_path": "test.txt.bak"},
            reversible=True
        )

        assert len(rollback.operations) == 1
        op = rollback.operations[0]

        assert op['type'] == "file_write"
        assert op['reversible'] is True
        assert 'timestamp' in op

    def test_add_multiple_operations(self):
        """Test adding multiple operations."""
        rollback = PartialRollback()

        rollback.add_operation("file_write", {"file": "a.txt"})
        rollback.add_operation("file_edit", {"file": "b.txt"})
        rollback.add_operation("file_delete", {"file": "c.txt"})

        assert len(rollback.operations) == 3

    @pytest.mark.asyncio
    async def test_rollback_file_write(self, tmp_path):
        """Test rolling back file write operation."""
        rollback = PartialRollback()

        # Simulate file write with backup
        original_file = tmp_path / "test.txt"
        backup_file = tmp_path / "test.txt.bak"

        original_file.write_text("modified content")
        backup_file.write_text("original content")

        rollback.add_operation(
            "file_write",
            {
                "file_path": str(original_file),
                "backup_path": str(backup_file)
            }
        )

        # Rollback
        successful, failed = await rollback.rollback_last_n(1)

        assert successful == 1
        assert failed == 0
        assert original_file.read_text() == "original content"

    @pytest.mark.asyncio
    async def test_rollback_file_delete(self, tmp_path):
        """Test rolling back file deletion."""
        rollback = PartialRollback()

        # Simulate deleted file with backup content
        deleted_file = tmp_path / "deleted.txt"

        rollback.add_operation(
            "file_delete",
            {
                "file_path": str(deleted_file),
                "backup_content": "recovered content"
            }
        )

        # Rollback
        successful, failed = await rollback.rollback_last_n(1)

        assert successful == 1
        assert deleted_file.exists()
        assert deleted_file.read_text() == "recovered content"

    @pytest.mark.asyncio
    async def test_rollback_file_edit(self, tmp_path):
        """Test rolling back file edit."""
        rollback = PartialRollback()

        # Simulate edited file
        edited_file = tmp_path / "edited.txt"
        edited_file.write_text("new content")

        rollback.add_operation(
            "file_edit",
            {
                "file_path": str(edited_file),
                "original_content": "old content"
            }
        )

        # Rollback
        successful, failed = await rollback.rollback_last_n(1)

        assert successful == 1
        assert edited_file.read_text() == "old content"

    @pytest.mark.asyncio
    async def test_rollback_irreversible_operation(self):
        """Test handling irreversible operations."""
        rollback = PartialRollback()

        rollback.add_operation(
            "command_execute",
            {"command": "rm -rf /tmp/test"},
            reversible=False
        )

        # Rollback
        successful, failed = await rollback.rollback_last_n(1)

        assert successful == 0
        assert failed == 1

    @pytest.mark.asyncio
    async def test_rollback_multiple_operations(self, tmp_path):
        """Test rolling back multiple operations."""
        rollback = PartialRollback()

        # Add multiple operations
        for i in range(5):
            file = tmp_path / f"file{i}.txt"
            file.write_text(f"content {i}")

            rollback.add_operation(
                "file_write",
                {
                    "file_path": str(file),
                    "backup_path": str(file) + ".bak"
                }
            )

        # Create backups
        for i in range(5):
            (tmp_path / f"file{i}.txt.bak").write_text(f"backup {i}")

        # Rollback 3 operations
        successful, failed = await rollback.rollback_last_n(3)

        assert successful == 3
        assert len(rollback.operations) == 2

    @pytest.mark.asyncio
    async def test_rollback_until_timestamp(self, tmp_path):
        """Test rolling back until target timestamp."""
        import time

        rollback = PartialRollback()

        # Add operations at different times
        rollback.add_operation("op1", {"data": "1"})
        time.sleep(0.1)

        target_time = time.time()
        time.sleep(0.1)

        rollback.add_operation("op2", {"data": "2"})
        rollback.add_operation("op3", {"data": "3"})

        # Rollback operations after target
        successful, failed = await rollback.rollback_until(target_time)

        assert len(rollback.operations) == 1  # Only op1 remains

    def test_get_operations(self):
        """Test getting operations list."""
        rollback = PartialRollback()

        rollback.add_operation("op1", {"a": 1})
        rollback.add_operation("op2", {"b": 2})

        ops = rollback.get_operations()
        assert len(ops) == 2

        # Should be a copy
        ops.append({})
        assert len(rollback.operations) == 2

    def test_clear_operations(self):
        """Test clearing operations."""
        rollback = PartialRollback()

        rollback.add_operation("op1", {"a": 1})
        rollback.add_operation("op2", {"b": 2})

        rollback.clear_operations()
        assert rollback.operations == []

    def test_get_summary(self):
        """Test getting operations summary."""
        rollback = PartialRollback()

        rollback.add_operation("file_write", {"a": 1}, reversible=True)
        rollback.add_operation("file_edit", {"b": 2}, reversible=True)
        rollback.add_operation("command", {"c": 3}, reversible=False)

        summary = rollback.get_summary()

        assert summary['total_operations'] == 3
        assert summary['reversible'] == 2
        assert summary['irreversible'] == 1
        assert set(summary['types']) == {'file_write', 'file_edit', 'command'}
        assert summary['oldest'] is not None
        assert summary['newest'] is not None
