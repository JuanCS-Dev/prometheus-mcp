"""Few-shot examples for teaching the LLM correct tool usage patterns."""

FEW_SHOT_EXAMPLES = [
    # Example 1: Simple file reading
    {
        "user": "show me the README",
        "assistant": '[{"tool": "readfile", "args": {"path": "README.md"}}]',
        "category": "file_reading",
        "explanation": "Direct file read request"
    },

    # Example 2: File search
    {
        "user": "find all TODO comments in python files",
        "assistant": '[{"tool": "searchfiles", "args": {"pattern": "TODO", "path": ".", "file_pattern": "*.py"}}]',
        "category": "search",
        "explanation": "Search with file type filter"
    },

    # Example 3: File editing
    {
        "user": "replace 'old_name' with 'new_name' in config.py",
        "assistant": '[{"tool": "editfile", "args": {"path": "config.py", "edits": [{"search": "old_name", "replace": "new_name"}]}}]',
        "category": "file_writing",
        "explanation": "Search and replace in file"
    },

    # Example 4: Multi-step workflow
    {
        "user": "show git status and diff",
        "assistant": '[{"tool": "gitstatus", "args": {}}, {"tool": "gitdiff", "args": {}}]',
        "category": "git",
        "explanation": "Sequential tool calls"
    },

    # Example 5: Directory operations
    {
        "user": "list files in the src directory",
        "assistant": '[{"tool": "ls", "args": {"path": "src"}}]',
        "category": "terminal",
        "explanation": "Unix-like ls command"
    },

    # Example 6: File creation
    {
        "user": "create a new file called test.py with a hello world function",
        "assistant": '[{"tool": "writefile", "args": {"path": "test.py", "content": "def hello():\\n    print(\\"Hello, World!\\")\\n\\nif __name__ == \\"__main__\\":\\n    hello()\\n"}}]',
        "category": "file_writing",
        "explanation": "Create file with content"
    },

    # Example 7: Shell command for complex operations
    {
        "user": "find all files larger than 10MB",
        "assistant": '[{"tool": "bashcommand", "args": {"command": "find . -type f -size +10M -exec ls -lh {} \\\\;"}}]',
        "category": "execution",
        "explanation": "Use shell when no specific tool exists"
    },

    # Example 8: Directory tree
    {
        "user": "show me the project structure",
        "assistant": '[{"tool": "getdirectorytree", "args": {"path": ".", "max_depth": 3}}]',
        "category": "search",
        "explanation": "Directory tree visualization"
    },

    # Example 9: Safe file deletion
    {
        "user": "delete temp.log",
        "assistant": '[{"tool": "deletefile", "args": {"path": "temp.log"}}]',
        "category": "file_management",
        "explanation": "Safe deletion (moves to .trash)"
    },

    # Example 10: Context query
    {
        "user": "what files have I been working on?",
        "assistant": '[{"tool": "getcontext", "args": {}}]',
        "category": "context",
        "explanation": "Query session context"
    },

    # Example 11: Git workflow
    {
        "user": "stage all changes and show status",
        "assistant": '[{"tool": "bashcommand", "args": {"command": "git add -A"}}, {"tool": "gitstatus", "args": {}}]',
        "category": "git",
        "explanation": "Combine shell and tools"
    },

    # Example 12: Multiple file reading
    {
        "user": "read main.py and utils.py",
        "assistant": '[{"tool": "readmultiplefiles", "args": {"paths": ["main.py", "utils.py"]}}]',
        "category": "file_reading",
        "explanation": "Batch file reading"
    },

    # Example 13: Directory creation
    {
        "user": "create a folder called tests",
        "assistant": '[{"tool": "mkdir", "args": {"path": "tests"}}]',
        "category": "file_management",
        "explanation": "Directory creation"
    },

    # Example 14: Navigate + list
    {
        "user": "go to src and list files",
        "assistant": '[{"tool": "cd", "args": {"path": "src"}}, {"tool": "ls", "args": {}}]',
        "category": "terminal",
        "explanation": "Navigation workflow"
    },

    # Example 15: Conversational (no tool needed)
    {
        "user": "what does the rm command do?",
        "assistant": "The `rm` command removes (deletes) files or directories. In this CLI, we have a safe `rm` tool that moves files to `.trash/` instead of permanently deleting them. You can also use `deletefile` which does the same thing. Would you like to delete a specific file?",
        "category": "explanation",
        "explanation": "Answer questions directly without tools"
    },

    # Example 16: Error recovery pattern
    {
        "user": "read config.yaml",
        "assistant": '[{"tool": "readfile", "args": {"path": "config.yaml"}}]',
        "category": "error_recovery",
        "explanation": "Initial attempt",
        "follow_up": {
            "error": "File 'config.yaml' not found",
            "recovery": "I see that config.yaml doesn't exist. Let me search for similar files: [{'tool': 'bashcommand', 'args': {'command': 'find . -name \"config.*\" -o -name \"*.yaml\"'}}]"
        }
    },

    # Example 17: Complex search and replace
    {
        "user": "in all python files, replace print statements with logging.info",
        "assistant": '[{"tool": "searchfiles", "args": {"pattern": "print\\\\(", "path": ".", "file_pattern": "*.py"}}]',
        "category": "search",
        "explanation": "First find occurrences, then user can confirm replacement"
    },

    # Example 18: Git commit workflow
    {
        "user": "commit with message 'fix bug'",
        "assistant": '[{"tool": "bashcommand", "args": {"command": "git add -A && git commit -m \\"fix bug\\""}}]',
        "category": "git",
        "explanation": "Combined git operations"
    },

    # Example 19: Copy and modify
    {
        "user": "copy main.py to backup.py",
        "assistant": '[{"tool": "cp", "args": {"source": "main.py", "destination": "backup.py"}}]',
        "category": "file_management",
        "explanation": "File copy operation"
    },

    # Example 20: Insert at specific line
    {
        "user": "add import logging at the top of utils.py",
        "assistant": '[{"tool": "insertlines", "args": {"path": "utils.py", "line": 1, "content": "import logging\\n"}}]',
        "category": "file_writing",
        "explanation": "Insert at specific position"
    },
]


