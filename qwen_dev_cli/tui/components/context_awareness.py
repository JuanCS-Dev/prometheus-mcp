"""
Context Awareness System - DAY 8 Phase 4
Smart context management and optimization

Research-Driven Features (Nov 2025):
1. Intelligent file relevance scoring (Cursor/Cody inspiration)
2. Auto-context optimization (token efficiency)
3. Workspace intelligence (semantic understanding)
4. Smart suggestions based on context

Constitutional Compliance:
- P1 (Completude): Full context state tracking
- P2 (Validação): Validates context relevance
- P3 (Ceticismo): Questions unnecessary context
- P6 (Eficiência): Minimizes token usage (<10% overhead)
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import re
import time
from collections import defaultdict, deque

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn, TaskID
from rich.live import Live


# Week 4 Day 1 Consolidation: ContentType from ContextOptimizer
class ContentType(Enum):
    """Type of content in context."""
    FILE_CONTENT = "file_content"
    TOOL_RESULT = "tool_result"
    CONVERSATION = "conversation"
    CODE_SNIPPET = "code_snippet"
    ERROR_MESSAGE = "error_message"


# Week 4 Day 1 Consolidation: ContextItem from ContextOptimizer
@dataclass
class ContextItem:
    """Item in the context window with LRU tracking."""
    id: str
    content: str
    content_type: ContentType
    token_count: int
    timestamp: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    relevance_score: float = 1.0
    pinned: bool = False


@dataclass
class OptimizationMetrics:
    """Metrics from optimization operation."""
    items_before: int
    items_after: int
    tokens_before: int
    tokens_after: int
    items_removed: int
    tokens_freed: int
    duration_ms: float


@dataclass
class FileRelevance:
    """File relevance scoring for context optimization"""
    path: str
    score: float  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)
    last_accessed: Optional[datetime] = None
    token_count: int = 0
    dependencies: Set[str] = field(default_factory=set)
    
    @property
    def is_relevant(self) -> bool:
        """Check if file meets relevance threshold"""
        return self.score >= 0.5
    
    @property
    def priority(self) -> str:
        """Get priority level"""
        if self.score >= 0.8:
            return "HIGH"
        elif self.score >= 0.5:
            return "MEDIUM"
        else:
            return "LOW"


@dataclass
class TokenUsageSnapshot:
    """Snapshot of token usage at a point in time"""
    timestamp: datetime
    total_tokens: int
    input_tokens: int
    output_tokens: int
    cost_estimate_usd: float = 0.0


@dataclass
class ContextWindow:
    """Represents current context window state (Enhanced DAY 8 Phase 4)"""
    total_tokens: int
    max_tokens: int
    files: Dict[str, FileRelevance] = field(default_factory=dict)
    auto_added: Set[str] = field(default_factory=set)
    user_pinned: Set[str] = field(default_factory=set)
    
    # NEW: Real-time token tracking (DAY 8 Phase 4)
    current_input_tokens: int = 0
    current_output_tokens: int = 0
    streaming_tokens: int = 0  # Tokens being streamed right now
    usage_history: deque = field(default_factory=lambda: deque(maxlen=100))  # Last 100 snapshots
    
    @property
    def utilization(self) -> float:
        """Context window utilization (0.0 to 1.0)"""
        return self.total_tokens / self.max_tokens if self.max_tokens > 0 else 0.0
    
    @property
    def available_tokens(self) -> int:
        """Tokens available for new context"""
        return max(0, self.max_tokens - self.total_tokens)
    
    @property
    def is_critical(self) -> bool:
        """Check if context is critically full (>90%)"""
        return self.utilization > 0.9
    
    @property
    def is_warning(self) -> bool:
        """Check if context is in warning zone (>80%)"""
        return self.utilization > 0.8
    
    def add_token_snapshot(
        self,
        input_tokens: int,
        output_tokens: int,
        cost_estimate: float = 0.0
    ) -> None:
        """Add token usage snapshot (DAY 8 Phase 4)"""
        snapshot = TokenUsageSnapshot(
            timestamp=datetime.now(),
            total_tokens=input_tokens + output_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_estimate_usd=cost_estimate
        )
        self.usage_history.append(snapshot)
        self.current_input_tokens = input_tokens
        self.current_output_tokens = output_tokens
        # Update total tokens
        self.total_tokens = input_tokens + output_tokens
    
    def update_tokens(self, input_tokens: int, output_tokens: int, cost: float = 0.0) -> None:
        """Alias for add_token_snapshot for easier testing"""
        self.add_token_snapshot(input_tokens, output_tokens, cost)


class ContextAwarenessEngine:
    """
    Intelligent context management system
    
    Features (Research-Driven):
    - File relevance scoring (Cursor/Cody algorithms)
    - Auto-optimization (removes low-value context)
    - Dependency tracking (includes related files)
    - Smart suggestions (predicts needed files)
    - Token budget management
    
    Constitutional Alignment:
    - P6 (Eficiência): Minimizes token waste
    - P3 (Ceticismo): Questions every context addition
    - P2 (Validação): Validates relevance before adding
    """
    
    def __init__(
        self,
        max_context_tokens: int = 100_000,
        console: Optional[Console] = None
    ):
        self.max_context_tokens = max_context_tokens
        self.console = console or Console()
        
        # Context tracking
        self.window = ContextWindow(
            total_tokens=0,
            max_tokens=max_context_tokens
        )
        
        # Week 4 Day 1: Enhanced with ContextOptimizer features
        self.items: Dict[str, ContextItem] = {}  # LRU tracking
        self.optimizations_performed = 0
        self.total_tokens_freed = 0
        
        # Thresholds (from ContextOptimizer)
        self.warning_threshold = 0.8
        self.critical_threshold = 0.9
        
        # Relevance tracking
        self.access_history: Dict[str, List[datetime]] = defaultdict(list)
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.semantic_cache: Dict[str, Set[str]] = {}  # File -> keywords
        
        # Scoring weights (research-optimized)
        self.weights = {
            "recent_access": 0.3,
            "frequency": 0.2,
            "dependencies": 0.25,
            "semantic": 0.15,
            "user_pinned": 0.1
        }
        
    def score_file_relevance(
        self,
        file_path: str,
        current_task: Optional[str] = None,
        recent_files: Optional[List[str]] = None
    ) -> FileRelevance:
        """
        Score file relevance using multi-factor analysis
        
        Factors (research-based):
        1. Recent access (recency bias - Cursor inspiration)
        2. Access frequency (popularity)
        3. Dependency connections (import/require analysis)
        4. Semantic similarity (keyword matching)
        5. User pinning (explicit importance)
        
        Args:
            file_path: Path to score
            current_task: Current user task description
            recent_files: Recently accessed files
            
        Returns:
            FileRelevance score object
        """
        scores = {}
        reasons = []
        
        # Factor 1: Recent Access (exponential decay)
        recent_score = self._score_recent_access(file_path)
        scores["recent_access"] = recent_score
        if recent_score > 0.5:
            reasons.append("Recently accessed")
            
        # Factor 2: Access Frequency
        freq_score = self._score_frequency(file_path)
        scores["frequency"] = freq_score
        if freq_score > 0.7:
            reasons.append("Frequently accessed")
            
        # Factor 3: Dependencies
        dep_score = self._score_dependencies(file_path, recent_files or [])
        scores["dependencies"] = dep_score
        if dep_score > 0.5:
            reasons.append("Connected to active files")
            
        # Factor 4: Semantic Similarity
        if current_task:
            semantic_score = self._score_semantic(file_path, current_task)
            scores["semantic"] = semantic_score
            if semantic_score > 0.6:
                reasons.append("Matches current task")
        else:
            scores["semantic"] = 0.0
            
        # Factor 5: User Pinned
        if file_path in self.window.user_pinned:
            scores["user_pinned"] = 1.0
            reasons.append("User pinned")
        else:
            scores["user_pinned"] = 0.0
            
        # Weighted sum
        final_score = sum(
            scores[factor] * self.weights[factor]
            for factor in scores
        )
        
        return FileRelevance(
            path=file_path,
            score=final_score,
            reasons=reasons,
            last_accessed=self.access_history[file_path][-1] if self.access_history[file_path] else None,
            token_count=self._estimate_tokens(file_path),
            dependencies=self.dependency_graph.get(file_path, set())
        )
    
    def optimize_context(
        self,
        target_utilization: float = 0.8,
        preserve_pinned: bool = True
    ) -> Dict[str, Any]:
        """
        Auto-optimize context window
        
        Removes low-relevance files to stay within target utilization.
        
        Args:
            target_utilization: Target context utilization (0.0-1.0)
            preserve_pinned: Keep user-pinned files
            
        Returns:
            Optimization report
        """
        if self.window.utilization <= target_utilization:
            return {
                "action": "none",
                "reason": "Context utilization acceptable",
                "removed": []
            }
            
        # Score all files
        scored_files = [
            (path, self.score_file_relevance(path))
            for path in self.window.files
        ]
        
        # Sort by score (ascending - remove lowest first)
        scored_files.sort(key=lambda x: x[1].score)
        
        removed = []
        target_tokens = int(self.max_context_tokens * target_utilization)
        
        for path, relevance in scored_files:
            # Stop if target reached
            if self.window.total_tokens <= target_tokens:
                break
                
            # Skip pinned files
            if preserve_pinned and path in self.window.user_pinned:
                continue
                
            # Remove file
            if path in self.window.files:
                del self.window.files[path]
                self.window.total_tokens -= relevance.token_count
                self.window.auto_added.discard(path)
                removed.append((path, relevance.score))
                
        return {
            "action": "optimized",
            "removed": removed,
            "tokens_freed": sum(r[1] for r in removed),
            "new_utilization": self.window.utilization
        }
    
    def suggest_context(
        self,
        current_task: str,
        max_suggestions: int = 5
    ) -> List[FileRelevance]:
        """
        Suggest relevant files for current task
        
        Uses:
        - Semantic analysis
        - Dependency graph
        - Historical patterns
        
        Args:
            current_task: User's current task description
            max_suggestions: Maximum suggestions to return
            
        Returns:
            List of FileRelevance objects (sorted by score)
        """
        # Get all project files (simplified - would scan workspace)
        candidate_files = self._get_candidate_files()
        
        # Score each candidate
        suggestions = []
        for file_path in candidate_files:
            if file_path not in self.window.files:  # Only suggest new files
                relevance = self.score_file_relevance(
                    file_path,
                    current_task=current_task,
                    recent_files=list(self.window.files.keys())
                )
                
                if relevance.is_relevant:
                    suggestions.append(relevance)
                    
        # Sort by score (descending)
        suggestions.sort(key=lambda x: x.score, reverse=True)
        
        return suggestions[:max_suggestions]
    
    def add_file_to_context(
        self,
        file_path: str,
        pinned: bool = False,
        auto_include_deps: bool = True
    ) -> bool:
        """
        Add file to context window
        
        Args:
            file_path: File to add
            pinned: Mark as user-pinned
            auto_include_deps: Automatically include dependencies
            
        Returns:
            Success status
        """
        # Check if file exists
        if not Path(file_path).exists():
            return False
            
        # Estimate tokens
        token_count = self._estimate_tokens(file_path)
        
        # Check if fits
        if token_count > self.window.available_tokens:
            # Try auto-optimization
            opt_result = self.optimize_context(target_utilization=0.7)
            if token_count > self.window.available_tokens:
                return False  # Still doesn't fit
                
        # Add file
        relevance = self.score_file_relevance(file_path)
        relevance.token_count = token_count
        
        self.window.files[file_path] = relevance
        self.window.total_tokens += token_count
        
        if pinned:
            self.window.user_pinned.add(file_path)
        else:
            self.window.auto_added.add(file_path)
            
        # Track access
        self.access_history[file_path].append(datetime.now())
        
        # Auto-include dependencies
        if auto_include_deps:
            deps = self._extract_dependencies(file_path)
            self.dependency_graph[file_path] = deps
            
            for dep in deps:
                if dep not in self.window.files and Path(dep).exists():
                    dep_tokens = self._estimate_tokens(dep)
                    if dep_tokens <= self.window.available_tokens:
                        self.add_file_to_context(dep, pinned=False, auto_include_deps=False)
                        
        return True
    
    def render_context_panel(self) -> Panel:
        """Render context awareness panel"""
        table = Table(title="🧠 Context Window", show_header=True)
        table.add_column("File", style="cyan", width=40)
        table.add_column("Relevance", width=10)
        table.add_column("Tokens", justify="right", width=10)
        table.add_column("Status", width=10)
        
        for path, relevance in self.window.files.items():
            # Status icons
            status = []
            if path in self.window.user_pinned:
                status.append("📌")
            if path in self.window.auto_added:
                status.append("🤖")
                
            # Relevance indicator
            if relevance.priority == "HIGH":
                rel_icon = "🟢"
            elif relevance.priority == "MEDIUM":
                rel_icon = "🟡"
            else:
                rel_icon = "🔴"
                
            table.add_row(
                Path(path).name,
                f"{rel_icon} {relevance.score:.2f}",
                f"{relevance.token_count:,}",
                " ".join(status)
            )
            
        # Summary
        summary = Text()
        summary.append(f"\n📊 Utilization: ", style="bold")
        summary.append(f"{self.window.utilization*100:.1f}%", 
                      style="red" if self.window.is_critical else "green")
        summary.append(f" ({self.window.total_tokens:,}/{self.max_context_tokens:,} tokens)\n",
                      style="dim")
        
        return Panel(
            table,
            subtitle=summary,
            border_style="cyan"
        )
    
    def render_token_usage_realtime(self) -> Panel:
        """
        Render real-time token usage panel (DAY 8 Phase 4)
        
        Shows:
        - Current input/output tokens
        - Streaming token counter
        - Usage trend (last 10 interactions)
        - Cost estimate
        """
        content = Text()
        
        # Current session stats
        content.append("📊 Current Session\n", style="bold cyan")
        content.append(f"  Input:  {self.window.current_input_tokens:,} tokens\n", style="green")
        content.append(f"  Output: {self.window.current_output_tokens:,} tokens\n", style="yellow")
        
        if self.window.streaming_tokens > 0:
            content.append(f"  🔄 Streaming: {self.window.streaming_tokens:,} tokens\n", style="magenta bold")
        
        total_session = self.window.current_input_tokens + self.window.current_output_tokens
        content.append(f"  Total:  {total_session:,} tokens\n\n", style="bold")
        
        # Usage trend (last 10 snapshots)
        if self.window.usage_history:
            content.append("📈 Recent Trend\n", style="bold cyan")
            
            recent = list(self.window.usage_history)[-10:]
            for i, snapshot in enumerate(recent, 1):
                time_str = snapshot.timestamp.strftime("%H:%M:%S")
                content.append(f"  {time_str} | ", style="dim")
                content.append(f"↑{snapshot.input_tokens:,} ", style="green")
                content.append(f"↓{snapshot.output_tokens:,}", style="yellow")
                
                if snapshot.cost_estimate_usd > 0:
                    content.append(f" | ${snapshot.cost_estimate_usd:.4f}", style="magenta")
                
                content.append("\n")
            
            # Calculate cumulative cost
            total_cost = sum(s.cost_estimate_usd for s in self.window.usage_history)
            if total_cost > 0:
                content.append(f"\n💰 Cumulative Cost: ${total_cost:.4f}\n", style="bold magenta")
        
        # Warning if approaching limit
        if self.window.is_critical:
            content.append("\n⚠️  CRITICAL: Context >90% full!\n", style="bold red")
            content.append("    Consider optimizing context.\n", style="red")
        elif self.window.is_warning:
            content.append("\n⚠️  WARNING: Context >80% full\n", style="bold yellow")
        
        return Panel(
            content,
            title="🔢 Token Usage (Real-Time)",
            border_style="magenta"
        )
    
    def update_streaming_tokens(self, delta: int) -> None:
        """
        Update streaming token counter (DAY 8 Phase 4)
        Called during LLM streaming to show real-time progress
        
        Args:
            delta: Token count delta (positive = adding, negative = finalizing)
        """
        self.window.streaming_tokens = max(0, self.window.streaming_tokens + delta)
    
    def finalize_streaming_session(
        self,
        final_input_tokens: int,
        final_output_tokens: int,
        cost_estimate: float = 0.0
    ) -> None:
        """
        Finalize streaming session and record snapshot (DAY 8 Phase 4)
        
        Args:
            final_input_tokens: Total input tokens for this interaction
            final_output_tokens: Total output tokens for this interaction
            cost_estimate: Estimated cost in USD
        """
        self.window.streaming_tokens = 0
        self.window.add_token_snapshot(
            input_tokens=final_input_tokens,
            output_tokens=final_output_tokens,
            cost_estimate=cost_estimate
        )
    
    # Helper methods
    
    def _score_recent_access(self, file_path: str) -> float:
        """Score based on recent access (exponential decay)"""
        if file_path not in self.access_history:
            return 0.0
            
        last_access = self.access_history[file_path][-1]
        time_since = (datetime.now() - last_access).total_seconds()
        
        # Exponential decay: e^(-t/3600) (half-life = 1 hour)
        import math
        return math.exp(-time_since / 3600)
    
    def _score_frequency(self, file_path: str) -> float:
        """Score based on access frequency"""
        if file_path not in self.access_history:
            return 0.0
            
        # Count accesses in last 24h
        cutoff = datetime.now() - timedelta(hours=24)
        recent_accesses = [
            t for t in self.access_history[file_path]
            if t > cutoff
        ]
        
        # Normalize (assume max 20 accesses = 1.0)
        return min(1.0, len(recent_accesses) / 20.0)
    
    def _score_dependencies(self, file_path: str, recent_files: List[str]) -> float:
        """Score based on dependency connections"""
        if file_path not in self.dependency_graph:
            return 0.0
            
        deps = self.dependency_graph[file_path]
        
        # Count how many recent files are connected
        connected = sum(1 for f in recent_files if f in deps)
        
        return min(1.0, connected / max(1, len(recent_files)))
    
    def _score_semantic(self, file_path: str, task: str) -> float:
        """Score based on semantic similarity to task"""
        if file_path not in self.semantic_cache:
            self.semantic_cache[file_path] = self._extract_keywords(file_path)
            
        file_keywords = self.semantic_cache[file_path]
        task_keywords = set(re.findall(r'\w+', task.lower()))
        
        # Jaccard similarity
        intersection = len(file_keywords & task_keywords)
        union = len(file_keywords | task_keywords)
        
        return intersection / union if union > 0 else 0.0
    
    def _estimate_tokens(self, file_path: str) -> int:
        """Estimate token count for file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                # Rough estimate: 1 token ≈ 4 chars
                return len(content) // 4
        except Exception:
            return 0
    
    def _extract_dependencies(self, file_path: str) -> Set[str]:
        """Extract file dependencies (imports, requires)"""
        deps = set()
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
                # Python imports
                for match in re.finditer(r'from\s+(\S+)\s+import', content):
                    deps.add(match.group(1).replace('.', '/') + '.py')
                    
                for match in re.finditer(r'import\s+(\S+)', content):
                    deps.add(match.group(1).replace('.', '/') + '.py')
                    
        except Exception:
            pass
            
        return deps
    
    def _extract_keywords(self, file_path: str) -> Set[str]:
        """Extract semantic keywords from file"""
        keywords = set()
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                # Extract function/class names
                for match in re.finditer(r'(?:def|class)\s+(\w+)', content):
                    keywords.add(match.group(1).lower())
        except Exception:
            pass
            
        return keywords
    
    def _get_candidate_files(self) -> List[str]:
        """Get candidate files for suggestions (simplified)"""
        # In real implementation, would scan workspace
        return []


