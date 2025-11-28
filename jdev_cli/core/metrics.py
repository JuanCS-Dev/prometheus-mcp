"""
Metrics & Telemetry Module - Constitutional Layer 5 (Incentive/Behavioral Control)

Implements DETER-AGENT metrics:
- LEI (Lazy Execution Index) - Measures incomplete/partial implementations
- HRI (Hallucination Rate Index) - Measures invalid tool calls/outputs
- CPI (Completeness-Precision Index) - Measures task completion quality

Target Standards (Constituição Vértice v3.0):
- LEI < 1.0 (lower is better, 0 = perfect)
- HRI < 0.1 (lower is better, 0 = perfect)
- CPI > 0.9 (higher is better, 1.0 = perfect)
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
from pathlib import Path


@dataclass
class ToolCallMetrics:
    """Metrics for individual tool call execution."""
    tool_name: str
    success: bool
    execution_time: float
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ParseMetrics:
    """Metrics for LLM response parsing."""
    success: bool
    strategy_used: str
    num_tools_found: int
    parse_time: float
    had_errors: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionMetrics:
    """Aggregate metrics for a session."""
    session_id: str
    start_time: float
    end_time: Optional[float] = None

    # Tool execution metrics
    tool_calls: List[ToolCallMetrics] = field(default_factory=list)
    total_tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0

    # Parse metrics
    parse_attempts: List[ParseMetrics] = field(default_factory=list)
    total_parses: int = 0
    successful_parses: int = 0
    failed_parses: int = 0

    # DETER-AGENT metrics
    lei: float = 0.0  # Lazy Execution Index
    hri: float = 0.0  # Hallucination Rate Index
    cpi: float = 0.0  # Completeness-Precision Index

    # User interaction
    user_messages: int = 0
    assistant_messages: int = 0
    total_tokens_estimated: int = 0


class MetricsCollector:
    """
    Centralized metrics collection for DETER-AGENT compliance.
    
    Implements Constitutional Layer 5 (Incentive/Behavioral Control):
    - Tracks all tool executions
    - Tracks all parse attempts
    - Calculates LEI, HRI, CPI metrics
    - Provides session-level aggregates
    """

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.metrics = SessionMetrics(
            session_id=session_id,
            start_time=time.time()
        )
        self._metrics_dir = Path.home() / ".qwen_logs" / "metrics"
        self._metrics_dir.mkdir(parents=True, exist_ok=True)

    def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        execution_time: float,
        error: Optional[str] = None
    ):
        """Record metrics for a tool call execution."""
        metric = ToolCallMetrics(
            tool_name=tool_name,
            success=success,
            execution_time=execution_time,
            error=error
        )
        self.metrics.tool_calls.append(metric)
        self.metrics.total_tool_calls += 1

        if success:
            self.metrics.successful_tool_calls += 1
        else:
            self.metrics.failed_tool_calls += 1

        # Update HRI (hallucination = invalid tool calls)
        self._update_hri()

    def record_parse_attempt(
        self,
        success: bool,
        strategy_used: str,
        num_tools_found: int,
        parse_time: float,
        had_errors: bool = False
    ):
        """Record metrics for a parse attempt."""
        metric = ParseMetrics(
            success=success,
            strategy_used=strategy_used,
            num_tools_found=num_tools_found,
            parse_time=parse_time,
            had_errors=had_errors
        )
        self.metrics.parse_attempts.append(metric)
        self.metrics.total_parses += 1

        if success:
            self.metrics.successful_parses += 1
        else:
            self.metrics.failed_parses += 1

        # Update HRI (parse failures indicate potential hallucination)
        self._update_hri()

    def record_user_message(self, tokens_estimate: int = 0):
        """Record a user message."""
        self.metrics.user_messages += 1
        self.metrics.total_tokens_estimated += tokens_estimate

    def record_assistant_message(self, tokens_estimate: int = 0):
        """Record an assistant message."""
        self.metrics.assistant_messages += 1
        self.metrics.total_tokens_estimated += tokens_estimate

    def record_lei_event(self, event_type: str, severity: float = 1.0):
        """
        Record a lazy execution event.
        
        Args:
            event_type: Type of lazy behavior (e.g., 'incomplete_impl', 'missing_test')
            severity: How severe (0.0 = minor, 1.0 = major)
        """
        # LEI accumulates - each lazy event adds to the index
        self.metrics.lei += severity

    def set_cpi(self, completeness: float, precision: float):
        """
        Set Completeness-Precision Index.
        
        Args:
            completeness: 0.0-1.0, how complete the implementation is
            precision: 0.0-1.0, how precise/correct the implementation is
        
        CPI = (completeness + precision) / 2
        """
        self.metrics.cpi = (completeness + precision) / 2.0

    def _update_hri(self):
        """
        Update Hallucination Rate Index.
        
        HRI = (failed_tool_calls + failed_parses) / (total_tool_calls + total_parses)
        
        A high HRI indicates the LLM is generating invalid outputs (hallucinating).
        """
        total_operations = self.metrics.total_tool_calls + self.metrics.total_parses
        if total_operations == 0:
            self.metrics.hri = 0.0
            return

        failures = self.metrics.failed_tool_calls + self.metrics.failed_parses
        self.metrics.hri = failures / total_operations

    def track_execution(
        self,
        prompt_tokens: int = 0,
        llm_calls: int = 1,
        tools_executed: int = 1,
        success: bool = True
    ):
        """
        Track execution metrics (test compatibility method).
        
        Args:
            prompt_tokens: Number of tokens in prompt
            llm_calls: Number of LLM calls made
            tools_executed: Number of tools executed
            success: Whether execution was successful
        """
        # Record user message with token count
        self.record_user_message(prompt_tokens)

        # Record tool call
        self.record_tool_call(
            tool_name="generic_tool",
            success=success,
            execution_time=0.1
        )

        # Record LEI event (lazy if multiple LLM calls for simple task)
        if llm_calls > 1:
            self.record_lei_event("multiple_llm_calls", severity=llm_calls * 0.1)

    def calculate_lei(self) -> float:
        """
        Calculate Lazy Execution Index.
        
        Returns:
            LEI value (lower is better, < 1.0 is good)
        """
        return self.metrics.lei

    def get_summary(self) -> Dict:
        """Get a summary of current metrics."""
        return {
            "session_id": self.session_id,
            "duration": time.time() - self.metrics.start_time,
            "tool_calls": {
                "total": self.metrics.total_tool_calls,
                "successful": self.metrics.successful_tool_calls,
                "failed": self.metrics.failed_tool_calls,
                "success_rate": (
                    self.metrics.successful_tool_calls / self.metrics.total_tool_calls
                    if self.metrics.total_tool_calls > 0 else 0.0
                )
            },
            "parse_attempts": {
                "total": self.metrics.total_parses,
                "successful": self.metrics.successful_parses,
                "failed": self.metrics.failed_parses,
                "success_rate": (
                    self.metrics.successful_parses / self.metrics.total_parses
                    if self.metrics.total_parses > 0 else 0.0
                )
            },
            "deter_agent_metrics": {
                "lei": self.metrics.lei,
                "hri": self.metrics.hri,
                "cpi": self.metrics.cpi,
                "constitutional_compliance": self._check_compliance()
            },
            "messages": {
                "user": self.metrics.user_messages,
                "assistant": self.metrics.assistant_messages,
                "total_tokens_estimated": self.metrics.total_tokens_estimated
            }
        }

    def _check_compliance(self) -> Dict[str, bool]:
        """Check if metrics meet Constitutional standards."""
        return {
            "lei_compliant": self.metrics.lei < 1.0,
            "hri_compliant": self.metrics.hri < 0.1,
            "cpi_compliant": self.metrics.cpi > 0.9
        }

    def save_metrics(self):
        """Save metrics to disk for analysis."""
        self.metrics.end_time = time.time()

        metrics_file = self._metrics_dir / f"{self.session_id}.json"

        # Convert to JSON-serializable format
        data = {
            "session_id": self.metrics.session_id,
            "start_time": self.metrics.start_time,
            "end_time": self.metrics.end_time,
            "duration": self.metrics.end_time - self.metrics.start_time,
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "success": tc.success,
                    "execution_time": tc.execution_time,
                    "error": tc.error,
                    "timestamp": tc.timestamp
                }
                for tc in self.metrics.tool_calls
            ],
            "parse_attempts": [
                {
                    "success": pa.success,
                    "strategy": pa.strategy_used,
                    "num_tools": pa.num_tools_found,
                    "parse_time": pa.parse_time,
                    "had_errors": pa.had_errors,
                    "timestamp": pa.timestamp
                }
                for pa in self.metrics.parse_attempts
            ],
            "aggregates": {
                "total_tool_calls": self.metrics.total_tool_calls,
                "successful_tool_calls": self.metrics.successful_tool_calls,
                "failed_tool_calls": self.metrics.failed_tool_calls,
                "total_parses": self.metrics.total_parses,
                "successful_parses": self.metrics.successful_parses,
                "failed_parses": self.metrics.failed_parses,
                "user_messages": self.metrics.user_messages,
                "assistant_messages": self.metrics.assistant_messages,
                "total_tokens_estimated": self.metrics.total_tokens_estimated
            },
            "deter_agent_metrics": {
                "lei": self.metrics.lei,
                "hri": self.metrics.hri,
                "cpi": self.metrics.cpi,
                "compliance": self._check_compliance()
            },
            "summary": self.get_summary()
        }

        with open(metrics_file, 'w') as f:
            json.dump(data, f, indent=2)

        return metrics_file

    @staticmethod
    def load_metrics(session_id: str) -> Optional['MetricsCollector']:
        """Load metrics from a previous session."""
        metrics_dir = Path.home() / ".qwen_logs" / "metrics"
        metrics_file = metrics_dir / f"{session_id}.json"

        if not metrics_file.exists():
            return None

        with open(metrics_file, 'r') as f:
            data = json.load(f)

        collector = MetricsCollector(session_id)
        collector.metrics.start_time = data["start_time"]
        collector.metrics.end_time = data.get("end_time")

        # Restore aggregates
        agg = data["aggregates"]
        collector.metrics.total_tool_calls = agg["total_tool_calls"]
        collector.metrics.successful_tool_calls = agg["successful_tool_calls"]
        collector.metrics.failed_tool_calls = agg["failed_tool_calls"]
        collector.metrics.total_parses = agg["total_parses"]
        collector.metrics.successful_parses = agg["successful_parses"]
        collector.metrics.failed_parses = agg["failed_parses"]
        collector.metrics.user_messages = agg["user_messages"]
        collector.metrics.assistant_messages = agg["assistant_messages"]
        collector.metrics.total_tokens_estimated = agg["total_tokens_estimated"]

        # Restore DETER-AGENT metrics
        dam = data["deter_agent_metrics"]
        collector.metrics.lei = dam["lei"]
        collector.metrics.hri = dam["hri"]
        collector.metrics.cpi = dam["cpi"]

        return collector


class MetricsAggregator:
    """Aggregate metrics across multiple sessions for analysis."""

    @staticmethod
    def get_all_sessions() -> List[str]:
        """Get all session IDs with metrics."""
        metrics_dir = Path.home() / ".qwen_logs" / "metrics"
        if not metrics_dir.exists():
            return []

        return [f.stem for f in metrics_dir.glob("*.json")]

    @staticmethod
    def aggregate_metrics() -> Dict:
        """
        Aggregate metrics across all sessions.
        
        Returns project-wide DETER-AGENT compliance stats.
        """
        sessions = MetricsAggregator.get_all_sessions()

        if not sessions:
            return {
                "total_sessions": 0,
                "error": "No metrics found"
            }

        total_lei = 0.0
        total_hri = 0.0
        total_cpi = 0.0
        total_tool_calls = 0
        total_parses = 0
        compliant_sessions = 0

        for session_id in sessions:
            collector = MetricsCollector.load_metrics(session_id)
            if not collector:
                continue

            total_lei += collector.metrics.lei
            total_hri += collector.metrics.hri
            total_cpi += collector.metrics.cpi
            total_tool_calls += collector.metrics.total_tool_calls
            total_parses += collector.metrics.total_parses

            compliance = collector._check_compliance()
            if all(compliance.values()):
                compliant_sessions += 1

        num_sessions = len(sessions)

        return {
            "total_sessions": num_sessions,
            "compliant_sessions": compliant_sessions,
            "compliance_rate": compliant_sessions / num_sessions,
            "average_metrics": {
                "lei": total_lei / num_sessions,
                "hri": total_hri / num_sessions,
                "cpi": total_cpi / num_sessions
            },
            "totals": {
                "tool_calls": total_tool_calls,
                "parse_attempts": total_parses
            },
            "constitutional_standards": {
                "lei_target": "< 1.0",
                "hri_target": "< 0.1",
                "cpi_target": "> 0.9"
            }
        }
