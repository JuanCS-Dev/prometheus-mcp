"""Plan Mode Tools - EnterPlanMode/ExitPlanMode for structured planning.

Claude Code parity: Implements planning mode for complex tasks that require
careful exploration and design before implementation.

Author: Juan CS
Date: 2025-11-26
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .base import Tool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


# =============================================================================
# PLAN MODE STATE
# =============================================================================

@dataclass
class PlanState:
    """Current state of plan mode."""

    active: bool = False
    plan_file: Optional[Path] = None
    started_at: Optional[datetime] = None
    task_description: str = ""
    exploration_notes: List[str] = field(default_factory=list)
    files_explored: List[str] = field(default_factory=list)
    decisions_made: List[Dict[str, str]] = field(default_factory=list)
    questions_pending: List[str] = field(default_factory=list)
    plan_content: str = ""
    approved: bool = False


# Global plan state
_plan_state = PlanState()


def get_plan_state() -> PlanState:
    """Get the current plan state."""
    return _plan_state


def reset_plan_state() -> None:
    """Reset plan state (for testing)."""
    global _plan_state
    _plan_state = PlanState()


# =============================================================================
# ENTER PLAN MODE TOOL
# =============================================================================

class EnterPlanModeTool(Tool):
    """Transition into planning mode for complex tasks.

    Claude Code parity: EnterPlanMode tool for structured task planning.

    Use this when:
    - Task has multiple valid approaches with trade-offs
    - Significant architectural decisions are needed
    - Large-scale changes touching many files
    - Requirements are unclear and need exploration
    - User input needed before starting implementation

    In plan mode:
    - Explore codebase using Glob, Grep, Read tools
    - Understand existing patterns and architecture
    - Design implementation approach
    - Present plan to user for approval
    - Use AskUserQuestion to clarify approaches
    - Exit with ExitPlanMode when ready
    """

    def __init__(self):
        super().__init__()
        self.name = "enter_plan_mode"
        self.category = ToolCategory.CONTEXT
        self.description = "Enter planning mode for complex tasks requiring exploration"
        self.parameters = {
            "task_description": {
                "type": "string",
                "description": "Brief description of the task to plan",
                "required": False
            },
            "plan_file": {
                "type": "string",
                "description": "Path for the plan file (default: .qwen/plans/current_plan.md)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Enter plan mode."""
        global _plan_state

        task_description = kwargs.get("task_description", "")
        plan_file = kwargs.get("plan_file", ".qwen/plans/current_plan.md")

        # Check if already in plan mode
        if _plan_state.active:
            return ToolResult(
                success=False,
                error="Already in plan mode. Use exit_plan_mode to exit first."
            )

        # Create plan file directory
        plan_path = Path(plan_file)
        plan_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize plan state
        _plan_state = PlanState(
            active=True,
            plan_file=plan_path,
            started_at=datetime.now(),
            task_description=task_description,
        )

        # Create initial plan file
        initial_content = self._create_plan_template(task_description)
        plan_path.write_text(initial_content, encoding="utf-8")

        logger.info(f"Entered plan mode: {plan_path}")

        return ToolResult(
            success=True,
            data={
                "status": "plan_mode_active",
                "plan_file": str(plan_path),
                "task": task_description,
                "message": "Plan mode activated. Explore the codebase and design your approach.",
                "next_steps": [
                    "Use Glob/Grep/Read to explore the codebase",
                    "Write your plan to the plan file",
                    "Use AskUserQuestion to clarify decisions",
                    "Call exit_plan_mode when ready for approval"
                ]
            },
            metadata={
                "mode": "planning",
                "started_at": _plan_state.started_at.isoformat()
            }
        )

    def _create_plan_template(self, task_description: str) -> str:
        """Create initial plan file template."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        return f"""# Implementation Plan

**Created:** {timestamp}
**Task:** {task_description or "To be defined"}
**Status:** In Progress

## Task Description

{task_description or "_Describe the task here_"}

## Exploration Notes

_Add notes from codebase exploration here_

## Current Architecture

_Document relevant existing patterns_

## Proposed Approach

_Describe your implementation approach_

## Implementation Steps

- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

## Questions / Decisions Needed

_List any clarifications needed from the user_

## Risks / Considerations

_Document any potential issues_

