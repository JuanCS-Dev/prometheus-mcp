"""
Auto-Recovery Loop System

Implements Constitutional Layer 4 (Execution): Verify-Fix-Execute loop
- Detects errors automatically
- Sends error + context to LLM for analysis
- LLM suggests correction
- Re-executes with corrected command
- Max 2 iterations with mandatory diagnosis (Constitutional P6)

Inspired by:
- Claude Code: Self-healing code execution
- GitHub Copilot: Error correction suggestions
- Cursor AI: Context-aware debugging
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for recovery strategies."""
    SYNTAX = "syntax"                    # Syntax errors, parse errors
    PERMISSION = "permission"            # Permission denied, access errors
    NOT_FOUND = "not_found"             # File/resource not found
    COMMAND_NOT_FOUND = "command_not_found"  # Command not installed
    TIMEOUT = "timeout"                  # Timeout errors
    TYPE_ERROR = "type_error"           # Type mismatches
    VALUE_ERROR = "value_error"         # Invalid values
    NETWORK = "network"                  # Network errors
    UNKNOWN = "unknown"                  # Unknown errors


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY_MODIFIED = "retry_modified"    # Retry with modified command
    RETRY_ALTERNATIVE = "retry_alternative"  # Try alternative approach
    SUGGEST_INSTALL = "suggest_install"  # Suggest installing missing tool
    SUGGEST_PERMISSION = "suggest_permission"  # Suggest permission fix
    ESCALATE = "escalate"                # Cannot auto-recover, need human
    ABORT = "abort"                      # Cannot recover, abort


@dataclass
class RecoveryContext:
    """Context for error recovery attempt."""
    attempt_number: int
    max_attempts: int
    error: str
    error_category: ErrorCategory
    failed_tool: str
    failed_args: Dict[str, Any]
    previous_result: Any
    
    # Conversation context
    user_intent: str
    previous_commands: List[Dict[str, Any]]
    
    # Diagnosis
    diagnosis: Optional[str] = None
    suggested_fix: Optional[str] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "attempt": f"{self.attempt_number}/{self.max_attempts}",
            "error": self.error,
            "category": self.error_category.value,
            "tool": self.failed_tool,
            "args": self.failed_args,
            "diagnosis": self.diagnosis,
            "suggested_fix": self.suggested_fix,
            "strategy": self.recovery_strategy.value if self.recovery_strategy else None,
        }


@dataclass
class RecoveryResult:
    """Result of recovery attempt."""
    success: bool
    recovered: bool
    attempts_used: int
    
    # If recovered
    corrected_tool: Optional[str] = None
    corrected_args: Optional[Dict[str, Any]] = None
    result: Any = None
    
    # If failed
    final_error: Optional[str] = None
    escalation_reason: Optional[str] = None
    
    # Learning
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None


