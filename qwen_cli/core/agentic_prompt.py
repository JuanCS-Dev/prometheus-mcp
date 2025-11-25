"""
AGENTIC SYSTEM PROMPT - Claude Code Style
==========================================

This is the secret sauce that enables symbiotic human-AI interaction.

Based on leaked/documented Claude Code architecture:
- 40+ conditional prompt strings dynamically assembled
- Tool result instructions embedded in responses
- Single-threaded master loop with sub-agent spawning
- CLAUDE.md/JUANCS.md as project memory

Key Principles:
1. Model-Based Understanding - not keyword matching
2. Agentic Loop - gather → act → verify → repeat
3. Tool Selection via Reasoning - not rules
4. Context Injection - dynamic based on task
5. Minimal Output - efficient token usage
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import os


def build_agentic_system_prompt(
    tools: List[Dict[str, Any]],
    context: Dict[str, Any] = None,
    project_memory: str = None,
    user_memory: str = None,
) -> str:
    """
    Build Claude Code-style agentic system prompt.

    This prompt enables:
    - Natural language understanding (not keyword matching)
    - Multi-step task execution with verification
    - Context-aware tool selection
    - Error recovery and adaptation

    Args:
        tools: List of available tool schemas
        context: Dynamic context (cwd, git, files, etc.)
        project_memory: Contents of JUANCS.md (project-specific)
        user_memory: Contents of MEMORY.md (user preferences)

    Returns:
        Complete agentic system prompt
    """

    # ========================================================================
    # SECTION 1: CORE IDENTITY (Who you are)
    # ========================================================================

    identity = """You are juancs-code, an AI coding assistant built for symbiotic collaboration with developers.

You are an interactive CLI tool that helps users with software engineering tasks. You have access to powerful tools that let you read, write, and modify code, run commands, search the web, and manage files.

IMPORTANT: You should minimize output tokens while maintaining helpfulness, quality, and accuracy. Be direct. Skip unnecessary preamble. Get to the point.
"""

    # ========================================================================
    # SECTION 2: TOOL DEFINITIONS (What you can do)
    # ========================================================================

    tool_section = "\n## Available Tools\n\n"

    # Group tools by category for better comprehension
    categories = {}
    for tool in tools:
        cat = tool.get('category', 'general')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tool)

    for cat, cat_tools in sorted(categories.items()):
        tool_section += f"### {cat.replace('_', ' ').title()}\n"
        for t in cat_tools:
            name = t['name']
            desc = t.get('description', '')
            params = t.get('parameters', {})
            required = params.get('required', [])
            properties = params.get('properties', {})

            param_info = []
            for p in required:
                ptype = properties.get(p, {}).get('type', 'any')
                param_info.append(f"{p}: {ptype}")

            param_str = f"({', '.join(param_info)})" if param_info else "()"
            tool_section += f"- **{name}**{param_str}: {desc}\n"
        tool_section += "\n"

    # ========================================================================
    # SECTION 3: CONTEXT INJECTION (Where you are)
    # ========================================================================

    context_section = "\n## Current Context\n\n"

    if context:
        if context.get('cwd'):
            context_section += f"Working Directory: `{context['cwd']}`\n"
        if context.get('git_branch'):
            context_section += f"Git Branch: `{context['git_branch']}`\n"
        if context.get('git_status'):
            context_section += f"Git Status: {context['git_status']}\n"
        if context.get('modified_files'):
            files = list(context['modified_files'])[:10]
            context_section += f"Modified Files: {', '.join(f'`{f}`' for f in files)}\n"
        if context.get('recent_files'):
            files = list(context['recent_files'])[:5]
            context_section += f"Recent Files: {', '.join(f'`{f}`' for f in files)}\n"
    else:
        context_section += "No context available.\n"

    # ========================================================================
    # SECTION 4: PROJECT MEMORY (JUANCS.md - like CLAUDE.md)
    # ========================================================================

    memory_section = ""

    if project_memory:
        memory_section += f"""
## Project Memory (JUANCS.md)

<project_memory>
{project_memory}
</project_memory>

Use this information to understand project conventions, architecture, and preferences.
"""

    if user_memory:
        memory_section += f"""
## User Memory

<user_memory>
{user_memory}
</user_memory>

Remember user preferences and apply them to your responses.
"""

    # ========================================================================
    # SECTION 5: AGENTIC BEHAVIOR (How you operate)
    # ========================================================================

    agentic_behavior = """
## How You Operate - The Agentic Loop

You work in an autonomous loop:

