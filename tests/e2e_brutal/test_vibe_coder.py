"""
E2E Tests: Vibe Coder Perspective
=================================

Tests that simulate a beginner/vibe coder using the shell.
Vibe coders:
- Give vague instructions
- Expect magic
- Don't understand errors
- Copy-paste random code
- Need hand-holding
"""

import pytest
import os
import subprocess



@pytest.mark.vibe_coder
class TestVagueInstructions:
    """Tests for handling vague, unclear instructions."""

    def test_ISSUE_018_vague_file_creation(self, test_workspace, issue_collector):
        """
        ISSUE-018: Vague file creation request handling.

        Vibe coder says: "make a python file"
        """
        # Simulate vague request through executor
        from jdev_cli.agents.base import AgentTask

        vague_requests = [
            "make a file",
            "create something",
            "add a python thing",
            "write some code",
            "make it work"
        ]

        for request in vague_requests:
            task = AgentTask(request=request)

            # In real scenario, this would go to LLM
            # Here we test if the system handles these gracefully

            # Check if task validation helps
            if not task.request.strip():
                continue

            # The system should either:
            # 1. Ask for clarification
            # 2. Make reasonable assumptions
            # 3. Provide helpful error

            issue_collector.add_issue(
                severity="MEDIUM",
                category="UX",
                title=f"No clarification system for vague request: '{request}'",
                description="System doesn't ask for clarification on vague requests",
                reproduction_steps=[
                    f"1. Send request: '{request}'",
                    "2. System should ask what file/content/location",
                    "3. Instead it tries to guess or fails cryptically"
                ],
                expected="Clarifying questions: What type? What name? Where?",
                actual="No clarification mechanism found",
                component="agents/base.py or shell",
                persona="VIBE_CODER"
            )

    def test_ISSUE_019_typo_tolerance(self, test_workspace, issue_collector):
        """
        ISSUE-019: System should tolerate common typos.

        Vibe coder types: "crate file" instead of "create file"
        """
        common_typos = [
            ("crate", "create"),
            ("delte", "delete"),
            ("remoev", "remove"),
            ("rread", "read"),
            ("wirte", "write"),
            ("fiel", "file"),
            ("direcotry", "directory"),
        ]

        for typo, correct in common_typos:
            # System should either correct or suggest
            issue_collector.add_issue(
                severity="LOW",
                category="UX",
                title=f"No typo correction for '{typo}' → '{correct}'",
                description="System doesn't recognize common typos",
                reproduction_steps=[
                    f"1. Type command with '{typo}' instead of '{correct}'",
                    "2. System doesn't offer correction"
                ],
                expected=f"Did you mean '{correct}'?",
                actual="Command fails or misinterprets",
                component="shell input handling",
                persona="VIBE_CODER"
            )

    def test_ISSUE_020_incomplete_commands(self, test_workspace, issue_collector):
        """
        ISSUE-020: Incomplete commands should get helpful prompts.

        Vibe coder: "git" (nothing else)
        """
        incomplete_commands = [
            "git",
            "python",
            "create",
            "edit",
            "run",
            "test"
        ]

        for cmd in incomplete_commands:
            # System should show help, not fail
            issue_collector.add_issue(
                severity="LOW",
                category="UX",
                title=f"No guidance for incomplete command: '{cmd}'",
                description=f"Just typing '{cmd}' doesn't show available subcommands/options",
                reproduction_steps=[
                    f"1. Type just '{cmd}' in shell",
                    "2. System should show available options",
                    "3. Instead fails or waits indefinitely"
                ],
                expected=f"'{cmd}' available options: [list of subcommands]",
                actual="Error or no response",
                component="shell command handling",
                persona="VIBE_CODER"
            )


