"""
AuditLogger - Governance Audit Logging
Pipeline de Diamante - Camada 4: OUTPUT SHIELD

Addresses: ISSUE-080, ISSUE-082 (Governance audit logging)

Implements:
- Complete traceability for governance decisions
- Correlation IDs for tracing
- Multiple backends (file, structured)
- Query interface for review

Design Philosophy:
- Every decision is logged
- Full traceability
- Tamper-evident logs
- Searchable history
"""

from __future__ import annotations

import os
import json
import time
import hashlib
import threading
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    # Governance events
    GOVERNANCE_CHECK = "governance_check"
    GOVERNANCE_BLOCK = "governance_block"
    GOVERNANCE_ALLOW = "governance_allow"

    # Operation events
    OPERATION_START = "operation_start"
    OPERATION_COMPLETE = "operation_complete"
    OPERATION_FAIL = "operation_fail"
    OPERATION_ROLLBACK = "operation_rollback"

    # Security events
    SECURITY_VIOLATION = "security_violation"
    SECURITY_WARNING = "security_warning"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"

    # Agent events
    AGENT_START = "agent_start"
    AGENT_HANDOFF = "agent_handoff"
    AGENT_COMPLETE = "agent_complete"

    # User events
    USER_INPUT = "user_input"
    USER_APPROVAL = "user_approval"
    USER_REJECTION = "user_rejection"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


@dataclass
class AuditEntry:
    """A single audit log entry."""
    event_id: str
    timestamp: float
    event_type: AuditEventType
    severity: AuditSeverity

    # Context
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: Optional[str] = None

    # Event details
    action: str = ""
    resource: str = ""
    outcome: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    # Integrity
    previous_hash: Optional[str] = None
    entry_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "outcome": self.outcome,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Deserialize from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            event_type=AuditEventType(data["event_type"]),
            severity=AuditSeverity(data["severity"]),
            correlation_id=data.get("correlation_id"),
            session_id=data.get("session_id"),
            agent_id=data.get("agent_id"),
            user_id=data.get("user_id"),
            action=data.get("action", ""),
            resource=data.get("resource", ""),
            outcome=data.get("outcome", ""),
            details=data.get("details", {}),
            previous_hash=data.get("previous_hash"),
            entry_hash=data.get("entry_hash"),
        )

    def compute_hash(self) -> str:
        """Compute hash for this entry."""
        data = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "action": self.action,
            "resource": self.resource,
            "outcome": self.outcome,
            "previous_hash": self.previous_hash,
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]


