#!/usr/bin/env python3
"""
BRUTAL TEST RUNNER
==================

Runs the complete E2E brutal test suite and generates a comprehensive report.

Usage:
    python run_brutal_tests.py [--quick] [--category CATEGORY]

Options:
    --quick     Run only critical tests
    --category  Run specific category (senior, vibe_coder, script_kid, stress, integration)
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def run_tests(category: str = None, quick: bool = False) -> Dict[str, Any]:
    """Run pytest and capture results."""

    test_dir = Path(__file__).parent

    cmd = [
        sys.executable, "-m", "pytest",
        str(test_dir),
        "-v",
        "--tb=short",
        "-x" if quick else "",  # Stop on first failure if quick
    ]

    if category:
        cmd.extend(["-m", category])

    # Remove empty strings
    cmd = [c for c in cmd if c]

    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=test_dir.parent.parent  # Project root
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


def parse_issues_from_code() -> List[Dict[str, Any]]:
    """Parse all ISSUE-XXX from test files."""

    issues = []
    test_dir = Path(__file__).parent

    issue_id = 0
    for test_file in test_dir.glob("test_*.py"):
        content = test_file.read_text()

        # Find all issue definitions
        import re

        # Pattern: ISSUE-XXX: Title
        pattern = r'ISSUE[_-](\d+)[:\s]+([^\n"]+)'

        for match in re.finditer(pattern, content):
            issue_num = match.group(1)
            title = match.group(2).strip()

            # Try to find severity
            severity = "MEDIUM"
            if 'severity="CRITICAL"' in content[match.start():match.start()+500]:
                severity = "CRITICAL"
            elif 'severity="HIGH"' in content[match.start():match.start()+500]:
                severity = "HIGH"
            elif 'severity="LOW"' in content[match.start():match.start()+500]:
                severity = "LOW"

            # Try to find category
            category = "UNKNOWN"
            cat_match = re.search(r'category="([^"]+)"', content[match.start():match.start()+500])
            if cat_match:
                category = cat_match.group(1)

            # Determine persona from filename
            persona = "UNKNOWN"
            if "senior" in test_file.name:
                persona = "SENIOR"
            elif "vibe" in test_file.name:
                persona = "VIBE_CODER"
            elif "script" in test_file.name:
                persona = "SCRIPT_KID"
            elif "stress" in test_file.name:
                persona = "STRESS_TEST"
            elif "integration" in test_file.name:
                persona = "INTEGRATION"

            issues.append({
                "id": f"ISSUE-{issue_num.zfill(3)}",
                "title": title,
                "severity": severity,
                "category": category,
                "persona": persona,
                "file": test_file.name
            })

    return sorted(issues, key=lambda x: int(x["id"].split("-")[1]))


def generate_markdown_report(issues: List[Dict[str, Any]], test_result: Dict[str, Any]) -> str:
    """Generate comprehensive markdown report."""

    # Count by severity
    by_severity = {}
    by_category = {}
    by_persona = {}

    for issue in issues:
        by_severity.setdefault(issue["severity"], []).append(issue)
        by_category.setdefault(issue["category"], []).append(issue)
        by_persona.setdefault(issue["persona"], []).append(issue)

    report = f"""# BRUTAL E2E TEST REPORT - qwen-dev-cli

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Issues Found:** {len(issues)}
**Test Exit Code:** {test_result['returncode']}

---

## Executive Summary

This report documents all issues found during brutal E2E testing of the qwen-dev-cli shell.
Tests were designed from three user perspectives:

1. **Senior Developer** - Expects precision, reliability, professional error handling
2. **Vibe Coder** - Beginner who expects magic, gives vague instructions
3. **Script Kid** - Malicious actor attempting to break security

---

## Issue Distribution

### By Severity

