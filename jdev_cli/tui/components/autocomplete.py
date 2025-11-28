"""Context-aware autocomplete component."""
import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class CompletionType(Enum):
    """Types of completions."""
    COMMAND = "command"
    FILE = "file"
    TOOL = "tool"
    VARIABLE = "variable"
    SNIPPET = "snippet"
    HISTORICAL = "historical"


@dataclass
class CompletionItem:
    """Single completion item."""
    text: str
    display: str
    type: CompletionType
    description: Optional[str] = None
    score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ContextAwareCompleter(Completer):
    """
    Context-aware autocomplete with semantic understanding.
    
    Features:
    - File path completion with fuzzy matching
    - Tool name completion with descriptions
    - Command history with smart ranking
    - Code snippets based on context
    - Variable/symbol completion from codebase
    """

    def __init__(
        self,
        tools_registry: Optional[Any] = None,
        indexer: Optional[Any] = None,
        recent_tracker: Optional[Any] = None
    ):
        self.tools_registry = tools_registry
        self.indexer = indexer
        self.recent_tracker = recent_tracker
        self._cache: Dict[str, List[CompletionItem]] = {}

    def get_completions(self, document: Document, complete_event):
        """Get completions for current document."""
        text = document.text_before_cursor
        word = document.get_word_before_cursor()

        if not word:
            return

        # Get all completion sources
        completions = []
        completions.extend(self._get_tool_completions(word))
        completions.extend(self._get_file_completions(word))
        completions.extend(self._get_historical_completions(word))
        completions.extend(self._get_symbol_completions(word))

        # Sort by score (highest first)
        completions.sort(key=lambda x: x.score, reverse=True)

        # Convert to prompt_toolkit Completion objects
        for item in completions:
            yield Completion(
                text=item.text,
                start_position=-len(word),
                display=item.display,
                display_meta=item.description or ""
            )

    def _get_tool_completions(self, prefix: str) -> List[CompletionItem]:
        """Get tool name completions."""
        if not self.tools_registry:
            return []

        completions = []
        try:
            # Use get_all() instead of list_tools() (correct API)
            all_tools = self.tools_registry.get_all()

            for tool_name, tool in all_tools.items():
                if tool_name.startswith(prefix.lower()):
                    score = self._calculate_prefix_score(prefix, tool_name)

                    completions.append(CompletionItem(
                        text=tool_name,
                        display=f"🔧 {tool_name}",
                        type=CompletionType.TOOL,
                        description=getattr(tool, 'description', None),
                        score=score + 10.0,  # Boost tool completions
                        metadata={"tool": tool_name}
                    ))
        except Exception as e:
            logger.debug(f"Failed to get tool completions: {e}")

        return completions

    def _get_file_completions(self, prefix: str) -> List[CompletionItem]:
        """Get file path completions."""
        if not self.recent_tracker:
            return []

        completions = []
        recent_files = self.recent_tracker.get_recent_files(limit=50)

        for file_path in recent_files:
            file_name = file_path.split('/')[-1]
            if prefix.lower() in file_name.lower():
                score = self._calculate_fuzzy_score(prefix, file_name)

                completions.append(CompletionItem(
                    text=file_path,
                    display=f"📄 {file_name}",
                    type=CompletionType.FILE,
                    description=file_path,
                    score=score + 5.0,  # Moderate boost
                    metadata={"path": file_path}
                ))

        return completions

    def _get_historical_completions(self, prefix: str) -> List[CompletionItem]:
        """Get completions from command history."""
        # History integration deferred - requires prompt_toolkit setup
        return []

    def _get_symbol_completions(self, prefix: str) -> List[CompletionItem]:
        """Get symbol completions from indexed codebase."""
        if not self.indexer:
            return []

        completions = []

        # Search for symbols (functions, classes, etc.)
        try:
            results = self.indexer.search_symbols(prefix, limit=10)
            for result in results:
                score = result.get('score', 0.0)
                symbol_name = result.get('symbol', '')
                symbol_type = result.get('type', 'unknown')

                icon = self._get_symbol_icon(symbol_type)

                completions.append(CompletionItem(
                    text=symbol_name,
                    display=f"{icon} {symbol_name}",
                    type=CompletionType.VARIABLE,
                    description=f"{symbol_type} in {result.get('file', '')}",
                    score=score,
                    metadata=result
                ))
        except Exception as e:
            logger.debug(f"Failed to get semantic completions: {e}")

        return completions

    def _calculate_prefix_score(self, prefix: str, target: str) -> float:
        """Calculate score for prefix match."""
        if not prefix:
            return 0.0

        prefix = prefix.lower()
        target = target.lower()

        if target.startswith(prefix):
            # Exact prefix match gets highest score
            return 100.0 * (len(prefix) / len(target))

        return 0.0

    def _calculate_fuzzy_score(self, query: str, target: str) -> float:
        """Calculate fuzzy match score."""
        if not query:
            return 0.0

        query = query.lower()
        target = target.lower()

        # Exact match
        if query == target:
            return 100.0

        # Prefix match
        if target.startswith(query):
            return 90.0 * (len(query) / len(target))

        # Substring match
        if query in target:
            return 70.0 * (len(query) / len(target))

        # Character-by-character fuzzy match
        score = 0.0
        query_idx = 0
        for char in target:
            if query_idx < len(query) and char == query[query_idx]:
                score += 1.0
                query_idx += 1

        if query_idx == len(query):
            return 50.0 * (score / len(target))

        return 0.0

    def _get_symbol_icon(self, symbol_type: str) -> str:
        """Get icon for symbol type."""
        icons = {
            'function': '⚡',
            'class': '📦',
            'method': '🔹',
            'variable': '📌',
            'constant': '🔒',
            'module': '📚',
            'unknown': '❓'
        }
        return icons.get(symbol_type.lower(), '❓')


