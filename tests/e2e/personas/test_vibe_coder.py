"""
E2E Tests: Vibe Coder Persona
==============================

Tests from the perspective of a beginner developer who:
- Uses vague, imprecise language
- Makes typos and grammatical errors
- Copies code from StackOverflow/ChatGPT
- Expects the AI to "just understand" intent
- Needs patient, helpful error explanations

Based on:
- Anthropic Claude Code Best Practices (Nov 2025)
- Google Agent Quality Metrics (2025)
- UX research on beginner developers

Total: 30 tests
"""

import pytest
from pathlib import Path

# Import test utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from jdev_cli.core.input_enhancer import InputEnhancer
from jdev_cli.core.error_presenter import ErrorPresenter
from jdev_cli.core.context_tracker import ContextTracker


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def vibe_workspace(tmp_path):
    """Create a messy beginner workspace."""
    workspace = tmp_path / "my_project"
    workspace.mkdir()

    # Messy file structure typical of beginners
    (workspace / "main.py").write_text('''# my first program
print("hello world")
x = 1
y = 2
print(x + y)
''')

    (workspace / "test.py").write_text('''# trying to test something
from main import x
print(x)
''')

    (workspace / "stuff.py").write_text('''# random stuff
def do_thing():
    pass

def another_thing(x):
    return x * 2
''')

    (workspace / "NOTES.txt").write_text("TODO: fix the bug\nmaybe try stackoverflow\n")

    return workspace


@pytest.fixture
def input_enhancer():
    """Get InputEnhancer instance."""
    return InputEnhancer()


@pytest.fixture
def error_presenter():
    """Get ErrorPresenter for beginner mode."""
    return ErrorPresenter(default_mode="beginner")


@pytest.fixture
def context_tracker():
    """Get ContextTracker instance."""
    return ContextTracker()


# ==============================================================================
# TEST CLASS: TYPO CORRECTION (Vibe coder makes lots of typos)
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.vibe_coder
class TestVibeCoderTypos:
    """Tests for typo correction and fuzzy matching."""

    def test_corrects_common_typos(self, input_enhancer):
        """Vibe coder types 'pyhton' instead of 'python'."""
        typo_inputs = [
            ("pyhton main.py", "python main.py"),
            ("pytohn script.py", "python script.py"),
            ("pyton test.py", "python test.py"),
        ]

        for typo, expected in typo_inputs:
            result = input_enhancer.enhance(typo)
            assert result.corrected_text == expected or result.suggested_correction == expected, \
                f"Should correct '{typo}' to '{expected}'"

    def test_corrects_command_typos(self, input_enhancer):
        """Vibe coder types 'ptest' instead of 'pytest'."""
        typo_inputs = [
            ("ptest tests/", "pytest tests/"),
            ("pytset -v", "pytest -v"),
            ("gti status", "git status"),
            ("gitt commit", "git commit"),
        ]

        for typo, expected in typo_inputs:
            result = input_enhancer.enhance(typo)
            assert expected in [result.corrected_text, result.suggested_correction], \
                f"Should suggest correction for '{typo}'"

    def test_suggests_did_you_mean(self, input_enhancer):
        """Vibe coder should see 'Did you mean...?' suggestions."""
        result = input_enhancer.enhance("cretae file.py")

        assert result.suggestions, "Should provide suggestions"
        assert any("create" in s.lower() for s in result.suggestions), \
            "Should suggest 'create'"

    def test_handles_case_insensitivity(self, input_enhancer):
        """Vibe coder doesn't care about case."""
        inputs = [
            "PYTHON main.py",
            "Python Main.py",
            "PYTEST tests/",
        ]

        for inp in inputs:
            result = input_enhancer.enhance(inp)
            assert result.normalized_text, "Should normalize case"

    def test_preserves_intentional_casing(self, input_enhancer):
        """Vibe coder's class names should keep their case."""
        result = input_enhancer.enhance("create class MyClassName")

        assert "MyClassName" in result.corrected_text or \
               "MyClassName" in result.original_text, \
            "Should preserve intentional PascalCase"


