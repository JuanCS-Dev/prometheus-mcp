"""E2E Tests: Auditing and Validation Workflows.

Tests security auditing, code review, and validation capabilities.
"""

import pytest
import time
from pathlib import Path

from .conftest import TestResult


class TestSecurityAudit:
    """Test security auditing capabilities."""

    @pytest.mark.asyncio
    async def test_detect_hardcoded_secrets(self, sample_python_project, e2e_report):
        """Test detection of hardcoded secrets."""
        start_time = time.time()
        result = TestResult(
            name="detect_hardcoded_secrets",
            status="passed",
            duration=0.0,
            metadata={"audit_type": "secrets"}
        )

        try:
            from jdev_cli.tools.search import SearchFilesTool

            search_tool = SearchFilesTool()

            # Search for potential secrets
            patterns = [
                ("API_KEY.*=.*['\"]", "API keys"),
                ("password.*=.*['\"]", "Passwords"),
                ("secret.*=.*['\"]", "Secrets"),
                ("token.*=.*['\"]", "Tokens"),
                ("postgresql://.*:.*@", "Database credentials"),
            ]

            findings = []
            for pattern, name in patterns:
                search_result = await search_tool._execute_validated(
                    pattern=pattern,
                    path=str(sample_python_project),
                    file_pattern="*.py",
                    ignore_case=True
                )

                if search_result.success and search_result.data.get("matches"):
                    for match in search_result.data["matches"]:
                        findings.append({
                            "type": name,
                            "file": match["file"],
                            "line": match.get("line", "?"),
                            "severity": "HIGH"
                        })

            # Should find the hardcoded secrets in config.py
            assert len(findings) > 0, "Should detect hardcoded secrets"

            result.logs.append(f"✓ Scanned for {len(patterns)} secret patterns")
            result.logs.append(f"✓ Found {len(findings)} potential secrets")
            for f in findings[:3]:
                result.logs.append(f"  ⚠️ {f['type']} in {Path(f['file']).name}")

            result.metadata["patterns_checked"] = len(patterns)
            result.metadata["findings"] = len(findings)
            result.metadata["severity_breakdown"] = {"HIGH": len(findings)}

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_detect_security_vulnerabilities(self, temp_project, e2e_report):
        """Test detection of common security vulnerabilities."""
        start_time = time.time()
        result = TestResult(
            name="detect_security_vulnerabilities",
            status="passed",
            duration=0.0,
            metadata={"audit_type": "vulnerabilities"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool
            from jdev_cli.tools.search import SearchFilesTool

            write_tool = WriteFileTool()
            search_tool = SearchFilesTool()

            # Create vulnerable code
            vulnerable_code = '''"""Vulnerable code examples for testing."""

import os
import subprocess
import pickle
import yaml

# VULN 1: Command injection
def run_command(user_input):
    os.system(f"echo {user_input}")  # Dangerous!

# VULN 2: SQL Injection (simulated)
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection!
    return query

# VULN 3: Insecure deserialization
def load_data(data):
    return pickle.loads(data)  # Arbitrary code execution!

# VULN 4: YAML unsafe load
def parse_config(yaml_str):
    return yaml.load(yaml_str)  # Should use safe_load!

# VULN 5: Hardcoded credentials
DB_PASSWORD = "super_secret_123"
API_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"

# VULN 6: Path traversal
def read_file(filename):
    with open(f"/data/{filename}") as f:  # Path traversal possible!
        return f.read()

# VULN 7: Weak crypto
import hashlib
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()  # MD5 is weak!
'''
            vuln_file = temp_project / "vulnerable.py"
            await write_tool._execute_validated(
                path=str(vuln_file),
                content=vulnerable_code
            )

            # Scan for vulnerabilities
            vuln_patterns = [
                ("os\\.system\\(", "Command Injection", "CRITICAL"),
                ("subprocess\\..*shell=True", "Shell Injection", "CRITICAL"),
                ("pickle\\.loads", "Insecure Deserialization", "HIGH"),
                ("yaml\\.load\\(", "Unsafe YAML Load", "HIGH"),
                ("eval\\(", "Code Injection", "CRITICAL"),
                ("exec\\(", "Code Execution", "CRITICAL"),
                ("md5|sha1", "Weak Hashing", "MEDIUM"),
                ("SELECT.*\\+|SELECT.*%|SELECT.*f\"", "SQL Injection", "CRITICAL"),
            ]

            vulnerabilities = []
            for pattern, name, severity in vuln_patterns:
                search_result = await search_tool._execute_validated(
                    pattern=pattern,
                    path=str(temp_project),
                    file_pattern="*.py"
                )

                if search_result.success and search_result.data.get("matches"):
                    for match in search_result.data["matches"]:
                        vulnerabilities.append({
                            "type": name,
                            "severity": severity,
                            "file": match["file"],
                            "line": match.get("line", "?")
                        })

            result.logs.append(f"✓ Checked {len(vuln_patterns)} vulnerability patterns")
            result.logs.append(f"✓ Found {len(vulnerabilities)} vulnerabilities")

            # Group by severity
            by_severity = {}
            for v in vulnerabilities:
                sev = v["severity"]
                by_severity[sev] = by_severity.get(sev, 0) + 1

            for sev, count in sorted(by_severity.items()):
                emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(sev, "⚪")
                result.logs.append(f"  {emoji} {sev}: {count}")

            result.metadata["vulnerabilities_found"] = len(vulnerabilities)
            result.metadata["by_severity"] = by_severity

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestCodeQualityAudit:
    """Test code quality auditing."""

    @pytest.mark.asyncio
    async def test_detect_code_smells(self, temp_project, e2e_report):
        """Test detection of code smells."""
        start_time = time.time()
        result = TestResult(
            name="detect_code_smells",
            status="passed",
            duration=0.0,
            metadata={"audit_type": "code_quality"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool
            from jdev_cli.tools.search import SearchFilesTool

            write_tool = WriteFileTool()
            search_tool = SearchFilesTool()

            # Create code with smells
            smelly_code = '''"""Code with various code smells."""

# SMELL: Magic numbers
def calculate_price(quantity):
    return quantity * 19.99 * 1.08 * 0.95

# SMELL: Long function
def process_order(order):
    # Validate order
    if not order:
        return None
    if not order.get("items"):
        return None
    if not order.get("customer"):
        return None
    if not order.get("shipping"):
        return None
    # Calculate totals
    subtotal = 0
    for item in order["items"]:
        price = item.get("price", 0)
        qty = item.get("quantity", 0)
        subtotal += price * qty
    # Apply discounts
    discount = 0
    if subtotal > 100:
        discount = subtotal * 0.1
    elif subtotal > 50:
        discount = subtotal * 0.05
    # Calculate tax
    tax = (subtotal - discount) * 0.08
    # Calculate shipping
    shipping = 0
    if order["shipping"] == "express":
        shipping = 15.99
    elif order["shipping"] == "standard":
        shipping = 5.99
    # Calculate total
    total = subtotal - discount + tax + shipping
    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "shipping": shipping,
        "total": total
    }

# SMELL: Too many parameters
def create_user(name, email, phone, address, city, state, zip_code,
                country, birthday, gender, preferences, notifications):
    pass

# SMELL: Deep nesting
def check_permissions(user, resource, action):
    if user:
        if user.is_active:
            if user.role:
                if user.role == "admin":
                    return True
                else:
                    if resource:
                        if resource.owner == user.id:
                            return True
                        else:
                            if action == "read":
                                return resource.is_public
    return False

# SMELL: Dead code
def unused_function():
    """This function is never called."""
    pass

OLD_CONSTANT = "not used"
'''
            smell_file = temp_project / "smelly.py"
            await write_tool._execute_validated(
                path=str(smell_file),
                content=smelly_code
            )

            # Detect code smells
            smells_found = []

            # Check for magic numbers
            search_result = await search_tool._execute_validated(
                pattern=r"\d+\.\d{2}",
                path=str(temp_project / "smelly.py")
            )
            if search_result.success and search_result.data.get("matches"):
                smells_found.append({
                    "type": "Magic Numbers",
                    "count": len(search_result.data["matches"]),
                    "severity": "LOW"
                })

            # Check for long functions (by counting lines with same indent)
            content = smell_file.read_text()
            functions = content.count("def ")
            lines = len(content.splitlines())
            avg_func_length = lines / max(functions, 1)
            if avg_func_length > 20:
                smells_found.append({
                    "type": "Long Functions",
                    "count": 1,
                    "severity": "MEDIUM",
                    "detail": f"Average {avg_func_length:.0f} lines/function"
                })

            # Check for deep nesting
            max_indent = max(len(line) - len(line.lstrip()) for line in content.splitlines() if line.strip())
            if max_indent > 16:
                smells_found.append({
                    "type": "Deep Nesting",
                    "count": 1,
                    "severity": "MEDIUM",
                    "detail": f"Max indent: {max_indent} spaces"
                })

            # Check for too many parameters
            search_result = await search_tool._execute_validated(
                pattern=r"def \w+\([^)]{100,}\)",
                path=str(temp_project / "smelly.py")
            )
            if search_result.success and search_result.data.get("matches"):
                smells_found.append({
                    "type": "Too Many Parameters",
                    "count": len(search_result.data["matches"]),
                    "severity": "MEDIUM"
                })

            result.logs.append("✓ Analyzed code for smells")
            result.logs.append(f"✓ Found {len(smells_found)} types of code smells")
            for smell in smells_found:
                detail = smell.get('detail', f"{smell['count']} occurrences")
                result.logs.append(f"  ⚠️ {smell['type']}: {detail}")

            result.metadata["smells_found"] = len(smells_found)
            result.metadata["smell_types"] = [s["type"] for s in smells_found]

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_check_test_coverage(self, sample_python_project, e2e_report):
        """Test checking test coverage indicators."""
        start_time = time.time()
        result = TestResult(
            name="check_test_coverage",
            status="passed",
            duration=0.0,
            metadata={"audit_type": "coverage"}
        )

        try:
            from jdev_cli.tools.search import SearchFilesTool

            search_tool = SearchFilesTool()

            # Find all Python files
            py_files = list(sample_python_project.rglob("*.py"))
            src_files = [f for f in py_files if "test" not in f.name.lower() and f.parent.name != "tests"]
            test_files = [f for f in py_files if "test" in f.name.lower() or f.parent.name == "tests"]

            # Find functions in source files
            search_result = await search_tool._execute_validated(
                pattern=r"def \w+\(",
                path=str(sample_python_project / "src"),
                file_pattern="*.py"
            )

            src_functions = 0
            if search_result.success and search_result.data.get("matches"):
                src_functions = len(search_result.data["matches"])

            # Find test functions
            search_result = await search_tool._execute_validated(
                pattern=r"def test_\w+\(",
                path=str(sample_python_project / "tests"),
                file_pattern="*.py"
            )

            test_functions = 0
            if search_result.success and search_result.data.get("matches"):
                test_functions = len(search_result.data["matches"])

            # Calculate coverage ratio
            coverage_ratio = test_functions / max(src_functions, 1)

            result.logs.append(f"✓ Found {len(src_files)} source files")
            result.logs.append(f"✓ Found {len(test_files)} test files")
            result.logs.append(f"✓ Source functions: {src_functions}")
            result.logs.append(f"✓ Test functions: {test_functions}")
            result.logs.append(f"✓ Test/Function ratio: {coverage_ratio:.1%}")

            if coverage_ratio < 0.5:
                result.logs.append("  ⚠️ Warning: Low test coverage!")
            elif coverage_ratio >= 1.0:
                result.logs.append("  ✅ Good test coverage!")

            result.metadata["source_files"] = len(src_files)
            result.metadata["test_files"] = len(test_files)
            result.metadata["source_functions"] = src_functions
            result.metadata["test_functions"] = test_functions
            result.metadata["coverage_ratio"] = f"{coverage_ratio:.1%}"

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error


class TestComplianceAudit:
    """Test compliance auditing capabilities."""

    @pytest.mark.asyncio
    async def test_license_compliance(self, temp_project, e2e_report):
        """Test checking license compliance."""
        start_time = time.time()
        result = TestResult(
            name="license_compliance",
            status="passed",
            duration=0.0,
            metadata={"audit_type": "license"}
        )

        try:
            from jdev_cli.tools.file_ops import WriteFileTool
            from jdev_cli.tools.search import SearchFilesTool

            write_tool = WriteFileTool()
            search_tool = SearchFilesTool()

            # Create requirements with various licenses
            requirements = """# Production dependencies
fastapi>=0.104.0  # MIT
uvicorn>=0.24.0  # BSD
pydantic>=2.5.0  # MIT
sqlalchemy>=2.0.0  # MIT
redis>=5.0.0  # MIT
celery>=5.3.0  # BSD

# Dev dependencies
pytest>=7.4.0  # MIT
black>=23.0.0  # MIT
ruff>=0.1.0  # MIT
"""
            await write_tool._execute_validated(
                path=str(temp_project / "requirements.txt"),
                content=requirements
            )

            # Create a license file
            license_content = """MIT License

Copyright (c) 2024 E2E Test

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
"""
            await write_tool._execute_validated(
                path=str(temp_project / "LICENSE"),
                content=license_content
            )

            # Check for license file
            license_exists = (temp_project / "LICENSE").exists()

            # Parse requirements for license info
            req_content = (temp_project / "requirements.txt").read_text()
            licenses_found = {
                "MIT": req_content.count("# MIT"),
                "BSD": req_content.count("# BSD"),
                "Apache": req_content.count("# Apache"),
                "GPL": req_content.count("# GPL")
            }

            result.logs.append(f"✓ License file present: {license_exists}")
            result.logs.append("✓ Project license: MIT")
            result.logs.append("✓ Dependencies analyzed:")
            for lic, count in licenses_found.items():
                if count > 0:
                    result.logs.append(f"  - {lic}: {count} packages")

            # Check for GPL (copyleft) which might be incompatible
            if licenses_found.get("GPL", 0) > 0:
                result.logs.append("  ⚠️ Warning: GPL dependencies found - check compatibility!")

            result.metadata["has_license"] = license_exists
            result.metadata["project_license"] = "MIT"
            result.metadata["dependency_licenses"] = licenses_found

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error

    @pytest.mark.asyncio
    async def test_documentation_audit(self, sample_python_project, e2e_report):
        """Test auditing documentation completeness."""
        start_time = time.time()
        result = TestResult(
            name="documentation_audit",
            status="passed",
            duration=0.0,
            metadata={"audit_type": "documentation"}
        )

        try:
            from jdev_cli.tools.search import SearchFilesTool

            search_tool = SearchFilesTool()

            # Check for README
            has_readme = (sample_python_project / "README.md").exists()

            # Check for docstrings in Python files
            search_result = await search_tool._execute_validated(
                pattern=r'"""[^"]+"""',
                path=str(sample_python_project / "src"),
                file_pattern="*.py"
            )

            docstrings_count = 0
            if search_result.success and search_result.data.get("matches"):
                docstrings_count = len(search_result.data["matches"])

            # Check for functions without docstrings
            search_result = await search_tool._execute_validated(
                pattern=r"def \w+\([^)]*\):\s*\n\s*[^\"']",
                path=str(sample_python_project / "src"),
                file_pattern="*.py"
            )

            undocumented = 0
            if search_result.success and search_result.data.get("matches"):
                undocumented = len(search_result.data["matches"])

            # Check for type hints
            search_result = await search_tool._execute_validated(
                pattern=r"def \w+\([^)]*:[^)]+\)",
                path=str(sample_python_project / "src"),
                file_pattern="*.py"
            )

            typed_functions = 0
            if search_result.success and search_result.data.get("matches"):
                typed_functions = len(search_result.data["matches"])

            result.logs.append(f"✓ README.md present: {has_readme}")
            result.logs.append(f"✓ Docstrings found: {docstrings_count}")
            result.logs.append(f"✓ Functions with type hints: {typed_functions}")
            if undocumented > 0:
                result.logs.append(f"  ⚠️ Functions without docstrings: ~{undocumented}")

            # Calculate documentation score
            score = 0
            if has_readme:
                score += 30
            if docstrings_count > 3:
                score += 40
            if typed_functions > 2:
                score += 30

            result.logs.append(f"✓ Documentation score: {score}/100")

            result.metadata["has_readme"] = has_readme
            result.metadata["docstrings"] = docstrings_count
            result.metadata["typed_functions"] = typed_functions
            result.metadata["doc_score"] = score

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration = time.time() - start_time
            e2e_report.add_result(result)

        assert result.status == "passed", result.error
