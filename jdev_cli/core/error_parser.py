"""Minimal error parser stub (consolidated from removed module)."""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ErrorAnalysis:
    """Analysis result for an error."""
    error_type: str = "unknown"
    user_friendly: str = "An error occurred"
    suggestions: List[str] = None
    can_auto_fix: bool = False
    auto_fix_command: Optional[str] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class ErrorParser:
    """Minimal error parser."""

    def parse(self, error_text: str, suggestion: str = "") -> ErrorAnalysis:
        """Parse error text and return analysis."""
        # Simple heuristics
        suggestions = []
        user_friendly = error_text[:200] if error_text else "Unknown error"

        if "ModuleNotFoundError" in error_text or "ImportError" in error_text:
            user_friendly = "Missing module or import error"
            suggestions = ["Check if the module is installed", "Run pip install <module>"]
        elif "FileNotFoundError" in error_text:
            user_friendly = "File not found"
            suggestions = ["Check the file path", "Ensure the file exists"]
        elif "PermissionError" in error_text:
            user_friendly = "Permission denied"
            suggestions = ["Check file permissions", "Run with appropriate privileges"]
        elif "SyntaxError" in error_text:
            user_friendly = "Syntax error in code"
            suggestions = ["Check the line mentioned in the error", "Look for missing brackets or quotes"]

        if suggestion:
            suggestions.insert(0, suggestion)

        return ErrorAnalysis(
            user_friendly=user_friendly,
            suggestions=suggestions[:5]
        )


# Singleton instance
error_parser = ErrorParser()