| Severity | Count | Percentage |
|----------|-------|------------|
| CRITICAL | {len(by_severity.get('CRITICAL', []))} | {len(by_severity.get('CRITICAL', [])) * 100 // len(issues) if issues else 0}% |
| HIGH | {len(by_severity.get('HIGH', []))} | {len(by_severity.get('HIGH', [])) * 100 // len(issues) if issues else 0}% |
| MEDIUM | {len(by_severity.get('MEDIUM', []))} | {len(by_severity.get('MEDIUM', [])) * 100 // len(issues) if issues else 0}% |
| LOW | {len(by_severity.get('LOW', []))} | {len(by_severity.get('LOW', [])) * 100 // len(issues) if issues else 0}% |

### By Category

| Category | Count |
|----------|-------|
"""

    for cat, cat_issues in sorted(by_category.items()):
        report += f"| {cat} | {len(cat_issues)} |\n"

    report += """
### By User Persona

| Persona | Count |
|---------|-------|
"""

    for persona, p_issues in sorted(by_persona.items()):
        report += f"| {persona} | {len(p_issues)} |\n"

    report += """

---

## Critical Issues (Must Fix)

"""

    for issue in by_severity.get('CRITICAL', []):
        report += f"""### {issue['id']}: {issue['title']}
- **Category:** {issue['category']}
- **Persona:** {issue['persona']}
- **File:** {issue['file']}

"""

    report += """
---

## High Priority Issues

"""

    for issue in by_severity.get('HIGH', []):
        report += f"""### {issue['id']}: {issue['title']}
- **Category:** {issue['category']}
- **Persona:** {issue['persona']}
- **File:** {issue['file']}

"""

    report += """
---

## Medium Priority Issues

"""

    for issue in by_severity.get('MEDIUM', []):
        report += f"- **{issue['id']}**: {issue['title']} ({issue['category']})\n"

    report += """
---

## Low Priority Issues

"""

    for issue in by_severity.get('LOW', []):
        report += f"- **{issue['id']}**: {issue['title']} ({issue['category']})\n"

    report += """
---

## Complete Issue List

| ID | Title | Severity | Category | Persona |
|----|-------|----------|----------|---------|
"""

    for issue in issues:
        title_short = issue['title'][:50] + "..." if len(issue['title']) > 50 else issue['title']
        report += f"| {issue['id']} | {title_short} | {issue['severity']} | {issue['category']} | {issue['persona']} |\n"

    report += f"""

---

## Recommendations

### Immediate Actions (CRITICAL)
1. Fix all CRITICAL security issues before any release
2. Address path traversal and command injection vulnerabilities
3. Implement proper input validation

### Short-term (HIGH)
1. Add atomic file operations to prevent corruption
2. Implement proper error messages for beginners
3. Add undo/rollback functionality

### Medium-term (MEDIUM)
1. Add typo correction and fuzzy matching
2. Implement progress indicators for long operations
3. Add session persistence and crash recovery

### Nice-to-have (LOW)
1. Add frustration detection
2. Implement learning/verbose mode
3. Add multilingual support

---

## Test Output

```
{test_result['stdout'][-2000:] if test_result['stdout'] else 'No stdout'}
```

### Errors (if any)

```
{test_result['stderr'][-1000:] if test_result['stderr'] else 'No stderr'}
```

---

*Report generated by BRUTAL E2E Test Suite v1.0*
"""

    return report


def main():
    """Main entry point."""

    import argparse

    parser = argparse.ArgumentParser(description="Run brutal E2E tests")
    parser.add_argument("--quick", action="store_true", help="Quick mode - stop on first failure")
    parser.add_argument("--category", help="Run specific category")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing tests")

    args = parser.parse_args()

    print("=" * 60)
    print("BRUTAL E2E TEST SUITE - qwen-dev-cli")
    print("=" * 60)
    print()

    # Parse issues from code
    print("Parsing issues from test files...")
    issues = parse_issues_from_code()
    print(f"Found {len(issues)} documented issues")
    print()

    # Run tests if not report-only
    if not args.report_only:
        print("Running tests...")
        test_result = run_tests(category=args.category, quick=args.quick)
    else:
        test_result = {"returncode": 0, "stdout": "", "stderr": ""}

    # Generate report
    print("\nGenerating report...")
    report = generate_markdown_report(issues, test_result)

    # Save report
    report_path = Path(__file__).parent / "BRUTAL_TEST_REPORT.md"
    report_path.write_text(report)
    print(f"Report saved to: {report_path}")

    # Also save JSON
    json_report = {
        "generated": datetime.now().isoformat(),
        "total_issues": len(issues),
        "issues": issues,
        "test_returncode": test_result["returncode"]
    }
    json_path = Path(__file__).parent / "BRUTAL_TEST_REPORT.json"
    with open(json_path, "w") as f:
        json.dump(json_report, f, indent=2)
    print(f"JSON report saved to: {json_path}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Issues: {len(issues)}")

    by_sev = {}
    for i in issues:
        by_sev.setdefault(i["severity"], 0)
        by_sev[i["severity"]] += 1

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        print(f"  {sev}: {by_sev.get(sev, 0)}")

    print()

    if len(issues) >= 70:
        print("✅ TARGET MET: 70+ issues documented")
    else:
        print(f"⚠️  TARGET NOT MET: Only {len(issues)} issues (need 70+)")

    return 0 if len(issues) >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