class SmartAutoSuggest:
    """
    Smart auto-suggest based on context and history.
    
    Provides inline suggestions as you type, similar to:
    - Fish shell
    - GitHub Copilot
    - Cursor AI
    """

    def __init__(
        self,
        history: Optional[Any] = None,
        indexer: Optional[Any] = None
    ):
        self.history = history
        self.indexer = indexer
        self._suggestion_cache: Dict[str, str] = {}

    def get_suggestion(self, text: str, context: Optional[Dict] = None) -> Optional[str]:
        """Get suggestion for current text."""
        if not text:
            return None

        # Check cache first
        if text in self._suggestion_cache:
            return self._suggestion_cache[text]

        # Try history-based suggestion
        history_suggestion = self._get_history_suggestion(text)
        if history_suggestion:
            self._suggestion_cache[text] = history_suggestion
            return history_suggestion

        # Try context-based suggestion
        if context:
            context_suggestion = self._get_context_suggestion(text, context)
            if context_suggestion:
                self._suggestion_cache[text] = context_suggestion
                return context_suggestion

        return None

    def _get_history_suggestion(self, text: str) -> Optional[str]:
        """Get suggestion from history."""
        if not self.history:
            return None

        # Find most recent command that starts with text
        for item in reversed(list(self.history.load_history_strings())):
            if item.startswith(text) and len(item) > len(text):
                return item[len(text):]

        return None

    def _get_context_suggestion(self, text: str, context: Dict) -> Optional[str]:
        """Get suggestion based on context."""
        # ML suggestions deferred - requires training data
        return None

    def clear_cache(self):
        """Clear suggestion cache."""
        self._suggestion_cache.clear()


def create_completer(
    tools_registry: Optional[Any] = None,
    indexer: Optional[Any] = None,
    recent_tracker: Optional[Any] = None
) -> ContextAwareCompleter:
    """Create configured autocompleter."""
    return ContextAwareCompleter(
        tools_registry=tools_registry,
        indexer=indexer,
        recent_tracker=recent_tracker
    )