# Examples grouped by category for context-aware selection
EXAMPLES_BY_CATEGORY = {
    "file_reading": [ex for ex in FEW_SHOT_EXAMPLES if ex.get("category") == "file_reading"],
    "file_writing": [ex for ex in FEW_SHOT_EXAMPLES if ex.get("category") == "file_writing"],
    "file_management": [ex for ex in FEW_SHOT_EXAMPLES if ex.get("category") == "file_management"],
    "search": [ex for ex in FEW_SHOT_EXAMPLES if ex.get("category") == "search"],
    "execution": [ex for ex in FEW_SHOT_EXAMPLES if ex.get("category") == "execution"],
    "git": [ex for ex in FEW_SHOT_EXAMPLES if ex.get("category") == "git"],
    "terminal": [ex for ex in FEW_SHOT_EXAMPLES if ex.get("category") == "terminal"],
    "context": [ex for ex in FEW_SHOT_EXAMPLES if ex.get("category") == "context"],
}


def get_examples_for_context(user_input: str, max_examples: int = 5) -> list:
    """Get relevant few-shot examples based on user input.
    
    Args:
        user_input: User's query/command
        max_examples: Maximum examples to return
        
    Returns:
        List of relevant examples
    """
    # Simple keyword matching for now
    # TODO: Use embeddings for semantic similarity

    keywords = {
        "file_reading": ["read", "show", "cat", "display", "view", "content"],
        "file_writing": ["write", "create", "edit", "modify", "replace", "change", "update"],
        "file_management": ["copy", "move", "delete", "remove", "rename", "cp", "mv", "rm"],
        "search": ["find", "search", "grep", "look", "locate"],
        "execution": ["run", "execute", "command", "bash"],
        "git": ["git", "commit", "push", "pull", "status", "diff", "branch"],
        "terminal": ["ls", "cd", "pwd", "mkdir", "list", "directory"],
        "context": ["context", "session", "history", "what", "working on"],
    }

    user_lower = user_input.lower()

    # Score each category
    category_scores = {}
    for category, words in keywords.items():
        score = sum(1 for word in words if word in user_lower)
        if score > 0:
            category_scores[category] = score

    # Get examples from top categories
    selected = []
    for category in sorted(category_scores, key=category_scores.get, reverse=True):
        examples = EXAMPLES_BY_CATEGORY.get(category, [])
        remaining = max_examples - len(selected)
        selected.extend(examples[:remaining])
        if len(selected) >= max_examples:
            break

    # If not enough, add random examples
    if len(selected) < max_examples:
        import random
        remaining = max_examples - len(selected)
        pool = [ex for ex in FEW_SHOT_EXAMPLES if ex not in selected]
        selected.extend(random.sample(pool, min(remaining, len(pool))))

    return selected[:max_examples]


