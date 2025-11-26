"""
Governance Module - Risk Assessment and Observer Pattern
========================================================

Extracted from Bridge GOD CLASS (Nov 2025 Refactoring).

Features:
- Risk level assessment (LOW, MEDIUM, HIGH, CRITICAL)
- ELP (Emoji Language Protocol) for visual reporting
- Observer mode: monitors but never blocks
- Pattern-based threat detection
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(Enum):
    """Risk levels for governance assessment."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GovernanceConfig:
    """Governance configuration - Observer mode by default."""
    mode: str = "observer"  # observer | enforcer | off
    block_on_violation: bool = False
    report_format: str = "elp"  # emoji language protocol
    verbosity: str = "minimal"
    alerts: bool = True


# ELP (Emoji Language Protocol) symbols
ELP = {
    "approved": "✅",
    "warning": "⚠️",
    "alert": "🔴",
    "observed": "👀",
    "blocked": "🚫",
    "low": "🟢",
    "medium": "🟡",
    "high": "🟠",
    "critical": "🔴",
    "agent": "🤖",
    "tool": "🔧",
    "thinking": "💭",
    "done": "✓",
    "error": "✗",
}


class GovernanceObserver:
    """
    Governance in Observer mode.

    - Monitors all actions
    - Reports via ELP (Emoji Language Protocol)
    - NEVER blocks (observer mode)
    - Logs for later review
    """

    # Patterns that indicate higher risk
    HIGH_RISK_PATTERNS = [
        r"rm\s+-rf",
        r"sudo\s+",
        r"chmod\s+777",
        r">\s*/dev/",
        r"mkfs\.",
        r"dd\s+if=",
        r"curl.*\|\s*bash",
        r"wget.*\|\s*sh",
    ]

    CRITICAL_PATTERNS = [
        r"rm\s+-rf\s+/",
        r":(){ :\|:& };:",  # Fork bomb
        r">\s*/dev/sda",
        r"/etc/passwd",
        r"/etc/shadow",
    ]

    MEDIUM_RISK_KEYWORDS = [
        "delete", "remove", "drop", "truncate",
        "production", "deploy", "migrate",
        "secret", "password", "token", "key",
        "database", "db", "sql",
    ]

    def __init__(self, config: Optional[GovernanceConfig] = None):
        self.config = config or GovernanceConfig()
        self.observations: List[Dict[str, Any]] = []

    def assess_risk(self, content: str) -> tuple[RiskLevel, str]:
        """
        Assess risk level of content.

        Returns (risk_level, reason).
        """
        content_lower = content.lower()

        # Check critical patterns
        for pattern in self.CRITICAL_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return RiskLevel.CRITICAL, f"Critical pattern detected: {pattern}"

        # Check high risk patterns
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return RiskLevel.HIGH, f"High-risk pattern: {pattern}"

        # Check medium risk keywords
        for keyword in self.MEDIUM_RISK_KEYWORDS:
            if keyword in content_lower:
                return RiskLevel.MEDIUM, f"Contains sensitive keyword: {keyword}"

        return RiskLevel.LOW, "Standard operation"

    def observe(self, action: str, content: str, agent: str = "user") -> str:
        """
        Observe an action and return ELP report.

        Never blocks - only reports.
        """
        risk, reason = self.assess_risk(content)

        observation = {
            "action": action,
            "content": content[:100],  # Truncate for log
            "agent": agent,
            "risk": risk.value,
            "reason": reason,
        }
        self.observations.append(observation)

        # Generate ELP report
        risk_emoji = ELP.get(risk.value, "❓")

        if risk == RiskLevel.CRITICAL:
            return f"{risk_emoji} CRITICAL - {reason}"
        elif risk == RiskLevel.HIGH:
            return f"{risk_emoji} HIGH RISK - {reason}"
        elif risk == RiskLevel.MEDIUM:
            return f"{ELP['warning']} MEDIUM - {reason}"
        else:
            return f"{ELP['approved']} LOW RISK"

    def get_status_emoji(self) -> str:
        """Get current governance status as emoji."""
        if not self.observations:
            return f"{ELP['observed']} Observer"

        # Check recent observations
        recent = self.observations[-5:] if len(self.observations) > 5 else self.observations
        risks = [obs["risk"] for obs in recent]

        if "critical" in risks:
            return f"{ELP['critical']} Critical"
        elif "high" in risks:
            return f"{ELP['high']} High Risk"
        elif "medium" in risks:
            return f"{ELP['warning']} Caution"
        else:
            return f"{ELP['approved']} Clear"


__all__ = [
    'RiskLevel',
    'GovernanceConfig',
    'GovernanceObserver',
    'ELP',
]
