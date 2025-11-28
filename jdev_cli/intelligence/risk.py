"""Risk assessment for commands (Claude Code pattern).

Boris Cherny: Quantify everything. Risk is measurable.
"""

import re
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RiskScore:
    """Immutable risk assessment.
    
    Each dimension scored 0.0-1.0 (0 = safe, 1 = dangerous)
    """

    destructiveness: float
    reversibility: float  # 0 = irreversible, 1 = easily reversible
    scope: float
    security: float

    @property
    def overall(self) -> float:
        """Weighted overall risk score.
        
        Weights from Claude Code research:
        - Destructiveness: 40% (can it delete data?)
        - Reversibility: 30% (can we undo?)
        - Scope: 20% (how much affected?)
        - Security: 10% (security implications?)
        """
        return (
            self.destructiveness * 0.4 +
            (1.0 - self.reversibility) * 0.3 +
            self.scope * 0.2 +
            self.security * 0.1
        )

    @property
    def level(self) -> RiskLevel:
        """Get risk level from score."""
        # Special case: Very high destructiveness OR security = CRITICAL
        if self.destructiveness >= 0.9 or self.security >= 0.85:
            return RiskLevel.CRITICAL

        if self.overall >= 0.65:
            return RiskLevel.CRITICAL
        elif self.overall >= 0.45:
            return RiskLevel.HIGH
        elif self.overall >= 0.25:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @property
    def requires_confirmation(self) -> bool:
        """Should require user confirmation?"""
        return self.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]


# Dangerous command patterns
DESTRUCTIVE_PATTERNS = [
    (r'rm\s+-rf?\s+/', 0.95),  # rm -rf /
    (r'rm\s+-rf?\s+\*', 0.9),  # rm -rf *
    (r'rm\s+-rf?\s+~', 0.85),  # rm -rf ~
    (r'rm\s+-rf', 0.7),        # rm -rf anything
    (r'rm\s+', 0.5),           # rm without -rf
    (r'dd\s+', 0.8),           # dd (disk destroyer)
    (r'mkfs', 0.95),           # format filesystem
    (r'fdisk', 0.8),           # partition table manipulation
    (r'truncate', 0.6),        # truncate files
    (r'>\s*/dev/', 0.85),      # Redirect to device

    (r'git\s+push\s+(-f|--force)', 0.6),  # Force push
]

SECURITY_PATTERNS = [
    (r'curl.*\|.*sh', 0.9),     # Pipe curl to shell
    (r'wget.*\|.*sh', 0.9),     # Pipe wget to shell
    (r'chmod\s+777', 0.7),      # Dangerous permissions
    (r'chmod\s+-R\s+777', 0.85), # Recursive 777
    (r'sudo\s+rm', 0.6),        # sudo rm
    (r'sudo\s+chmod', 0.5),     # sudo chmod
    (r'eval\s+', 0.6),          # eval (code injection risk)
    (r'--insecure', 0.5),       # Disable SSL verification
]

SCOPE_PATTERNS = [
    (r'/\s*\*', 1.0),  # Root with wildcard              # Root with wildcard
    (r'/root', 0.9),            # Root directory
    (r'/etc', 0.8),             # System config
    (r'/var', 0.7),             # System var
    (r'/usr', 0.6),             # System usr
    (r'-R\s+/', 0.8),           # Recursive from root
    (r'--recursive', 0.6),      # Recursive flag
]


def assess_risk(command: str) -> RiskScore:
    """Assess risk of executing a command.
    
    Args:
        command: Command to assess
        
    Returns:
        RiskScore with detailed assessment
        
    Examples:
        >>> assess_risk("ls -la")
        RiskScore(destructiveness=0.0, reversibility=1.0, scope=0.0, security=0.0)
        
        >>> assess_risk("rm -rf /")
        RiskScore(destructiveness=0.95, reversibility=0.0, scope=1.0, security=0.0)
    """
    if not command:
        return RiskScore(0.0, 1.0, 0.0, 0.0)

    # Assess destructiveness
    destructiveness = 0.0
    for pattern, score in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command):
            destructiveness = max(destructiveness, score)

    # Assess security
    security = 0.0
    for pattern, score in SECURITY_PATTERNS:
        if re.search(pattern, command):
            security = max(security, score)

    # Assess scope
    scope = 0.3  # Default: local scope
    for pattern, score in SCOPE_PATTERNS:
        if re.search(pattern, command):
            scope = max(scope, score)

    # Assess reversibility
    reversibility = 1.0  # Default: reversible
    if destructiveness > 0.5:
        reversibility = 0.1  # Destructive commands are hard to reverse
    elif destructiveness > 0.0:
        reversibility = 0.5  # Somewhat reversible

    return RiskScore(
        destructiveness=destructiveness,
        reversibility=reversibility,
        scope=scope,
        security=security
    )


def get_risk_warning(score: RiskScore, command: str) -> str:
    """Generate human-readable risk warning.
    
    Args:
        score: Risk assessment
        command: Command being assessed
        
    Returns:
        Warning message appropriate for risk level
    """
    if score.level == RiskLevel.CRITICAL:
        return f"""⛔ CRITICAL RISK: This command is extremely dangerous!

Command: {command}
Risk Level: {score.level.value.upper()}
Overall Score: {score.overall:.2f}/1.00

Dangers:
- Destructiveness: {score.destructiveness:.2f} {'🔴' if score.destructiveness > 0.7 else ''}
- Irreversibility: {1-score.reversibility:.2f} {'🔴' if score.reversibility < 0.3 else ''}
- Scope: {score.scope:.2f} {'🔴' if score.scope > 0.7 else ''}
- Security: {score.security:.2f} {'🔴' if score.security > 0.7 else ''}

⚠️  This action cannot be easily undone. Consider safer alternatives.
"""

    elif score.level == RiskLevel.HIGH:
        return f"""⚠️  HIGH RISK: This command could cause significant damage.

Command: {command}
Risk Level: {score.level.value.upper()}

Proceed with caution. Consider backing up first.
"""

    elif score.level == RiskLevel.MEDIUM:
        return f"""💡 MEDIUM RISK: This command has some risks.

Command: {command}

Consider reviewing the command before executing.
"""

    return ""  # Low risk, no warning needed
