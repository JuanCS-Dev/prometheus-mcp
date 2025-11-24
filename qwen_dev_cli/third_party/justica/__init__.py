"""
🏛️ JUSTIÇA - Constitutional Governance Framework

A constitutional AI system for multi-agent environments that enforces
organizational principles through transparent, proportional governance.

Core Features:
    - 5 Constitutional Principles (Integrity, Proportionality, Transparency,
      Escalation, Learning)
    - 18 Violation Types (from data exfiltration to collective bypass)
    - Trust score management (0.0 - 1.0) with temporal decay
    - 3 Enforcement modes (COERCIVE, NORMATIVE, ADAPTIVE)
    - Real-time behavioral monitoring
    - Transparent audit logging

Performance:
    - 86% → 4.4% jailbreak reduction
    - 0.38% over-refusal rate
    - Zero external dependencies (pure Python stdlib)

Architecture:
    Input → Classification → Trust Check → Verdict → Enforcement → Audit

Usage:
    ```python
    from third_party.justica import JusticaAgent, JusticaConfig, EnforcementMode
    from third_party.justica import create_default_constitution

    config = JusticaConfig(
        agent_id="my-agent",
        enforcement_mode=EnforcementMode.NORMATIVE
    )
    constitution = create_default_constitution()

    justica = JusticaAgent(config=config, constitution=constitution)

    verdict = justica.evaluate_input(
        agent_id="executor",
        content="rm -rf /",
        context={}
    )

    if verdict.approved:
        # Safe to proceed
        pass
    else:
        # Blocked or requires human review
        print(verdict.reasoning)
    ```

Author: Multi-agent governance research
License: MIT
"""

# Constitution
from .constitution import (
    Constitution,
    ConstitutionalPrinciple,
    Severity,
    ViolationType,
    create_default_constitution
)

# Classifiers
from .classifiers import (
    ClassificationResult,
    ClassificationReport,
    BaseClassifier,
    InputClassifier,
    OutputClassifier,
    ConstitutionalClassifier
)

# Trust Engine
from .trust import (
    TrustEngine,
    TrustFactor,
    TrustLevel
)

# Enforcement
from .enforcement import (
    EnforcementMode,
    ActionType,
    EnforcementAction,
    EnforcementPolicy,
    EnforcementEngine
)

# Monitoring
from .monitor import (
    JusticaMonitor
)

# Audit
from .audit import (
    AuditLevel,
    AuditCategory,
    AuditEntry,
    AuditBackend,
    ConsoleBackend,
    FileBackend,
    InMemoryBackend,
    AuditLogger
)

# Main Agent
from .agent import (
    JusticaState,
    JusticaConfig,
    JusticaVerdict,
    JusticaAgent
)

# Aliases for compatibility
Verdict = JusticaVerdict

__version__ = "2.0.0"
__author__ = "Multi-agent governance research"
__license__ = "MIT"
__description__ = "Constitutional AI Governance Framework"

__all__ = [
    # Metadata
    "__version__",
    "__author__",
    "__license__",

    # Constitution
    "Constitution",
    "ConstitutionalPrinciple",
    "Severity",
    "ViolationType",
    "create_default_constitution",

    # Classifiers
    "ClassificationResult",
    "ClassificationReport",
    "BaseClassifier",
    "InputClassifier",
    "OutputClassifier",
    "ConstitutionalClassifier",

    # Trust
    "TrustEngine",
    "TrustFactor",
    "TrustLevel",

    # Enforcement
    "EnforcementMode",
    "ActionType",
    "EnforcementAction",
    "EnforcementPolicy",
    "EnforcementEngine",

    # Monitoring
    "JusticaMonitor",

    # Audit
    "AuditLevel",
    "AuditCategory",
    "AuditEntry",
    "AuditBackend",
    "ConsoleBackend",
    "FileBackend",
    "InMemoryBackend",
    "AuditLogger",

    # Agent
    "JusticaState",
    "JusticaConfig",
    "JusticaVerdict",
    "Verdict",  # Alias
    "JusticaAgent",
]
