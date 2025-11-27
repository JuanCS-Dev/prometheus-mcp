"""
Blaxel Multi-Agent Code Review System.

Hackathon Day 30 - Blaxel Choice Award ($2,500)

ARCHITECTURE (Multi-Agent with Supervisor Pattern):
┌─────────────────────────────────────────────────────────────┐
│                    SUPERVISOR AGENT                         │
│              (Orchestrates & Synthesizes)                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    ▼             ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐
│Research│  │ Security │  │Performance│  │  Style   │
│ Agent  │  │  Agent   │  │  Agent    │  │  Agent   │
└────────┘  └──────────┘  └───────────┘  └──────────┘
    │             │             │             │
    └─────────────┴─────────────┴─────────────┘
                        │
                   FINAL REVIEW

Deploy: bl deploy --name juan-code-reviewer
Run: bl run juan-code-reviewer "Review this PR: https://github.com/..."

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# BLAXEL SDK COMPATIBILITY
# =============================================================================

try:
    from blaxel import Agent, tool
    from blaxel.sandbox import Sandbox
    BLAXEL_AVAILABLE = True
except ImportError:
    BLAXEL_AVAILABLE = False

    def tool(func):
        """Stub @tool decorator."""
        func._is_tool = True
        return func

    class Agent:
        """Stub Agent base class."""
        name: str = "stub-agent"
        description: str = "Stub agent"

    class Sandbox:
        """Stub Sandbox for local development."""
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def run(self, cmd: str) -> dict:
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}


# =============================================================================
# AGENT STATE & TYPES
# =============================================================================

class ReviewSeverity(Enum):
    """Severity levels for review findings."""
    CRITICAL = "critical"  # Security vulnerabilities, data loss
    HIGH = "high"          # Major bugs, performance issues
    MEDIUM = "medium"      # Code smells, maintainability
    LOW = "low"            # Style, suggestions
    INFO = "info"          # FYI comments


@dataclass
class ReviewFinding:
    """A single code review finding."""
    severity: ReviewSeverity
    category: str  # security, performance, style, bug
    file: str
    line: Optional[int]
    title: str
    description: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class AgentState:
    """Shared state between agents."""
    # Input
    code: str = ""
    files: List[Dict[str, str]] = field(default_factory=list)
    pr_url: Optional[str] = None
    language: str = "python"

    # Intermediate results from each agent
    research_context: str = ""
    security_findings: List[ReviewFinding] = field(default_factory=list)
    performance_findings: List[ReviewFinding] = field(default_factory=list)
    style_findings: List[ReviewFinding] = field(default_factory=list)

    # Final output
    final_review: str = ""
    overall_score: int = 0  # 0-100


# =============================================================================
# GEMINI CLIENT
# =============================================================================

class GeminiClient:
    """Lightweight Gemini client using httpx (avoids ADC conflicts)."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, model: str = "gemini-2.0-flash-exp"):
        self.model = model
        self.api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=60.0)

    async def generate(self, prompt: str, system: str = "") -> str:
        """Generate a response from Gemini via REST API."""
        await self._ensure_client()

        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        url = f"{self.BASE_URL}/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
            }
        }

        response = await self._client.post(url, json=payload)

        if response.status_code != 200:
            raise Exception(f"Gemini API error {response.status_code}: {response.text}")

        data = response.json()

        # Extract text from response
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return f"Error parsing response: {data}"

    async def stream(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        """Stream a response from Gemini (simulated for simplicity)."""
        # For multi-agent use, we don't need streaming
        response = await self.generate(prompt, system)
        yield response


# =============================================================================
# SPECIALIZED AGENTS
# =============================================================================

class ResearchAgent:
    """
    Agent 1: Research & Context Gathering

    Analyzes the code structure, understands the intent,
    and provides context for other agents.
    """

    SYSTEM_PROMPT = """You are a code research agent. Your job is to:
1. Understand the purpose and structure of the code
2. Identify the programming language and frameworks used
3. Summarize what each file/function does
4. Note any patterns or architectural decisions
5. Identify dependencies and external APIs

Output a structured analysis that other agents can use for context.
Be concise but thorough. Focus on facts, not opinions."""

    def __init__(self, llm: GeminiClient):
        self.llm = llm

    async def analyze(self, state: AgentState) -> str:
        """Analyze code and return context summary."""
        prompt = f"""Analyze this code and provide context:

Language: {state.language}
Files: {len(state.files)}

Code:
```
{state.code[:10000]}
```

Provide:
1. Purpose of the code
2. Main components/classes/functions
3. Dependencies used
4. Architectural patterns
5. Key data flows"""

        return await self.llm.generate(prompt, self.SYSTEM_PROMPT)


class SecurityAgent:
    """
    Agent 2: Security Analysis

    Scans for OWASP Top 10 vulnerabilities, insecure patterns,
    and security best practices violations.
    """

    SYSTEM_PROMPT = """You are a security analysis agent. Your job is to find:

CRITICAL:
- SQL Injection
- Command Injection
- XSS (Cross-Site Scripting)
- Authentication bypasses
- Hardcoded credentials/secrets
- Path traversal

HIGH:
- Insecure deserialization
- SSRF vulnerabilities
- Broken access control
- Cryptographic failures

MEDIUM:
- Missing input validation
- Verbose error messages
- Insecure defaults
- Missing rate limiting

Output findings in JSON format with severity, file, line (if known), and remediation."""

    def __init__(self, llm: GeminiClient):
        self.llm = llm

    async def analyze(self, state: AgentState) -> List[ReviewFinding]:
        """Find security vulnerabilities."""
        prompt = f"""Analyze this {state.language} code for security vulnerabilities:

Context: {state.research_context[:2000]}

Code:
```
{state.code[:15000]}
```

Output JSON array of findings:
[{{"severity": "critical|high|medium|low", "file": "...", "line": N, "title": "...", "description": "...", "suggestion": "..."}}]

Be specific. No false positives. If no issues found, return empty array []."""

        response = await self.llm.generate(prompt, self.SYSTEM_PROMPT)

        # Parse JSON from response
        findings = []
        try:
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group())
                for item in items:
                    # Normalize severity to lowercase
                    sev = item.get("severity", "medium").lower()
                    if sev not in ["critical", "high", "medium", "low", "info"]:
                        sev = "medium"
                    findings.append(ReviewFinding(
                        severity=ReviewSeverity(sev),
                        category="security",
                        file=item.get("file", "unknown"),
                        line=item.get("line"),
                        title=item.get("title", "Security Issue"),
                        description=item.get("description", ""),
                        suggestion=item.get("suggestion"),
                    ))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse security findings: {e}")

        return findings