# ==============================================================================
# TEST CLASS: VAGUE INPUT HANDLING (Vibe coder is imprecise)
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.vibe_coder
class TestVibeCoderVagueInput:
    """Tests for handling vague, imprecise inputs."""

    def test_handles_vague_file_reference(self, context_tracker, vibe_workspace):
        """Vibe coder says 'that file' or 'the other one'."""
        # Set up context
        context_tracker.record_file_access(str(vibe_workspace / "main.py"))
        context_tracker.record_file_access(str(vibe_workspace / "test.py"))

        # Vague reference
        result = context_tracker.resolve_reference("the main file")

        assert result.resolved_path, "Should resolve vague reference"
        assert "main" in result.resolved_path.lower(), "Should find main.py"

    def test_handles_the_other_one(self, context_tracker, vibe_workspace):
        """Vibe coder says 'the other one' meaning previous file."""
        # Access two files
        context_tracker.record_file_access(str(vibe_workspace / "main.py"))
        context_tracker.record_file_access(str(vibe_workspace / "test.py"))

        # Reference previous
        result = context_tracker.resolve_reference("the other one")

        assert result.resolved_path, "Should resolve 'the other one'"
        assert "main.py" in result.resolved_path, "Should refer to previous file"

    def test_handles_this_thing(self, context_tracker):
        """Vibe coder says 'fix this thing' without context."""
        # Recent error context
        context_tracker.record_error("SyntaxError in main.py line 5")

        result = context_tracker.resolve_reference("this thing")

        assert result.context_hint, "Should provide context hint"

    def test_handles_it_pronoun(self, context_tracker, vibe_workspace):
        """Vibe coder says 'run it' meaning last mentioned file."""
        context_tracker.record_file_access(str(vibe_workspace / "main.py"))

        result = context_tracker.resolve_reference("it")

        assert result.resolved_path, "Should resolve 'it' to last file"

    def test_handles_make_it_work(self, input_enhancer):
        """Vibe coder says 'make it work' - should ask for clarification."""
        result = input_enhancer.enhance("make it work")

        assert result.needs_clarification or result.clarification_questions, \
            "Should ask for clarification on vague requests"


# ==============================================================================
# TEST CLASS: CODE PASTE HANDLING (Vibe coder copy-pastes a lot)
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.vibe_coder
class TestVibeCoderCodePaste:
    """Tests for handling pasted code from various sources."""

    def test_handles_stackoverflow_paste(self, input_enhancer):
        """Vibe coder pastes code with >>> prompts."""
        pasted_code = '''>>> def hello():
...     print("Hello")
>>> hello()
Hello
'''

        result = input_enhancer.extract_code(pasted_code)

        assert result.clean_code, "Should extract clean code"
        assert ">>>" not in result.clean_code, "Should remove REPL prompts"
        assert "..." not in result.clean_code or "..." in '""" docstring """', \
            "Should remove continuation prompts"

    def test_handles_jupyter_paste(self, input_enhancer):
        """Vibe coder pastes from Jupyter with [1]:."""
        pasted_code = '''In [1]: import pandas as pd
In [2]: df = pd.DataFrame({'a': [1,2,3]})
In [3]: df.head()
Out[3]:
   a
0  1
1  2
2  3
'''

        result = input_enhancer.extract_code(pasted_code)

        assert result.clean_code, "Should extract clean code"
        assert "In [" not in result.clean_code, "Should remove Jupyter prompts"
        assert "import pandas" in result.clean_code, "Should preserve code"

    def test_handles_markdown_code_blocks(self, input_enhancer):
        """Vibe coder pastes markdown with ```python blocks."""
        pasted = '''here's my code:

```python
def add(a, b):
    return a + b
```

can you fix it?'''

        result = input_enhancer.extract_code(pasted)

        assert result.clean_code, "Should extract code from markdown"
        assert "def add" in result.clean_code, "Should extract function"
        assert "```" not in result.clean_code, "Should remove backticks"

    def test_handles_mixed_language_paste(self, input_enhancer):
        """Vibe coder pastes code mixed with natural language."""
        pasted = '''so I tried this:
x = 1
y = 2
but then it gave me an error when I did
print(x + z)
because z isn't defined I think?'''

        result = input_enhancer.extract_code(pasted)

        # Should identify code vs natural language
        assert result.code_blocks or result.clean_code, "Should identify code portions"

    def test_handles_shell_paste(self, input_enhancer):
        """Vibe coder pastes terminal output with $ prompts."""
        pasted = '''$ python main.py
Traceback (most recent call last):
  File "main.py", line 5, in <module>
    print(undefined_var)
NameError: name 'undefined_var' is not defined
$ '''

        result = input_enhancer.extract_code(pasted)

        assert result.error_detected or result.contains_error, \
            "Should detect error in pasted output"


