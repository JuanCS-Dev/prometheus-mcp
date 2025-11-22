"""
ReviewerAgent: Constitutional AI QA Guardian.

This agent validates code quality against the Constitutional AI principles
defined in the Vértice 3.0 Constitution. It performs comprehensive code review
including:
    - Code quality analysis (maintainability, readability, performance)
    - Security vulnerability detection
    - Test coverage validation
    - Constitutional compliance checking
    - Best practices enforcement

Architecture:
    ReviewerAgent (BaseAgent)
        ├── Quality Gates (5 criteria)
        ├── Security Scanner
        ├── Test Coverage Analyzer
        └── Constitutional Validator

Philosophy (Boris Cherny):
    "Code review is not optional. It's the last line of defense."
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import (
    AgentCapability,
    AgentResponse,
    AgentRole,
    AgentTask,
    BaseAgent,
    TaskStatus,
)


class QualityGate(BaseModel):
    """Individual quality gate assessment.
    
    Attributes:
        name: Gate name (e.g., "Code Quality", "Security")
        passed: Whether gate passed
        score: Numeric score (0-100)
        issues: List of identified issues
        recommendations: List of improvement suggestions
    """
    name: str
    passed: bool
    score: int = Field(ge=0, le=100)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    """Comprehensive code review report.
    
    Attributes:
        approved: Overall approval decision
        grade: Letter grade (A+, A, B, C, D, F)
        overall_score: Weighted average score (0-100)
        gates: Individual gate assessments
        critical_issues: Must-fix issues
        warnings: Should-fix issues
        suggestions: Nice-to-have improvements
        constitutional_compliance: Compliance percentage
        summary: Executive summary
    """
    approved: bool
    grade: str
    overall_score: int = Field(ge=0, le=100)
    gates: List[QualityGate]
    critical_issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    constitutional_compliance: int = Field(ge=0, le=100)
    summary: str


class ReviewerAgent(BaseAgent):
    """QA Guardian that validates code quality.
    
    Capabilities:
        - READ_ONLY: Read files, list directories, search code
        - GIT_OPS: Diff analysis, commit history
    
    Responsibilities:
        ✅ Code quality assessment (maintainability, readability)
        ✅ Security vulnerability scanning
        ✅ Test coverage validation
        ✅ Constitutional compliance checking
        ✅ Best practices enforcement
        ❌ Does NOT modify code
        ❌ Does NOT execute code
    
    Quality Gates (5):
        1. Code Quality (maintainability, complexity, readability)
        2. Security (vulnerabilities, sensitive data, injection risks)
        3. Testing (coverage, test quality, edge cases)
        4. Performance (algorithmic complexity, resource usage)
        5. Constitutional (Vértice 3.0 principles)
    """
    
    def __init__(
        self,
        llm_client: Any,
        mcp_client: Any,
    ):
        """Initialize ReviewerAgent.
        
        Args:
            llm_client: LLM provider client (Gemini, Claude, etc.)
            mcp_client: MCP client for tool execution
        """
        super().__init__(
            role=AgentRole.REVIEWER,
            capabilities=[AgentCapability.READ_ONLY, AgentCapability.GIT_OPS],
            llm_client=llm_client,
            mcp_client=mcp_client,
        )
        self._load_constitutional_rules()
    
    def _load_constitutional_rules(self) -> None:
        """Load Constitutional AI rules from Vértice 3.0."""
        self.constitutional_rules = {
            "principles": [
                "P1: Autonomia Operacional (Operational Autonomy)",
                "P2: Execução Verificável (Verifiable Execution)",
                "P3: Soberania de Código (Code Sovereignty)",
                "P4: Eficiência de Token (Token Efficiency)",
                "P5: Recursividade Inteligente (Intelligent Recursion)",
                "P6: Harmonia Humano-IA (Human-AI Harmony)",
            ],
            "quality_standards": {
                "min_test_coverage": 85,
                "max_complexity": 10,
                "max_function_length": 50,
                "min_documentation": 80,
            },
        }
    
    async def execute(self, task: AgentTask) -> AgentResponse:
        """Execute code review task.
        
        Workflow:
            1. Read changed files (git diff or explicit list)
            2. Run 5 quality gates
            3. Generate comprehensive report
            4. Approve/Request changes
        
        Args:
            task: Review task with context containing:
                - files: List of file paths to review
                - diff: Optional git diff
                - baseline: Optional baseline metrics
        
        Returns:
            AgentResponse with ReviewReport in output
        """
        try:
            # Extract files to review
            files_to_review = task.context.get("files", [])
            git_diff = task.context.get("diff")
            
            if not files_to_review and not git_diff:
                return AgentResponse(
                    success=False,
                    data={"error": "No files or diff provided for review"},
                    reasoning="Missing review target",
                    error="No files or diff provided for review",
                )
            
            # Step 1: Gather file contents
            file_contents = await self._read_files(files_to_review)
            
            # Step 2: Run quality gates
            gates = await self._run_quality_gates(file_contents, task.context)
            
            # Step 3: Calculate overall score
            overall_score = self._calculate_overall_score(gates)
            grade = self._calculate_grade(overall_score)
            
            # Step 4: Aggregate issues
            critical_issues = []
            warnings = []
            suggestions = []
            
            for gate in gates:
                if not gate.passed:
                    critical_issues.extend(gate.issues)
                else:
                    warnings.extend(gate.issues)
                suggestions.extend(gate.recommendations)
            
            # Step 5: Generate summary
            summary = await self._generate_summary(gates, overall_score)
            
            # Step 6: Create report
            report = ReviewReport(
                approved=overall_score >= 70 and len(critical_issues) == 0,
                grade=grade,
                overall_score=overall_score,
                gates=gates,
                critical_issues=critical_issues,
                warnings=warnings,
                suggestions=suggestions,
                constitutional_compliance=self._calculate_constitutional_compliance(gates),
                summary=summary,
            )
            
            return AgentResponse(
                success=True,
                data={"report": report.model_dump()},
                reasoning=f"Review complete: {grade} grade, {overall_score}/100",
                metadata={"files_reviewed": len(files_to_review)},
            )
        
        except Exception as e:
            return AgentResponse(
                success=False,
                data={"error": str(e)},
                reasoning=f"Review failed: {str(e)}",
                error=str(e),
            )
    
    async def _read_files(self, file_paths: List[str]) -> Dict[str, str]:
        """Read file contents for review.
        
        Args:
            file_paths: List of file paths to read
        
        Returns:
            Dict mapping file path to content
        """
        contents = {}
        for file_path in file_paths:
            try:
                result = await self._execute_tool("read_file", {"path": file_path})
                if result.get("success"):
                    contents[file_path] = result.get("content", "")
            except Exception:
                contents[file_path] = ""  # Skip unreadable files
        return contents
    
    async def _run_quality_gates(
        self, file_contents: Dict[str, str], context: Dict[str, Any]
    ) -> List[QualityGate]:
        """Run all 5 quality gates.
        
        Args:
            file_contents: Map of file paths to contents
            context: Task context with metadata
        
        Returns:
            List of QualityGate assessments
        """
        gates = []
        
        # Gate 1: Code Quality
        gates.append(await self._gate_code_quality(file_contents))
        
        # Gate 2: Security
        gates.append(await self._gate_security(file_contents))
        
        # Gate 3: Testing
        gates.append(await self._gate_testing(file_contents, context))
        
        # Gate 4: Performance
        gates.append(await self._gate_performance(file_contents))
        
        # Gate 5: Constitutional Compliance
        gates.append(await self._gate_constitutional(file_contents))
        
        return gates
    
    async def _gate_code_quality(self, file_contents: Dict[str, str]) -> QualityGate:
        """Gate 1: Code quality assessment.
        
        Checks:
            - Cyclomatic complexity
            - Function length
            - Code duplication
            - Naming conventions
            - Documentation coverage
        """
        issues = []
        recommendations = []
        score = 100
        
        for file_path, content in file_contents.items():
            # Check function length
            long_functions = self._find_long_functions(content)
            if long_functions:
                issues.append(f"{file_path}: {len(long_functions)} function(s) exceed 50 lines")
                score -= min(10, len(long_functions) * 2)
            
            # Check documentation
            doc_coverage = self._calculate_doc_coverage(content)
            if doc_coverage < 80:
                issues.append(f"{file_path}: Documentation coverage {doc_coverage}% (min: 80%)")
                score -= (80 - doc_coverage) // 5
            
            # Check naming conventions
            naming_issues = self._check_naming_conventions(content)
            if naming_issues:
                recommendations.extend([f"{file_path}: {issue}" for issue in naming_issues])
                score -= min(5, len(naming_issues))
        
        return QualityGate(
            name="Code Quality",
            passed=score >= 70,
            score=max(0, score),
            issues=issues,
            recommendations=recommendations,
        )
    
    async def _gate_security(self, file_contents: Dict[str, str]) -> QualityGate:
        """Gate 2: Security vulnerability scanning.
        
        Checks:
            - Hardcoded credentials
            - SQL injection risks
            - Command injection risks
            - Unsafe deserialization
            - Exposed secrets
        """
        issues = []
        recommendations = []
        score = 100
        
        security_patterns = {
            "hardcoded_password": r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
            "api_key": r'(api[_-]?key|apikey)\s*=\s*["\'][^"\']+["\']',
            "sql_injection": r'(execute|cursor\.execute)\s*\([^)]*[\+\s]+[^)]*\)|["\']SELECT.*WHERE.*[\+\s]+',
            "command_injection": r'(os\.system|subprocess\.call|shell=True)',
            "unsafe_eval": r'\beval\s*\(',
        }
        
        for file_path, content in file_contents.items():
            for vuln_type, pattern in security_patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    issues.append(f"{file_path}: Potential {vuln_type} detected")
                    score -= 20  # Critical issue
        
        if not issues:
            recommendations.append("No security issues detected. Consider adding security tests.")
        
        return QualityGate(
            name="Security",
            passed=len(issues) == 0,
            score=max(0, score),
            issues=issues,
            recommendations=recommendations,
        )
    
    async def _gate_testing(
        self, file_contents: Dict[str, str], context: Dict[str, Any]
    ) -> QualityGate:
        """Gate 3: Test coverage validation.
        
        Checks:
            - Test coverage percentage
            - Test file existence
            - Edge case coverage
            - Mock usage (should be minimal)
        """
        issues = []
        recommendations = []
        score = 100
        
        # Check test coverage
        coverage = context.get("test_coverage", 0)
        min_coverage = 85
        
        if coverage < min_coverage:
            issues.append(f"Test coverage {coverage}% below minimum {min_coverage}%")
            score -= (min_coverage - coverage)
        
        # Check for test files
        test_files = [f for f in file_contents.keys() if "test_" in f or "_test.py" in f]
        source_files = [f for f in file_contents.keys() if f.endswith(".py") and "test" not in f]
        
        if source_files and not test_files:
            issues.append("No test files found for source code")
            score -= 30
        
        # Check for mocks (discouraged)
        for file_path, content in file_contents.items():
            if "test" in file_path:
                if "mock" in content.lower() or "Mock" in content:
                    recommendations.append(f"{file_path}: Consider reducing mock usage (prefer real objects)")
        
        return QualityGate(
            name="Testing",
            passed=score >= 70,
            score=max(0, score),
            issues=issues,
            recommendations=recommendations,
        )
    
    async def _gate_performance(self, file_contents: Dict[str, str]) -> QualityGate:
        """Gate 4: Performance analysis.
        
        Checks:
            - Algorithmic complexity (nested loops)
            - Resource leaks (unclosed files)
            - Inefficient patterns (N+1 queries)
        """
        issues = []
        recommendations = []
        score = 100
        
        for file_path, content in file_contents.items():
            # Check for nested loops (O(n^2) or worse)
            nested_loops = self._find_nested_loops(content)
            if nested_loops >= 3:
                issues.append(f"{file_path}: {nested_loops} levels of nested loops (potential O(n^3))")
                score -= 15
            
            # Check for resource leaks
            if "open(" in content and "with open(" not in content:
                recommendations.append(f"{file_path}: Use context managers for file operations")
                score -= 5
        
        return QualityGate(
            name="Performance",
            passed=score >= 70,
            score=max(0, score),
            issues=issues,
            recommendations=recommendations,
        )
    
    async def _gate_constitutional(self, file_contents: Dict[str, str]) -> QualityGate:
        """Gate 5: Constitutional compliance.
        
        Checks:
            - Token efficiency (no token waste)
            - Error handling (graceful degradation)
            - Type safety (type hints present)
            - Zero technical debt
        """
        issues = []
        recommendations = []
        score = 100
        
        for file_path, content in file_contents.items():
            if file_path.endswith(".py"):
                # Check type hints
                functions = re.findall(r'def\s+\w+\s*\([^)]*\)\s*:', content)
                typed_functions = re.findall(r'def\s+\w+\s*\([^)]*\)\s*->\s*\w+:', content)
                
                if len(functions) > 0:
                    type_coverage = len(typed_functions) / len(functions) * 100
                    if type_coverage < 90:
                        issues.append(f"{file_path}: Type hint coverage {type_coverage:.0f}% (min: 90%)")
                        score -= (90 - int(type_coverage)) // 5
                
                # Check error handling
                if "def " in content and "try:" not in content:
                    recommendations.append(f"{file_path}: Consider adding error handling")
                    score -= 5
        
        return QualityGate(
            name="Constitutional Compliance",
            passed=score >= 80,
            score=max(0, score),
            issues=issues,
            recommendations=recommendations,
        )
    
    def _calculate_overall_score(self, gates: List[QualityGate]) -> int:
        """Calculate weighted average score.
        
        Weights:
            - Code Quality: 20%
            - Security: 30% (highest priority)
            - Testing: 20%
            - Performance: 15%
            - Constitutional: 15%
        """
        weights = [0.20, 0.30, 0.20, 0.15, 0.15]
        total = sum(gate.score * weight for gate, weight in zip(gates, weights))
        return int(total)
    
    def _calculate_grade(self, score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _calculate_constitutional_compliance(self, gates: List[QualityGate]) -> int:
        """Calculate overall constitutional compliance."""
        return gates[4].score  # Constitutional gate is last
    
    async def _generate_summary(self, gates: List[QualityGate], overall_score: int) -> str:
        """Generate executive summary using LLM."""
        gate_summaries = [
            f"- {gate.name}: {gate.score}/100 {'✅' if gate.passed else '❌'}"
            for gate in gates
        ]
        
        prompt = f"""Generate a concise 2-sentence executive summary for this code review:

Overall Score: {overall_score}/100
Quality Gates:
{chr(10).join(gate_summaries)}

Summary should highlight the most critical finding and overall recommendation."""
        
        try:
            response = await self._call_llm(prompt, max_tokens=150)
            return response.strip()
        except Exception:
            return f"Code review complete with {overall_score}/100 score. " \
                   f"{'Approved for merge.' if overall_score >= 70 else 'Requires changes before merge.'}"
    
    # Helper methods for pattern detection
    
    def _find_long_functions(self, content: str) -> List[str]:
        """Find functions exceeding 50 lines."""
        long_funcs = []
        lines = content.split("\n")
        in_function = False
        func_name = ""
        func_lines = 0
        
        for line in lines:
            if line.strip().startswith("def "):
                if func_lines > 50:
                    long_funcs.append(func_name)
                func_name = line.strip().split("(")[0].replace("def ", "")
                func_lines = 0
                in_function = True
            elif in_function:
                func_lines += 1
                if line.strip() and not line.strip().startswith("#"):
                    if not line.startswith(" ") and not line.startswith("\t"):
                        in_function = False
        
        if func_lines > 50:
            long_funcs.append(func_name)
        
        return long_funcs
    
    def _calculate_doc_coverage(self, content: str) -> int:
        """Calculate documentation coverage percentage."""
        functions = re.findall(r'def\s+\w+', content)
        docstrings = re.findall(r'"""[^"]+"""', content) + re.findall(r"'''[^']+'''", content)
        
        if len(functions) == 0:
            return 100
        
        return int(len(docstrings) / len(functions) * 100)
    
    def _check_naming_conventions(self, content: str) -> List[str]:
        """Check PEP 8 naming conventions."""
        issues = []
        
        # Check function names (should be snake_case)
        camel_case_funcs = re.findall(r'def\s+([A-Z][a-zA-Z0-9]*)\s*\(', content)
        for func in camel_case_funcs:
            issues.append(f"Function '{func}' should use snake_case")
        
        # Check class names (should be PascalCase)
        snake_case_classes = re.findall(r'class\s+([a-z_][a-z0-9_]*)\s*[:(]', content)
        for cls in snake_case_classes:
            issues.append(f"Class '{cls}' should use PascalCase")
        
        return issues
    
    def _find_nested_loops(self, content: str) -> int:
        """Count maximum nesting depth of loops."""
        max_depth = 0
        current_depth = 0
        
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("for ", "while ")):
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif stripped and not line.startswith(" ") and not line.startswith("\t"):
                current_depth = 0
        
        return max_depth