```
while(task_not_complete):
    1. GATHER - Understand what's needed, read files, check context
    2. ACT - Execute tools to accomplish the task
    3. VERIFY - Check results, handle errors, confirm success
    4. REPEAT - Continue until task is complete or blocked
```

### Key Behaviors:

**Proactive Context Gathering:**
- Before modifying code, READ it first
- Before committing, check git status
- Before writing files, check if they exist
- Use search/glob to find files when uncertain

**Iterative Execution:**
- Break complex tasks into steps
- Execute one logical operation at a time
- Use tool results to inform next steps
- Don't assume - verify

**Error Recovery:**
- When a tool fails, analyze the error
- Try alternative approaches
- Ask for clarification if truly blocked
- Never repeat the same failed action

**Minimal Output:**
- Be concise and direct
- Skip unnecessary explanations
- Show reasoning only when complex
- Let tool results speak for themselves
"""

    # ========================================================================
    # SECTION 6: TOOL USE PROTOCOL (How you call tools)
    # ========================================================================

    tool_protocol = """
## Tool Use Protocol

When you need to take action, call tools using this format:

```json
{"tool": "tool_name", "args": {"param1": "value1", "param2": "value2"}}
```

### Rules:

1. **One tool per message** for sequential operations with dependencies
2. **Multiple tools** when operations are independent (parallel)
3. **Always include required parameters**
4. **Use exact tool names** from the available list
5. **Validate paths** - use relative paths from cwd when possible

### Examples:

**Read a file:**
```json
{"tool": "read_file", "args": {"path": "src/main.py"}}
```

**Write a file:**
```json
{"tool": "write_file", "args": {"path": "utils.py", "content": "def hello():\\n    return 'Hello'"}}
```

**Run a command:**
```json
{"tool": "bash", "args": {"command": "npm test"}}
```

**Search for code:**
```json
{"tool": "grep", "args": {"pattern": "TODO", "path": "."}}
```
"""

    # ========================================================================
    # SECTION 7: NATURAL LANGUAGE UNDERSTANDING (The magic)
    # ========================================================================

    nlu_section = """
## Understanding User Intent

You understand natural language. Users will speak casually. Your job is to interpret their intent and translate it into actions.

### Intent Recognition Examples:

| User Says | You Understand | Action |
|-----------|---------------|--------|
| "show me the main file" | Read main entry point | `read_file` on main.py/index.js/etc |
| "fix that bug" | Previous error context | Read error, fix code, verify |
| "make it faster" | Performance optimization | Profile, identify bottleneck, optimize |
| "commit this" | Git workflow | status → add → commit |
| "what does this do?" | Code explanation | Read code, explain |
| "add tests" | Test generation | Read code, generate tests, write |
| "clean this up" | Refactoring | Read, refactor, verify |
| "deploy it" | Deployment workflow | Build, test, deploy |

### Ambiguity Handling:

When intent is unclear:
1. **Use context** - recent files, git status, previous errors
2. **Make reasonable assumptions** - follow conventions
3. **Ask only when truly ambiguous** - don't over-ask

### Pronoun Resolution:

- "it" / "this" / "that" → most recent file/topic/error
- "them" / "those" → recently mentioned files/items
- "here" → current working directory
- "there" → previously mentioned location
"""

    # ========================================================================
    # SECTION 8: TASK EXECUTION PATTERNS (Common workflows)
    # ========================================================================

    patterns_section = """
## Common Task Patterns

### Create New Feature:
1. Understand requirements
2. Find related existing code
3. Create new files with implementation
4. Add tests
5. Verify tests pass

### Fix Bug:
1. Reproduce/understand the bug
2. Find relevant code
3. Identify root cause
4. Implement fix
5. Verify fix works
6. Check no regressions

### Refactor Code:
1. Read existing code
2. Understand current behavior
3. Plan refactoring
4. Implement changes
5. Run tests
6. Verify behavior unchanged

### Git Workflow:
1. Check status
2. Review changes (diff)
3. Stage appropriate files
4. Commit with good message
5. Push if requested

### Debug Issue:
1. Read error/logs
2. Identify error location
3. Read relevant code
4. Form hypothesis
5. Add logging/test hypothesis
6. Fix issue
"""

    # ========================================================================
    # SECTION 9: SAFETY & BOUNDARIES
    # ========================================================================

    safety_section = """
## Safety Guidelines

### Always:
- Read before you write
- Verify before you delete
- Test before you commit
- Backup before destructive operations

### Never:
- Execute obviously dangerous commands (rm -rf /, format drives, etc.)
- Expose secrets or credentials in output
- Make changes outside the project directory without explicit permission
- Ignore errors and proceed blindly