class PerformanceAgent:
    """
    Agent 3: Performance Analysis

    Identifies performance bottlenecks, inefficient algorithms,
    and resource usage issues.
    """

    SYSTEM_PROMPT = """You are a performance analysis agent. Find:

HIGH IMPACT:
- O(n²) or worse algorithms that could be O(n) or O(n log n)
- N+1 query problems
- Memory leaks
- Blocking I/O in async code
- Missing caching opportunities

MEDIUM IMPACT:
- Unnecessary loops
- String concatenation in loops
- Large object copies
- Unoptimized database queries

LOW IMPACT:
- Minor inefficiencies
- Premature optimization opportunities

Output findings with specific recommendations and Big-O analysis where applicable."""

    def __init__(self, llm: GeminiClient):
        self.llm = llm

    async def analyze(self, state: AgentState) -> List[ReviewFinding]:
        """Find performance issues."""
        prompt = f"""Analyze this {state.language} code for performance:

Context: {state.research_context[:2000]}

Code:
```
{state.code[:15000]}
```

Output JSON array:
[{{"severity": "high|medium|low", "file": "...", "line": N, "title": "...", "description": "...", "suggestion": "..."}}]

Focus on measurable impact. Avoid nitpicking."""

        response = await self.llm.generate(prompt, self.SYSTEM_PROMPT)

        findings = []
        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group())
                for item in items:
                    sev = item.get("severity", "medium").lower()
                    if sev not in ["critical", "high", "medium", "low", "info"]:
                        sev = "medium"
                    findings.append(ReviewFinding(
                        severity=ReviewSeverity(sev),
                        category="performance",
                        file=item.get("file", "unknown"),
                        line=item.get("line"),
                        title=item.get("title", "Performance Issue"),
                        description=item.get("description", ""),
                        suggestion=item.get("suggestion"),
                    ))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse performance findings: {e}")

        return findings


