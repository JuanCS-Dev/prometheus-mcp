# Error Recovery System - User Guide
**Version:** 1.0  
**Last Updated:** 2025-11-20  
**Status:** Production Ready ✅

---

## 📖 Overview

The Error Recovery System provides intelligent, automated error recovery with retry logic, circuit breaker pattern, and dual rollback capabilities.

---

## 🎯 Quick Start

```python
from qwen_dev_cli.core.recovery import ErrorRecoveryEngine, RecoveryContext, ErrorCategory

# Initialize
engine = ErrorRecoveryEngine(
    llm_client=your_llm_client,
    max_attempts=2,
    enable_retry_policy=True,
    enable_circuit_breaker=True
)

# Create context
context = RecoveryContext(
    attempt_number=1,
    max_attempts=2,
    error="Connection timeout",
    error_category=ErrorCategory.NETWORK,
    failed_tool="http_get",
    failed_args={"url": "https://api.example.com"},
    previous_result=None,
    user_intent="Fetch API data",
    previous_commands=[]
)

# Attempt recovery
result = await engine.attempt_recovery_with_backoff(context, Exception("timeout"))

# Use result
if result.corrected_args:
    print(f"Use: {result.corrected_args}")
else:
    print(f"Escalate: {result.escalation_reason}")
```

For full documentation, see source code docstrings and test examples in `tests/test_day7_mega_validation.py`.
