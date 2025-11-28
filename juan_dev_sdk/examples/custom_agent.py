#!/usr/bin/env python3
"""
Custom Agent Example.

SCALE & SUSTAIN Phase 2.3 - SDK Example.

Demonstrates how to create a custom agent using the juan-dev-sdk.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import sys
from pathlib import Path

# Add SDK to path for development
sdk_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(sdk_path))

from juan_dev_sdk import JuanDevClient
from juan_dev_sdk.agents import AgentBuilder, create_agent


# Example 1: Simple agent using builder pattern
def create_code_reviewer_agent():
    """Create a code review agent using the builder pattern."""

    agent = (
        AgentBuilder("code-reviewer")
        .with_description("Reviews code for quality, security, and best practices")
        .with_system_prompt("""
You are an expert code reviewer. Your role is to:
1. Identify bugs and potential issues
2. Check for security vulnerabilities
3. Suggest improvements for readability and maintainability
4. Ensure code follows best practices

Be constructive and specific in your feedback.
        """)
        .with_capabilities([
            "read_file",
            "glob",
            "grep",
        ])
        .with_config({
            "temperature": 0.3,
            "max_tokens": 4096,
        })
        .build()
    )

    return agent


# Example 2: Using the convenience function
def create_documentation_agent():
    """Create a documentation agent using the convenience function."""

    agent = create_agent(
        name="doc-generator",
        description="Generates documentation for code",
        system_prompt="""
You are a technical documentation expert. Generate clear, comprehensive
documentation including:
- Module/function descriptions
- Parameter documentation
- Return value documentation
- Usage examples
- Edge cases and warnings
        """,
        capabilities=["read_file", "glob"],
    )

    return agent


# Example 3: Agent with custom handler
class SecurityAuditAgent:
    """
    Custom agent class for security auditing.

    This example shows how to create a more complex agent
    with custom logic and state management.
    """

    def __init__(self):
        self.vulnerabilities_found = []
        self.files_scanned = 0

        self.agent = (
            AgentBuilder("security-auditor")
            .with_description("Scans code for security vulnerabilities")
            .with_system_prompt("""
You are a security expert. Analyze code for:
- SQL injection vulnerabilities
- XSS vulnerabilities
- Command injection
- Path traversal
- Insecure deserialization
- Hardcoded secrets
- OWASP Top 10 issues

Report findings with severity levels: CRITICAL, HIGH, MEDIUM, LOW
            """)
            .with_capabilities(["read_file", "glob", "grep"])
            .with_metadata({
                "version": "1.0.0",
                "author": "Security Team",
            })
            .build()
        )

    async def scan_file(self, client: JuanDevClient, file_path: str) -> dict:
        """Scan a single file for vulnerabilities."""
        self.files_scanned += 1

        # Read the file content
        prompt = f"""
Analyze the following file for security vulnerabilities: {file_path}

Focus on:
1. Input validation issues
2. Authentication/authorization problems
3. Data exposure risks
4. Injection vulnerabilities

Format your response as JSON with fields:
- vulnerabilities: list of findings
- risk_level: overall risk (CRITICAL/HIGH/MEDIUM/LOW)
- recommendations: list of fixes
        """

        response_chunks = []
        async for chunk in client.chat(prompt, agent=self.agent.name):
            response_chunks.append(chunk)

        response = "".join(response_chunks)

        # Parse and store results
        result = {
            "file": file_path,
            "response": response,
            "scanned_at": asyncio.get_event_loop().time(),
        }

        return result

    async def scan_directory(
        self,
        client: JuanDevClient,
        directory: str,
        patterns: list = None
    ) -> dict:
        """Scan a directory for vulnerabilities."""
        patterns = patterns or ["*.py", "*.js", "*.ts"]

        # This would use glob to find files
        prompt = f"""
List all files matching {patterns} in {directory} that should be scanned
for security issues. Prioritize files that:
1. Handle user input
2. Connect to databases
3. Make HTTP requests
4. Handle authentication
        """

        async for chunk in client.chat(prompt, agent=self.agent.name):
            pass  # Process response

        return {
            "directory": directory,
            "files_scanned": self.files_scanned,
            "vulnerabilities": self.vulnerabilities_found,
        }


# Example 4: Async agent execution
async def run_agent_example():
    """Demonstrate running custom agents."""

    print("=== Juan Dev SDK - Custom Agent Examples ===\n")

    # Create agents
    reviewer = create_code_reviewer_agent()
    doc_gen = create_documentation_agent()
    security = SecurityAuditAgent()

    print("Created agents:")
    print(f"  - {reviewer.name}: {reviewer.description}")
    print(f"  - {doc_gen.name}: {doc_gen.description}")
    print(f"  - {security.agent.name}: {security.agent.description}")

    # Example: Using with client (when server is available)
    print("\n--- Agent Configuration ---")
    print(f"Code Reviewer capabilities: {reviewer.capabilities}")
    print(f"Doc Generator capabilities: {doc_gen.capabilities}")
    print(f"Security Auditor metadata: {security.agent.metadata}")

    # Simulate agent usage
    print("\n--- Simulated Usage ---")
    print("To use these agents with a running server:")
    print("""
    async with JuanDevClient() as client:
        # Use code reviewer
        async for chunk in client.chat(
            "Review the auth.py file for issues",
            agent="code-reviewer"
        ):
            print(chunk, end="")

        # Use documentation generator
        async for chunk in client.chat(
            "Generate docs for utils/helpers.py",
            agent="doc-generator"
        ):
            print(chunk, end="")

        # Use security auditor
        results = await security.scan_directory(client, "src/")
        print(f"Found {len(results['vulnerabilities'])} issues")
    """)


def main():
    """Main entry point."""
    asyncio.run(run_agent_example())


if __name__ == "__main__":
    main()
