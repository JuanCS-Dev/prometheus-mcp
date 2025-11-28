"""
SecurityAgent: The Penetration Tester - Offensive Security Specialist.

This agent performs security audits on codebases, detecting vulnerabilities,
exposed secrets, and dependency risks. It follows OWASP guidelines and
provides actionable remediation advice.

Capabilities:
    - Vulnerability scanning (SQL, XSS, Command Injection, eval)
    - Secret detection (API keys, AWS credentials, tokens)
    - Dependency auditing (CVE scanning via pip-audit)
    - OWASP Top 10 compliance scoring

Architecture:
    SecurityAgent extends BaseAgent with READ_ONLY + BASH_EXEC capabilities.
    It uses pattern matching, AST analysis, and external tools (pip-audit).

Philosophy (Boris Cherny):
    "Security is not a feature. It's a non-negotiable."
"""

import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import (
    AgentCapability,
    AgentResponse,
    AgentRole,
    AgentTask,
    BaseAgent,
)


class VulnerabilityType(str, Enum):
    """Classification of security vulnerabilities."""

    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    UNSAFE_DESERIALIZATION = "unsafe_deserialization"
    EVAL_USAGE = "eval_usage"
    HARDCODED_SECRET = "hardcoded_secret"
    WEAK_CRYPTO = "weak_crypto"


class SeverityLevel(str, Enum):
    """CVSS-inspired severity classification."""

    CRITICAL = "critical"  # 9.0-10.0
    HIGH = "high"  # 7.0-8.9
    MEDIUM = "medium"  # 4.0-6.9
    LOW = "low"  # 0.1-3.9
    INFO = "info"  # 0.0


@dataclass
class Vulnerability:
    """Represents a single security vulnerability."""

    type: VulnerabilityType
    severity: SeverityLevel
    file: str
    line: int
    code_snippet: str
    description: str
    remediation: str
    cwe_id: Optional[str] = None  # Common Weakness Enumeration


@dataclass
class Secret:
    """Represents an exposed secret/credential."""

    type: str  # "api_key", "aws_key", "github_token", etc.
    file: str
    line: int
    pattern: str
    confidence: float  # 0.0-1.0


@dataclass
class DependencyVulnerability:
    """Represents a vulnerable dependency."""

    package: str
    version: str
    cve_id: str
    severity: SeverityLevel
    description: str
    fixed_version: Optional[str] = None


