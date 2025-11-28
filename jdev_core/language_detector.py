"""
jdev_core.language_detector: Language Detection Utility.

Uses fast-langdetect (FastText-based) for automatic language detection.
Enables responding in the same language as the user's prompt.

This module is pure domain logic with no UI dependencies.
"""

from typing import Optional, Tuple

# Language name mapping (ISO 639-1 to full names)
LANGUAGE_NAMES = {
    "pt": "Portuguese",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "nl": "Dutch",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "vi": "Vietnamese",
    "th": "Thai",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "cs": "Czech",
    "el": "Greek",
    "he": "Hebrew",
    "hu": "Hungarian",
    "id": "Indonesian",
    "ms": "Malay",
    "ro": "Romanian",
    "uk": "Ukrainian",
}


class LanguageDetector:
    """
    Fast language detection using FastText.

    Usage:
        detector = LanguageDetector()
        lang_code = detector.detect("Ola, como voce esta?")  # Returns "pt"
        lang_name = detector.get_language_name(lang_code)     # Returns "Portuguese"
    """

    _detector = None

    @classmethod
    def _get_detector(cls):
        """Lazy load the detector to avoid startup cost."""
        if cls._detector is None:
            try:
                from fast_langdetect import detect
                cls._detector = detect
            except ImportError:
                cls._detector = None
        return cls._detector

    @classmethod
    def detect(cls, text: str) -> str:
        """
        Detect the language of the given text.

        Args:
            text: The text to analyze

        Returns:
            ISO 639-1 language code (e.g., "pt", "en", "es")
            Falls back to "en" if detection fails
        """
        if not text or len(text.strip()) < 3:
            return "en"

        detector = cls._get_detector()
        if detector is None:
            return "en"

        try:
            # fast-langdetect returns [{"lang": "pt", "score": 0.99}, ...]
            result = detector(text)
            if isinstance(result, list) and result:
                return result[0].get("lang", "en")
            return "en"
        except Exception:
            return "en"

    @classmethod
    def get_language_name(cls, code: str) -> str:
        """
        Get the full language name from ISO 639-1 code.

        Args:
            code: ISO 639-1 language code

        Returns:
            Full language name (e.g., "Portuguese", "English")
        """
        return LANGUAGE_NAMES.get(code, "English")

    @classmethod
    def detect_with_name(cls, text: str) -> Tuple[str, str]:
        """
        Detect language and return both code and name.

        Args:
            text: The text to analyze

        Returns:
            Tuple of (language_code, language_name)
        """
        code = cls.detect(text)
        name = cls.get_language_name(code)
        return code, name

    @classmethod
    def get_prompt_instruction(cls, text: str) -> Optional[str]:
        """
        Generate a prompt instruction for the detected language.

        Args:
            text: The user's prompt text

        Returns:
            Instruction string like "Respond in Portuguese." or None for English
        """
        # DISABLE FORCED TRANSLATION (Fix for "OláOlá" duplication issue)
        # The model is smart enough to reply in the correct language without this.
        # code, name = cls.detect_with_name(text)

        # # Don't add instruction for English (default)
        # if code == "en":
        #     return None

        # return f"Respond in {name}."
        return None