class StyleAgent:
    """
    Agent 4: Code Style & Best Practices

    Checks coding standards, naming conventions,
    documentation, and maintainability.
    """

    SYSTEM_PROMPT = """You are a code style and best practices agent. Check:

CODE QUALITY:
- Clear naming conventions
- Function/class size (too large?)
- Code duplication (DRY violations)
- Dead code
- Missing error handling

DOCUMENTATION:
- Missing docstrings/comments
- Outdated comments
- Complex logic without explanation

MAINTAINABILITY:
- Magic numbers/strings
- Deep nesting
- Long parameter lists
- Tight coupling

Be constructive, not pedantic. Focus on readability and maintainability."""

    def __init__(self, llm: GeminiClient):
        self.llm = llm

    async def analyze(self, state: AgentState) -> List[ReviewFinding]:
        """Find style and best practice issues."""
        prompt = f"""Review this {state.language} code for style and best practices:

Context: {state.research_context[:2000]}

Code:
```
{state.code[:15000]}
```

Output JSON array:
[{{"severity": "medium|low|info", "file": "...", "line": N, "title": "...", "description": "...", "suggestion": "..."}}]

Be helpful, not nitpicky. Focus on real maintainability concerns."""

        response = await self.llm.generate(prompt, self.SYSTEM_PROMPT)

        findings = []
        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group())
                for item in items:
                    sev = item.get("severity", "low").lower()
                    if sev not in ["critical", "high", "medium", "low", "info"]:
                        sev = "low"
                    findings.append(ReviewFinding(
                        severity=ReviewSeverity(sev),
                        category="style",
                        file=item.get("file", "unknown"),
                        line=item.get("line"),
                        title=item.get("title", "Style Issue"),
                        description=item.get("description", ""),
                        suggestion=item.get("suggestion"),
                    ))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse style findings: {e}")

        return findings


class SupervisorAgent:
    """
    Supervisor Agent: Orchestration & Final Review

    Coordinates the specialized agents and produces
    a final, consolidated code review.
    """

    SYSTEM_PROMPT = """You are the lead code reviewer. You receive findings from:
- Research Agent (code understanding)
- Security Agent (vulnerability detection)
- Performance Agent (optimization opportunities)
- Style Agent (best practices)

Your job is to:
1. Consolidate findings, removing duplicates
2. Prioritize by severity and impact
3. Write a professional, actionable code review
4. Calculate an overall code quality score (0-100)

Format the review as:
## Summary
[Brief overview]

## Score: XX/100

## Critical Issues
[If any]

## High Priority
[...]

## Recommendations
[...]

## What's Good
[Positive feedback]"""

    def __init__(self, llm: GeminiClient):
        self.llm = llm

    async def synthesize(self, state: AgentState) -> tuple[str, int]:
        """Produce final consolidated review."""

        # Format all findings
        all_findings = (
            state.security_findings +
            state.performance_findings +
            state.style_findings
        )

        findings_text = "\n".join([
            f"[{f.severity.value.upper()}] {f.category}: {f.title}\n"
            f"  File: {f.file}, Line: {f.line}\n"
            f"  {f.description}\n"
            f"  Suggestion: {f.suggestion or 'N/A'}"
            for f in all_findings
        ]) or "No issues found."

        prompt = f"""Create a final code review based on these findings:

## Research Context
{state.research_context[:3000]}

## Findings from Specialized Agents
{findings_text}

## Statistics
- Security findings: {len(state.security_findings)}
- Performance findings: {len(state.performance_findings)}
- Style findings: {len(state.style_findings)}
- Critical issues: {sum(1 for f in all_findings if f.severity == ReviewSeverity.CRITICAL)}
- High issues: {sum(1 for f in all_findings if f.severity == ReviewSeverity.HIGH)}

Write a professional code review. Include the score in format "## Score: XX/100"."""

        review = await self.llm.generate(prompt, self.SYSTEM_PROMPT)

        # Extract score
        score = 70  # Default
        score_match = re.search(r'Score:\s*(\d+)/100', review)
        if score_match:
            score = int(score_match.group(1))

        return review, score