---
*Plan created by JuanCS-DevCode*
"""


# =============================================================================
# EXIT PLAN MODE TOOL
# =============================================================================

class ExitPlanModeTool(Tool):
    """Exit planning mode and submit plan for approval.

    Claude Code parity: ExitPlanMode tool for plan submission.

    Use this when:
    - Plan file is complete with implementation steps
    - All clarifying questions have been resolved
    - Ready for user to review and approve the plan

    Important:
    - Requires user approval before implementation begins
    - If there are ambiguities, use AskUserQuestion first
    - Only use for implementation planning, not research tasks
    """

    def __init__(self):
        super().__init__()
        self.name = "exit_plan_mode"
        self.category = ToolCategory.CONTEXT
        self.description = "Exit planning mode and submit plan for user approval"
        self.parameters = {
            "summary": {
                "type": "string",
                "description": "Brief summary of the plan",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Exit plan mode."""
        global _plan_state

        summary = kwargs.get("summary", "")

        # Check if in plan mode
        if not _plan_state.active:
            return ToolResult(
                success=False,
                error="Not currently in plan mode. Use enter_plan_mode first."
            )

        # Read plan file content
        plan_content = ""
        if _plan_state.plan_file and _plan_state.plan_file.exists():
            plan_content = _plan_state.plan_file.read_text(encoding="utf-8")

        # Validate plan has content
        if len(plan_content) < 100:
            return ToolResult(
                success=False,
                error="Plan file appears empty or too short. Please write your plan before exiting."
            )

        # Store plan content
        _plan_state.plan_content = plan_content
        _plan_state.active = False  # Exit plan mode

        logger.info(f"Exited plan mode: {_plan_state.plan_file}")

        return ToolResult(
            success=True,
            data={
                "status": "plan_submitted",
                "plan_file": str(_plan_state.plan_file),
                "summary": summary or "Plan submitted for approval",
                "plan_preview": plan_content[:500] + "..." if len(plan_content) > 500 else plan_content,
                "message": "Plan mode exited. Awaiting user approval.",
                "approval_required": True
            },
            metadata={
                "mode": "awaiting_approval",
                "files_explored": len(_plan_state.files_explored),
                "decisions_made": len(_plan_state.decisions_made),
                "duration_seconds": (
                    (datetime.now() - _plan_state.started_at).total_seconds()
                    if _plan_state.started_at else 0
                )
            }
        )


# =============================================================================
# PLAN MODE HELPERS
# =============================================================================

class AddPlanNoteTool(Tool):
    """Add a note to the current plan.

    Use during plan mode to document exploration findings,
    architecture notes, or decision rationale.
    """

    def __init__(self):
        super().__init__()
        self.name = "add_plan_note"
        self.category = ToolCategory.CONTEXT
        self.description = "Add a note to the current plan"
        self.parameters = {
            "note": {
                "type": "string",
                "description": "Note content to add",
                "required": True
            },
            "section": {
                "type": "string",
                "description": "Section to add note to (exploration, architecture, approach)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Add note to plan."""
        global _plan_state

        note = kwargs.get("note", "")
        section = kwargs.get("section", "exploration")

        if not _plan_state.active:
            return ToolResult(
                success=False,
                error="Not in plan mode. Use enter_plan_mode first."
            )

        if not note:
            return ToolResult(success=False, error="Note content is required")

        # Add to exploration notes
        _plan_state.exploration_notes.append(note)

        # Append to plan file if exists
        if _plan_state.plan_file and _plan_state.plan_file.exists():
            content = _plan_state.plan_file.read_text(encoding="utf-8")

            # Find appropriate section
            section_map = {
                "exploration": "## Exploration Notes",
                "architecture": "## Current Architecture",
                "approach": "## Proposed Approach",
            }
            section_header = section_map.get(section, "## Exploration Notes")

            # Insert note after section header
            if section_header in content:
                insert_point = content.find(section_header) + len(section_header)
                # Find end of section header line
                line_end = content.find("\n", insert_point)
                if line_end != -1:
                    timestamp = datetime.now().strftime("%H:%M")
                    new_content = (
                        content[:line_end + 1] +
                        f"\n- [{timestamp}] {note}\n" +
                        content[line_end + 1:]
                    )
                    _plan_state.plan_file.write_text(new_content, encoding="utf-8")

        return ToolResult(
            success=True,
            data={
                "note_added": note[:100],
                "section": section,
                "total_notes": len(_plan_state.exploration_notes)
            }
        )


class GetPlanStatusTool(Tool):
    """Get current plan mode status."""

    def __init__(self):
        super().__init__()
        self.name = "get_plan_status"
        self.category = ToolCategory.CONTEXT
        self.description = "Get current planning mode status"
        self.parameters = {}

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Get plan status."""
        global _plan_state

        if not _plan_state.active and not _plan_state.plan_content:
            return ToolResult(
                success=True,
                data={
                    "active": False,
                    "message": "Not in plan mode"
                }
            )

        plan_content = ""
        if _plan_state.plan_file and _plan_state.plan_file.exists():
            plan_content = _plan_state.plan_file.read_text(encoding="utf-8")

        return ToolResult(
            success=True,
            data={
                "active": _plan_state.active,
                "plan_file": str(_plan_state.plan_file) if _plan_state.plan_file else None,
                "task": _plan_state.task_description,
                "started_at": _plan_state.started_at.isoformat() if _plan_state.started_at else None,
                "notes_count": len(_plan_state.exploration_notes),
                "files_explored": len(_plan_state.files_explored),
                "decisions_count": len(_plan_state.decisions_made),
                "questions_pending": len(_plan_state.questions_pending),
                "approved": _plan_state.approved,
                "plan_preview": plan_content[:300] if plan_content else None
            }
        )


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_plan_mode_tools() -> List[Tool]:
    """Get all plan mode tools."""
    return [
        EnterPlanModeTool(),
        ExitPlanModeTool(),
        AddPlanNoteTool(),
        GetPlanStatusTool(),
    ]
