"""
Interaction Tools - AskUserQuestion, Skill, SlashCommand
========================================================

User interaction tools for Claude Code parity.

Contains:
- AskUserQuestionTool: Ask user questions with options
- SkillTool: Execute skills (slash commands)
- SlashCommandTool: Execute slash commands with arguments

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import datetime
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from jdev_cli.tools.base import Tool, ToolCategory, ToolResult
from jdev_cli.tools._parity_utils import COMMAND_SEARCH_PATHS, SKILL_CACHE_TTL

logger = logging.getLogger(__name__)


# =============================================================================
# ASK USER QUESTION TOOL
# =============================================================================

class AskUserQuestionTool(Tool):
    """
    Ask the user a question with predefined options.

    Claude Code parity: Interactive question/answer during execution.
    Allows gathering user preferences, clarifying requirements, and getting decisions.

    Question Schema:
    - question: The question text
    - header: Short label (max 12 chars)
    - options: 2-4 choices with label and description
    - multiSelect: Allow multiple selections

    Example:
        result = await ask.execute(questions=[
            {
                "question": "Which database should we use?",
                "header": "Database",
                "options": [
                    {"label": "PostgreSQL", "description": "Robust relational DB"},
                    {"label": "SQLite", "description": "Simple file-based DB"}
                ],
                "multiSelect": False
            }
        ])
    """

    # Store pending questions
    _pending_questions: Dict[str, Dict[str, Any]] = {}
    _question_counter: int = 0

    def __init__(self):
        super().__init__()
        self.name = "ask_user_question"
        self.category = ToolCategory.CONTEXT
        self.description = "Ask user questions with predefined options"
        self.parameters = {
            "questions": {
                "type": "array",
                "description": "List of questions (1-4) with options",
                "required": True
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Create a question for the user."""
        questions = kwargs.get("questions", [])

        # Validate input
        if not questions:
            return ToolResult(success=False, error="questions array is required")

        if not isinstance(questions, list):
            return ToolResult(success=False, error="questions must be an array")

        if len(questions) > 4:
            return ToolResult(success=False, error="Maximum 4 questions allowed")

        # Validate question format
        validated_questions = []
        errors = []

        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                errors.append(f"Question {i+1}: must be an object")
                continue

            question_text = q.get("question", "")
            options = q.get("options", [])
            header = q.get("header", "Question")
            multi_select = q.get("multiSelect", False)

            # Validate question text
            if not question_text:
                errors.append(f"Question {i+1}: question text is required")
                continue

            # Validate options
            if not options or not isinstance(options, list):
                errors.append(f"Question {i+1}: options array is required")
                continue

            if len(options) < 2:
                errors.append(f"Question {i+1}: at least 2 options required")
                continue

            if len(options) > 4:
                options = options[:4]  # Limit to 4 options

            # Validate each option
            valid_options = []
            for j, opt in enumerate(options):
                if isinstance(opt, dict) and opt.get("label"):
                    valid_options.append({
                        "label": str(opt.get("label", ""))[:50],
                        "description": str(opt.get("description", ""))[:200]
                    })
                elif isinstance(opt, str):
                    valid_options.append({
                        "label": opt[:50],
                        "description": ""
                    })

            if len(valid_options) < 2:
                errors.append(f"Question {i+1}: at least 2 valid options required")
                continue

            validated_questions.append({
                "question": question_text[:500],
                "header": str(header)[:12],
                "options": valid_options,
                "multiSelect": bool(multi_select)
            })

        if errors:
            return ToolResult(
                success=False,
                error="; ".join(errors)
            )

        if not validated_questions:
            return ToolResult(success=False, error="No valid questions provided")

        # Store pending question
        AskUserQuestionTool._question_counter += 1
        question_id = f"q_{AskUserQuestionTool._question_counter}"

        AskUserQuestionTool._pending_questions[question_id] = {
            "id": question_id,
            "questions": validated_questions,
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat()
        }

        return ToolResult(
            success=True,
            data={
                "question_id": question_id,
                "questions": validated_questions,
                "status": "pending",
                "message": "Question(s) queued for user"
            },
            metadata={"count": len(validated_questions)}
        )

    @classmethod
    def get_pending_questions(cls) -> List[Dict]:
        """Get all pending questions."""
        return [
            q for q in cls._pending_questions.values()
            if q["status"] == "pending"
        ]

    @classmethod
    def answer_question(cls, question_id: str, answers: Dict) -> bool:
        """Record user's answer to a question."""
        if question_id not in cls._pending_questions:
            return False

        cls._pending_questions[question_id]["answers"] = answers
        cls._pending_questions[question_id]["status"] = "answered"
        return True

    @classmethod
    def clear_questions(cls) -> None:
        """Clear all pending questions (for testing)."""
        cls._pending_questions.clear()
        cls._question_counter = 0