# =============================================================================
# MAIN MULTI-AGENT SYSTEM
# =============================================================================

class CodeReviewAgentSquad(Agent):
    """
    Multi-Agent Code Review System for Blaxel.

    Orchestrates specialized agents to provide comprehensive,
    professional code reviews with actionable feedback.
    """

    name = "juan-code-reviewer"
    description = """Multi-Agent Code Review System.

Uses 4 specialized AI agents:
- Research Agent: Understands code context
- Security Agent: Finds vulnerabilities (OWASP Top 10)
- Performance Agent: Identifies bottlenecks
- Style Agent: Checks best practices

Produces professional code reviews with severity-based findings."""

    def __init__(self):
        super().__init__()
        self.llm = GeminiClient()

        # Initialize specialized agents
        self.research = ResearchAgent(self.llm)
        self.security = SecurityAgent(self.llm)
        self.performance = PerformanceAgent(self.llm)
        self.style = StyleAgent(self.llm)
        self.supervisor = SupervisorAgent(self.llm)

    @tool
    async def review_code(self, code: str, language: str = "python") -> str:
        """
        Review code using the multi-agent system.

        Args:
            code: The code to review
            language: Programming language (python, javascript, etc.)

        Returns:
            Comprehensive code review with findings and score
        """
        return await self._run_review(code=code, language=language)

    @tool
    async def review_file(self, path: str) -> str:
        """
        Review a file from the filesystem.

        Args:
            path: Path to the file to review

        Returns:
            Comprehensive code review
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()

            # Detect language from extension
            ext = path.split('.')[-1] if '.' in path else 'txt'
            lang_map = {
                'py': 'python', 'js': 'javascript', 'ts': 'typescript',
                'go': 'go', 'rs': 'rust', 'java': 'java', 'rb': 'ruby',
            }
            language = lang_map.get(ext, 'unknown')

            return await self._run_review(code=code, language=language)
        except Exception as e:
            return f"Error reading file: {e}"

    @tool
    async def review_pr(self, pr_url: str) -> str:
        """
        Review a GitHub Pull Request.

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

        Returns:
            Comprehensive code review of the PR changes
        """
        # Parse PR URL
        match = re.match(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
        if not match:
            return "Invalid PR URL format. Expected: https://github.com/owner/repo/pull/123"

        owner, repo, pr_num = match.groups()

        # Fetch PR diff using sandbox
        async with Sandbox() as sandbox:
            result = await sandbox.run(
                f"curl -s https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}/files"
            )

            if result.get("exit_code", 1) != 0:
                return f"Failed to fetch PR: {result.get('stderr', 'Unknown error')}"

            try:
                files = json.loads(result.get("stdout", "[]"))
            except json.JSONDecodeError:
                return "Failed to parse PR response"

        # Combine diffs
        code = "\n\n".join([
            f"### {f.get('filename', 'unknown')}\n```\n{f.get('patch', '')[:5000]}\n```"
            for f in files[:10]  # Limit to 10 files
        ])

        return await self._run_review(code=code, language="mixed", pr_url=pr_url)

    async def _run_review(
        self,
        code: str,
        language: str = "python",
        pr_url: Optional[str] = None
    ) -> str:
        """Execute the multi-agent review pipeline."""

        state = AgentState(
            code=code,
            language=language,
            pr_url=pr_url,
        )

        # Phase 1: Research (sequential - provides context for others)
        state.research_context = await self.research.analyze(state)

        # Phase 2: Parallel analysis by specialized agents
        security_task = asyncio.create_task(self.security.analyze(state))
        performance_task = asyncio.create_task(self.performance.analyze(state))
        style_task = asyncio.create_task(self.style.analyze(state))

        # Wait for all agents
        state.security_findings = await security_task
        state.performance_findings = await performance_task
        state.style_findings = await style_task

        # Phase 3: Supervisor synthesizes final review
        state.final_review, state.overall_score = await self.supervisor.synthesize(state)

        return state.final_review

    async def run(self, prompt: str) -> AsyncIterator[str]:
        """
        Main entry point for agent execution.

        Parses user intent and routes to appropriate tool.
        """
        prompt_lower = prompt.lower()

        # Route based on intent
        if "pr" in prompt_lower or "pull request" in prompt_lower or "github.com" in prompt:
            # Extract URL
            url_match = re.search(r'https://github\.com/[^\s]+', prompt)
            if url_match:
                yield "🔍 Analyzing Pull Request...\n\n"
                yield "🤖 Deploying agent squad:\n"
                yield "  ├── Research Agent: Understanding code...\n"
                yield "  ├── Security Agent: Scanning for vulnerabilities...\n"
                yield "  ├── Performance Agent: Finding bottlenecks...\n"
                yield "  └── Style Agent: Checking best practices...\n\n"

                review = await self.review_pr(url_match.group())
                yield review
                return

        if "file" in prompt_lower or "/" in prompt:
            # Extract file path
            path_match = re.search(r'[./\w]+\.\w+', prompt)
            if path_match:
                yield f"📄 Reviewing file: {path_match.group()}\n\n"
                review = await self.review_file(path_match.group())
                yield review
                return

        # Default: treat prompt as code or request
        if "```" in prompt:
            # Code block in prompt
            code_match = re.search(r'```(?:\w+)?\n?(.*?)```', prompt, re.DOTALL)
            if code_match:
                yield "📝 Reviewing code block...\n\n"
                review = await self.review_code(code_match.group(1))
                yield review
                return

        # Fallback: general response
        yield """🤖 **Juan Code Reviewer - Multi-Agent System**