class ErrorRecoveryEngine:
    """
    Error recovery engine with LLM-assisted diagnosis.
    
    Constitutional compliance:
    - Layer 4 (Execution): Verify-Fix-Execute loop
    - P6 (Eficiência): Max 2 iterations with mandatory diagnosis
    """
    
    def __init__(
        self,
        llm_client,
        max_attempts: int = 2,  # Constitutional P6
        enable_learning: bool = True,
    ):
        """Initialize recovery engine.
        
        Args:
            llm_client: LLM client for diagnosis
            max_attempts: Maximum recovery attempts (P6: should be 2)
            enable_learning: Enable learning from recovery attempts
        """
        self.llm = llm_client
        self.max_attempts = max_attempts
        self.enable_learning = enable_learning
        
        # Learning database
        self.recovery_history: List[Dict[str, Any]] = []
        self.common_errors: Dict[str, int] = {}
        self.successful_fixes: Dict[str, List[str]] = {}
        
        logger.info(
            f"Initialized ErrorRecoveryEngine "
            f"(max_attempts={max_attempts}, learning={enable_learning})"
        )
    
    def categorize_error(self, error: str) -> ErrorCategory:
        """
        Categorize error for recovery strategy.
        
        Args:
            error: Error message
        
        Returns:
            Error category
        """
        error_lower = error.lower()
        
        # Order matters! Check specific patterns first
        if "command not found" in error_lower or "command not recognized" in error_lower:
            return ErrorCategory.COMMAND_NOT_FOUND
        elif "syntax" in error_lower or "parse" in error_lower:
            return ErrorCategory.SYNTAX
        elif "permission" in error_lower or "denied" in error_lower or "forbidden" in error_lower:
            return ErrorCategory.PERMISSION
        elif "not found" in error_lower or "does not exist" in error_lower or "no such" in error_lower:
            return ErrorCategory.NOT_FOUND
        elif "timeout" in error_lower or "timed out" in error_lower:
            return ErrorCategory.TIMEOUT
        elif "type" in error_lower and "error" in error_lower:
            return ErrorCategory.TYPE_ERROR
        elif "value" in error_lower and "error" in error_lower:
            return ErrorCategory.VALUE_ERROR
        elif "network" in error_lower or "connection" in error_lower:
            return ErrorCategory.NETWORK
        else:
            return ErrorCategory.UNKNOWN
    
    def determine_strategy(
        self,
        category: ErrorCategory,
        context: RecoveryContext
    ) -> RecoveryStrategy:
        """
        Determine recovery strategy based on error category.
        
        Args:
            category: Error category
            context: Recovery context
        
        Returns:
            Recovery strategy
        """
        # Check if we've seen this error before
        if self.enable_learning and context.error in self.successful_fixes:
            return RecoveryStrategy.RETRY_MODIFIED
        
        # Strategy based on category
        if category == ErrorCategory.SYNTAX:
            return RecoveryStrategy.RETRY_MODIFIED
        elif category == ErrorCategory.PERMISSION:
            return RecoveryStrategy.SUGGEST_PERMISSION
        elif category == ErrorCategory.NOT_FOUND:
            return RecoveryStrategy.RETRY_ALTERNATIVE
        elif category == ErrorCategory.COMMAND_NOT_FOUND:
            return RecoveryStrategy.SUGGEST_INSTALL
        elif category == ErrorCategory.TIMEOUT:
            return RecoveryStrategy.RETRY_MODIFIED
        elif category in [ErrorCategory.TYPE_ERROR, ErrorCategory.VALUE_ERROR]:
            return RecoveryStrategy.RETRY_MODIFIED
        elif category == ErrorCategory.NETWORK:
            return RecoveryStrategy.RETRY_ALTERNATIVE
        else:
            # Unknown errors need LLM analysis
            if context.attempt_number < context.max_attempts:
                return RecoveryStrategy.RETRY_MODIFIED
            else:
                return RecoveryStrategy.ESCALATE
    
    async def diagnose_error(
        self,
        context: RecoveryContext
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Use LLM to diagnose error and suggest fix (Constitutional P6: mandatory diagnosis).
        
        Args:
            context: Recovery context
        
        Returns:
            (diagnosis, suggested_correction)
        """
        # Build diagnostic prompt
        prompt = self._build_diagnostic_prompt(context)
        
        try:
            # Get LLM analysis
            response = await self.llm.generate_async(
                messages=[
                    {"role": "system", "content": self._get_diagnostic_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            diagnosis_text = response.get("content", "")
            
            # Parse LLM response for correction
            correction = self._parse_correction(diagnosis_text, context)
            
            return diagnosis_text, correction
            
        except Exception as e:
            logger.error(f"LLM diagnosis failed: {e}")
            return f"LLM diagnosis failed: {e}", None
    
    def _get_diagnostic_system_prompt(self) -> str:
        """Get system prompt for error diagnosis."""
        return """You are an expert debugging assistant. Analyze errors and suggest precise fixes.

When analyzing an error:
1. Identify the ROOT CAUSE (not just symptoms)
2. Suggest a SPECIFIC correction
3. Consider the user's INTENT
4. Provide corrected tool call if possible

Format your response as:
DIAGNOSIS: [root cause analysis]
CORRECTION: [specific fix or alternative approach]
TOOL_CALL: [corrected JSON if applicable]

Be concise and actionable."""
    
    def _build_diagnostic_prompt(self, context: RecoveryContext) -> str:
        """Build diagnostic prompt for LLM."""
        return f"""ERROR ANALYSIS REQUEST:

User Intent: {context.user_intent}

Failed Tool: {context.failed_tool}
Arguments: {context.failed_args}

Error: {context.error}
Category: {context.error_category.value}

Attempt: {context.attempt_number}/{context.max_attempts}

Recent Commands:
{self._format_previous_commands(context.previous_commands)}

Please diagnose the error and suggest a correction."""
    
    def _format_previous_commands(self, commands: List[Dict[str, Any]]) -> str:
        """Format previous commands for context."""
        if not commands:
            return "None"
        
        lines = []
        for i, cmd in enumerate(commands[-3:]):  # Last 3 commands
            lines.append(f"{i+1}. {cmd.get('tool', 'unknown')}({cmd.get('args', {})})")
        
        return "\n".join(lines)
    
    def _parse_correction(
        self,
        diagnosis_text: str,
        context: RecoveryContext
    ) -> Optional[Dict[str, Any]]:
        """
        Parse LLM diagnosis for corrected tool call.
        
        Args:
            diagnosis_text: LLM diagnosis response
            context: Recovery context
        
        Returns:
            Corrected tool call or None
        """
        import json
        import re
        
        # Look for TOOL_CALL: in response
        if "TOOL_CALL:" in diagnosis_text:
            start_pos = diagnosis_text.index("TOOL_CALL:") + len("TOOL_CALL:")
            
            # Try to extract JSON
            try:
                # Find JSON object (handle multi-line)
                json_start = diagnosis_text.index("{", start_pos)
                
                # Find matching closing brace
                brace_count = 0
                json_end = json_start
                for i in range(json_start, len(diagnosis_text)):
                    if diagnosis_text[i] == '{':
                        brace_count += 1
                    elif diagnosis_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                json_str = diagnosis_text[json_start:json_end]
                correction = json.loads(json_str)
                return correction
            except (ValueError, json.JSONDecodeError, IndexError) as e:
                logger.debug(f"Failed to extract JSON correction: {e}")
        
        # Try to find JSON anywhere in response
        try:
            # Look for {... } pattern
            json_match = re.search(r'\{[^}]+\}', diagnosis_text)
            if json_match:
                correction = json.loads(json_match.group())
                # Validate it has tool and args
                if "tool" in correction and "args" in correction:
                    return correction
        except (json.JSONDecodeError, AttributeError) as e:
            logger.debug(f"Failed to parse correction JSON: {e}")
        
        # If no structured correction, return None (need human)
        return None
    
    async def attempt_recovery(
        self,
        context: RecoveryContext
    ) -> RecoveryResult:
        """
        Attempt error recovery (Constitutional Layer 4: Verify-Fix-Execute loop).
        
        Args:
            context: Recovery context
        
        Returns:
            Recovery result
        """
        logger.info(
            f"Starting recovery attempt {context.attempt_number}/{context.max_attempts} "
            f"for {context.failed_tool} (category: {context.error_category.value})"
        )
        
        # Track common errors
        if self.enable_learning:
            self.common_errors[context.error] = self.common_errors.get(context.error, 0) + 1
        
        # Determine strategy
        strategy = self.determine_strategy(context.error_category, context)
        context.recovery_strategy = strategy
        
        logger.info(f"Recovery strategy: {strategy.value}")
        
        # Execute strategy
        if strategy == RecoveryStrategy.ESCALATE:
            return RecoveryResult(
                success=False,
                recovered=False,
                attempts_used=context.attempt_number,
                final_error=context.error,
                escalation_reason="Cannot auto-recover, need human intervention"
            )
        
        elif strategy == RecoveryStrategy.ABORT:
            return RecoveryResult(
                success=False,
                recovered=False,
                attempts_used=context.attempt_number,
                final_error=context.error,
                escalation_reason="Fatal error, cannot recover"
            )
        
        # For other strategies, get LLM diagnosis (Constitutional P6: mandatory)
        diagnosis, correction = await self.diagnose_error(context)
        context.diagnosis = diagnosis
        
        if not correction:
            # LLM couldn't provide correction
            return RecoveryResult(
                success=False,
                recovered=False,
                attempts_used=context.attempt_number,
                final_error=context.error,
                escalation_reason="LLM could not suggest correction"
            )
        
        # We have a correction, mark for retry
        context.suggested_fix = str(correction)
        
        # Return result indicating correction is ready
        # (actual retry will be handled by caller with the corrected tool call)
        return RecoveryResult(
            success=True,
            recovered=False,  # Not yet executed
            attempts_used=context.attempt_number,
            corrected_tool=correction.get("tool"),
            corrected_args=correction.get("args"),
            what_worked="LLM provided correction"
        )
    
    def record_recovery_outcome(
        self,
        context: RecoveryContext,
        result: RecoveryResult,
        final_success: bool
    ):
        """
        Record recovery outcome for learning.
        
        Args:
            context: Recovery context
            result: Recovery result
            final_success: Whether final execution succeeded
        """
        if not self.enable_learning:
            return
        
        # Record to history
        record = {
            "timestamp": time.time(),
            "error": context.error,
            "category": context.error_category.value,
            "strategy": context.recovery_strategy.value if context.recovery_strategy else None,
            "diagnosis": context.diagnosis,
            "suggested_fix": context.suggested_fix,
            "attempts": result.attempts_used,
            "final_success": final_success,
        }
        
        self.recovery_history.append(record)
        
        # If successful, record the fix
        if final_success and context.suggested_fix:
            if context.error not in self.successful_fixes:
                self.successful_fixes[context.error] = []
            
            self.successful_fixes[context.error].append(context.suggested_fix)
            
            logger.info(f"Recorded successful fix for: {context.error[:50]}...")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        if not self.enable_learning:
            return {"learning_disabled": True}
        
        total_attempts = len(self.recovery_history)
        successful_recoveries = sum(1 for r in self.recovery_history if r["final_success"])
        
        return {
            "total_recovery_attempts": total_attempts,
            "successful_recoveries": successful_recoveries,
            "success_rate": successful_recoveries / total_attempts if total_attempts > 0 else 0.0,
            "common_errors": dict(sorted(
                self.common_errors.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),  # Top 10
            "learned_fixes": len(self.successful_fixes),
        }


# Helper function for shell integration
async def create_recovery_context(
    conversation_manager,
    turn,
    failed_tool: str,
    failed_args: Dict[str, Any],
    error: str,
    max_attempts: int = 2
) -> RecoveryContext:
    """
    Create recovery context from conversation turn.
    
    Args:
        conversation_manager: Conversation manager
        turn: Current conversation turn
        failed_tool: Tool that failed
        failed_args: Arguments that failed
        error: Error message
        max_attempts: Max recovery attempts
    
    Returns:
        Recovery context
    """
    from .recovery import ErrorCategory, ErrorRecoveryEngine
    
    # Categorize error
    engine = ErrorRecoveryEngine(llm_client=None)  # Temp for categorization
    category = engine.categorize_error(error)
    
    # Get previous commands
    previous_cmds = []
    for prev_turn in conversation_manager.turns[-3:]:  # Last 3 turns
        for tool_result in prev_turn.tool_results:
            previous_cmds.append({
                "tool": tool_result["tool"],
                "args": tool_result["args"],
                "success": tool_result["success"]
            })
    
    return RecoveryContext(
        attempt_number=1,
        max_attempts=max_attempts,
        error=error,
        error_category=category,
        failed_tool=failed_tool,
        failed_args=failed_args,
        previous_result=None,
        user_intent=turn.user_input,
        previous_commands=previous_cmds,
    )
