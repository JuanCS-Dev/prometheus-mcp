"""
InputEnhancer - Smart Input Processing
Pipeline de Diamante - Camada 1: INPUT FORTRESS

Addresses: ISSUE-019, ISSUE-031, ISSUE-032, ISSUE-033 (Input handling)

Implements intelligent input processing:
- Typo correction (Levenshtein distance)
- Markdown code block extraction
- StackOverflow paste cleaning (>>> removal)
- Multiline paste detection
- Command normalization

Design Philosophy:
- Accept messy input, return clean data
- Suggest corrections, don't auto-correct silently
- Handle real-world copy-paste scenarios
- Maintain user intent
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# Try to import Levenshtein for fast distance calculation
try:
    from Levenshtein import distance as levenshtein_distance
    HAS_LEVENSHTEIN = True
except ImportError:
    HAS_LEVENSHTEIN = False

    def levenshtein_distance(s1: str, s2: str) -> int:
        """Fallback Levenshtein distance implementation."""
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


class InputType(Enum):
    """Types of input detected."""
    PLAIN_TEXT = "plain_text"
    CODE_BLOCK = "code_block"
    COMMAND = "command"
    MULTILINE = "multiline"
    REPL_PASTE = "repl_paste"  # Python REPL (>>>)
    MIXED = "mixed"


@dataclass
class CodeBlock:
    """An extracted code block."""
    language: str
    code: str
    original: str


@dataclass
class CodeExtraction:
    """Result of code extraction."""
    clean_code: str
    code_blocks: List[CodeBlock] = field(default_factory=list)
    error_detected: bool = False
    contains_error: bool = False


@dataclass
class EnhancedInput:
    """Result of input enhancement."""
    original: str
    cleaned: str
    input_type: InputType
    code_blocks: List[CodeBlock] = field(default_factory=list)
    corrections: List[Tuple[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Vibe coder support fields
    suggestions: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    extracted_tasks: List[str] = field(default_factory=list)

    @property
    def needs_clarification(self) -> bool:
        """Check if the input needs clarification from the user."""
        if self.corrections:
            return True
        if any("ambiguous" in w.lower() or "unclear" in w.lower() for w in self.warnings):
            return True
        if self.input_type == InputType.MIXED and len(self.code_blocks) == 0:
            return True
        if self.is_incomplete:
            return True
        return False

    @property
    def has_code(self) -> bool:
        """Check if input contains code."""
        return len(self.code_blocks) > 0

    @property
    def corrected_text(self) -> str:
        """Get text with corrections applied."""
        text = self.cleaned
        for old, new in self.corrections:
            text = text.replace(old, new)
        return text

    @property
    def suggested_correction(self) -> Optional[str]:
        """Get the first suggested correction."""
        if self.corrections:
            return self.corrections[0][1]
        if self.suggestions:
            return self.suggestions[0]
        return None

    @property
    def normalized_text(self) -> str:
        """Get normalized version of text (lowercase commands, preserved identifiers)."""
        return self.cleaned.strip()

    @property
    def is_incomplete(self) -> bool:
        """Check if input appears to be incomplete."""
        incomplete_patterns = [
            r"^(can you|i want to|please|could you)\s*$",
            r"\s+(the|a|an|that|this)\s*$",
            r"^[^.!?]*\s+(and|but|or)\s*$",
        ]
        text = self.original.strip().lower()
        for pattern in incomplete_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return len(text.split()) <= 2 and not self.has_code

    @property
    def detected_contradiction(self) -> bool:
        """Check if input contains contradictory requests."""
        text = self.original.lower()
        contradictions = [
            ("delete", "keep"), ("remove", "save"), ("delete", "save"),
            ("stop", "start"), ("cancel", "continue"),
        ]
        for word1, word2 in contradictions:
            if word1 in text and word2 in text:
                return True
        return False

    @property
    def multiple_intents(self) -> bool:
        """Check if input contains multiple distinct requests."""
        connectors = [" and ", " also ", " plus ", " then ", " after that "]
        text = self.original.lower()
        count = sum(1 for c in connectors if c in text)
        return count >= 2 or len(self.extracted_tasks) > 1

    @property
    def is_question(self) -> bool:
        """Check if input is a question."""
        text = self.original.strip()
        return text.endswith("?") or text.lower().startswith(("what ", "how ", "why ", "when ", "where ", "can ", "does ", "is "))

    @property
    def wants_explanation(self) -> bool:
        """Check if user wants an explanation."""
        keywords = ["what does", "how does", "explain", "why", "what is", "what's"]
        text = self.original.lower()
        return any(kw in text for kw in keywords)


@dataclass
class TypoCorrection:
    """A suggested typo correction."""
    original: str
    suggestion: str
    distance: int
    confidence: float


class InputEnhancer:
    """
    Smart input processing and enhancement.

    Features:
    - Typo correction with Levenshtein distance
    - Markdown code block extraction
    - REPL paste cleaning (>>> prompts)
    - Multiline detection and handling
    - Command normalization

    Usage:
        enhancer = InputEnhancer()

        result = enhancer.enhance("```python\nprint('hello')\n```")
        print(result.code_blocks[0].code)  # print('hello')

        result = enhancer.enhance(">>> print('hello')")
        print(result.cleaned)  # print('hello')
    """

    # Common command vocabulary for typo correction
    COMMAND_VOCABULARY = {
        # File commands
        "read", "write", "edit", "create", "delete", "rename", "move", "copy",
        # Git commands
        "git", "commit", "push", "pull", "branch", "merge", "rebase", "checkout",
        "status", "diff", "log", "stash", "clone", "fetch",
        # Development commands
        "test", "run", "build", "install", "deploy", "start", "stop", "restart",
        # Analysis commands
        "search", "find", "grep", "list", "show", "view", "open", "close",
        # Help commands
        "help", "explain", "how", "what", "why", "fix", "debug", "analyze",
    }

    # Common typos and their corrections
    COMMON_TYPOS = {
        "teh": "the",
        "hte": "the",
        "taht": "that",
        "waht": "what",
        "adn": "and",
        "fiel": "file",
        "funciton": "function",
        "fucntion": "function",
        "retrun": "return",
        "pirnt": "print",
        "pritn": "print",
        "improt": "import",
        "imoprt": "import",
        "calss": "class",
        "defien": "define",
        "vaule": "value",
        "vlaue": "value",
        "lenght": "length",
        "widht": "width",
        "heigth": "height",
        "recieve": "receive",
        "seperate": "separate",
        "occured": "occurred",
        "exmaple": "example",
        "examle": "example",
        "chnage": "change",
        "cahnge": "change",
    }

    # Code block pattern
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w*)\n?(.*?)```',
        re.DOTALL
    )

    # REPL prompt patterns
    REPL_PATTERNS = [
        (re.compile(r'^>>> (.*)$', re.MULTILINE), "python"),
        (re.compile(r'^> (.*)$', re.MULTILINE), "shell"),
        (re.compile(r'^\$ (.*)$', re.MULTILINE), "bash"),
        (re.compile(r'^In \[\d+\]: (.*)$', re.MULTILINE), "ipython"),
    ]

    def __init__(
        self,
        enable_typo_correction: bool = True,
        typo_threshold: int = 2,  # Max Levenshtein distance
        custom_vocabulary: Optional[Set[str]] = None,
    ):
        """
        Initialize InputEnhancer.

        Args:
            enable_typo_correction: Enable typo detection/correction
            typo_threshold: Maximum edit distance for corrections
            custom_vocabulary: Additional words for typo checking
        """
        self.enable_typo_correction = enable_typo_correction
        self.typo_threshold = typo_threshold
        self.vocabulary = self.COMMAND_VOCABULARY.copy()
        if custom_vocabulary:
            self.vocabulary.update(custom_vocabulary)

    def enhance(self, input_text: str) -> EnhancedInput:
        """
        Enhance input text.

        Args:
            input_text: Raw user input

        Returns:
            EnhancedInput with cleaned text and metadata
        """
        original = input_text
        cleaned = input_text
        input_type = InputType.PLAIN_TEXT
        code_blocks: List[CodeBlock] = []
        corrections: List[Tuple[str, str]] = []
        warnings: List[str] = []
        metadata: Dict[str, Any] = {}

        # Detect and extract code blocks
        code_blocks, cleaned = self._extract_code_blocks(cleaned)
        if code_blocks:
            input_type = InputType.CODE_BLOCK

        # Clean REPL prompts
        cleaned, repl_lang = self._clean_repl_prompts(cleaned)
        if repl_lang:
            input_type = InputType.REPL_PASTE
            metadata["detected_language"] = repl_lang

        # Detect multiline
        if '\n' in cleaned.strip() and input_type == InputType.PLAIN_TEXT:
            input_type = InputType.MULTILINE

        # Check for typos
        if self.enable_typo_correction:
            corrections = self._detect_typos(cleaned)
            if corrections:
                metadata["has_typos"] = True

        # Normalize whitespace
        cleaned = self._normalize_whitespace(cleaned)

        # Check for common paste issues
        paste_warnings = self._check_paste_issues(original)
        warnings.extend(paste_warnings)

        return EnhancedInput(
            original=original,
            cleaned=cleaned,
            input_type=input_type,
            code_blocks=code_blocks,
            corrections=corrections,
            warnings=warnings,
            metadata=metadata,
        )

    def _extract_code_blocks(
        self,
        text: str
    ) -> Tuple[List[CodeBlock], str]:
        """Extract markdown code blocks from text."""
        code_blocks = []
        remaining = text

        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or "text"
            code = match.group(2).strip()

            block = CodeBlock(
                language=language,
                code=code,
                original=match.group(0)
            )
            code_blocks.append(block)

            # Remove code block from remaining text
            remaining = remaining.replace(match.group(0), "")

        return code_blocks, remaining.strip()

    def _clean_repl_prompts(
        self,
        text: str
    ) -> Tuple[str, Optional[str]]:
        """Remove REPL prompts from pasted code."""
        detected_language = None

        for pattern, language in self.REPL_PATTERNS:
            matches = list(pattern.finditer(text))
            if matches:
                detected_language = language
                # Extract just the code parts
                lines = []
                for match in matches:
                    lines.append(match.group(1))

                # If most lines matched, return cleaned
                total_lines = len([l for l in text.split('\n') if l.strip()])
                if len(matches) >= total_lines * 0.5:
                    return '\n'.join(lines), detected_language

        return text, detected_language

    def _detect_typos(
        self,
        text: str
    ) -> List[Tuple[str, str]]:
        """Detect potential typos and suggest corrections."""
        corrections = []
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())

        for word in words:
            # Check common typos first (fast path)
            if word in self.COMMON_TYPOS:
                corrections.append((word, self.COMMON_TYPOS[word]))
                continue

            # Check against vocabulary
            if word not in self.vocabulary and len(word) >= 3:
                best_match = self._find_closest_match(word)
                if best_match:
                    corrections.append((word, best_match))

        return corrections

    def _find_closest_match(self, word: str) -> Optional[str]:
        """Find closest match in vocabulary."""
        best_match = None
        best_distance = self.typo_threshold + 1

        for vocab_word in self.vocabulary:
            # Skip if length difference is too large
            if abs(len(word) - len(vocab_word)) > self.typo_threshold:
                continue

            distance = levenshtein_distance(word, vocab_word)
            if distance <= self.typo_threshold and distance < best_distance:
                best_distance = distance
                best_match = vocab_word

        return best_match

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]

        # Remove excessive blank lines
        normalized = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            normalized.append(line)
            prev_blank = is_blank

        return '\n'.join(normalized).strip()

    def _check_paste_issues(self, text: str) -> List[str]:
        """Check for common paste issues."""
        warnings = []

        # Check for line number prefixes (from code editors)
        if re.search(r'^\s*\d+[:\|]\s', text, re.MULTILINE):
            warnings.append("Text appears to contain line numbers. These may need to be removed.")

        # Check for tab/space mixing
        has_tabs = '\t' in text
        has_leading_spaces = re.search(r'^[ ]+\S', text, re.MULTILINE)
        if has_tabs and has_leading_spaces:
            warnings.append("Text mixes tabs and spaces for indentation.")

        # Check for very long lines (possibly concatenated)
        for line in text.split('\n'):
            if len(line) > 500:
                warnings.append("Some lines are very long. Check if they should be split.")
                break

        # Check for control characters
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text):
            warnings.append("Text contains control characters that may cause issues.")

        return warnings

    def suggest_command_correction(
        self,
        command: str,
        valid_commands: Set[str],
    ) -> Optional[TypoCorrection]:
        """
        Suggest correction for a misspelled command.

        Args:
            command: User's command
            valid_commands: Set of valid commands

        Returns:
            TypoCorrection if found
        """
        if command in valid_commands:
            return None

        best_match = None
        best_distance = self.typo_threshold + 1

        for valid in valid_commands:
            distance = levenshtein_distance(command.lower(), valid.lower())
            if distance <= self.typo_threshold and distance < best_distance:
                best_distance = distance
                best_match = valid

        if best_match:
            confidence = 1.0 - (best_distance / max(len(command), len(best_match)))
            return TypoCorrection(
                original=command,
                suggestion=best_match,
                distance=best_distance,
                confidence=confidence
            )

        return None

    def extract_code_from_mixed(self, text: str) -> List[str]:
        """
        Extract code snippets from mixed text/code input.

        Useful when user pastes text with inline code.
        """
        code_snippets = []

        # Extract markdown code blocks
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            code_snippets.append(match.group(2).strip())

        # Extract inline code
        inline_pattern = re.compile(r'`([^`]+)`')
        for match in inline_pattern.finditer(text):
            code_snippets.append(match.group(1))

        return code_snippets

    def extract_code(self, text: str) -> CodeExtraction:
        """
        Extract all code from input text.

        Returns CodeExtraction with clean code and metadata.
        """
        code_snippets = self.extract_code_from_mixed(text)
        clean_code = "\n".join(code_snippets) if code_snippets else ""

        # Detect if there's an error in the pasted output
        error_patterns = [
            r"Traceback \(most recent call last\)",
            r"Error:",
            r"Exception:",
            r"NameError:",
            r"TypeError:",
            r"SyntaxError:",
            r"ImportError:",
            r"ModuleNotFoundError:",
            r"AttributeError:",
            r"ValueError:",
            r"KeyError:",
            r"IndexError:",
        ]
        error_detected = any(re.search(p, text, re.IGNORECASE) for p in error_patterns)

        # Get code blocks
        code_blocks = []
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            code_blocks.append(CodeBlock(
                language=match.group(1) or "text",
                code=match.group(2).strip(),
                original=match.group(0)
            ))

        return CodeExtraction(
            clean_code=clean_code,
            code_blocks=code_blocks,
            error_detected=error_detected,
            contains_error=error_detected
        )

    def clean_stackoverflow_paste(self, text: str) -> str:
        """
        Clean pasted code from StackOverflow.

        Removes:
        - Line numbers
        - Copy button artifacts
        - Extra whitespace
        """
        cleaned = text

        # Remove line numbers (various formats)
        cleaned = re.sub(r'^\s*\d+\s*[\|:]\s*', '', cleaned, flags=re.MULTILINE)

        # Remove Python REPL prompts
        cleaned = re.sub(r'^>>>\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^\.\.\.\s*', '', cleaned, flags=re.MULTILINE)

        # Remove shell prompts
        cleaned = re.sub(r'^\$\s*', '', cleaned, flags=re.MULTILINE)

        # Remove "copy" button text sometimes included
        cleaned = re.sub(r'^copy$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)

        return self._normalize_whitespace(cleaned)


# Global instance
_default_enhancer: Optional[InputEnhancer] = None


def get_input_enhancer() -> InputEnhancer:
    """Get the default input enhancer instance."""
    global _default_enhancer
    if _default_enhancer is None:
        _default_enhancer = InputEnhancer()
    return _default_enhancer


# Convenience functions

def enhance_input(text: str) -> EnhancedInput:
    """Enhance input text."""
    return get_input_enhancer().enhance(text)


def extract_code_blocks(text: str) -> List[CodeBlock]:
    """Extract code blocks from text."""
    return get_input_enhancer().enhance(text).code_blocks


def clean_repl_paste(text: str) -> str:
    """Clean REPL prompts from pasted code."""
    return get_input_enhancer().enhance(text).cleaned


def suggest_correction(command: str, valid_commands: Set[str]) -> Optional[TypoCorrection]:
    """Suggest command correction."""
    return get_input_enhancer().suggest_command_correction(command, valid_commands)


# Export all public symbols
__all__ = [
    'InputType',
    'CodeBlock',
    'CodeExtraction',
    'EnhancedInput',
    'TypoCorrection',
    'InputEnhancer',
    'get_input_enhancer',
    'enhance_input',
    'extract_code_blocks',
    'clean_repl_paste',
    'suggest_correction',
]
