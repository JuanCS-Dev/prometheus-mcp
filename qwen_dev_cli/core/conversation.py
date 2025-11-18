"""
Multi-Turn Conversation Manager with State Machine

Implements Constitutional Layer 2 (Deliberation) & Layer 3 (State Management):
- Conversation state machine (IDLE → THINKING → EXECUTING → WAITING → ERROR)
- Context window management (sliding window, token counting)
- Tool result feedback loop (previous commands/results/errors → LLM)
- Error correction mechanism (auto-retry with context)
- Session continuity (resume interrupted sessions)

Inspired by:
- Claude Code: Multi-turn context preservation
- GitHub Copilot: Conversation state management
- Cursor AI: Context-aware error recovery
"""

import time
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Conversation states (Constitutional Layer 3 requirement)."""
    IDLE = "idle"               # Waiting for user input
    THINKING = "thinking"       # LLM processing request
    EXECUTING = "executing"     # Executing tool calls
    WAITING = "waiting"         # Waiting for tool results
    ERROR = "error"             # Error occurred, needs recovery
    RECOVERING = "recovering"   # Attempting auto-recovery


@dataclass
class ConversationTurn:
    """Single conversation turn with context."""
    turn_id: int
    timestamp: float
    state: ConversationState
    
    # User interaction
    user_input: str
    user_intent: Optional[str] = None
    
    # LLM response
    llm_response: Optional[str] = None
    llm_reasoning: Optional[str] = None  # Chain-of-thought
    
    # Tool execution
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Error tracking
    error: Optional[str] = None
    error_category: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    
    # Metadata
    tokens_used: int = 0
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "state": self.state.value,
            "user_input": self.user_input,
            "user_intent": self.user_intent,
            "llm_response": self.llm_response,
            "llm_reasoning": self.llm_reasoning,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "error": self.error,
            "error_category": self.error_category,
            "recovery_attempted": self.recovery_attempted,
            "recovery_successful": self.recovery_successful,
            "tokens_used": self.tokens_used,
            "execution_time": self.execution_time,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Create from dictionary."""
        data['state'] = ConversationState(data['state'])
        return cls(**data)


class ContextWindow:
    """
    Context window manager with sliding window and token counting.
    
    Constitutional Layer 3 (State Management) requirement:
    - Compactar contexto quando >60% da janela
    - Sliding window (últimas N mensagens)
    - Token counting para evitar overflow
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,  # Conservative limit
        soft_limit: float = 0.6,  # 60% triggers compaction
        hard_limit: float = 0.8,  # 80% forces aggressive compaction
    ):
        """Initialize context window manager.
        
        Args:
            max_tokens: Maximum tokens in context window
            soft_limit: Trigger compaction at this % (0.6 = 60%)
            hard_limit: Force aggressive compaction at this % (0.8 = 80%)
        """
        # EDGE CASE FIX: Enforce minimum viable context size
        if max_tokens > 0 and max_tokens < 100:
            logger.warning(f"max_tokens={max_tokens} too small, setting to 100")
            max_tokens = 100
        
        self.max_tokens = max_tokens
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit
        self.current_tokens = 0
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation).
        
        Rule of thumb: ~4 characters per token for English
        More accurate would use tiktoken, but this avoids dependency.
        """
        return len(text) // 4 + len(text.split())  # Hybrid estimate
    
    def get_usage_percentage(self) -> float:
        """Get current context usage as percentage (0.0-1.0)."""
        if self.max_tokens == 0:  # BUG FIX #1: Handle zero
            return 0.0
        return self.current_tokens / self.max_tokens
    
    def needs_compaction(self) -> Tuple[bool, str]:
        """
        Check if context needs compaction.
        
        Returns:
            (needs_compaction, reason)
        """
        usage = self.get_usage_percentage()
        
        if usage >= self.hard_limit:
            return True, f"hard_limit_reached ({usage:.0%})"
        elif usage >= self.soft_limit:
            return True, f"soft_limit_reached ({usage:.0%})"
        
        return False, "ok"
    
    def compact(
        self,
        turns: List[ConversationTurn],
        strategy: str = "sliding_window"
    ) -> List[ConversationTurn]:
        """
        Compact conversation history.
        
        Args:
            turns: Full conversation history
            strategy: Compaction strategy
                - "sliding_window": Keep last N turns
                - "summarize": Summarize old turns (requires LLM integration)
                - "aggressive": Keep only last 2 turns + errors
        
        Returns:
            Compacted turns list
        """
        if strategy == "sliding_window":
            # Keep last 10 turns by default
            return turns[-10:]
        
        elif strategy == "aggressive":
            # Keep only last 2 turns + any error turns
            recent = turns[-2:]
            error_turns = [t for t in turns[:-2] if t.error]
            return error_turns[-3:] + recent  # Max 5 turns total
        
        else:
            # Default: sliding window
            return turns[-10:]