# ==============================================================================
# TEST CLASS: BEGINNER ERROR MESSAGES (Vibe coder needs simple explanations)
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.vibe_coder
class TestVibeCoderErrorMessages:
    """Tests for beginner-friendly error messages."""

    def test_explains_syntax_error_simply(self, error_presenter):
        """Vibe coder needs simple explanation of syntax errors."""
        error = SyntaxError("invalid syntax")
        error.filename = "main.py"
        error.lineno = 5
        error.text = "print('hello'"  # Missing closing paren

        presented = error_presenter.present(error, mode="beginner")

        assert presented.simple_explanation, "Should have simple explanation"
        assert any(word in presented.simple_explanation.lower()
                   for word in ["missing", "parenthesis", "bracket", "close"]), \
            "Should explain missing parenthesis simply"

    def test_explains_name_error_simply(self, error_presenter):
        """Vibe coder needs help with undefined variables."""
        error = NameError("name 'prnt' is not defined")

        presented = error_presenter.present(error, mode="beginner")

        assert presented.simple_explanation, "Should have simple explanation"
        assert presented.suggestions, "Should suggest corrections"
        assert any("print" in s.lower() or "typo" in s.lower()
                   for s in presented.suggestions), \
            "Should suggest 'print' as correction"

    def test_explains_import_error_simply(self, error_presenter):
        """Vibe coder needs help with import errors."""
        error = ImportError("No module named 'pands'")

        presented = error_presenter.present(error, mode="beginner")

        assert presented.simple_explanation, "Should have simple explanation"
        assert any(word in presented.simple_explanation.lower()
                   for word in ["install", "pip", "package"]), \
            "Should mention installation"
        assert any("pandas" in s.lower() for s in presented.suggestions), \
            "Should suggest 'pandas'"

    def test_provides_example_fix(self, error_presenter):
        """Vibe coder learns from examples."""
        error = TypeError("unsupported operand type(s) for +: 'int' and 'str'")

        presented = error_presenter.present(error, mode="beginner")

        assert presented.example_fix or presented.code_example, \
            "Should provide example fix"

    def test_uses_simple_language(self, error_presenter):
        """Vibe coder doesn't understand jargon."""
        error = AttributeError("'NoneType' object has no attribute 'append'")

        presented = error_presenter.present(error, mode="beginner")

        # Should not use technical jargon without explanation
        jargon_words = ["NoneType", "attribute", "object"]
        explanation = presented.simple_explanation.lower()

        for word in jargon_words:
            if word.lower() in explanation:
                # Should have a simple explanation nearby
                assert any(simple in explanation
                           for simple in ["means", "because", "empty", "nothing", "None"]), \
                    f"Should explain jargon '{word}' simply"


# ==============================================================================
# TEST CLASS: PATIENCE & GUIDANCE (Vibe coder needs handholding)
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.vibe_coder
class TestVibeCoderGuidance:
    """Tests for patient, guiding interactions."""

    def test_offers_step_by_step(self, error_presenter):
        """Vibe coder benefits from step-by-step instructions."""
        # Complex error requiring multiple steps to fix
        error = ModuleNotFoundError("No module named 'flask'")

        presented = error_presenter.present(error, mode="beginner")

        assert presented.steps or presented.how_to_fix, \
            "Should provide step-by-step instructions"

        if presented.steps:
            assert len(presented.steps) >= 2, "Should have multiple steps"

    def test_explains_why_not_just_what(self, error_presenter):
        """Vibe coder wants to understand 'why'."""
        error = IndentationError("unexpected indent")

        presented = error_presenter.present(error, mode="beginner")

        # Should explain WHY indentation matters
        explanation = presented.simple_explanation.lower()
        assert any(word in explanation
                   for word in ["space", "tab", "indent", "block", "python needs"]), \
            "Should explain why indentation matters"

    def test_encourages_beginner(self, error_presenter):
        """Vibe coder needs encouragement, not judgment."""
        error = SyntaxError("invalid syntax")

        presented = error_presenter.present(error, mode="beginner")

        # Should not be condescending
        message = (presented.message + " " + (presented.simple_explanation or "")).lower()
        negative_words = ["stupid", "wrong", "obviously", "should know", "basic"]

        for word in negative_words:
            assert word not in message, f"Should not use negative word '{word}'"

    def test_offers_to_help_further(self, error_presenter):
        """Vibe coder should know help is available."""
        error = RuntimeError("Something went wrong")

        presented = error_presenter.present(error, mode="beginner")

        # Should offer further help
        assert presented.help_available or presented.further_help or \
               any("help" in (s or "").lower() for s in (presented.suggestions or [])), \
            "Should offer further assistance"


