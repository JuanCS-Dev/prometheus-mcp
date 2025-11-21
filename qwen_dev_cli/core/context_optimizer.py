"""
Auto-Context Optimization Engine.

Monitors context window usage and automatically optimizes to stay
within limits while maintaining relevant information.

Boris Cherny Implementation - Week 4 Day 1 Phase 2
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
from pathlib import Path


class ContentType(Enum):
    """Type of content in context."""
    FILE_CONTENT = "file_content"
    TOOL_RESULT = "tool_result"
    CONVERSATION = "conversation"
    CODE_SNIPPET = "code_snippet"
    ERROR_MESSAGE = "error_message"


@dataclass
class ContextItem:
    """Item in the context window."""
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


class ContextOptimizer:
    """
    Automatically optimizes context window usage.
    
    Features:
    - Token tracking
    - LRU-based eviction
    - Relevance scoring
    - Auto-pruning when >80% full
    - Content compression
    """
    
    def __init__(self, max_tokens: int = 100_000):
        """
        Initialize optimizer.
        
        Args:
            max_tokens: Maximum context window size
        """
        self.max_tokens = max_tokens
        self.items: Dict[str, ContextItem] = {}
        self.total_tokens = 0
        
        # Thresholds
        self.warning_threshold = 0.8  # Warn at 80%
        self.critical_threshold = 0.9  # Auto-prune at 90%
        
        # Statistics
        self.optimizations_performed = 0
        self.total_tokens_freed = 0
    
    def add_item(
        self, 
        item_id: str,
        content: str,
        content_type: ContentType,
        token_count: int,
        pinned: bool = False
    ) -> bool:
        """
        Add item to context.
        
        Args:
            item_id: Unique identifier
            content: Content to add
            content_type: Type of content
            token_count: Number of tokens
            pinned: If True, won't be auto-removed
            
        Returns:
            True if added, False if rejected
        """
        # Check if adding would exceed limit
        if self.total_tokens + token_count > self.max_tokens:
            # Try auto-optimization first
            if not pinned:
                self.auto_optimize(tokens_needed=token_count)
        
        # Re-check after optimization
        if self.total_tokens + token_count > self.max_tokens:
            return False
        
        # Add or update item
        if item_id in self.items:
            # Update existing
            old_item = self.items[item_id]
            self.total_tokens -= old_item.token_count
        
        item = ContextItem(
            id=item_id,
            content=content,
            content_type=content_type,
            token_count=token_count,
            timestamp=time.time(),
            pinned=pinned
        )
        
        self.items[item_id] = item
        self.total_tokens += token_count
        
        return True
    
    def access_item(self, item_id: str):
        """Mark item as accessed (for LRU)."""
        if item_id in self.items:
            item = self.items[item_id]
            item.access_count += 1
            item.last_accessed = time.time()
    
    def remove_item(self, item_id: str) -> bool:
        """Remove item from context."""
        if item_id in self.items:
            item = self.items.pop(item_id)
            self.total_tokens -= item.token_count
            return True
        return False
    
    def get_usage_percent(self) -> float:
        """Get current usage as percentage."""
        return (self.total_tokens / self.max_tokens) * 100
    
    def should_optimize(self) -> bool:
        """Check if optimization is needed."""
        usage = self.get_usage_percent()
        return usage >= (self.warning_threshold * 100)
    
    def must_optimize(self) -> bool:
        """Check if optimization is critical."""
        usage = self.get_usage_percent()
        return usage >= (self.critical_threshold * 100)
    
    def calculate_relevance(self, item: ContextItem) -> float:
        """
        Calculate relevance score for item.
        
        Factors:
        - Recency (when last accessed)
        - Frequency (access count)
        - Type (conversation > tool_result > file_content)
        - Pinned status
        """
        if item.pinned:
            return 1.0
        
        now = time.time()
        age_seconds = now - item.last_accessed
        
        # Recency score (exponential decay)
        recency_score = 1.0 / (1.0 + age_seconds / 300)  # Half-life 5 min
        
        # Frequency score (logarithmic)
        frequency_score = min(1.0, (item.access_count + 1) / 10)
        
        # Type score
        type_scores = {
            ContentType.CONVERSATION: 1.0,
            ContentType.ERROR_MESSAGE: 0.9,
            ContentType.CODE_SNIPPET: 0.8,
            ContentType.TOOL_RESULT: 0.7,
            ContentType.FILE_CONTENT: 0.6
        }
        type_score = type_scores.get(item.content_type, 0.5)
        
        # Weighted combination
        relevance = (
            0.4 * recency_score +
            0.3 * frequency_score +
            0.3 * type_score
        )
        
        return relevance
    
    def auto_optimize(
        self, 
        tokens_needed: int = 0,
        target_usage: float = 0.7
    ) -> OptimizationMetrics:
        """
        Automatically optimize context.
        
        Args:
            tokens_needed: Additional tokens needed
            target_usage: Target usage percentage (0.0-1.0)
            
        Returns:
            Metrics from optimization
        """
        start_time = time.time()
        
        items_before = len(self.items)
        tokens_before = self.total_tokens
        
        # Target tokens to keep
        target_tokens = int(self.max_tokens * target_usage) - tokens_needed
        
        # Calculate relevance for all items
        scored_items = []
        for item in self.items.values():
            if not item.pinned:
                relevance = self.calculate_relevance(item)
                scored_items.append((relevance, item))
        
        # Sort by relevance (lowest first = candidates for removal)
        scored_items.sort(key=lambda x: x[0])
        
        # Remove items until we reach target
        removed_ids = []
        tokens_freed = 0
        
        for relevance, item in scored_items:
            if self.total_tokens <= target_tokens:
                break
            
            removed_ids.append(item.id)
            tokens_freed += item.token_count
            self.total_tokens -= item.token_count
        
        # Actually remove items
        for item_id in removed_ids:
            self.items.pop(item_id, None)
        
        # Update statistics
        self.optimizations_performed += 1
        self.total_tokens_freed += tokens_freed
        
        duration_ms = (time.time() - start_time) * 1000
        
        return OptimizationMetrics(
            items_before=items_before,
            items_after=len(self.items),
            tokens_before=tokens_before,
            tokens_after=self.total_tokens,
            items_removed=len(removed_ids),
            tokens_freed=tokens_freed,
            duration_ms=duration_ms
        )
    
    def compress_content(self, content: str, target_length: int) -> str:
        """
        Compress content to target length.
        
        Strategy:
        - Keep first and last portions (context)
        - Truncate middle with ellipsis
        """
        if len(content) <= target_length:
            return content
        
        # Keep 40% from start, 40% from end
        keep_start = int(target_length * 0.4)
        keep_end = int(target_length * 0.4)
        
        start = content[:keep_start]
        end = content[-keep_end:]
        
        return f"{start}\n... [truncated] ...\n{end}"
    
    def get_stats(self) -> Dict:
        """Get optimizer statistics."""
        return {
            'total_items': len(self.items),
            'total_tokens': self.total_tokens,
            'max_tokens': self.max_tokens,
            'usage_percent': self.get_usage_percent(),
            'pinned_items': sum(1 for item in self.items.values() if item.pinned),
            'optimizations_performed': self.optimizations_performed,
            'total_tokens_freed': self.total_tokens_freed,
            'by_type': self._get_type_distribution()
        }
    
    def _get_type_distribution(self) -> Dict[str, int]:
        """Get token distribution by content type."""
        distribution = {}
        for item in self.items.values():
            type_name = item.content_type.value
            distribution[type_name] = distribution.get(type_name, 0) + item.token_count
        return distribution
    
    def get_recommendations(self) -> List[str]:
        """Get optimization recommendations."""
        recommendations = []
        
        usage = self.get_usage_percent()
        
        if usage >= 90:
            recommendations.append("CRITICAL: Context >90% full - immediate optimization needed")
        elif usage >= 80:
            recommendations.append("WARNING: Context >80% full - consider optimizing")
        
        # Check for old items
        now = time.time()
        old_items = [
            item for item in self.items.values()
            if (now - item.last_accessed) > 600 and not item.pinned
        ]
        
        if old_items:
            recommendations.append(
                f"Found {len(old_items)} items not accessed in 10+ minutes"
            )
        
        # Check for low-value items
        if self.items:
            low_relevance = [
                item for item in self.items.values()
                if self.calculate_relevance(item) < 0.3 and not item.pinned
            ]
            
            if low_relevance:
                recommendations.append(
                    f"Found {len(low_relevance)} low-relevance items that could be removed"
                )
        
        return recommendations