class ConversationManager:
    """
    Manages multi-turn conversations with state machine and context.
    
    Constitutional compliance:
    - Layer 2 (Deliberation): Auto-critique + error correction
    - Layer 3 (State Management): Context compaction + sliding window
    """
    
    def __init__(
        self,
        session_id: str,
        max_context_tokens: int = 4000,
        enable_auto_recovery: bool = True,
        max_recovery_attempts: int = 2,  # Constitutional P6: max 2 iterations
        max_turns: int = 1000,  # BUG FIX #6: Prevent memory leak
    ):
        """Initialize conversation manager.
        
        Args:
            session_id: Unique session identifier
            max_context_tokens: Maximum tokens in context window
            enable_auto_recovery: Enable automatic error recovery
            max_recovery_attempts: Max retry attempts (Constitutional P6)
            max_turns: Maximum turns to keep (prevents unbounded growth)
        """
        self.session_id = session_id
        self.enable_auto_recovery = enable_auto_recovery
        self.max_recovery_attempts = max_recovery_attempts
        self.max_turns = max_turns
        
        # State
        self.current_state = ConversationState.IDLE
        self.turns: List[ConversationTurn] = []
        self.turn_counter = 0
        
        # Context window management
        self.context_window = ContextWindow(max_tokens=max_context_tokens)
        
        # Metadata
        self.created_at = time.time()
        self.last_activity = time.time()
        
        logger.info(
            f"Initialized ConversationManager for session {session_id} "
            f"(max_tokens={max_context_tokens}, auto_recovery={enable_auto_recovery})"
        )
    
    def transition_state(self, new_state: ConversationState, reason: str = ""):
        """Transition to new state with logging."""
        old_state = self.current_state
        self.current_state = new_state
        self.last_activity = time.time()
        
        logger.info(
            f"State transition: {old_state.value} → {new_state.value} "
            f"({reason if reason else 'no reason'})"
        )
    
    def start_turn(self, user_input: str) -> ConversationTurn:
        """
        Start new conversation turn.
        
        Args:
            user_input: User's input text
        
        Returns:
            New ConversationTurn instance
        """
        self.turn_counter += 1
        self.transition_state(ConversationState.THINKING, "user_input_received")
        
        # EDGE CASE FIX: Estimate input size and protect against extreme overflow
        estimated_tokens = self.context_window.estimate_tokens(user_input)
        
        # BUG FIX #3: Check if context would overflow
        needs_compact, reason = self.context_window.needs_compaction()
        if needs_compact:
            logger.warning(f"Context window compaction needed: {reason}")
            self._compact_context()  # Method decides strategy internally
        
        # EDGE CASE FIX #2: If single turn exceeds context, compact preemptively
        if self.context_window.max_tokens > 0 and estimated_tokens > self.context_window.max_tokens * 0.5:
            logger.warning(
                f"Large input ({estimated_tokens} tokens > 50% of {self.context_window.max_tokens}), "
                "preemptive compaction"
            )
            self._compact_context()
        
        turn = ConversationTurn(
            turn_id=self.turn_counter,
            timestamp=time.time(),
            state=ConversationState.THINKING,
            user_input=user_input,
        )
        
        self.turns.append(turn)
        
        # BUG FIX #6: Enforce max_turns to prevent memory leak
        if len(self.turns) > self.max_turns:
            removed = len(self.turns) - self.max_turns
            self.turns = self.turns[-self.max_turns:]
            logger.warning(f"Removed {removed} old turns (max_turns={self.max_turns})")
        
        # Check if context needs compaction
        needs_compact, reason = self.context_window.needs_compaction()
        if needs_compact:
            logger.warning(f"Context window compaction needed: {reason}")
            self._compact_context()
        
        return turn
    
    def add_llm_response(
        self,
        turn: ConversationTurn,
        response: str,
        reasoning: Optional[str] = None,
        tokens_used: int = 0
    ):
        """
        Add LLM response to current turn.
        
        Args:
            turn: Current conversation turn
            response: LLM response text
            reasoning: Chain-of-thought reasoning (if available)
            tokens_used: Estimated tokens used
        """
        turn.llm_response = response
        turn.llm_reasoning = reasoning
        turn.tokens_used = tokens_used
        
        # Update context window token count
        self.context_window.current_tokens += tokens_used
        
        self.transition_state(ConversationState.EXECUTING, "llm_response_received")
    
    def add_tool_calls(self, turn: ConversationTurn, tool_calls: List[Dict[str, Any]]):
        """Add tool calls to current turn."""
        turn.tool_calls = tool_calls
        self.transition_state(ConversationState.EXECUTING, f"{len(tool_calls)}_tools_to_execute")
    
    def add_tool_result(
        self,
        turn: ConversationTurn,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        success: bool,
        error: Optional[str] = None
    ):
        """
        Add tool execution result.
        
        Args:
            turn: Current conversation turn
            tool_name: Tool that was executed
            args: Tool arguments
            result: Tool result
            success: Whether execution succeeded
            error: Error message if failed
        """
        tool_result = {
            "tool": tool_name,
            "args": args,
            "result": str(result) if result else None,
            "success": success,
            "error": error,
            "timestamp": time.time(),
        }
        
        turn.tool_results.append(tool_result)
        
        if not success and error:
            # Error occurred
            turn.error = error
            turn.error_category = self._categorize_error(error)
            self.transition_state(ConversationState.ERROR, f"tool_error: {tool_name}")
            
            # Attempt auto-recovery if enabled
            if self.enable_auto_recovery and not turn.recovery_attempted:
                self._attempt_recovery(turn)
        
        # Check if all tools completed
        if len(turn.tool_results) == len(turn.tool_calls):
            if not turn.error:
                self.transition_state(ConversationState.IDLE, "all_tools_completed_successfully")
            # If error, state is already ERROR
    
    def _categorize_error(self, error: str) -> str:
        """
        Categorize error for recovery strategy.
        
        Returns:
            Error category: syntax, permission, not_found, command_not_found, timeout, unknown
        """
        error_lower = error.lower()
        
        if "syntax" in error_lower or "parse" in error_lower:
            return "syntax"
        elif "permission" in error_lower or "denied" in error_lower:
            return "permission"
        elif "command not found" in error_lower:  # Check this BEFORE "not found"
            return "command_not_found"
        elif "not found" in error_lower or "does not exist" in error_lower:
            return "not_found"
        elif "timeout" in error_lower:
            return "timeout"
        else:
            return "unknown"
    
    def _attempt_recovery(self, turn: ConversationTurn):
        """
        Attempt automatic error recovery (Constitutional Layer 2 requirement).
        
        Args:
            turn: Turn with error to recover from
        """
        turn.recovery_attempted = True
        self.transition_state(ConversationState.RECOVERING, f"attempt_1/{self.max_recovery_attempts}")
        
        logger.info(
            f"Attempting auto-recovery for turn {turn.turn_id} "
            f"(category: {turn.error_category})"
        )
        
        # Recovery will be handled by external system (shell/LLM)
        # This just marks the turn for recovery
        # Actual recovery: send error + context back to LLM for retry
    
    def _compact_context(self):
        """
        Compact context window (Constitutional Layer 3 requirement).
        
        Implements progressive disclosure:
        - Soft limit (60%): Sliding window (keep last 10 turns)
        - Hard limit (80%): Aggressive (keep last 2 + errors)
        """
        usage = self.context_window.get_usage_percentage()
        
        if usage >= self.context_window.hard_limit:
            # Aggressive compaction
            logger.warning(f"Hard limit reached ({usage:.0%}), aggressive compaction")
            self.turns = self.context_window.compact(self.turns, strategy="aggressive")
        else:
            # Soft compaction
            logger.info(f"Soft limit reached ({usage:.0%}), sliding window compaction")
            self.turns = self.context_window.compact(self.turns, strategy="sliding_window")
        
        # Recalculate token count
        self.context_window.current_tokens = sum(
            self.context_window.estimate_tokens(turn.user_input) +
            self.context_window.estimate_tokens(turn.llm_response or "")
            for turn in self.turns
        )
        
        logger.info(
            f"Context compacted: {len(self.turns)} turns remaining, "
            f"{self.context_window.current_tokens} tokens ({usage:.0%} → {self.context_window.get_usage_percentage():.0%})"
        )
    
    def get_context_for_llm(self, include_last_n: int = 5) -> List[Dict[str, Any]]:
        """
        Get context for LLM (Constitutional Layer 3: Tool result feedback loop).
        
        Returns last N turns formatted for LLM consumption.
        
        Args:
            include_last_n: Number of recent turns to include
        
        Returns:
            List of message dictionaries for LLM
        """
        messages = []
        recent_turns = self.turns[-include_last_n:] if include_last_n > 0 else self.turns
        
        for turn in recent_turns:
            # User message
            messages.append({
                "role": "user",
                "content": turn.user_input
            })
            
            # Assistant response (if available)
            if turn.llm_response:
                messages.append({
                    "role": "assistant",
                    "content": turn.llm_response
                })
            
            # Tool results (if available) - Constitutional Layer 2: feedback loop
            if turn.tool_results:
                tool_summary = self._format_tool_results(turn.tool_results)
                messages.append({
                    "role": "system",
                    "content": f"[Tool Results]\n{tool_summary}"
                })
            
            # Error feedback (if available) - Constitutional Layer 2: error correction
            if turn.error:
                messages.append({
                    "role": "system",
                    "content": f"[Error Occurred]\nCategory: {turn.error_category}\nDetails: {turn.error}"
                })
        
        return messages
    
    def _format_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """Format tool results for LLM context."""
        lines = []
        for result in tool_results:
            status = "✓" if result["success"] else "✗"
            tool = result["tool"]
            
            if result["success"]:
                lines.append(f"{status} {tool}: {result['result']}")
            else:
                lines.append(f"{status} {tool}: ERROR - {result['error']}")
        
        return "\n".join(lines)
    
    def get_recovery_context(self, turn: ConversationTurn) -> Dict[str, Any]:
        """
        Get context for error recovery (Constitutional Layer 2 requirement).
        
        Returns:
            Dictionary with recovery context
        """
        return {
            "turn_id": turn.turn_id,
            "user_input": turn.user_input,
            "error": turn.error,
            "error_category": turn.error_category,
            "failed_tool_calls": [
                tc for tc in turn.tool_results if not tc["success"]
            ],
            "previous_turns": [
                {
                    "user_input": t.user_input,
                    "success": not bool(t.error)
                }
                for t in self.turns[-3:-1]  # Last 2 turns before error
            ],
            "recovery_attempt": 1,
            "max_attempts": self.max_recovery_attempts,
        }
    
    def save_session(self, path: Optional[Path] = None) -> Path:
        """
        Save conversation to disk for session continuity.
        
        Args:
            path: Optional save path (defaults to ~/.qwen_sessions/)
        
        Returns:
            Path where session was saved
        """
        if path is None:
            sessions_dir = Path.home() / ".qwen_sessions"
            sessions_dir.mkdir(exist_ok=True)
            path = sessions_dir / f"{self.session_id}.json"
        
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "current_state": self.current_state.value,
            "turn_counter": self.turn_counter,
            "turns": [turn.to_dict() for turn in self.turns],
            "context_tokens": self.context_window.current_tokens,
            "max_tokens": self.context_window.max_tokens,
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved conversation session to {path}")
        return path
    
    @classmethod
    def restore_session(cls, path: Path) -> 'ConversationManager':
        """
        Restore conversation from disk (session continuity).
        
        Args:
            path: Path to saved session
        
        Returns:
            Restored ConversationManager instance
        """
        with open(path, 'r') as f:
            data = json.load(f)
        
        manager = cls(
            session_id=data["session_id"],
            max_context_tokens=data["max_tokens"],
        )
        
        manager.created_at = data["created_at"]
        manager.last_activity = data["last_activity"]
        manager.current_state = ConversationState(data["current_state"])
        manager.turn_counter = data["turn_counter"]
        manager.turns = [ConversationTurn.from_dict(t) for t in data["turns"]]
        manager.context_window.current_tokens = data["context_tokens"]
        
        logger.info(f"Restored conversation session from {path} ({len(manager.turns)} turns)")
        return manager
    
    def get_summary(self) -> Dict[str, Any]:
        """Get conversation summary for monitoring."""
        duration = time.time() - self.created_at
        
        total_tool_calls = sum(len(turn.tool_calls) for turn in self.turns)
        successful_tools = sum(
            sum(1 for r in turn.tool_results if r["success"])
            for turn in self.turns
        )
        failed_tools = total_tool_calls - successful_tools
        
        error_turns = [t for t in self.turns if t.error]
        recovered_turns = [t for t in error_turns if t.recovery_successful]
        
        return {
            "session_id": self.session_id,
            "state": self.current_state.value,
            "duration_seconds": duration,
            "total_turns": len(self.turns),
            "total_tool_calls": total_tool_calls,
            "successful_tools": successful_tools,
            "failed_tools": failed_tools,
            "error_turns": len(error_turns),
            "recovered_turns": len(recovered_turns),
            "recovery_rate": len(recovered_turns) / len(error_turns) if error_turns else 0.0,
            "context_tokens": self.context_window.current_tokens,
            "context_usage": f"{self.context_window.get_usage_percentage():.0%}",
        }