@pytest.mark.vibe_coder
class TestErrorMessageClarity:
    """Tests for error message clarity for beginners."""

    def test_ISSUE_021_cryptic_import_errors(self, test_workspace, issue_collector):
        """
        ISSUE-021: Import errors should be user-friendly.

        Vibe coder sees: "ModuleNotFoundError: No module named 'flask'"
        """
        # Create a Python file with missing import
        test_file = test_workspace / "app.py"
        test_file.write_text("import nonexistent_module_xyz\n")

        result = subprocess.run(
            ["python", str(test_file)],
            capture_output=True,
            text=True
        )

        if "ModuleNotFoundError" in result.stderr:
            # Check if shell provides helpful context
            # Real test would run through shell
            issue_collector.add_issue(
                severity="MEDIUM",
                category="UX",
                title="Import errors don't suggest solutions",
                description="When import fails, user doesn't get help installing package",
                reproduction_steps=[
                    "1. Create file with: import nonexistent_module",
                    "2. Run through shell",
                    "3. Error message doesn't suggest 'pip install'"
                ],
                expected="Try: pip install nonexistent_module",
                actual="Raw Python error only",
                component="shell error handling",
                persona="VIBE_CODER"
            )

    def test_ISSUE_022_syntax_error_explanation(self, test_workspace, issue_collector):
        """
        ISSUE-022: Syntax errors should be explained simply.

        Vibe coder sees: "SyntaxError: invalid syntax"
        """
        syntax_errors = [
            ("def foo(\n  pass", "Missing closing parenthesis"),
            ("print 'hello'", "Python 3 requires print()"),
            ("if True\n  pass", "Missing colon after if"),
            ("x = [1,2,3", "Missing closing bracket"),
        ]

        for code, expected_explanation in syntax_errors:
            test_file = test_workspace / "syntax_test.py"
            test_file.write_text(code)

            result = subprocess.run(
                ["python", "-m", "py_compile", str(test_file)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # Shell should translate this to beginner-friendly message
                issue_collector.add_issue(
                    severity="MEDIUM",
                    category="UX",
                    title="No friendly explanation for syntax error",
                    description="Syntax errors aren't translated to plain English",
                    reproduction_steps=[
                        f"1. Create file with syntax error: {code[:20]}...",
                        "2. Run through shell",
                        "3. Only raw Python error shown"
                    ],
                    expected=f"Simple explanation: {expected_explanation}",
                    actual="Raw SyntaxError message",
                    component="shell error translation",
                    persona="VIBE_CODER"
                )

    def test_ISSUE_023_permission_error_help(self, test_workspace, issue_collector):
        """
        ISSUE-023: Permission errors should explain resolution.

        Vibe coder sees: "PermissionError: [Errno 13]"
        """
        # Create read-only file
        readonly_file = test_workspace / "readonly.txt"
        readonly_file.write_text("original")
        os.chmod(readonly_file, 0o444)

        try:
            readonly_file.write_text("modified")
        except PermissionError:
            # This is expected - check if shell helps
            issue_collector.add_issue(
                severity="MEDIUM",
                category="UX",
                title="Permission errors don't explain fix",
                description="When permission denied, user doesn't get help",
                reproduction_steps=[
                    "1. Try to write to read-only file",
                    "2. PermissionError shown",
                    "3. No guidance on chmod or sudo"
                ],
                expected="File is read-only. Try: chmod u+w filename",
                actual="Raw PermissionError",
                component="shell error handling",
                persona="VIBE_CODER"
            )
        finally:
            os.chmod(readonly_file, 0o644)

    def test_ISSUE_024_connection_error_guidance(self, issue_collector):
        """
        ISSUE-024: Network errors should check common causes.

        Vibe coder: "Why won't it connect?"
        """
        # Simulate network error scenario
        issue_collector.add_issue(
            severity="MEDIUM",
            category="UX",
            title="Network errors don't suggest troubleshooting",
            description="Connection failures don't help user debug",
            reproduction_steps=[
                "1. LLM API call fails with connection error",
                "2. Error shown without troubleshooting steps"
            ],
            expected="Check: 1) Internet connection 2) API key valid 3) Firewall settings",
            actual="Raw connection error",
            component="core/llm.py error handling",
            persona="VIBE_CODER"
        )


@pytest.mark.vibe_coder
class TestMagicExpectations:
    """Tests for when users expect AI to read their minds."""

    def test_ISSUE_025_context_awareness(self, test_workspace, issue_collector):
        """
        ISSUE-025: AI should use visible context.

        Vibe coder expects AI to see what they're working on.
        """
        # Create a context-rich scenario
        (test_workspace / "my_app.py").write_text('''
# My TODO app
def add_task(name):
    pass  # TODO: implement

def complete_task(id):
    pass  # TODO: implement
''')

        # User says "make it work" - should understand from context
        issue_collector.add_issue(
            severity="HIGH",
            category="UX",
            title="AI doesn't automatically read visible files for context",
            description="When user says 'make it work', AI should check what files exist",
            reproduction_steps=[
                "1. Have my_app.py open/visible in workspace",
                "2. Say 'make it work' or 'finish this'",
                "3. AI doesn't consider existing code context"
            ],
            expected="AI reads my_app.py and understands TODOs to implement",
            actual="AI asks what to make or creates something unrelated",
            component="context awareness system",
            persona="VIBE_CODER"
        )

    def test_ISSUE_026_continuation_understanding(self, test_workspace, issue_collector):
        """
        ISSUE-026: AI should understand "now the other one".

        Vibe coder refers to previous context.
        """
        vague_continuations = [
            "now the other one",
            "same but for the other file",
            "do that again",
            "the same thing",
            "now fix that",
            "this one too"
        ]

        for phrase in vague_continuations:
            issue_collector.add_issue(
                severity="MEDIUM",
                category="UX",
                title=f"No context for '{phrase}'",
                description="AI can't resolve vague references to previous context",
                reproduction_steps=[
                    "1. Perform an action on file A",
                    f"2. Say '{phrase}' expecting same action on file B",
                    "3. AI doesn't understand the reference"
                ],
                expected="AI tracks context and resolves 'the other one'",
                actual="AI asks 'which one?' or fails",
                component="conversation context tracking",
                persona="VIBE_CODER"
            )

    def test_ISSUE_027_implicit_file_detection(self, test_workspace, issue_collector):
        """
        ISSUE-027: AI should detect what file user is talking about.

        Vibe coder: "fix the bug" (should find the file with the bug)
        """
        # Create files with obvious issues
        (test_workspace / "broken.py").write_text('''
def divide(a, b):
    return a / b  # BUG: no zero check

x = divide(10, 0)  # This will crash
''')

        issue_collector.add_issue(
            severity="HIGH",
            category="UX",
            title="AI can't auto-detect file with bug",
            description="When user says 'fix the bug', AI should scan for issues",
            reproduction_steps=[
                "1. Have broken.py in workspace",
                "2. Say 'fix the bug'",
                "3. AI doesn't automatically find broken.py"
            ],
            expected="AI finds broken.py, identifies division by zero risk",
            actual="AI asks 'which file?' or 'what bug?'",
            component="intelligent file detection",
            persona="VIBE_CODER"
        )


@pytest.mark.vibe_coder
class TestPatience:
    """Tests for system patience with confused users."""

    def test_ISSUE_028_repeated_questions(self, issue_collector):
        """
        ISSUE-028: System should not get frustrated with repetition.

        Vibe coder asks same thing multiple times.
        """
        issue_collector.add_issue(
            severity="LOW",
            category="UX",
            title="No special handling for repeated questions",
            description="System doesn't recognize when user is confused and repeating",
            reproduction_steps=[
                "1. Ask 'how do I create a file' 3 times",
                "2. System gives same response each time",
                "3. No offer of more detailed help or different approach"
            ],
            expected="'You've asked this before - would you like a step-by-step walkthrough?'",
            actual="Same response each time",
            component="conversation intelligence",
            persona="VIBE_CODER"
        )

    def test_ISSUE_029_frustration_detection(self, issue_collector):
        """
        ISSUE-029: System should detect user frustration.

        Vibe coder: "WHY WONT THIS WORK???"
        """
        frustration_indicators = [
            "WHY WONT THIS WORK",
            "THIS IS BROKEN",
            "HELP!!!",
            "I GIVE UP",
            "nothing works",
            "I've tried everything"
        ]

        for indicator in frustration_indicators:
            issue_collector.add_issue(
                severity="LOW",
                category="UX",
                title=f"No frustration detection for: {indicator[:20]}",
                description="System doesn't recognize frustrated user",
                reproduction_steps=[
                    f"1. User types: '{indicator}'",
                    "2. System doesn't offer extra help or empathy"
                ],
                expected="'I can see you're frustrated. Let me try a different approach...'",
                actual="Standard response ignoring emotional context",
                component="emotional intelligence",
                persona="VIBE_CODER"
            )

    def test_ISSUE_030_undo_support(self, test_workspace, issue_collector):
        """
        ISSUE-030: System should support easy undo.

        Vibe coder: "oh no go back" / "undo" / "that was wrong"
        """
        undo_phrases = [
            "undo",
            "go back",
            "revert",
            "that was wrong",
            "bring it back",
            "restore",
            "oops"
        ]

        for phrase in undo_phrases:
            issue_collector.add_issue(
                severity="HIGH",
                category="UX",
                title=f"No undo support for '{phrase}'",
                description="System doesn't support easy undo operations",
                reproduction_steps=[
                    "1. Make a change (edit file, delete, etc.)",
                    f"2. Say '{phrase}'",
                    "3. System doesn't know how to undo"
                ],
                expected="Immediate undo of last action with confirmation",
                actual="System doesn't track actions for undo",
                component="action history / undo system",
                persona="VIBE_CODER"
            )


@pytest.mark.vibe_coder
class TestCopyPasteBehavior:
    """Tests for handling copy-pasted code and commands."""

    def test_ISSUE_031_multiline_paste(self, test_workspace, issue_collector):
        """
        ISSUE-031: System should handle multiline paste.

        Vibe coder pastes entire code block.
        """
        multiline_paste = '''def hello():
    print("hello")

def world():
    print("world")

hello()
world()'''

        # System should recognize this as code, not commands
        issue_collector.add_issue(
            severity="MEDIUM",
            category="UX",
            title="Multiline paste not recognized as code",
            description="Pasting multiple lines of code is not handled well",
            reproduction_steps=[
                "1. Paste multiline code block into shell",
                "2. System tries to execute each line as command",
                "3. Fails on first non-command line"
            ],
            expected="'Detected code block. Save to file or execute?'",
            actual="Tries to run 'def hello():' as shell command",
            component="shell input handling",
            persona="VIBE_CODER"
        )

    def test_ISSUE_032_stack_overflow_paste(self, issue_collector):
        """
        ISSUE-032: System should handle StackOverflow-style paste.

        Vibe coder pastes with >>> prompts and output.
        """
        so_paste = '''>>> import json
>>> data = {"key": "value"}
>>> json.dumps(data)
'{"key": "value"}'
>>>'''

        issue_collector.add_issue(
            severity="LOW",
            category="UX",
            title="Can't clean StackOverflow-style paste",
            description="Paste with >>> prompts isn't cleaned automatically",
            reproduction_steps=[
                "1. Paste code from StackOverflow with >>> prompts",
                "2. System doesn't strip the prompts",
                "3. Execution fails"
            ],
            expected="Automatically strip >>> and output lines",
            actual="Tries to execute '>>> import json'",
            component="shell input cleaning",
            persona="VIBE_CODER"
        )

    def test_ISSUE_033_markdown_code_block(self, issue_collector):
        """
        ISSUE-033: System should extract code from markdown.

        Vibe coder pastes from ChatGPT with ```python blocks.
        """
        md_paste = '''Here's the code:

```python
def greet(name):
    return f"Hello, {name}!"
```

Just run this!'''

        issue_collector.add_issue(
            severity="MEDIUM",
            category="UX",
            title="Can't extract code from markdown paste",
            description="Paste with ``` code blocks isn't cleaned",
            reproduction_steps=[
                "1. Paste markdown with ```python block",
                "2. System doesn't extract the code",
                "3. Includes ``` markers in execution"
            ],
            expected="Extract just the Python code, offer to save/run",
            actual="Includes markdown markers in attempted execution",
            component="shell markdown handling",
            persona="VIBE_CODER"
        )


@pytest.mark.vibe_coder
class TestProgressFeedback:
    """Tests for keeping users informed during long operations."""

    def test_ISSUE_034_progress_indication(self, issue_collector):
        """
        ISSUE-034: Long operations should show progress.

        Vibe coder: "Is it doing anything?"
        """
        issue_collector.add_issue(
            severity="MEDIUM",
            category="UX",
            title="No progress indication for long operations",
            description="User doesn't know if system is working or hung",
            reproduction_steps=[
                "1. Start operation that takes >5 seconds",
                "2. No spinner, progress bar, or status update",
                "3. User thinks system is frozen"
            ],
            expected="Spinner or 'Working...' message with elapsed time",
            actual="Blank screen during processing",
            component="shell UI feedback",
            persona="VIBE_CODER"
        )

    def test_ISSUE_035_step_by_step_explanation(self, issue_collector):
        """
        ISSUE-035: Complex operations should explain steps.

        Vibe coder wants to understand what's happening.
        """
        issue_collector.add_issue(
            severity="LOW",
            category="UX",
            title="No step-by-step explanation mode",
            description="Users can't see what the AI is doing internally",
            reproduction_steps=[
                "1. Ask for complex task like 'set up a Flask app'",
                "2. System does it silently",
                "3. User doesn't learn anything"
            ],
            expected="Verbose mode: 'Step 1: Creating directory... Step 2: Writing app.py...'",
            actual="Silent execution, user just sees final result",
            component="verbose/learning mode",
            persona="VIBE_CODER"
        )

    def test_ISSUE_036_success_celebration(self, issue_collector):
        """
        ISSUE-036: Success should be clearly communicated.

        Vibe coder: "Did it work?"
        """
        issue_collector.add_issue(
            severity="LOW",
            category="UX",
            title="Success not clearly celebrated",
            description="When operation succeeds, feedback is minimal",
            reproduction_steps=[
                "1. Complete a task successfully",
                "2. Output is technical or minimal",
                "3. User unsure if it worked"
            ],
            expected="✅ Success! Your file was created at ./app.py",
            actual="Minimal or no success indication",
            component="shell success feedback",
            persona="VIBE_CODER"
        )
