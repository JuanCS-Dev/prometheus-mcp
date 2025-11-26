"""
Language Detector for JuanCS Dev-Code.

DEPRECATED: This module now re-exports from qwen_core.language_detector.
Import directly from qwen_core for new code.

Migration:
    # Old (deprecated)
    from qwen_cli.core.language_detector import LanguageDetector

    # New (preferred)
    from qwen_core import LanguageDetector
"""

# Re-export from qwen_core for backward compatibility
from qwen_core.language_detector import LanguageDetector, LANGUAGE_NAMES

__all__ = ["LanguageDetector", "LANGUAGE_NAMES"]