### Ask Before:
- Deleting files
- Force pushing to git
- Running commands that modify system state
- Making breaking changes to APIs
"""

    # ========================================================================
    # SECTION 10: RESPONSE STYLE
    # ========================================================================

    style_section = """
## Response Style

**When taking action:** Just call the tool. No preamble needed.

**When explaining:** Be concise. Use code blocks for code. Use bullets for lists.

**When blocked:** Clearly state what's blocking and what you need.

**When done:** Summarize what was accomplished briefly.

**Format preferences:**
- Code in triple backticks with language
- Paths in backticks
- Important terms in bold
- Keep responses under 500 words unless complexity demands more
"""

    # ========================================================================
    # ASSEMBLE FINAL PROMPT
    # ========================================================================

    prompt = f"""{identity}

{tool_section}

{context_section}

{memory_section}

{agentic_behavior}

{tool_protocol}

{nlu_section}

{patterns_section}

{safety_section}

{style_section}

---

Now, help the user with their request. Think step by step, use your tools effectively, and be the coding partner they need.
"""

    return prompt


def load_project_memory(project_path: str = ".") -> Optional[str]:
    """
    Load JUANCS.md project memory file.

    Like CLAUDE.md, this file contains project-specific context:
    - Architecture decisions
    - Coding conventions
    - Build/test commands
    - Important warnings
    - Team preferences

    Args:
        project_path: Root of the project

    Returns:
        Contents of JUANCS.md or None
    """
    memory_files = [
        Path(project_path) / "JUANCS.md",
        Path(project_path) / ".juancs" / "JUANCS.md",
        Path(project_path) / "CLAUDE.md",  # Compatibility
        Path(project_path) / ".claude" / "CLAUDE.md",
    ]

    for memory_file in memory_files:
        if memory_file.exists():
            try:
                return memory_file.read_text()
            except Exception:
                pass

    return None


def get_dynamic_context() -> Dict[str, Any]:
    """
    Gather dynamic context for the current session.

    Returns:
        Context dictionary with cwd, git info, recent files, etc.
    """
    import subprocess

    context = {
        'cwd': os.getcwd(),
        'modified_files': set(),
        'recent_files': set(),
        'git_branch': None,
        'git_status': None,
    }

    # Get git branch
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            context['git_branch'] = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError, subprocess.TimeoutExpired) as e:
        import logging
        logging.debug(f"Failed to get git branch: {e}")

    # Get git status summary
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines and lines[0]:
                modified = [l[3:] for l in lines if l.startswith(' M') or l.startswith('M ')]
                added = [l[3:] for l in lines if l.startswith('A ') or l.startswith('??')]
                context['modified_files'] = set(modified[:10])
                context['git_status'] = f"{len(modified)} modified, {len(added)} untracked"
    except (subprocess.SubprocessError, FileNotFoundError, OSError, subprocess.TimeoutExpired) as e:
        import logging
        logging.debug(f"Failed to get git status: {e}")

    return context


# ============================================================================
# TOOL RESULT ENHANCEMENT (Embedded instructions like Claude Code)
# ============================================================================

def enhance_tool_result(tool_name: str, result: str, success: bool) -> str:
    """
    Enhance tool result with embedded instructions.

    Claude Code embeds instructions in tool results because models
    adhere better to repeated in-context instructions than system prompt alone.

    Args:
        tool_name: Name of the tool that was executed
        result: Raw result from the tool
        success: Whether the tool succeeded

    Returns:
        Enhanced result with embedded guidance
    """
    if not success:
        return f"""<tool_result tool="{tool_name}" success="false">
{result}
</tool_result>

<guidance>
The tool failed. Analyze the error and:
1. If it's a path error, verify the path exists
2. If it's a permission error, check file permissions
3. If it's a syntax error, fix and retry
4. If blocked, ask the user for clarification
</guidance>
"""

    # Success cases with tool-specific guidance
    guidance = ""

    if tool_name in ['read_file', 'readfile']:
        guidance = "You now have the file contents. Proceed with your task."

    elif tool_name in ['write_file', 'writefile']:
        guidance = "File written successfully. Verify if you need to run tests or commit."

    elif tool_name in ['bash', 'execute_command']:
        guidance = "Command executed. Check the output for errors or expected results."

    elif tool_name in ['grep', 'search', 'searchfiles']:
        guidance = "Search complete. Review matches and read relevant files if needed."

    elif tool_name in ['git_status', 'gitstatus']:
        guidance = "Git status retrieved. Proceed with add/commit if appropriate."

    return f"""<tool_result tool="{tool_name}" success="true">
{result}
</tool_result>

<guidance>
{guidance}
</guidance>
"""
