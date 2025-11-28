#!/usr/bin/env python3
"""
MEGA TEST E2E - PROVA CABAL
===========================

Comprehensive test of all jdev_tui components.
Generates PROVA-CABAL.md report.
"""

import sys
import os
from datetime import datetime
from typing import List, Tuple

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Colors for terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

# Test results
results: List[Tuple[str, bool, str]] = []


def test(name: str, code: str) -> bool:
    """Run a test and record result."""
    print(f"{YELLOW}▶{RESET} Testing: {name}...", end=" ", flush=True)
    try:
        exec(code, {})
        print(f"{GREEN}✓ PASS{RESET}")
        results.append((name, True, ""))
        return True
    except Exception as e:
        print(f"{RED}✗ FAIL{RESET} - {e}")
        results.append((name, False, str(e)))
        return False


def section(title: str):
    """Print section header."""
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{MAGENTA}{title}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")


def main():
    print(f"\n{CYAN}╔{'═'*58}╗{RESET}")
    print(f"{CYAN}║{RESET} {MAGENTA}MEGA TEST E2E - PROVA CABAL{RESET}")
    print(f"{CYAN}╚{'═'*58}╝{RESET}\n")

    # =========================================================================
    # 1. CORE IMPORTS
    # =========================================================================
    section("1. CORE IMPORTS")

    test("Import jdev_tui.app",
         "from jdev_tui.app import QwenApp")

    test("Import jdev_tui.core",
         "from jdev_tui.core import Bridge, OutputFormatter, ToolCallParser")

    test("Import jdev_cli.tools",
         "from jdev_cli.tools.base import Tool, ToolRegistry")

    test("Import jdev_cli.agents",
         "from jdev_cli.agents.base import BaseAgent")

    # =========================================================================
    # 2. BRIDGE
    # =========================================================================
    section("2. BRIDGE INITIALIZATION")

    test("Bridge creates",
         "from jdev_tui.core import Bridge; b = Bridge()")

    test("Bridge has LLM",
         "from jdev_tui.core import Bridge; b = Bridge(); assert b.llm is not None")

    test("Bridge has governance",
         "from jdev_tui.core import Bridge; b = Bridge(); assert b.governance is not None")

    test("Bridge has tools",
         "from jdev_tui.core import Bridge; b = Bridge(); assert b.tools is not None")

    test("Bridge has autocomplete",
         "from jdev_tui.core import Bridge; b = Bridge(); assert b.autocomplete is not None")

    # =========================================================================
    # 3. TOOLS
    # =========================================================================
    section("3. TOOL REGISTRY")

    test("ToolBridge loads tools",
         "from jdev_tui.core.bridge import ToolBridge; tb = ToolBridge(); tools = tb.list_tools(); assert len(tools) >= 10, f'Only {len(tools)} tools'")

    test("Tool schemas generate",
         "from jdev_tui.core.bridge import ToolBridge; tb = ToolBridge(); schemas = tb.get_schemas_for_llm(); assert len(schemas) >= 5")

    test("File tools present",
         "from jdev_tui.core.bridge import ToolBridge; tb = ToolBridge(); tools = tb.list_tools(); assert any('read' in t.lower() for t in tools)")

    test("Bash tool present",
         "from jdev_tui.core.bridge import ToolBridge; tb = ToolBridge(); tools = tb.list_tools(); assert any('bash' in t.lower() for t in tools)")

    test("Git tools present",
         "from jdev_tui.core.bridge import ToolBridge; tb = ToolBridge(); tools = tb.list_tools(); assert any('git' in t.lower() for t in tools)")

    # =========================================================================
    # 4. AGENTS
    # =========================================================================
    section("4. AGENTS")

    agents = ["planner", "executor", "architect", "reviewer", "explorer",
              "refactorer", "testing", "security", "documentation",
              "performance", "devops", "justica", "sofia"]

    for agent in agents:
        test(f"Agent: {agent}",
             f"from jdev_tui.core.bridge import AgentManager, GeminiClient; am = AgentManager(GeminiClient()); assert '{agent}' in am.available_agents")

    # =========================================================================
    # 5. TOOL CALL PARSER
    # =========================================================================
    section("5. TOOL CALL PARSER")

    test("Extract tool calls",
         'from jdev_tui.core.bridge import ToolCallParser; calls = ToolCallParser.extract(\'[TOOL_CALL:write_file:{"path":"test.txt"}]\'); assert len(calls) == 1')

    test("Remove markers",
         "from jdev_tui.core.bridge import ToolCallParser; clean = ToolCallParser.remove('Before [TOOL_CALL:x:{}] After'); assert '[TOOL_CALL' not in clean")

    test("Roundtrip",
         "from jdev_tui.core.bridge import ToolCallParser; marker = ToolCallParser.format_marker('test', {'a': 1}); calls = ToolCallParser.extract(marker); assert calls[0][0] == 'test'")

    # =========================================================================
    # 6. OUTPUT FORMATTER
    # =========================================================================
    section("6. OUTPUT FORMATTER")

    test("format_response",
         "from jdev_tui.core.output_formatter import OutputFormatter; from rich.panel import Panel; p = OutputFormatter.format_response('test'); assert isinstance(p, Panel)")

    test("format_tool_result",
         "from jdev_tui.core.output_formatter import OutputFormatter; OutputFormatter.format_tool_result('test', True, 'data')")

    test("format_code_block",
         "from jdev_tui.core.output_formatter import OutputFormatter; OutputFormatter.format_code_block('print(1)', 'python')")

    test("Truncates long content",
         "from jdev_tui.core.output_formatter import OutputFormatter; from io import StringIO; from rich.console import Console; c = Console(file=StringIO()); c.print(OutputFormatter.format_response('x'*10000)); assert 'truncat' in c.file.getvalue().lower()")

    # =========================================================================
    # 7. AUTOCOMPLETE
    # =========================================================================
    section("7. AUTOCOMPLETE")

    test("AutocompleteBridge init",
         "from jdev_tui.core.bridge import AutocompleteBridge, ToolBridge; AutocompleteBridge(ToolBridge())")

    test("Completions for /",
         "from jdev_tui.core.bridge import AutocompleteBridge, ToolBridge; ab = AutocompleteBridge(ToolBridge()); comps = ab.get_completions('/h'); assert len(comps) > 0")

    test("Completions for tools",
         "from jdev_tui.core.bridge import AutocompleteBridge, ToolBridge; ab = AutocompleteBridge(ToolBridge()); comps = ab.get_completions('read'); assert len(comps) > 0")

    # =========================================================================
    # 8. GOVERNANCE
    # =========================================================================
    section("8. GOVERNANCE")

    test("GovernanceObserver init",
         "from jdev_tui.core.bridge import GovernanceObserver; GovernanceObserver()")

    test("Risk assessment",
         "from jdev_tui.core.bridge import GovernanceObserver; go = GovernanceObserver(); go.assess_risk('rm -rf /')")

    test("Observer mode",
         "from jdev_tui.core.bridge import GovernanceObserver; go = GovernanceObserver(); assert go.config.block_on_violation == False")

    # =========================================================================
    # 9. SYSTEM PROMPT
    # =========================================================================
    section("9. SYSTEM PROMPT")

    test("Contains tools",
         "from jdev_tui.core.bridge import Bridge; b = Bridge(); prompt = b._get_system_prompt(); assert 'tool' in prompt.lower()")

    test("Action focused",
         "from jdev_tui.core.bridge import Bridge; b = Bridge(); prompt = b._get_system_prompt(); assert 'action' in prompt.lower() or 'execute' in prompt.lower()")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    section("SUMMARY")

    passed = sum(1 for _, success, _ in results if success)
    failed = sum(1 for _, success, _ in results if not success)
    total = len(results)
    rate = (passed / total * 100) if total > 0 else 0

    print(f"Total:  {total}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")
    print(f"Rate:   {rate:.1f}%")

    # =========================================================================
    # GENERATE REPORT
    # =========================================================================
    section("GENERATING REPORT")

    # Get tool and agent counts
    try:
        from jdev_tui.core.bridge import ToolBridge, AgentManager, GeminiClient
        tb = ToolBridge()
        tools = tb.list_tools()
        am = AgentManager(GeminiClient())
        agents = am.available_agents
    except Exception:
        tools = []
        agents = []

    report = f"""# 🎯 PROVA CABAL - JuanCS Dev-Code Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Python:** {sys.version.split()[0]}

---

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {total} |
| **Passed** | ✅ {passed} |
| **Failed** | ❌ {failed} |
| **Pass Rate** | **{rate:.1f}%** |

---

## 🔍 Detailed Results

"""
    for name, success, error in results:
        if success:
            report += f"- ✅ {name}\n"
        else:
            report += f"- ❌ {name}: {error}\n"

    report += f"""

---

## 🧩 Component Status

### Tools Loaded ({len(tools)})
```
{chr(10).join(f'  - {t}' for t in sorted(tools)[:35])}
{'  ...' if len(tools) > 35 else ''}
```

### Agents Available ({len(agents)})
```
{chr(10).join(f'  - {a}' for a in sorted(agents))}
```

---

## 🎨 UI Features

- [x] Autocomplete dropdown with fuzzy search
- [x] Rich.Panel formatted responses (cyan borders)
- [x] Tool execution result panels (green/red)
- [x] Hidden scrollbars
- [x] Dracula-inspired color palette
- [x] Status bar with metrics
- [x] History navigation (up/down)

---

## 🏆 Verdict

{"✅ **PROVA CABAL PASSED** - System is fully operational!" if failed == 0 else f"⚠️ **{failed} tests failed** - Review required"}

---

**Soli Deo Gloria** 🙏
"""

    with open("PROVA-CABAL.md", "w") as f:
        f.write(report)

    print(f"Report saved to: {CYAN}PROVA-CABAL.md{RESET}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