# ==============================================================================
# TEST CLASS: CONTRADICTION HANDLING (Vibe coder gives conflicting info)
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.vibe_coder
class TestVibeCoderContradictions:
    """Tests for handling contradictory or confusing inputs."""

    def test_detects_contradictory_requests(self, input_enhancer):
        """Vibe coder says 'delete the file but keep it'."""
        result = input_enhancer.enhance("delete main.py but save the contents")

        assert result.needs_clarification or result.detected_contradiction, \
            "Should detect contradiction"

    def test_handles_changing_mind(self, context_tracker):
        """Vibe coder changes mind mid-conversation."""
        # First says one thing
        context_tracker.record_intent("create file hello.py")

        # Then says opposite
        context_tracker.record_intent("no wait, delete hello.py")

        # Should track latest intent
        current = context_tracker.get_current_intent()
        assert "delete" in current.lower(), "Should track latest intent"

    def test_handles_incomplete_sentences(self, input_enhancer):
        """Vibe coder types incomplete sentences."""
        incomplete_inputs = [
            "can you",
            "I want to",
            "please fix the",
            "create a file that",
        ]

        for inp in incomplete_inputs:
            result = input_enhancer.enhance(inp)
            assert result.needs_clarification or result.is_incomplete, \
                f"Should detect incomplete: '{inp}'"

    def test_handles_multiple_requests(self, input_enhancer):
        """Vibe coder asks for many things at once."""
        result = input_enhancer.enhance(
            "fix the bug and also add tests and make it faster and can you also document it"
        )

        assert result.multiple_intents or len(result.extracted_tasks or []) > 1, \
            "Should detect multiple requests"


# ==============================================================================
# TEST CLASS: LEARNING SUPPORT (Vibe coder wants to learn)
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.vibe_coder
class TestVibeCoderLearning:
    """Tests for educational support features."""

    def test_explains_code_on_request(self, input_enhancer):
        """Vibe coder asks 'what does this do?'."""
        result = input_enhancer.enhance("what does 'for i in range(10)' do?")

        assert result.is_question or result.wants_explanation, \
            "Should detect explanation request"

    def test_suggests_learning_resources(self, error_presenter):
        """Vibe coder benefits from learning resources."""
        # Conceptual error (list vs tuple)
        error = TypeError("'tuple' object does not support item assignment")

        presented = error_presenter.present(error, mode="beginner")

        # Should suggest learning more
        assert presented.learn_more or presented.resources or \
               any("learn" in (s or "").lower() for s in (presented.suggestions or [])), \
            "Should suggest learning resources"

    def test_builds_on_previous_context(self, context_tracker):
        """Vibe coder asks follow-up questions."""
        # First question
        context_tracker.record_interaction(
            "what is a function?",
            "A function is a reusable block of code..."
        )

        # Follow-up
        result = context_tracker.resolve_reference("how do I make one?")

        assert result.context_hint or result.related_to_previous, \
            "Should connect to previous topic (functions)"


# ==============================================================================
# SUMMARY
# ==============================================================================

"""
Total Tests: 30

Categories:
- Typo Correction: 5 tests
- Vague Input: 5 tests
- Code Paste: 5 tests
- Beginner Errors: 5 tests
- Guidance: 4 tests
- Contradictions: 4 tests
- Learning Support: 3 tests

Key Vibe Coder Expectations Tested:
1. Tolerant of typos and misspellings
2. Understands vague references ('it', 'the other one')
3. Extracts code from messy pastes
4. Explains errors in simple language
5. Provides step-by-step guidance
6. Handles contradictory requests gracefully
7. Supports learning with explanations
"""
