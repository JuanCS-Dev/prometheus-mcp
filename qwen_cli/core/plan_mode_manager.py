"""
PlanModeManager - Plan Mode Management
======================================

Extracted from Bridge GOD CLASS (Nov 2025 Refactoring).

Features:
- Enter/exit plan mode for safe task planning
- Plan file creation and documentation
- Exploration log tracking
- Operation restriction enforcement (read-only in plan mode)
- Plan approval workflow
- Thread-safe operations with locking
"""

from __future__ import annotations

import datetime
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PlanModeManager:
    """
    Manages plan mode for safe, deliberate task execution.

    Plan mode provides a safe environment where:
    - Read-only operations are allowed
    - Write operations are blocked until approval
    - All decisions are documented in a plan file
    - Exploration is tracked and logged
    - User must explicitly approve before exiting

    Features:
    - Enter/exit plan mode
    - Plan file creation and documentation
    - Exploration log tracking with categories
    - Operation restriction enforcement
    - Plan approval workflow
    - Thread-safe state management with locking

    Usage:
        manager = PlanModeManager()
        result = manager.enter_plan_mode("Refactor authentication module")
        if result["success"]:
            manager.add_plan_note("Found legacy auth in auth.py", category="exploration")
            manager.add_plan_note("Need to migrate to OAuth2", category="plan")
            # Check restrictions before operations
            allowed, error = manager.check_plan_mode_restriction("write")
            # Exit with approval
            exit_result = manager.exit_plan_mode(approved=True)
    """

    # Maximum checkpoints to prevent memory leak (AIR GAP FIX)
    MAX_PLAN_NOTES = 500

    def __init__(self, plan_dir: Optional[Path] = None):
        """
        Initialize PlanModeManager.

        Args:
            plan_dir: Directory for storing plan files.
                     Defaults to .juancs/plans in current working directory
        """
        self._plan_dir = plan_dir or (Path.cwd() / ".juancs" / "plans")
        self._plan_mode_lock = threading.Lock()
        self._plan_mode: Dict[str, Any] = {
            "active": False,
            "plan_file": None,
            "task": None,
            "exploration_log": [],
            "read_only": True,
            "started_at": None
        }

    def _init_plan_mode(self) -> None:
        """Initialize plan mode state if not already done."""
        if not hasattr(self, '_plan_mode') or self._plan_mode is None:
            self._plan_mode = {
                "active": False,
                "plan_file": None,
                "task": None,
                "exploration_log": [],
                "read_only": True,
                "started_at": None
            }

    def enter_plan_mode(self, task: str = None) -> Dict[str, Any]:
        """
        Enter plan mode for careful task planning.

        In plan mode:
        - Read-only operations are allowed
        - Write operations are blocked
        - A plan file is created for documentation
        - User must approve before exiting

        Args:
            task: Optional task description for the plan

        Returns:
            Dictionary with keys:
            - success: Whether mode was entered
            - message: Status message
            - plan_file: Path to created plan file
            - task: Task description
            - restrictions: Description of restrictions in plan mode
            - error: Error message if unsuccessful

        Raises:
            None (returns error in dict on failure)
        """
        # Thread-safe plan mode entry
        with self._plan_mode_lock:
            self._init_plan_mode()

            if self._plan_mode["active"]:
                return {
                    "success": False,
                    "error": "Already in plan mode",
                    "state": self._plan_mode
                }

            try:
                # Create plan file
                self._plan_dir.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                plan_file = self._plan_dir / f"plan_{timestamp}.md"

                plan_content = f"""# Plan Mode - {timestamp}

## Task
{task or 'No task specified'}

## Status
- Started: {datetime.datetime.now().isoformat()}
- Status: IN PROGRESS

## Exploration Notes
<!-- Notes from codebase exploration -->

## Implementation Plan
<!-- Detailed plan steps -->

## Files to Modify
<!-- List files that will be changed -->

## Approval
- [ ] Plan reviewed
- [ ] Ready to implement
"""
                plan_file.write_text(plan_content, encoding="utf-8")

                self._plan_mode = {
                    "active": True,
                    "plan_file": str(plan_file),
                    "task": task,
                    "exploration_log": [],
                    "read_only": True,
                    "started_at": datetime.datetime.now().isoformat()
                }

                logger.info(f"Entered plan mode for task: {task}")

                return {
                    "success": True,
                    "message": "Entered plan mode",
                    "plan_file": str(plan_file),
                    "task": task,
                    "restrictions": "Write operations blocked until plan approved"
                }

            except Exception as e:
                logger.error(f"Failed to enter plan mode: {e}")
                return {
                    "success": False,
                    "error": f"Failed to enter plan mode: {str(e)}"
                }

    def exit_plan_mode(self, approved: bool = False) -> Dict[str, Any]:
        """
        Exit plan mode.

        If approved=True, updates the plan file with approval checkmarks
        and completion timestamp.

        Args:
            approved: Whether the plan was approved by user for execution

        Returns:
            Dictionary with keys:
            - success: Whether mode was exited
            - approved: Whether plan was approved
            - plan_file: Path to plan file
            - exploration_count: Number of exploration notes
            - message: Status message
            - error: Error message if unsuccessful
        """
        self._init_plan_mode()

        if not self._plan_mode["active"]:
            return {
                "success": False,
                "error": "Not in plan mode"
            }

        plan_file = self._plan_mode["plan_file"]

        if approved and plan_file:
            # Update plan file with approval
            try:
                plan_path = Path(plan_file)
                if plan_path.exists():
                    content = plan_path.read_text(encoding="utf-8")
                    content = content.replace(
                        "- [ ] Plan reviewed",
                        "- [x] Plan reviewed"
                    ).replace(
                        "- [ ] Ready to implement",
                        "- [x] Ready to implement"
                    ).replace(
                        "Status: IN PROGRESS",
                        f"Status: APPROVED ({datetime.datetime.now().isoformat()})"
                    )
                    plan_path.write_text(content, encoding="utf-8")
                    logger.info(f"Plan approved: {plan_file}")
            except Exception as e:
                logger.warning(f"Failed to update plan file: {e}")

        result = {
            "success": True,
            "approved": approved,
            "plan_file": plan_file,
            "exploration_count": len(self._plan_mode["exploration_log"]),
            "message": "Plan approved - ready to implement" if approved else "Plan mode exited without approval"
        }

        # Reset state
        self._plan_mode = {
            "active": False,
            "plan_file": None,
            "task": None,
            "exploration_log": [],
            "read_only": True,
            "started_at": None
        }

        logger.info(f"Exited plan mode (approved={approved})")

        return result

    def is_plan_mode(self) -> bool:
        """
        Check if currently in plan mode.

        Returns:
            True if in plan mode, False otherwise
        """
        self._init_plan_mode()
        return self._plan_mode["active"]

    def get_plan_mode_state(self) -> Dict[str, Any]:
        """
        Get current plan mode state.

        Returns:
            Dictionary with plan mode state:
            - active: Whether in plan mode
            - plan_file: Path to plan file
            - task: Task description
            - exploration_log: List of notes
            - read_only: Whether read-only mode
            - started_at: ISO format timestamp of when mode was entered
        """
        self._init_plan_mode()
        return self._plan_mode.copy()

    def add_plan_note(self, note: str, category: str = "exploration") -> bool:
        """
        Add a note to the current plan.

        Note is appended to both the in-memory exploration log and the
        plan file under the appropriate section.

        Args:
            note: Note content to add
            category: Category for the note. Options:
                     - "exploration": Codebase exploration findings
                     - "plan": Implementation plan steps
                     - "files": Files to be modified
                     - "other": Miscellaneous notes

        Returns:
            True if note was added, False if not in plan mode
        """
        self._init_plan_mode()

        if not self._plan_mode["active"]:
            logger.debug("Cannot add plan note: not in plan mode")
            return False

        # Enforce note limit to prevent memory leak
        if len(self._plan_mode["exploration_log"]) >= self.MAX_PLAN_NOTES:
            logger.warning(f"Plan notes exceeded limit ({self.MAX_PLAN_NOTES}), skipping new note")
            return False

        # Add to in-memory log
        self._plan_mode["exploration_log"].append({
            "category": category,
            "note": note,
            "timestamp": datetime.datetime.now().isoformat()
        })

        # Also append to plan file
        plan_file = self._plan_mode["plan_file"]
        if plan_file:
            try:
                plan_path = Path(plan_file)
                if plan_path.exists():
                    content = plan_path.read_text(encoding="utf-8")

                    # Map category to section marker
                    marker_map = {
                        "exploration": "## Exploration Notes",
                        "plan": "## Implementation Plan",
                        "files": "## Files to Modify"
                    }
                    marker = marker_map.get(category, "## Exploration Notes")

                    # Find marker and append after it
                    if marker in content:
                        parts = content.split(marker)
                        if len(parts) >= 2:
                            parts[1] = f"\n- {note}" + parts[1]
                            content = marker.join(parts)
                            plan_path.write_text(content, encoding="utf-8")
            except Exception as e:
                logger.debug(f"Failed to update plan file with note: {e}")

        logger.debug(f"Added plan note ({category}): {note[:50]}...")
        return True

    def check_plan_mode_restriction(self, operation: str) -> Tuple[bool, Optional[str]]:
        """
        Check if an operation is allowed in plan mode.

        Enforces read-only restrictions when in plan mode. Read operations
        like search, read, and list are always allowed. Write operations
        like create, edit, delete, execute, and run are blocked.

        Args:
            operation: Operation name to check (write, edit, delete, execute, etc.)

        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
            - (True, None) if operation is allowed
            - (False, error_message) if operation is blocked
        """
        self._init_plan_mode()

        if not self._plan_mode["active"]:
            return True, None  # Not in plan mode, allow all operations

        # Read-only operations always allowed
        read_only_ops = {"read", "glob", "grep", "ls", "search", "list", "get", "check"}

        if any(op in operation.lower() for op in read_only_ops):
            return True, None

        # Write operations blocked in plan mode
        write_ops = {"write", "edit", "delete", "create", "execute", "run", "bash"}

        if any(op in operation.lower() for op in write_ops):
            error_msg = f"Operation '{operation}' blocked in plan mode. Exit plan mode with /plan-exit to enable writes."
            logger.debug(error_msg)
            return False, error_msg

        return True, None

    def get_plan_summary(self) -> Dict[str, Any]:
        """
        Get summary of current plan.

        Returns:
            Dictionary with plan summary:
            - task: Task description
            - active: Whether plan is active
            - duration: Time since plan started (if active)
            - notes_count: Number of notes in exploration log
            - plan_file: Path to plan file
        """
        self._init_plan_mode()

        duration = None
        if self._plan_mode["active"] and self._plan_mode["started_at"]:
            started = datetime.datetime.fromisoformat(self._plan_mode["started_at"])
            duration = str(datetime.datetime.now() - started)

        return {
            "task": self._plan_mode["task"],
            "active": self._plan_mode["active"],
            "duration": duration,
            "notes_count": len(self._plan_mode["exploration_log"]),
            "plan_file": self._plan_mode["plan_file"]
        }

    def get_exploration_log(self) -> List[Dict[str, Any]]:
        """
        Get the complete exploration log for current plan.

        Returns:
            List of exploration entries with keys:
            - category: Note category
            - note: Note content
            - timestamp: ISO format timestamp
        """
        self._init_plan_mode()
        return self._plan_mode["exploration_log"].copy()

    def clear_plan_mode(self) -> None:
        """
        Force clear plan mode state.

        WARNING: This discards any unsaved plan data.
        Only use in emergency situations.
        """
        with self._plan_mode_lock:
            self._plan_mode = {
                "active": False,
                "plan_file": None,
                "task": None,
                "exploration_log": [],
                "read_only": True,
                "started_at": None
            }
            logger.warning("Plan mode forcibly cleared")
