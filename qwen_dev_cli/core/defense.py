"""
Prompt Injection Defense & Auto-Critique Module

Implements Constitutional Layer 1 (Strategic Control) defense mechanisms:
- Prompt injection detection
- Malicious pattern filtering
- Input sanitization
- Auto-critique for tool call validation

Layer 2 (Cognitive Control) auto-critique:
- Pre-execution validation
- Post-execution review
- Error pattern detection
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class InjectionDetection:
    """Result of prompt injection detection."""
    is_malicious: bool
    confidence: float  # 0.0-1.0
    patterns_found: List[str]
    sanitized_input: str
    reason: Optional[str] = None


class PromptInjectionDefender:
    """
    Detect and prevent prompt injection attacks.
    
    Constitutional Article VI requirement:
    "Defesa Contra Prompt Injection"
    """
    
    # Known injection patterns
    INJECTION_PATTERNS = [
        # System override attempts
        (r"ignore\s+(all|previous|above)\s+(instructions|prompts|rules)", 0.9),
        (r"ignore.*instructions.*delete", 0.95),  # High confidence for combined pattern
        (r"disregard\s+(previous|all|system)", 0.9),
        (r"forget\s+(everything|all|your)", 0.8),
        
        # Role confusion attacks
        (r"you\s+are\s+now\s+a\s+different", 0.85),
        (r"act\s+as\s+(a\s+)?(different|new)\s+(ai|assistant|system)", 0.85),
        (r"pretend\s+(you|to)\s+(are|be)", 0.7),
        
        # Instruction manipulation
        (r"new\s+(instruction|directive|rule):", 0.8),
        (r"override\s+(mode|setting|instruction)", 0.9),
        (r"system\s+message:", 0.8),
        (r"admin\s+(command|mode|override)", 0.9),
        
        # Prompt leaking attempts
        (r"show\s+(me\s+)?(your|the)\s+(prompt|system\s+message|instructions)", 0.8),
        (r"what\s+(are|is)\s+your\s+(instructions|system\s+prompt)", 0.8),
        (r"repeat\s+(your|the)\s+instructions", 0.8),
        
        # Delimiter attacks
        (r"```[\s\S]*system", 0.7),
        (r"<\|im_start\|>system", 0.9),
        (r"<\|system\|>", 0.9),
        
        # Jailbreak attempts
        (r"dan\s+mode", 0.9),  # Do Anything Now
        (r"developer\s+mode", 0.85),
        (r"evil\s+(mode|assistant)", 0.9),
        
        # Code injection in prompts
        (r"eval\(", 0.8),
        (r"exec\(", 0.8),
        (r"__import__", 0.85),
    ]
    
    # Suspicious patterns (lower confidence)
    SUSPICIOUS_PATTERNS = [
        (r"ignore", 0.3),
        (r"bypass", 0.4),
        (r"hack", 0.4),
        (r"jailbreak", 0.6),
        (r"exploit", 0.5),
    ]
    
    def detect(self, user_input: str) -> InjectionDetection:
        """
        Detect prompt injection attempts.
        
        Returns InjectionDetection with:
        - is_malicious: True if high-confidence injection detected
        - confidence: 0.0-1.0 confidence score
        - patterns_found: List of matched patterns
        - sanitized_input: Cleaned version of input
        """
        patterns_found = []
        max_confidence = 0.0
        
        # Check against injection patterns
        for pattern, confidence in self.INJECTION_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                patterns_found.append(pattern)
                max_confidence = max(max_confidence, confidence)
        
        # Check suspicious patterns (add to confidence)
        for pattern, confidence in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                patterns_found.append(pattern)
                max_confidence = min(1.0, max_confidence + confidence * 0.5)
        
        # Threshold for malicious classification
        is_malicious = max_confidence >= 0.75
        
        # Sanitize input
        sanitized = self._sanitize(user_input)
        
        reason = None
        if is_malicious:
            reason = f"High confidence ({max_confidence:.2f}) injection detected: {patterns_found[:3]}"
        
        return InjectionDetection(
            is_malicious=is_malicious,
            confidence=max_confidence,
            patterns_found=patterns_found,
            sanitized_input=sanitized,
            reason=reason
        )
    
    def _sanitize(self, text: str) -> str:
        """
        Sanitize input by removing/escaping dangerous patterns.
        
        This is a conservative approach - we don't modify the input heavily,
        just escape obvious attempts.
        """
        sanitized = text
        
        # Remove system-like delimiters
        sanitized = re.sub(r"<\|.*?\|>", "", sanitized)
        
        # Escape code blocks that might contain injections
        sanitized = re.sub(r"```system", "```text", sanitized, flags=re.IGNORECASE)
        
        # Remove obvious override attempts
        sanitized = re.sub(
            r"(ignore|disregard|forget)\s+(previous|all|above)\s+(instructions|prompts)",
            "[FILTERED]",
            sanitized,
            flags=re.IGNORECASE
        )
        
        return sanitized


class AutoCritic:
    """
    Auto-critique mechanism for tool call validation.
    
    Constitutional Article VII requirement:
    "Protocolo de Auto-Crítica Obrigatória"
    
    Validates tool calls before execution and reviews results after.
    """
    
    def __init__(self):
        self.error_patterns = []
    
    def pre_execution_critique(
        self,
        tool_calls: List[Dict],
        context: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Critique tool calls BEFORE execution.
        
        Returns:
            (should_execute, warnings)
        """
        warnings = []
        
        # Check for empty tool calls
        if not tool_calls:
            warnings.append("No tool calls generated - possible hallucination or unclear prompt")
        
        # Check for duplicate tool calls
        tool_names = [tc.get("name") for tc in tool_calls]
        if len(tool_names) != len(set(tool_names)):
            warnings.append("Duplicate tool calls detected - potential confusion")
        
        # Check for dangerous patterns
        for tc in tool_calls:
            name = tc.get("name", "")
            args = tc.get("args", {})
            
            # Check for destructive operations without confirmation
            if name in ["delete_file", "rm"] and not context.get("confirmed"):
                warnings.append(f"Destructive operation '{name}' without confirmation")
            
            # Check for overly broad operations
            if name == "bash_command":
                cmd = args.get("command", "")
                if "rm -rf /" in cmd or "sudo" in cmd:
                    warnings.append(f"Dangerous bash command detected: {cmd}")
                    return False, warnings  # Block execution
        
        # Check for missing required context
        if context.get("cwd") is None:
            warnings.append("No working directory context - operations may fail")
        
        should_execute = len([w for w in warnings if "block" in w.lower()]) == 0
        
        return should_execute, warnings
    
    def post_execution_critique(
        self,
        tool_calls: List[Dict],
        results: List[Dict]
    ) -> List[str]:
        """
        Critique tool execution results AFTER execution.
        
        Identifies potential issues:
        - Failed operations
        - Incomplete implementations
        - Error patterns
        """
        issues = []
        
        for i, (tc, result) in enumerate(zip(tool_calls, results)):
            name = tc.get("name", "unknown")
            success = result.get("success", False)
            error = result.get("error")
            
            if not success:
                issues.append(f"Tool '{name}' failed: {error}")
                
                # Track error patterns
                self.error_patterns.append({
                    "tool": name,
                    "error": error,
                    "args": tc.get("args")
                })
            
            # Check for lazy execution indicators
            if "TODO" in str(result) or "NotImplemented" in str(result):
                issues.append(f"Lazy execution detected in '{name}': TODO/NotImplemented found")
            
            # Check for empty/minimal results
            output = result.get("output", "")
            if success and len(output) < 10 and name not in ["mkdir", "touch", "cd"]:
                issues.append(f"Suspiciously short output from '{name}': {len(output)} chars")
        
        return issues
    
    def suggest_improvements(self) -> List[str]:
        """
        Suggest improvements based on error patterns.
        
        This implements basic learning from failures.
        """
        if not self.error_patterns:
            return ["No errors detected - system performing well"]
        
        suggestions = []
        
        # Group errors by tool
        tool_errors = {}
        for ep in self.error_patterns:
            tool = ep["tool"]
            if tool not in tool_errors:
                tool_errors[tool] = []
            tool_errors[tool].append(ep["error"])
        
        # Suggest fixes for common patterns
        for tool, errors in tool_errors.items():
            if len(errors) > 3:
                suggestions.append(
                    f"Tool '{tool}' has {len(errors)} failures - consider reviewing implementation"
                )
            
            # Check for permission errors
            permission_errors = [e for e in errors if e and "permission" in e.lower()]
            if permission_errors:
                suggestions.append(
                    f"Tool '{tool}' has permission errors - check file access patterns"
                )
        
        return suggestions