I can review code for security, performance, and style issues.

**Usage:**
- Review a PR: `Review https://github.com/owner/repo/pull/123`
- Review a file: `Review ./src/main.py`
- Review code: Paste code in a \`\`\`code block\`\`\`

**What I check:**
- 🔒 Security: OWASP Top 10, credentials, injection
- ⚡ Performance: Algorithms, queries, memory
- ✨ Style: Best practices, naming, documentation

Ready when you are!"""


# =============================================================================
# EXPORTS
# =============================================================================

# Export agent instance for Blaxel CLI
agent = CodeReviewAgentSquad()

__all__ = [
    "CodeReviewAgentSquad",
    "ReviewFinding",
    "ReviewSeverity",
    "AgentState",
    "agent",
]

# CLI entrypoint
if __name__ == "__main__":
    async def main():
        import sys

        if len(sys.argv) < 2:
            print("Usage: python blaxel_agent.py 'Review https://github.com/...'")
            print("       python blaxel_agent.py 'Review ./src/main.py'")
            return

        prompt = " ".join(sys.argv[1:])
        agent = CodeReviewAgentSquad()

        print("🚀 Juan Code Reviewer - Multi-Agent System")
        print("=" * 50)

        async for chunk in agent.run(prompt):
            print(chunk, end="", flush=True)

        print()

    asyncio.run(main())