# Example usage
if __name__ == "__main__":
    console = Console()
    engine = ContextAwarenessEngine(max_context_tokens=100_000, console=console)
    
    # Simulate adding files
    engine.add_file_to_context("src/main.py", pinned=True)
    engine.add_file_to_context("src/utils.py")
    engine.add_file_to_context("src/models.py")
    
    # Render context panel
    console.print(engine.render_context_panel())
    
    # Suggest context for task
    suggestions = engine.suggest_context("implement authentication system")
    console.print("\n🤖 Suggested Files:")
    for suggestion in suggestions:
        console.print(f"  • {suggestion.path} (score: {suggestion.score:.2f})")

    # ========================================================================
    # WEEK 4 DAY 1 CONSOLIDATION: Methods from ContextOptimizer
    # ========================================================================
    
    def add_item(self, item_id: str, content: str, content_type, token_count: int, pinned: bool = False) -> bool:
        """Add item with LRU tracking."""
        if self.window.total_tokens + token_count > self.max_context_tokens:
            if not pinned:
                self.auto_optimize(tokens_needed=token_count)
        if self.window.total_tokens + token_count > self.max_context_tokens:
            return False
        if item_id in self.items:
            old_item = self.items[item_id]
            self.window.total_tokens -= old_item.token_count
        item = ContextItem(id=item_id, content=content, content_type=content_type, token_count=token_count, timestamp=time.time(), pinned=pinned)
        self.items[item_id] = item
        self.window.total_tokens += token_count
        return True
    
    def auto_optimize(self, tokens_needed: int = 0, target_usage: float = 0.7):
        """Auto-optimize using LRU."""
        start = time.time()
        items_before = len(self.items)
        tokens_before = self.window.total_tokens
        target_tokens = int(self.max_context_tokens * target_usage) - tokens_needed
        scored = [(self.calculate_item_relevance(item), item) for item in self.items.values() if not item.pinned]
        scored.sort(key=lambda x: x[0])
        removed, freed = [], 0
        for _, item in scored:
            if self.window.total_tokens <= target_tokens: break
            removed.append(item.id)
            freed += item.token_count
            self.window.total_tokens -= item.token_count
        for rid in removed: self.items.pop(rid, None)
        self.optimizations_performed += 1
        self.total_tokens_freed += freed
        return OptimizationMetrics(items_before, len(self.items), tokens_before, self.window.total_tokens, len(removed), freed, (time.time() - start) * 1000)
    
    def calculate_item_relevance(self, item) -> float:
        """Calculate relevance for LRU."""
        if item.pinned: return 1.0
        age = time.time() - item.last_accessed
        recency = 1.0 / (1.0 + age / 300)
        frequency = min(1.0, (item.access_count + 1) / 10)
        return 0.7 * recency + 0.3 * frequency
    
    def get_optimization_stats(self) -> dict:
        """Get stats."""
        return {'total_items': len(self.items), 'total_tokens': self.window.total_tokens, 'max_tokens': self.max_context_tokens, 'usage_percent': self.window.utilization * 100, 'pinned_items': sum(1 for i in self.items.values() if i.pinned), 'optimizations_performed': self.optimizations_performed, 'total_tokens_freed': self.total_tokens_freed}
    
    def get_optimization_recommendations(self) -> list:
        """Get recommendations."""
        recs = []
        usage = self.window.utilization * 100
        if usage >= 90: recs.append("CRITICAL: Context >90% full")
        elif usage >= 80: recs.append("WARNING: Context >80% full")
        return recs
