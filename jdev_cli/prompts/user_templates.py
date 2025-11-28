"""User prompt templates for building context-rich prompts."""

from typing import List, Dict, Any


def format_tool_schemas(tool_schemas: List[Dict]) -> str:
    """Format tool schemas in a concise, readable way.
    
    Args:
        tool_schemas: List of tool schema dictionaries
        
    Returns:
        Formatted tool schemas string
    """
    formatted = []

    # Group by category
    by_category = {}
    for schema in tool_schemas:
        category = schema.get('category', 'other')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(schema)

    # Format each category
    for category, schemas in sorted(by_category.items()):
        formatted.append(f"\n**{category.upper()}:**")
        for schema in schemas:
            name = schema['name']
            desc = schema['description']

            # Get required parameters
            params = schema['parameters'].get('properties', {})
            required = schema['parameters'].get('required', [])

            param_str = ""
            if params:
                required_params = [f"{p}*" for p in required]
                optional_params = [p for p in params.keys() if p not in required]
                all_params = required_params + optional_params
                param_str = f" ({', '.join(all_params)})"

            formatted.append(f"  • {name}{param_str}: {desc}")

    return "\n".join(formatted)


def format_context(context: Dict[str, Any]) -> str:
    """Format session context for prompt.
    
    Args:
        context: Context dictionary with cwd, files, etc.
        
    Returns:
        Formatted context string
    """
    parts = []

    if 'cwd' in context:
        parts.append(f"📁 Current directory: `{context['cwd']}`")

    if 'recent_files' in context and context['recent_files']:
        files = list(context['recent_files'])[:5]
        parts.append(f"📄 Recent files: {', '.join(f'`{f}`' for f in files)}")

    if 'modified_files' in context and context['modified_files']:
        files = list(context['modified_files'])[:5]
        parts.append(f"✏️  Modified: {', '.join(f'`{f}`' for f in files)}")

    if 'last_command' in context:
        parts.append(f"⚡ Last command: `{context['last_command']}`")

    if 'git_branch' in context:
        parts.append(f"🔀 Git branch: `{context['git_branch']}`")

    return "\n".join(parts) if parts else "No context available"


def format_conversation_history(history: List[Dict], max_turns: int = 5) -> str:
    """Format conversation history for context.
    
    Args:
        history: List of conversation turns
        max_turns: Maximum turns to include
        
    Returns:
        Formatted history string
    """
    if not history:
        return ""

    # Take last N turns
    recent = history[-max_turns:]

    formatted = []
    for turn in recent:
        role = turn.get('role', 'user')
        content = turn.get('content', '')

        # Truncate long content
        if len(content) > 200:
            content = content[:200] + "..."

        if role == 'user':
            formatted.append(f"User: {content}")
        elif role == 'assistant':
            formatted.append(f"Assistant: {content}")
        elif role == 'tool':
            tool_name = turn.get('tool_name', 'unknown')
            success = turn.get('success', False)
            status = "✓" if success else "✗"
            formatted.append(f"Tool {status}: {tool_name}")

    return "\n".join(formatted)


def format_error_context(error: str, previous_action: str = None) -> str:
    """Format error context for recovery prompts.
    
    Args:
        error: Error message
        previous_action: What was attempted
        
    Returns:
        Formatted error context
    """
    parts = [
        "❌ **Error occurred:**",
        f"```\n{error}\n```"
    ]

    if previous_action:
        parts.append(f"\n**Previous action:** {previous_action}")

    parts.append("\n**Please analyze this error and suggest:**")
    parts.append("1. What went wrong")
    parts.append("2. How to fix it")
    parts.append("3. Alternative approach if applicable")

    return "\n".join(parts)


def build_user_prompt(
    user_input: str,
    tool_schemas: List[Dict] = None,
    context: Dict = None,
    conversation_history: List[Dict] = None,
    few_shot_examples: List[Dict] = None,
    error_context: Dict = None
) -> str:
    """Build complete user prompt with all context.
    
    Args:
        user_input: User's query/command
        tool_schemas: Available tool schemas
        context: Current session context
        conversation_history: Recent conversation
        few_shot_examples: Relevant few-shot examples
        error_context: Error recovery context
        
    Returns:
        Complete formatted user prompt
    """
    sections = []

    # Add context if available
    if context:
        sections.append("## CURRENT CONTEXT")
        sections.append(format_context(context))
        sections.append("")

    # Add conversation history if available
    if conversation_history:
        history_text = format_conversation_history(conversation_history)
        if history_text:
            sections.append("## CONVERSATION HISTORY")
            sections.append(history_text)
            sections.append("")

    # Add few-shot examples if provided
    if few_shot_examples:
        sections.append("## EXAMPLES")
        from .few_shot_examples import format_examples_for_prompt
        sections.append(format_examples_for_prompt(few_shot_examples))
        sections.append("")

    # Add error context if this is recovery
    if error_context:
        sections.append(format_error_context(
            error_context.get('error', ''),
            error_context.get('previous_action')
        ))
        sections.append("")

    # Add tool schemas in concise format
    if tool_schemas:
        sections.append("## AVAILABLE TOOLS")
        sections.append(format_tool_schemas(tool_schemas))
        sections.append("")

    # Add user input
    sections.append("## USER REQUEST")
    sections.append(user_input)
    sections.append("")
    sections.append("**Respond with either:**")
    sections.append("1. JSON array of tool calls: `[{\"tool\": \"name\", \"args\": {...}}]`")
    sections.append("2. Helpful text response if no tools needed")

    return "\n".join(sections)


# Pre-built templates for common scenarios
TEMPLATES = {
    "simple_query": """## USER REQUEST
{user_input}

Available tools: {tool_names}

Respond with JSON tool call(s) or helpful text.""",

    "with_context": """## CONTEXT
{context}

## USER REQUEST
{user_input}

{tools_section}

Respond with appropriate tool calls or text.""",

    "error_recovery": """## PREVIOUS ERROR
{error}

## USER TRYING
{user_input}

Analyze the error and suggest a fix using available tools:
{tool_names}""",

    "multi_step": """## WORKFLOW REQUEST
{user_input}

This likely requires multiple steps. Plan the workflow and execute as tool calls.

Available tools:
{tool_names}

Return JSON array of sequential tool calls.""",
}


def get_template(template_name: str) -> str:
    """Get a pre-built template by name.
    
    Args:
        template_name: Template identifier
        
    Returns:
        Template string
    """
    return TEMPLATES.get(template_name, TEMPLATES["simple_query"])


def build_minimal_prompt(user_input: str, tool_names: List[str]) -> str:
    """Build minimal prompt for simple queries.
    
    Args:
        user_input: User's input
        tool_names: List of available tool names
        
    Returns:
        Minimal prompt string
    """
    return f"""User: {user_input}

Tools: {', '.join(tool_names)}

Respond with JSON tool call or text:"""


def build_chain_of_thought_prompt(user_input: str, context: Dict = None) -> str:
    """Build prompt that encourages chain-of-thought reasoning.
    
    Args:
        user_input: User's input
        context: Optional context
        
    Returns:
        Chain-of-thought prompt
    """
    prompt = [
        "## USER REQUEST",
        user_input,
        "",
        "**Think step by step:**",
        "1. What is the user trying to achieve?",
        "2. Which tools or commands are needed?",
        "3. What order should they execute in?",
        "4. Are there any dependencies or risks?",
        "",
        "Then respond with tool calls or explanation."
    ]

    if context:
        prompt.insert(0, f"## CONTEXT\n{format_context(context)}\n")

    return "\n".join(prompt)
