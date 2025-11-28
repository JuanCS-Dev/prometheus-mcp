"""
ExplorerAgent: The Context Navigator

This agent performs smart context gathering with token budget awareness.
It finds relevant files without loading the entire codebase.

Philosophy (Boris Cherny):
    "Context is king, but tokens are expensive."
    - Search before loading
    - Load only what's needed
    - Track token budget
    - 80% reduction from naive approach

Capabilities: READ_ONLY + smart search
"""

from typing import Any, Dict

from jdev_cli.agents.base import (
    AgentCapability,
    AgentRole,
    AgentTask,
    AgentResponse,
    BaseAgent,
)


EXPLORER_SYSTEM_PROMPT = """You are the Explorer Agent - a context navigator who finds relevant code efficiently.

ROLE: Smart Context Gatherer
CAPABILITIES: READ_ONLY + Search (Codebase & Web) (you can search, read, and fetch URLs, never modify)

YOUR MISSION:
1. Find files relevant to the user's request
2. Build focused context map (NOT the entire codebase)
3. Identify dependencies and relationships
4. Stay within token budget (prefer grep over full file reads)
5. Search web/docs if internal context is insufficient

STRATEGY:
1. Extract keywords from request
2. Use grep/search to find relevant files
3. Read ONLY the relevant files (max 5-10 files)
4. Summarize findings

TOKEN BUDGET RULES:
- Avoid loading entire codebase (50K+ tokens)
- Use grep for initial discovery
- Read files selectively (first N lines or specific functions)
- Target: 5K-10K tokens for context (10x reduction)

OUTPUT FORMAT (strict JSON):
{
    "relevant_files": [
        {
            "path": "src/auth/jwt.py",
            "relevance": "HIGH" | "MEDIUM" | "LOW",
            "reason": "Contains JWT token validation logic",
            "key_symbols": ["verify_token", "generate_token"],
            "line_range": [10, 150]  # optional
        }
    ],
    "dependencies": [
        {"from": "api.py", "to": "auth.py", "type": "imports"}
    ],
    "context_summary": "Brief summary of what was found",
    "token_estimate": 5000  # estimated context size
}

SEARCH STRATEGY:
- Use keywords: function names, class names, imports
- Look for: definitions, usages, tests
- Prioritize: entry points, interfaces, core logic
- Use web_search for external documentation or libraries
- Avoid: vendor folders, node_modules, __pycache__

PERSONALITY:
- Efficient and precise
- Minimalist (less is more)
- Budget-conscious
- Boris Cherny: "Load what you need, not what you can."

Remember: Your job is to build focused context, not dump the entire codebase.
"""


class ExplorerAgent(BaseAgent):
    """Explorer Agent - Smart context gathering with token awareness.
    
    The Explorer finds relevant files for a task without loading the entire
    codebase. It uses smart search strategies to minimize token usage while
    maximizing context quality.
    
    Usage:
        explorer = ExplorerAgent(llm_client, mcp_client)
        task = AgentTask(
            request="Find files related to authentication",
            session_id="session-123",
            context={"max_files": 10}  # optional limit
        )
        response = await explorer.execute(task)
        
        if response.success:
            files = response.data["relevant_files"]
            for file in files:
                print(f"{file['path']} - {file['relevance']}")
    """

    def __init__(
        self,
        llm_client: Any,
        mcp_client: Any,
    ) -> None:
        """Initialize Explorer agent.
        
        Args:
            llm_client: LLM client for context analysis
            mcp_client: MCP client for file operations
        """
        super().__init__(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=llm_client,
            mcp_client=mcp_client,
            system_prompt=EXPLORER_SYSTEM_PROMPT,
        )

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Find relevant files and build focused context.
        
        Args:
            task: Task with search request and optional constraints
            
        Returns:
            AgentResponse with relevant files and context map
            
        Process:
            1. Extract keywords from request
            2. Search for relevant files (grep/find)
            3. Analyze findings with LLM
            4. Return focused file list
        """
        try:
            # Extract max files limit
            max_files = task.context.get("max_files", 10)

            # Build search prompt
            search_prompt = self._build_search_prompt(task, max_files)

            # Call LLM for intelligent file selection
            llm_response = await self._call_llm(search_prompt)

            # Parse JSON response
            import json
            try:
                context_data = json.loads(llm_response)
            except json.JSONDecodeError:
                # Fallback: extract file paths from text
                context_data = self._extract_files_fallback(llm_response)

            # Validate response structure
            if "relevant_files" not in context_data:
                return AgentResponse(
                    success=False,
                    reasoning="LLM response missing 'relevant_files' field",
                    error="Invalid LLM response format",
                )

            relevant_files = context_data["relevant_files"]

            # Enforce max files limit
            if len(relevant_files) > max_files:
                relevant_files = relevant_files[:max_files]
                context_data["relevant_files"] = relevant_files

            # Calculate token estimate
            token_estimate = context_data.get("token_estimate", 0)
            if token_estimate == 0:
                # Rough estimate: 200 tokens per file
                token_estimate = len(relevant_files) * 200

            # Return successful exploration
            return AgentResponse(
                success=True,
                data=context_data,
                reasoning=context_data.get(
                    "context_summary",
                    f"Found {len(relevant_files)} relevant files",
                ),
                metadata={
                    "file_count": len(relevant_files),
                    "token_estimate": token_estimate,
                    "within_budget": token_estimate <= 10000,
                },
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                reasoning=f"Explorer search failed: {str(e)}",
                error=str(e),
            )

    def _build_search_prompt(self, task: AgentTask, max_files: int) -> str:
        """Build prompt for LLM-guided file search.
        
        Args:
            task: Task with search request
            max_files: Maximum number of files to return
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Find files relevant to this request:

REQUEST: {task.request}

CONSTRAINTS:
- Maximum {max_files} files
- Focus on: entry points, core logic, interfaces
- Avoid: vendor folders, generated files, caches

"""
        # Add project structure if provided
        if "project_root" in task.context:
            prompt += f"\nProject root: {task.context['project_root']}\n"

        if "file_patterns" in task.context:
            prompt += f"\nFile patterns: {task.context['file_patterns']}\n"

        prompt += """
Respond with JSON containing relevant files, dependencies, and context summary.
Remember: Quality over quantity. Less is more.
"""
        return prompt

    def _extract_files_fallback(self, llm_response: str) -> Dict[str, Any]:
        """Extract file paths from non-JSON LLM response (fallback).
        
        Args:
            llm_response: Raw LLM text response
            
        Returns:
            Dictionary with extracted files
        """
        import re

        # Extract file paths using regex
        # Match patterns like: src/path/file.py, ./path/file.js, etc.
        file_pattern = r'(?:^|\s)([a-zA-Z0-9_./\\-]+\.[a-zA-Z]+)'
        matches = re.findall(file_pattern, llm_response)

        # Filter to likely code files
        code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.c', '.cpp', '.h'}
        relevant_files = [
            {
                "path": match,
                "relevance": "UNKNOWN",
                "reason": "Extracted from text response",
                "key_symbols": [],
            }
            for match in matches
            if any(match.endswith(ext) for ext in code_extensions)
        ]

        return {
            "relevant_files": relevant_files[:10],  # Max 10
            "dependencies": [],
            "context_summary": "Files extracted from text response (fallback)",
            "token_estimate": len(relevant_files) * 200,
        }
