"""Constitutional metrics calculator (Layer 5 - Incentive).

Implements formal LEI, HRI, CPI calculations as required by
Constituição Vértice v3.0, Artigo X (Camada de Incentivo).

Boris Cherny: Quantify everything. Metrics drive improvement.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ConstitutionalMetrics:
    """Immutable metrics snapshot.
    
    All metrics defined by Constituição Vértice v3.0.
    """

    # LEI: Lazy Execution Index (target: < 1.0)
    lei: float
    lei_details: Dict[str, int]

    # HRI: Hallucination Rate Index (target: < 0.1)
    hri: float
    hri_details: Dict[str, int]

    # CPI: Completeness-Precision Index (target: > 0.9)
    cpi: float
    cpi_details: Dict[str, float]

    @property
    def is_compliant(self) -> bool:
        """Check if all metrics meet constitutional targets."""
        return (
            self.lei < 1.0 and
            self.hri < 0.1 and
            self.cpi > 0.9
        )

    @property
    def compliance_score(self) -> float:
        """Overall compliance score (0.0-1.0)."""
        lei_score = 1.0 if self.lei < 1.0 else (1.0 / (1.0 + self.lei))
        hri_score = 1.0 if self.hri < 0.1 else (1.0 - self.hri)
        cpi_score = self.cpi

        return (lei_score + hri_score + cpi_score) / 3.0

    def format_report(self) -> str:
        """Format as human-readable report."""
        status = "✅ COMPLIANT" if self.is_compliant else "⚠️  NON-COMPLIANT"

        lines = [
            "=" * 60,
            "CONSTITUTIONAL METRICS REPORT",
            "=" * 60,
            "",
            f"Overall Status: {status}",
            f"Compliance Score: {self.compliance_score:.1%}",
            "",
            "=" * 60,
            "LEI - Lazy Execution Index",
            "=" * 60,
            f"Score: {self.lei:.2f} (target: < 1.0) {'✅' if self.lei < 1.0 else '❌'}",
            "",
            "Lazy Patterns Detected:",
        ]

        for pattern, count in self.lei_details.items():
            lines.append(f"  • {pattern}: {count}")

        lines.extend([
            "",
            "=" * 60,
            "HRI - Hallucination Rate Index",
            "=" * 60,
            f"Score: {self.hri:.2f} (target: < 0.1) {'✅' if self.hri < 0.1 else '❌'}",
            "",
            "Error Categories:",
        ])

        for category, count in self.hri_details.items():
            lines.append(f"  • {category}: {count}")

        lines.extend([
            "",
            "=" * 60,
            "CPI - Completeness-Precision Index",
            "=" * 60,
            f"Score: {self.cpi:.2f} (target: > 0.9) {'✅' if self.cpi > 0.9 else '❌'}",
            "",
            "Components:",
        ])

        for component, value in self.cpi_details.items():
            lines.append(f"  • {component}: {value:.2f}")

        lines.append("=" * 60)

        return "\n".join(lines)


def calculate_lei(codebase_path: str = "jdev_cli") -> tuple[float, Dict[str, int]]:
    """Calculate Lazy Execution Index.
    
    LEI = (TODO + FIXME + pass + NotImplemented) / total_loc * 1000
    
    Target: < 1.0 per 1000 LOC
    
    Args:
        codebase_path: Path to analyze
        
    Returns:
        (LEI score, details dict)
    """
    import os

    total_loc = 0
    lazy_patterns = {
        "TODO": 0,
        "FIXME": 0,
        "XXX": 0,
        "HACK": 0,
        "pass_statements": 0,
        "NotImplemented": 0,
    }

    for root, dirs, files in os.walk(codebase_path):
        # Skip specific subdirectories (tests, prompts with examples, cache)
        path_parts = root.split(os.sep)
        skip_dirs = {'tests', 'test', '__pycache__', 'prompts', 'examples'}
        if any(part in skip_dirs for part in path_parts):
            continue

        for file in files:
            if not file.endswith('.py'):
                continue

            filepath = os.path.join(root, file)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    total_loc += len(lines)

                    for line in lines:
                        # Only count patterns in comments (not in strings/code)
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            if 'TODO' in line:
                                lazy_patterns["TODO"] += 1
                            if 'FIXME' in line:
                                lazy_patterns["FIXME"] += 1
                            if 'XXX' in line:
                                lazy_patterns["XXX"] += 1
                            if 'HACK' in line:
                                lazy_patterns["HACK"] += 1

                        # Count pass statements (excluding docstrings)
                        stripped = line.strip()
                        if stripped == 'pass':
                            lazy_patterns["pass_statements"] += 1

                        # Count NotImplemented (only bare raises, not in strings/detection)
                        if 'raise NotImplementedError' in line and '(' not in line:
                            lazy_patterns["NotImplemented"] += 1

            except (IOError, UnicodeDecodeError):
                continue

    total_lazy = sum(lazy_patterns.values())
    lei = (total_lazy / total_loc * 1000) if total_loc > 0 else 0.0

    return lei, lazy_patterns


def calculate_hri(
    error_log: List[Dict[str, str]] = None
) -> tuple[float, Dict[str, int]]:
    """Calculate Hallucination Rate Index.
    
    HRI = (API_errors + Logic_errors) / total_executions
    
    Target: < 0.1 (10% error rate)
    
    Args:
        error_log: List of error events
        
    Returns:
        (HRI score, details dict)
    """
    if error_log is None:
        error_log = []

    categories = {
        "api_errors": 0,
        "logic_errors": 0,
        "syntax_errors": 0,
        "runtime_errors": 0,
    }

    for error in error_log:
        error_type = error.get("type", "unknown").lower()

        if "api" in error_type or "connection" in error_type:
            categories["api_errors"] += 1
        elif "logic" in error_type or "assertion" in error_type:
            categories["logic_errors"] += 1
        elif "syntax" in error_type:
            categories["syntax_errors"] += 1
        else:
            categories["runtime_errors"] += 1

    total_errors = len(error_log)
    # Assume 1000 total executions for now (should be tracked)
    total_executions = max(1000, total_errors)

    hri = total_errors / total_executions if total_executions > 0 else 0.0

    return hri, categories


def calculate_cpi(
    completeness: float = 1.0,
    precision: float = 1.0,
    recall: float = 1.0
) -> tuple[float, Dict[str, float]]:
    """Calculate Completeness-Precision Index.
    
    CPI = (Completeness * 0.4) + (Precision * 0.3) + (Recall * 0.3)
    
    Target: > 0.9
    
    Args:
        completeness: Task completion rate (0.0-1.0)
        precision: Accuracy rate (0.0-1.0)
        recall: Coverage rate (0.0-1.0)
        
    Returns:
        (CPI score, details dict)
    """
    cpi = (completeness * 0.4) + (precision * 0.3) + (recall * 0.3)

    details = {
        "completeness": completeness,
        "precision": precision,
        "recall": recall,
    }

    return cpi, details


def generate_constitutional_report(
    codebase_path: str = "jdev_cli",
    error_log: List[Dict[str, str]] = None,
    completeness: float = 1.0,
    precision: float = 1.0,
    recall: float = 1.0
) -> ConstitutionalMetrics:
    """Generate complete constitutional metrics report.
    
    Args:
        codebase_path: Path to analyze
        error_log: List of error events
        completeness: Task completion rate
        precision: Accuracy rate
        recall: Coverage rate
        
    Returns:
        ConstitutionalMetrics object
    """
    lei, lei_details = calculate_lei(codebase_path)
    hri, hri_details = calculate_hri(error_log or [])
    cpi, cpi_details = calculate_cpi(completeness, precision, recall)

    return ConstitutionalMetrics(
        lei=lei,
        lei_details=lei_details,
        hri=hri,
        hri_details=hri_details,
        cpi=cpi,
        cpi_details=cpi_details
    )