class SecurityAgent(BaseAgent):
    """The Penetration Tester - Offensive Security Specialist.

    This agent scans code for security vulnerabilities, exposed secrets,
    and vulnerable dependencies. It provides OWASP-compliant scoring and
    actionable remediation advice.

    Capabilities:
        - READ_ONLY: Read files and directory structures
        - BASH_EXEC: Run security tools (pip-audit, bandit)

    Type Safety:
        All vulnerability data is strongly typed via dataclasses.
        Pattern matching uses compiled regex for performance.
    """

    def __init__(
        self,
        llm_client: Any,
        mcp_client: Any,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize SecurityAgent with scanning patterns."""
        super().__init__(
            role=AgentRole.SECURITY,
            capabilities=[AgentCapability.READ_ONLY, AgentCapability.BASH_EXEC],
            llm_client=llm_client,
            mcp_client=mcp_client,
        )

        # Compile regex patterns for performance
        self._patterns = self._compile_patterns()

        # OWASP scoring weights
        self._severity_penalties = {
            SeverityLevel.CRITICAL: 20,
            SeverityLevel.HIGH: 10,
            SeverityLevel.MEDIUM: 5,
            SeverityLevel.LOW: 2,
            SeverityLevel.INFO: 0,
        }

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for vulnerability and secret detection."""
        return {
            # SQL Injection patterns
            "sql_inject": re.compile(
                r'(execute|cursor\.execute|executemany)\s*\(\s*["\'].*?%s.*?["\']',
                re.IGNORECASE,
            ),
            "sql_format": re.compile(
                r'(execute|cursor\.execute|executemany)\s*\(\s*.*?\.format\s*\(',
                re.IGNORECASE,
            ),
            "sql_fstring": re.compile(
                r'(execute|cursor\.execute|executemany)\s*\(\s*f["\']',
                re.IGNORECASE,
            ),
            # Command Injection patterns
            "cmd_inject": re.compile(
                r'(os\.system|subprocess\.call|subprocess\.run|eval|exec)\s*\(',
                re.IGNORECASE,
            ),
            "shell_true": re.compile(r'shell\s*=\s*True', re.IGNORECASE),
            # Path Traversal patterns
            "path_traversal": re.compile(r'open\s*\([^)]*\+[^)]*\)', re.IGNORECASE),
            # Secret patterns (high entropy + context)
            "api_key": re.compile(
                r'(api[_-]?key|apikey)["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-]{32,})',
                re.IGNORECASE,
            ),
            "aws_key": re.compile(
                r'(AKIA[0-9A-Z]{16})', re.IGNORECASE
            ),  # AWS Access Key
            "github_token": re.compile(
                r'(ghp_[A-Za-z0-9_]{36})', re.IGNORECASE
            ),  # GitHub Personal Token
            "private_key": re.compile(
                r'-----BEGIN\s+(RSA|OPENSSH|EC)\s+PRIVATE\s+KEY-----',
                re.IGNORECASE,
            ),
            # Weak Crypto patterns
            "md5": re.compile(r'hashlib\.md5\s*\(', re.IGNORECASE),
            "sha1": re.compile(r'hashlib\.sha1\s*\(', re.IGNORECASE),
            # Unsafe deserialization
            "pickle": re.compile(r'pickle\.loads?\s*\(', re.IGNORECASE),
            "yaml_unsafe": re.compile(r'yaml\.load\s*\([^)]*\)', re.IGNORECASE),
        }

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Execute security audit on specified files or directory.

        Args:
            task: Contains context with root_dir or metadata with target_file

        Returns:
            AgentResponse with vulnerabilities, secrets, dependencies, and OWASP score
        """
        try:
            # Determine scan scope
            target_path = Path(task.context.get("root_dir", "."))
            if "target_file" in task.metadata:
                target_path = Path(task.metadata["target_file"])

            # Phase 1: Scan for vulnerabilities
            vulnerabilities = await self._scan_vulnerabilities(target_path)

            # Phase 2: Detect secrets
            secrets = await self._detect_secrets(target_path)

            # Phase 3: Check dependencies (if requirements.txt exists)
            dep_vulns = await self._check_dependencies(target_path)

            # Phase 4: Calculate OWASP score
            owasp_score = self._calculate_owasp_score(
                vulnerabilities, secrets, dep_vulns
            )

            # Compile report
            report = self._generate_report(
                vulnerabilities, secrets, dep_vulns, owasp_score
            )

            return AgentResponse(
                success=True,
                data={
                    "report": report,
                    "vulnerabilities": [self._vuln_to_dict(v) for v in vulnerabilities],
                    "secrets": [self._secret_to_dict(s) for s in secrets],
                    "dependencies": [self._dep_to_dict(d) for d in dep_vulns],
                    "owasp_score": owasp_score,
                },
                reasoning=f"Security scan complete: {len(vulnerabilities)} vulnerabilities, "
                          f"{len(secrets)} secrets, {len(dep_vulns)} vulnerable dependencies. "
                          f"OWASP Score: {owasp_score}/100",
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                reasoning=f"Security scan failed: {str(e)}",
                error=str(e),
            )

    async def _scan_vulnerabilities(self, target: Path) -> List[Vulnerability]:
        """Scan for code vulnerabilities using pattern matching and AST analysis."""
        vulnerabilities: List[Vulnerability] = []

        if target.is_file():
            files = [target]
        else:
            files = list(target.rglob("*.py"))

        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                # Pattern-based detection
                vulnerabilities.extend(
                    self._detect_sql_injection(file, lines, content)
                )
                vulnerabilities.extend(
                    self._detect_command_injection(file, lines, content)
                )
                vulnerabilities.extend(self._detect_path_traversal(file, lines))
                vulnerabilities.extend(self._detect_weak_crypto(file, lines))
                vulnerabilities.extend(self._detect_unsafe_deserialization(file, lines))

                # AST-based detection (eval/exec)
                vulnerabilities.extend(self._detect_eval_usage(file, content))

            except Exception:
                continue  # Skip files with encoding issues

        return vulnerabilities

    def _detect_sql_injection(
        self, file: Path, lines: List[str], content: str
    ) -> List[Vulnerability]:
        """Detect SQL injection vulnerabilities."""
        vulns = []

        for i, line in enumerate(lines, 1):
            # Check for string formatting in SQL (%, .format(), f-strings)
            if (
                self._patterns["sql_inject"].search(line)
                or self._patterns["sql_format"].search(line)
                or self._patterns["sql_fstring"].search(line)
            ):
                vulns.append(
                    Vulnerability(
                        type=VulnerabilityType.SQL_INJECTION,
                        severity=SeverityLevel.HIGH,
                        file=str(file),
                        line=i,
                        code_snippet=line.strip(),
                        description="SQL query uses string formatting, vulnerable to injection",
                        remediation="Use parameterized queries (e.g., cursor.execute(query, (param,)))",
                        cwe_id="CWE-89",
                    )
                )

        return vulns

    def _detect_command_injection(
        self, file: Path, lines: List[str], content: str
    ) -> List[Vulnerability]:
        """Detect command injection vulnerabilities."""
        vulns = []

        for i, line in enumerate(lines, 1):
            # Check for shell=True in subprocess
            if self._patterns["shell_true"].search(line):
                vulns.append(
                    Vulnerability(
                        type=VulnerabilityType.COMMAND_INJECTION,
                        severity=SeverityLevel.CRITICAL,
                        file=str(file),
                        line=i,
                        code_snippet=line.strip(),
                        description="subprocess call with shell=True allows command injection",
                        remediation="Use shell=False and pass command as list: ['cmd', 'arg1']",
                        cwe_id="CWE-78",
                    )
                )

            # Check for os.system usage
            if "os.system" in line:
                vulns.append(
                    Vulnerability(
                        type=VulnerabilityType.COMMAND_INJECTION,
                        severity=SeverityLevel.HIGH,
                        file=str(file),
                        line=i,
                        code_snippet=line.strip(),
                        description="os.system() is unsafe, allows command injection",
                        remediation="Use subprocess.run() with shell=False",
                        cwe_id="CWE-78",
                    )
                )

        return vulns

    def _detect_path_traversal(self, file: Path, lines: List[str]) -> List[Vulnerability]:
        """Detect path traversal vulnerabilities."""
        vulns = []

        for i, line in enumerate(lines, 1):
            if self._patterns["path_traversal"].search(line) and ".." in line:
                vulns.append(
                    Vulnerability(
                        type=VulnerabilityType.PATH_TRAVERSAL,
                        severity=SeverityLevel.MEDIUM,
                        file=str(file),
                        line=i,
                        code_snippet=line.strip(),
                        description="Path concatenation may allow directory traversal",
                        remediation="Use Path().resolve() and validate against base directory",
                        cwe_id="CWE-22",
                    )
                )

        return vulns

    def _detect_weak_crypto(self, file: Path, lines: List[str]) -> List[Vulnerability]:
        """Detect usage of weak cryptographic algorithms."""
        vulns = []

        for i, line in enumerate(lines, 1):
            if self._patterns["md5"].search(line) or self._patterns["sha1"].search(
                line
            ):
                vulns.append(
                    Vulnerability(
                        type=VulnerabilityType.WEAK_CRYPTO,
                        severity=SeverityLevel.MEDIUM,
                        file=str(file),
                        line=i,
                        code_snippet=line.strip(),
                        description="MD5/SHA1 are cryptographically broken",
                        remediation="Use SHA-256 or SHA-3 for hashing",
                        cwe_id="CWE-327",
                    )
                )

        return vulns

    def _detect_unsafe_deserialization(
        self, file: Path, lines: List[str]
    ) -> List[Vulnerability]:
        """Detect unsafe deserialization (pickle, yaml.load)."""
        vulns = []

        for i, line in enumerate(lines, 1):
            if self._patterns["pickle"].search(line):
                vulns.append(
                    Vulnerability(
                        type=VulnerabilityType.UNSAFE_DESERIALIZATION,
                        severity=SeverityLevel.HIGH,
                        file=str(file),
                        line=i,
                        code_snippet=line.strip(),
                        description="pickle.load() can execute arbitrary code",
                        remediation="Use json.load() or validate pickle source",
                        cwe_id="CWE-502",
                    )
                )

            if self._patterns["yaml_unsafe"].search(line) and "SafeLoader" not in line:
                vulns.append(
                    Vulnerability(
                        type=VulnerabilityType.UNSAFE_DESERIALIZATION,
                        severity=SeverityLevel.HIGH,
                        file=str(file),
                        line=i,
                        code_snippet=line.strip(),
                        description="yaml.load() without SafeLoader can execute code",
                        remediation="Use yaml.safe_load() instead",
                        cwe_id="CWE-502",
                    )
                )

        return vulns

    def _detect_eval_usage(self, file: Path, content: str) -> List[Vulnerability]:
        """Detect eval/exec usage via EvalExecDetector."""
        detections = EvalExecDetector.detect(content)
        vulns = []
        for lineno, description in detections:
            vulns.append(
                Vulnerability(
                    type=VulnerabilityType.EVAL_USAGE,
                    severity=SeverityLevel.CRITICAL,
                    file=str(file),
                    line=lineno,
                    code_snippet=description,
                    description=description,
                    remediation="Avoid eval/exec. Use ast.literal_eval() for safe evaluation",
                    cwe_id="CWE-95",
                )
            )
        return vulns

    async def _detect_secrets(self, target: Path) -> List[Secret]:
        """Detect exposed secrets using pattern matching."""
        secrets: List[Secret] = []

        if target.is_file():
            files = [target]
        else:
            # Scan common config files + source code
            patterns = ["*.py", "*.json", "*.yaml", "*.yml", "*.env", ".env*"]
            files = []
            for pattern in patterns:
                files.extend(target.rglob(pattern))

        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    # API Keys
                    match = self._patterns["api_key"].search(line)
                    if match:
                        secrets.append(
                            Secret(
                                type="api_key",
                                file=str(file),
                                line=i,
                                pattern=match.group(2),
                                confidence=0.9,
                            )
                        )

                    # AWS Keys
                    match = self._patterns["aws_key"].search(line)
                    if match:
                        secrets.append(
                            Secret(
                                type="aws_access_key",
                                file=str(file),
                                line=i,
                                pattern=match.group(1),
                                confidence=1.0,
                            )
                        )

                    # GitHub Tokens
                    match = self._patterns["github_token"].search(line)
                    if match:
                        secrets.append(
                            Secret(
                                type="github_token",
                                file=str(file),
                                line=i,
                                pattern=match.group(1),
                                confidence=1.0,
                            )
                        )

                    # Private Keys
                    match = self._patterns["private_key"].search(line)
                    if match:
                        secrets.append(
                            Secret(
                                type="private_key",
                                file=str(file),
                                line=i,
                                pattern="[PRIVATE KEY DETECTED]",
                                confidence=1.0,
                            )
                        )

            except Exception:
                continue

        return secrets

    async def _check_dependencies(self, target: Path) -> List[DependencyVulnerability]:
        """Check dependencies for known CVEs using pip-audit."""
        dep_vulns = []

        # Find requirements.txt
        req_file = None
        if target.is_file() and target.name == "requirements.txt":
            req_file = target
        elif target.is_dir():
            candidates = list(target.glob("requirements*.txt"))
            if candidates:
                req_file = candidates[0]

        if not req_file:
            return dep_vulns

        try:
            # Run pip-audit
            result = subprocess.run(
                ["pip-audit", "-r", str(req_file), "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # pip-audit returns empty JSON on no vulns
                import json

                data = json.loads(result.stdout)
                for vuln in data.get("vulnerabilities", []):
                    dep_vulns.append(
                        DependencyVulnerability(
                            package=vuln["name"],
                            version=vuln["version"],
                            cve_id=vuln["id"],
                            severity=self._map_cvss_to_severity(vuln.get("cvss", 0)),
                            description=vuln.get("description", "No description"),
                            fixed_version=vuln.get("fixed_version"),
                        )
                    )

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass  # pip-audit not installed or timeout

        return dep_vulns

    def _map_cvss_to_severity(self, cvss_score: float) -> SeverityLevel:
        """Map CVSS score to severity level."""
        if cvss_score >= 9.0:
            return SeverityLevel.CRITICAL
        elif cvss_score >= 7.0:
            return SeverityLevel.HIGH
        elif cvss_score >= 4.0:
            return SeverityLevel.MEDIUM
        elif cvss_score > 0.0:
            return SeverityLevel.LOW
        else:
            return SeverityLevel.INFO

    def _calculate_owasp_score(
        self,
        vulnerabilities: List[Vulnerability],
        secrets: List[Secret],
        dep_vulns: List[DependencyVulnerability],
    ) -> int:
        """Calculate OWASP compliance score (0-100).

        Scoring:
            - Start at 100
            - Deduct points based on severity
            - Minimum score: 0
        """
        score = 100

        # Deduct for code vulnerabilities
        for vuln in vulnerabilities:
            score -= self._severity_penalties[vuln.severity]

        # Deduct for exposed secrets (always critical)
        score -= len(secrets) * self._severity_penalties[SeverityLevel.CRITICAL]

        # Deduct for dependency vulnerabilities
        for dep in dep_vulns:
            score -= self._severity_penalties[dep.severity]

        return max(0, score)

    def _generate_report(
        self,
        vulnerabilities: List[Vulnerability],
        secrets: List[Secret],
        dep_vulns: List[DependencyVulnerability],
        owasp_score: int,
    ) -> str:
        """Generate human-readable security report."""
        report = []
        report.append("=" * 80)
        report.append("SECURITY AUDIT REPORT")
        report.append("=" * 80)
        report.append("")

        # OWASP Score
        report.append(f"🛡️  OWASP COMPLIANCE SCORE: {owasp_score}/100")
        if owasp_score >= 90:
            report.append("   Status: ✅ EXCELLENT")
        elif owasp_score >= 70:
            report.append("   Status: ⚠️  GOOD (minor issues)")
        elif owasp_score >= 50:
            report.append("   Status: 🔶 FAIR (needs attention)")
        else:
            report.append("   Status: 🔴 CRITICAL (immediate action required)")
        report.append("")

        # Vulnerabilities
        report.append(f"🐛 CODE VULNERABILITIES: {len(vulnerabilities)}")
        if vulnerabilities:
            for vuln in sorted(
                vulnerabilities, key=lambda v: list(SeverityLevel).index(v.severity)
            ):
                report.append(f"   [{vuln.severity.upper()}] {vuln.type.value}")
                report.append(f"      File: {vuln.file}:{vuln.line}")
                report.append(f"      Code: {vuln.code_snippet}")
                report.append(f"      Fix:  {vuln.remediation}")
                report.append("")

        # Secrets
        report.append(f"🔑 EXPOSED SECRETS: {len(secrets)}")
        if secrets:
            for secret in secrets:
                report.append(f"   [CRITICAL] {secret.type}")
                report.append(f"      File: {secret.file}:{secret.line}")
                report.append(
                    f"      Confidence: {secret.confidence * 100:.0f}%"
                )
                report.append("")

        # Dependencies
        report.append(f"📦 VULNERABLE DEPENDENCIES: {len(dep_vulns)}")
        if dep_vulns:
            for dep in dep_vulns:
                report.append(f"   [{dep.severity.upper()}] {dep.package}=={dep.version}")
                report.append(f"      CVE: {dep.cve_id}")
                if dep.fixed_version:
                    report.append(f"      Fix: Upgrade to {dep.fixed_version}")
                report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    def _vuln_to_dict(self, vuln: Vulnerability) -> Dict[str, Any]:
        """Convert Vulnerability to dict for serialization."""
        return {
            "type": vuln.type.value,
            "severity": vuln.severity.value,
            "file": vuln.file,
            "line": vuln.line,
            "code": vuln.code_snippet,
            "description": vuln.description,
            "remediation": vuln.remediation,
            "cwe_id": vuln.cwe_id,
        }

    def _secret_to_dict(self, secret: Secret) -> Dict[str, Any]:
        """Convert Secret to dict for serialization."""
        return {
            "type": secret.type,
            "file": secret.file,
            "line": secret.line,
            "confidence": secret.confidence,
        }

    def _dep_to_dict(self, dep: DependencyVulnerability) -> Dict[str, Any]:
        """Convert DependencyVulnerability to dict for serialization."""
        return {
            "package": dep.package,
            "version": dep.version,
            "cve_id": dep.cve_id,
            "severity": dep.severity.value,
            "description": dep.description,
            "fixed_version": dep.fixed_version,
        }