class AuditLogger:
    """
    Governance audit logger with full traceability.

    Features:
    - Tamper-evident chain of hashes
    - Multiple severity levels
    - Correlation ID tracking
    - File and memory backends
    - Query interface

    Usage:
        audit = AuditLogger()

        # Log governance decision
        audit.log_governance(
            action="execute_command",
            resource="rm -rf /tmp/test",
            outcome="blocked",
            details={"reason": "Dangerous command pattern"}
        )

        # Query logs
        blocked = audit.query(event_type=AuditEventType.GOVERNANCE_BLOCK)
    """

    DEFAULT_LOG_DIR = ".qwen_audit_logs"
    MAX_MEMORY_ENTRIES = 1000

    def __init__(
        self,
        log_dir: Optional[str] = None,
        session_id: Optional[str] = None,
        enable_file_logging: bool = True,
        enable_chain_hashing: bool = True,
    ):
        """
        Initialize AuditLogger.

        Args:
            log_dir: Directory for log files
            session_id: Session identifier
            enable_file_logging: Write logs to file
            enable_chain_hashing: Enable tamper-evident hashing
        """
        import uuid

        self.log_dir = Path(log_dir or self.DEFAULT_LOG_DIR)
        self.session_id = session_id or str(uuid.uuid4())
        self.enable_file_logging = enable_file_logging
        self.enable_chain_hashing = enable_chain_hashing

        self._entries: List[AuditEntry] = []
        self._last_hash: Optional[str] = None
        self._entry_counter = 0
        self._lock = threading.Lock()

        # Correlation context
        self._correlation_stack: List[str] = []
        self._current_correlation: Optional[str] = None

        if enable_file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        self._entry_counter += 1
        return f"evt_{int(time.time() * 1000)}_{self._entry_counter}"

    def log(
        self,
        event_type: AuditEventType,
        action: str,
        resource: str = "",
        outcome: str = "",
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AuditEntry:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            action: Action being audited
            resource: Resource affected
            outcome: Outcome of action
            severity: Event severity
            details: Additional details
            agent_id: Agent performing action
            user_id: User involved

        Returns:
            Created AuditEntry
        """
        with self._lock:
            entry = AuditEntry(
                event_id=self._generate_event_id(),
                timestamp=time.time(),
                event_type=event_type,
                severity=severity,
                correlation_id=self._current_correlation,
                session_id=self.session_id,
                agent_id=agent_id,
                user_id=user_id,
                action=action,
                resource=resource,
                outcome=outcome,
                details=details or {},
                previous_hash=self._last_hash,
            )

            # Compute chain hash
            if self.enable_chain_hashing:
                entry.entry_hash = entry.compute_hash()
                self._last_hash = entry.entry_hash

            # Store in memory
            self._entries.append(entry)
            if len(self._entries) > self.MAX_MEMORY_ENTRIES:
                self._entries.pop(0)

            # Write to file
            if self.enable_file_logging:
                self._write_to_file(entry)

            return entry

    def log_governance(
        self,
        action: str,
        resource: str,
        outcome: str,
        blocked: bool = False,
        **kwargs
    ) -> AuditEntry:
        """Log a governance decision."""
        event_type = AuditEventType.GOVERNANCE_BLOCK if blocked else AuditEventType.GOVERNANCE_ALLOW
        severity = AuditSeverity.WARNING if blocked else AuditSeverity.INFO

        return self.log(
            event_type=event_type,
            action=action,
            resource=resource,
            outcome=outcome,
            severity=severity,
            **kwargs
        )

    def log_security(
        self,
        action: str,
        resource: str,
        violation: bool = False,
        **kwargs
    ) -> AuditEntry:
        """Log a security event."""
        event_type = AuditEventType.SECURITY_VIOLATION if violation else AuditEventType.SECURITY_WARNING
        severity = AuditSeverity.ERROR if violation else AuditSeverity.WARNING

        return self.log(
            event_type=event_type,
            action=action,
            resource=resource,
            severity=severity,
            **kwargs
        )

    def log_operation(
        self,
        action: str,
        resource: str,
        success: bool,
        **kwargs
    ) -> AuditEntry:
        """Log an operation event."""
        event_type = AuditEventType.OPERATION_COMPLETE if success else AuditEventType.OPERATION_FAIL
        severity = AuditSeverity.INFO if success else AuditSeverity.ERROR

        return self.log(
            event_type=event_type,
            action=action,
            resource=resource,
            outcome="success" if success else "failure",
            severity=severity,
            **kwargs
        )

    def log_agent(
        self,
        agent_id: str,
        action: str,
        event_type: AuditEventType = AuditEventType.AGENT_START,
        **kwargs
    ) -> AuditEntry:
        """Log an agent event."""
        return self.log(
            event_type=event_type,
            action=action,
            agent_id=agent_id,
            **kwargs
        )

    @contextmanager
    def correlation_context(self, correlation_id: Optional[str] = None):
        """
        Context manager for correlation ID tracking.

        Usage:
            with audit.correlation_context("task-123"):
                audit.log(...)  # Will have correlation_id="task-123"
        """
        import uuid
        correlation_id = correlation_id or str(uuid.uuid4())

        self._correlation_stack.append(self._current_correlation or "")
        self._current_correlation = correlation_id

        try:
            yield correlation_id
        finally:
            self._current_correlation = self._correlation_stack.pop() or None

    def query(
        self,
        event_type: Optional[AuditEventType] = None,
        severity_min: Optional[AuditSeverity] = None,
        correlation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """
        Query audit logs.

        Args:
            event_type: Filter by event type
            severity_min: Minimum severity
            correlation_id: Filter by correlation ID
            agent_id: Filter by agent ID
            since: Only entries after this timestamp
            limit: Maximum entries to return

        Returns:
            List of matching entries
        """
        results = []

        for entry in reversed(self._entries):
            if event_type and entry.event_type != event_type:
                continue
            if severity_min and entry.severity.value < severity_min.value:
                continue
            if correlation_id and entry.correlation_id != correlation_id:
                continue
            if agent_id and entry.agent_id != agent_id:
                continue
            if since and entry.timestamp < since:
                continue

            results.append(entry)
            if len(results) >= limit:
                break

        return results

    def verify_chain(self) -> Tuple[bool, List[str]]:
        """
        Verify the integrity of the audit chain.

        Returns:
            (is_valid, errors)
        """
        errors = []
        prev_hash = None

        for entry in self._entries:
            if entry.previous_hash != prev_hash:
                errors.append(f"Chain break at {entry.event_id}")

            if self.enable_chain_hashing:
                computed = entry.compute_hash()
                if entry.entry_hash != computed:
                    errors.append(f"Hash mismatch at {entry.event_id}")

            prev_hash = entry.entry_hash

        return len(errors) == 0, errors

    def _write_to_file(self, entry: AuditEntry) -> None:
        """Write entry to log file."""
        try:
            date_str = datetime.fromtimestamp(entry.timestamp).strftime("%Y-%m-%d")
            log_file = self.log_dir / f"audit_{date_str}.jsonl"

            with open(log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def export(self, output_path: str, format: str = "json") -> bool:
        """
        Export audit logs to file.

        Args:
            output_path: Output file path
            format: Export format (json, csv)

        Returns:
            Success status
        """
        try:
            if format == "json":
                with open(output_path, "w") as f:
                    json.dump([e.to_dict() for e in self._entries], f, indent=2)

            elif format == "csv":
                import csv
                with open(output_path, "w", newline="") as f:
                    if self._entries:
                        writer = csv.DictWriter(f, fieldnames=self._entries[0].to_dict().keys())
                        writer.writeheader()
                        for entry in self._entries:
                            writer.writerow(entry.to_dict())

            return True

        except Exception as e:
            logger.error(f"Failed to export audit logs: {e}")
            return False


# Global instance
_default_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the default audit logger instance."""
    global _default_logger
    if _default_logger is None:
        _default_logger = AuditLogger()
    return _default_logger


# Convenience functions

def audit_log(event_type: AuditEventType, action: str, **kwargs) -> AuditEntry:
    """Log an audit event."""
    return get_audit_logger().log(event_type, action, **kwargs)


def audit_governance(action: str, resource: str, blocked: bool = False, **kwargs) -> AuditEntry:
    """Log a governance decision."""
    return get_audit_logger().log_governance(action, resource, blocked=blocked, **kwargs)


def audit_security(action: str, resource: str, violation: bool = False, **kwargs) -> AuditEntry:
    """Log a security event."""
    return get_audit_logger().log_security(action, resource, violation=violation, **kwargs)


# Export all public symbols
__all__ = [
    'AuditEventType',
    'AuditSeverity',
    'AuditEntry',
    'AuditLogger',
    'get_audit_logger',
    'audit_log',
    'audit_governance',
    'audit_security',
]
