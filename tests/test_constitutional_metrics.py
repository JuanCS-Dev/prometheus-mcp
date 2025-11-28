"""Tests for constitutional metrics.

Validates LEI, HRI, CPI calculations per Constituição Vértice v3.0.
"""

import pytest
import tempfile
import os
from jdev_cli.core.constitutional_metrics import (
    calculate_lei,
    calculate_hri,
    calculate_cpi,
    generate_constitutional_report,
    ConstitutionalMetrics
)


class TestLEI:
    """Test Lazy Execution Index calculation."""

    def test_clean_code_low_lei(self):
        """Clean code should have LEI < 1.0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create clean Python file
            filepath = os.path.join(tmpdir, "clean.py")
            with open(filepath, 'w') as f:
                f.write("""
def hello():
    return "world"

class MyClass:
    def method(self):
        return 42
""")

            lei, details = calculate_lei(tmpdir)
            assert lei < 1.0
            assert sum(details.values()) == 0

    def test_lazy_code_high_lei(self):
        """Code with TODOs/pass should have higher LEI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "lazy.py")
            with open(filepath, 'w') as f:
                f.write("""
# TODO: Implement this
def todo_function():
    pass

# FIXME: Fix this later
def fixme_function():
    raise NotImplementedError
""")

            lei, details = calculate_lei(tmpdir)
            assert lei > 0.0
            assert details["TODO"] > 0
            assert details["FIXME"] > 0
            assert details["pass_statements"] > 0

    def test_lei_target_threshold(self):
        """LEI target is < 1.0 per 1000 LOC."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with exactly 1 TODO in 1000 lines
            filepath = os.path.join(tmpdir, "target.py")
            with open(filepath, 'w') as f:
                f.write("# TODO: One todo\n")
                for _ in range(999):
                    f.write("x = 1\n")

            lei, _ = calculate_lei(tmpdir)
            assert lei == 1.0  # Exactly at threshold


class TestHRI:
    """Test Hallucination Rate Index calculation."""

    def test_no_errors_zero_hri(self):
        """No errors should give HRI = 0."""
        hri, details = calculate_hri([])
        assert hri == 0.0
        assert all(v == 0 for v in details.values())

    def test_api_errors_counted(self):
        """API errors should be tracked."""
        errors = [
            {"type": "api_error", "message": "Connection failed"},
            {"type": "api_timeout", "message": "Timeout"},
        ]

        hri, details = calculate_hri(errors)
        assert details["api_errors"] == 2
        assert hri > 0.0

    def test_hri_target_threshold(self):
        """HRI target is < 0.1 (10%)."""
        # 99 errors in 1000 executions = 9.9%
        errors = [{"type": "error"} for _ in range(99)]
        hri, _ = calculate_hri(errors)
        assert hri < 0.1


class TestCPI:
    """Test Completeness-Precision Index calculation."""

    def test_perfect_cpi(self):
        """Perfect scores should give CPI = 1.0."""
        cpi, details = calculate_cpi(1.0, 1.0, 1.0)
        assert cpi == 1.0
        assert details["completeness"] == 1.0
        assert details["precision"] == 1.0
        assert details["recall"] == 1.0

    def test_weighted_cpi(self):
        """CPI uses weighted formula."""
        # Completeness: 40%, Precision: 30%, Recall: 30%
        cpi, _ = calculate_cpi(1.0, 0.5, 0.5)
        expected = (1.0 * 0.4) + (0.5 * 0.3) + (0.5 * 0.3)
        assert abs(cpi - expected) < 0.01

    def test_cpi_target_threshold(self):
        """CPI target is > 0.9."""
        cpi, _ = calculate_cpi(0.95, 0.95, 0.85)
        assert cpi > 0.9


class TestConstitutionalMetrics:
    """Test ConstitutionalMetrics object."""

    def test_metrics_immutable(self):
        """Metrics should be immutable."""
        metrics = ConstitutionalMetrics(
            lei=0.5,
            lei_details={},
            hri=0.05,
            hri_details={},
            cpi=0.95,
            cpi_details={}
        )

        with pytest.raises(AttributeError):
            metrics.lei = 1.0  # type: ignore

    def test_compliance_check(self):
        """is_compliant should check all thresholds."""
        # All targets met
        compliant = ConstitutionalMetrics(
            lei=0.5,
            lei_details={},
            hri=0.05,
            hri_details={},
            cpi=0.95,
            cpi_details={}
        )
        assert compliant.is_compliant

        # LEI too high
        non_compliant = ConstitutionalMetrics(
            lei=1.5,
            lei_details={},
            hri=0.05,
            hri_details={},
            cpi=0.95,
            cpi_details={}
        )
        assert not non_compliant.is_compliant

    def test_compliance_score(self):
        """compliance_score should be 0.0-1.0."""
        metrics = ConstitutionalMetrics(
            lei=0.5,
            lei_details={},
            hri=0.05,
            hri_details={},
            cpi=0.95,
            cpi_details={}
        )

        score = metrics.compliance_score
        assert 0.0 <= score <= 1.0

    def test_format_report(self):
        """format_report should generate readable output."""
        metrics = ConstitutionalMetrics(
            lei=0.67,
            lei_details={"TODO": 5, "pass_statements": 2},
            hri=0.05,
            hri_details={"api_errors": 2},
            cpi=0.95,
            cpi_details={"completeness": 0.95}
        )

        report = metrics.format_report()
        assert "CONSTITUTIONAL METRICS REPORT" in report
        assert "LEI" in report
        assert "HRI" in report
        assert "CPI" in report
        assert "0.67" in report


class TestIntegration:
    """Integration tests."""

    def test_generate_full_report(self):
        """generate_constitutional_report should work end-to-end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample code
            filepath = os.path.join(tmpdir, "sample.py")
            with open(filepath, 'w') as f:
                f.write("""
def clean_function():
    return 42

class GoodClass:
    def method(self):
        return "result"
""")

            metrics = generate_constitutional_report(
                codebase_path=tmpdir,
                error_log=[],
                completeness=0.95,
                precision=0.95,
                recall=0.90
            )

            assert isinstance(metrics, ConstitutionalMetrics)
            assert metrics.lei >= 0.0
            assert metrics.hri >= 0.0
            assert 0.0 <= metrics.cpi <= 1.0