# =============================================================================
# SKILL TOOL
# =============================================================================

class SkillTool(Tool):
    """
    Execute a skill (slash command) within the conversation.

    Claude Code Parity: Implements the Skill tool for executing
    user-defined slash commands from .claude/commands/ or .jdev/commands/.

    Skills are markdown files that expand into prompts when invoked.

    Example:
        result = await skill.execute(skill="review-pr")
        prompt = result.data["prompt"]
    """

    # Track available skills (class-level cache)
    _skills_cache: Dict[str, Dict[str, Any]] = {}
    _cache_time: float = 0.0

    def __init__(self):
        super().__init__()
        self.name = "skill"
        self.category = ToolCategory.CONTEXT
        self.description = "Execute a skill (slash command)"
        self.parameters = {
            "skill": {
                "type": "string",
                "description": "The skill name (no arguments). E.g., 'pdf' or 'review-pr'",
                "required": True
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute skill/slash command."""
        skill_name = kwargs.get("skill", "")

        if not skill_name:
            return ToolResult(success=False, error="skill name is required")

        # Clean skill name
        skill_name = skill_name.lstrip("/").strip().lower()

        if not skill_name:
            return ToolResult(success=False, error="Invalid skill name")

        # Refresh skills cache if needed
        if time.time() - SkillTool._cache_time > SKILL_CACHE_TTL:
            self._refresh_skills_cache()

        # Check if skill exists
        if skill_name not in SkillTool._skills_cache:
            available = list(SkillTool._skills_cache.keys())[:10]
            hint = f" Available: {', '.join(available)}" if available else ""
            return ToolResult(
                success=False,
                error=f"Skill '{skill_name}' not found.{hint}"
            )

        skill = SkillTool._skills_cache[skill_name]

        return ToolResult(
            success=True,
            data={
                "skill": skill_name,
                "prompt": skill.get("content", ""),
                "description": skill.get("description", ""),
                "source": skill.get("source", ""),
                "status": "loaded"
            },
            metadata={
                "file": skill.get("file", ""),
                "scope": skill.get("scope", "project")
            }
        )

    def _refresh_skills_cache(self) -> None:
        """Refresh the skills cache from command files."""
        SkillTool._skills_cache = {}
        SkillTool._cache_time = time.time()

        # Look for command files in multiple locations
        search_paths = []
        for base in COMMAND_SEARCH_PATHS:
            search_paths.append(Path(base))  # Project-level
            search_paths.append(Path.home() / base.lstrip("./"))  # User-level

        for search_path in search_paths:
            if not search_path.exists():
                continue

            scope = "user" if str(Path.home()) in str(search_path) else "project"

            try:
                for md_file in search_path.glob("*.md"):
                    skill_name = md_file.stem.lower()

                    # Don't overwrite existing (project takes precedence)
                    if skill_name in SkillTool._skills_cache:
                        continue

                    try:
                        content = md_file.read_text(encoding="utf-8")

                        # Extract description from first line if it's a heading
                        lines = content.split("\n")
                        description = ""
                        if lines and lines[0].startswith("#"):
                            description = lines[0].lstrip("# ").strip()

                        SkillTool._skills_cache[skill_name] = {
                            "content": content,
                            "description": description[:200],
                            "file": str(md_file),
                            "source": search_path.name,
                            "scope": scope
                        }
                        logger.debug(f"Loaded skill: {skill_name} from {md_file}")

                    except Exception as e:
                        logger.warning(f"Failed to load skill {md_file}: {e}")
                        continue

            except PermissionError:
                logger.debug(f"Permission denied reading {search_path}")
                continue

    @classmethod
    def list_skills(cls) -> List[Dict[str, str]]:
        """List all available skills."""
        return [
            {
                "name": name,
                "description": skill.get("description", ""),
                "scope": skill.get("scope", "project")
            }
            for name, skill in cls._skills_cache.items()
        ]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear skills cache (for testing)."""
        cls._skills_cache.clear()
        cls._cache_time = 0.0


# =============================================================================
# SLASH COMMAND TOOL
# =============================================================================

class SlashCommandTool(Tool):
    """
    Execute a slash command within the conversation.

    Claude Code Parity: Implements the SlashCommand tool for
    executing custom slash commands with arguments.

    Slash commands are defined in .claude/commands/ or .jdev/commands/
    as markdown files that expand into prompts.

    Argument substitution patterns:
    - $1, ${1}: First argument
    - {args}, {{args}}: All arguments
    - $ARGUMENTS: All arguments

    Example:
        result = await cmd.execute(command="/review-pr 123")
        expanded = result.data["expanded_prompt"]
    """

    def __init__(self):
        super().__init__()
        self.name = "slash_command"
        self.category = ToolCategory.CONTEXT
        self.description = "Execute a slash command with arguments"
        self.parameters = {
            "command": {
                "type": "string",
                "description": "The slash command to execute, including arguments. E.g., '/review-pr 123'",
                "required": True
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute slash command."""
        command = kwargs.get("command", "")

        if not command:
            return ToolResult(success=False, error="command is required")

        # Parse command and arguments
        command = command.strip()
        parts = command.lstrip("/").split(maxsplit=1)
        cmd_name = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if not cmd_name:
            return ToolResult(success=False, error="Invalid command format")

        # Use SkillTool to find the command
        skill_tool = SkillTool()
        skill_tool._refresh_skills_cache()

        if cmd_name not in SkillTool._skills_cache:
            available = list(SkillTool._skills_cache.keys())[:5]
            hint = f" Try: {', '.join(available)}" if available else ""
            return ToolResult(
                success=False,
                error=f"Command '/{cmd_name}' not found.{hint}"
            )

        skill = SkillTool._skills_cache[cmd_name]
        prompt = skill.get("content", "")

        # Substitute arguments if present
        if args:
            # Support multiple substitution patterns
            substitutions = [
                ("$1", args),
                ("${1}", args),
                ("{args}", args),
                ("{{args}}", args),
                ("$ARGUMENTS", args),
                ("${ARGUMENTS}", args),
            ]

            for pattern, replacement in substitutions:
                prompt = prompt.replace(pattern, replacement)

        return ToolResult(
            success=True,
            data={
                "command": cmd_name,
                "args": args,
                "expanded_prompt": prompt,
                "status": "expanded"
            },
            metadata={
                "file": skill.get("file", ""),
                "has_args": bool(args),
                "description": skill.get("description", "")
            }
        )


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_interaction_tools() -> List[Tool]:
    """Get all user interaction tools."""
    return [
        AskUserQuestionTool(),
        SkillTool(),
        SlashCommandTool(),
    ]


__all__ = [
    "AskUserQuestionTool",
    "SkillTool",
    "SlashCommandTool",
    "get_interaction_tools",
]
