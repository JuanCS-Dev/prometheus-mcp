"""Minimal danger detector stub (consolidated from removed module)."""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class DangerLevel(Enum):
    """Danger level for commands."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DangerWarning:
    """Warning about dangerous operation."""
    level: DangerLevel
    message: str
    command: str
    suggestion: Optional[str] = None


class DangerDetector:
    """Minimal danger detector for shell commands."""

    DANGEROUS_PATTERNS = [
        ("rm -rf /", DangerLevel.CRITICAL, "Deletes entire filesystem"),
        ("rm -rf ~", DangerLevel.CRITICAL, "Deletes home directory"),
        ("rm -rf *", DangerLevel.HIGH, "Deletes all files in current directory"),
        (":(){:|:&};:", DangerLevel.CRITICAL, "Fork bomb"),
        ("chmod 777", DangerLevel.MEDIUM, "Makes files world-writable"),
        ("curl | bash", DangerLevel.HIGH, "Executes remote script"),
        ("wget | bash", DangerLevel.HIGH, "Executes remote script"),
        ("> /dev/sda", DangerLevel.CRITICAL, "Overwrites disk"),
        ("mkfs", DangerLevel.CRITICAL, "Formats filesystem"),
        ("dd if=", DangerLevel.HIGH, "Low-level disk operation"),
    ]

    def check(self, command: str) -> List[DangerWarning]:
        """Check command for dangerous patterns."""
        warnings = []
        cmd_lower = command.lower()

        for pattern, level, message in self.DANGEROUS_PATTERNS:
            if pattern.lower() in cmd_lower:
                warnings.append(DangerWarning(
                    level=level,
                    message=message,
                    command=command,
                    suggestion="Review this command carefully before executing"
                ))

        return warnings

    def is_dangerous(self, command: str) -> bool:
        """Check if command is dangerous."""
        warnings = self.check(command)
        return any(w.level in (DangerLevel.HIGH, DangerLevel.CRITICAL) for w in warnings)


# Singleton instance
danger_detector = DangerDetector()