def format_examples_for_prompt(examples: list) -> str:
    """Format few-shot examples for inclusion in prompt.
    
    Args:
        examples: List of example dicts
        
    Returns:
        Formatted string with examples
    """
    formatted = []
    for i, ex in enumerate(examples, 1):
        formatted.append(f"Example {i}:")
        formatted.append(f"User: {ex['user']}")
        formatted.append(f"Assistant: {ex['assistant']}")
        if 'explanation' in ex:
            formatted.append(f"// {ex['explanation']}")
        formatted.append("")

    return "\n".join(formatted)


# Error recovery examples
ERROR_RECOVERY_EXAMPLES = [
    {
        "scenario": "file_not_found",
        "error": "FileNotFoundError: [Errno 2] No such file or directory: 'config.py'",
        "analysis": "The file doesn't exist in the current directory.",
        "recovery": "Let me search for similar files: find . -name 'config*' -o -name '*.py'",
        "action": '[{"tool": "bashcommand", "args": {"command": "find . -name \\"config*\\""}}]'
    },
    {
        "scenario": "permission_denied",
        "error": "PermissionError: [Errno 13] Permission denied: '/etc/hosts'",
        "analysis": "This file requires elevated permissions.",
        "recovery": "You'll need sudo access. Would you like me to try with: sudo cat /etc/hosts",
        "action": "Ask for confirmation before using sudo"
    },
    {
        "scenario": "syntax_error",
        "error": "SyntaxError: invalid syntax in file.py line 15",
        "analysis": "There's a Python syntax error.",
        "recovery": "Let me read the file to see the problematic line",
        "action": '[{"tool": "readfile", "args": {"path": "file.py"}}]'
    },
    {
        "scenario": "command_not_found",
        "error": "bash: ripgrep: command not found",
        "analysis": "The ripgrep tool is not installed.",
        "recovery": "Would you like to use grep instead, or install ripgrep?",
        "action": "Suggest fallback: grep -r [pattern] ."
    },
]


def get_error_recovery_example(error_msg: str) -> dict:
    """Get error recovery example based on error message.
    
    Args:
        error_msg: Error message string
        
    Returns:
        Relevant recovery example dict
    """
    error_lower = error_msg.lower()

    # Match error patterns
    if "not found" in error_lower or "no such file" in error_lower:
        return ERROR_RECOVERY_EXAMPLES[0]
    elif "permission" in error_lower:
        return ERROR_RECOVERY_EXAMPLES[1]
    elif "syntax" in error_lower:
        return ERROR_RECOVERY_EXAMPLES[2]
    elif "command not found" in error_lower:
        return ERROR_RECOVERY_EXAMPLES[3]

    # Default generic recovery
    return {
        "scenario": "generic",
        "error": error_msg,
        "analysis": "An error occurred.",
        "recovery": "Let me try to understand and fix this issue.",
        "action": "Analyze error and suggest alternative"
    }