class ContextCompactor:
    """
    Smart context compaction for Layer 3 (State Management).
    
    Constitutional Article VIII requirement:
    "Compactação Ativa de Contexto"
    
    Reduces context window usage while preserving critical information.
    """
    
    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count.
        
        Rough estimate: 1 token ≈ 4 characters for English text.
        This is conservative (actual is closer to 3-3.5 for GPT models).
        """
        return len(text) // 4
    
    def compact(
        self,
        messages: List[Dict],
        preserve_system: bool = True
    ) -> List[Dict]:
        """
        Compact message history to fit within max_tokens.
        
        Strategy:
        1. Always preserve system message (if preserve_system=True)
        2. Always preserve last user message
        3. Summarize middle messages
        4. Keep most recent messages at full detail
        """
        if not messages:
            return messages
        
        total_tokens = sum(self.estimate_tokens(str(m)) for m in messages)
        
        if total_tokens <= self.max_tokens:
            return messages  # No compaction needed
        
        compacted = []
        
        # Preserve system message
        if preserve_system and messages[0].get("role") == "system":
            compacted.append(messages[0])
            messages = messages[1:]
        
        # Preserve last user message
        last_user_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                last_user_idx = i
                break
        
        if last_user_idx is not None:
            last_user = messages[last_user_idx]
            messages = messages[:last_user_idx] + messages[last_user_idx + 1:]
        else:
            last_user = None
        
        # Keep recent messages (last 5)
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        old_messages = messages[:-5] if len(messages) > 5 else []
        
        # Summarize old messages
        if old_messages:
            summary = self._summarize_messages(old_messages)
            compacted.append({
                "role": "system",
                "content": f"[Previous conversation summary: {summary}]"
            })
        
        # Add recent messages
        compacted.extend(recent_messages)
        
        # Add back last user message
        if last_user:
            compacted.append(last_user)
        
        return compacted
    
    def _summarize_messages(self, messages: List[Dict]) -> str:
        """Summarize a list of messages into a brief description."""
        # Count message types
        user_msgs = sum(1 for m in messages if m.get("role") == "user")
        assistant_msgs = sum(1 for m in messages if m.get("role") == "assistant")
        
        # Extract key topics (simple keyword extraction)
        all_text = " ".join(m.get("content", "") for m in messages)
        words = all_text.lower().split()
        
        # Common technical keywords
        keywords = []
        for word in ["file", "code", "test", "error", "fix", "implement", "create"]:
            if word in words:
                keywords.append(word)
        
        summary = f"{user_msgs} user messages, {assistant_msgs} assistant responses"
        if keywords:
            summary += f" about: {', '.join(keywords[:3])}"
        
        return summary
