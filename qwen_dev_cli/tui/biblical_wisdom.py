"""
Biblical Wisdom for Loading States.

Handpicked verses about building, purpose, persistence, truth, and the Way.
These appear during "thinking" moments to inspire and ground the user.

Philosophy:
- Faith meets craft
- Purpose-driven development
- Every waiting moment is a meditation

Created: 2025-11-18 20:24 UTC
"""

import random
from typing import List, Dict


class BiblicalWisdom:
    """Biblical quotes for loading/thinking states."""
    
    # Categorized verses for context-aware display
    VERSES = {
        'building': [
            "Unless the LORD builds the house, the builders labor in vain. — Psalm 127:1",
            "By wisdom a house is built, and through understanding it is established. — Proverbs 24:3",
            "So built we the wall; and all the wall was joined together. — Nehemiah 4:6",
            "For we are God's fellow workers; you are God's field, God's building. — 1 Corinthians 3:9",
            "Every house is built by someone, but God is the builder of everything. — Hebrews 3:4",
        ],
        
        'purpose': [
            "For I know the plans I have for you, declares the LORD. — Jeremiah 29:11",
            "The heart of man plans his way, but the LORD establishes his steps. — Proverbs 16:9",
            "Many are the plans in a person's heart, but it is the LORD's purpose that prevails. — Proverbs 19:21",
            "Commit your work to the LORD, and your plans will be established. — Proverbs 16:3",
            "To man belong the plans of the heart, but from the LORD comes the reply. — Proverbs 16:1",
        ],
        
        'persistence': [
            "Let us not become weary in doing good, for at the proper time we will reap. — Galatians 6:9",
            "I press on toward the goal to win the prize. — Philippians 3:14",
            "Be steadfast, immovable, always abounding in the work of the Lord. — 1 Corinthians 15:58",
            "Run in such a way as to get the prize. — 1 Corinthians 9:24",
            "Finishing is better than starting. Patience is better than pride. — Ecclesiastes 7:8",
        ],
        
        'truth': [
            "Then you will know the truth, and the truth will set you free. — John 8:32",
            "The LORD is near to all who call on him in truth. — Psalm 145:18",
            "Buy the truth and do not sell it; get wisdom, discipline and understanding. — Proverbs 23:23",
            "Speak the truth in love. — Ephesians 4:15",
            "The sum of your word is truth. — Psalm 119:160",
        ],
        
        'the_way': [
            "I am the way and the truth and the life. — John 14:6",
            "Trust in the LORD with all your heart and lean not on your own understanding. — Proverbs 3:5-6",
            "Show me your ways, LORD, teach me your paths. — Psalm 25:4",
            "Whether you turn to the right or to the left, your ears will hear a voice behind you, saying, 'This is the way; walk in it.' — Isaiah 30:21",
            "In all your ways acknowledge him, and he will make straight your paths. — Proverbs 3:6",
        ],
        
        'excellence': [
            "Whatever you do, work at it with all your heart, as working for the Lord. — Colossians 3:23",
            "Do you see someone skilled in their work? They will serve before kings. — Proverbs 22:29",
            "Finally, brothers and sisters, whatever is true, whatever is noble, whatever is right, whatever is pure, whatever is lovely, whatever is admirable—if anything is excellent or praiseworthy—think about such things. — Philippians 4:8",
            "Each one should use whatever gift he has received to serve others. — 1 Peter 4:10",
            "The plans of the diligent lead to profit. — Proverbs 21:5",
        ],
        
        'wisdom': [
            "If any of you lacks wisdom, let him ask God. — James 1:5",
            "The fear of the LORD is the beginning of wisdom. — Proverbs 9:10",
            "Get wisdom, get understanding; do not forget my words. — Proverbs 4:5",
            "Wisdom is supreme; therefore get wisdom. — Proverbs 4:7",
            "For the LORD gives wisdom; from his mouth come knowledge and understanding. — Proverbs 2:6",
        ],
    }
    
    def __init__(self):
        """Initialize wisdom collection."""
        self._all_verses: List[str] = []
        for category_verses in self.VERSES.values():
            self._all_verses.extend(category_verses)
        
        self._last_verse: str = ""
    
    def get_random(self) -> str:
        """
        Get a random verse (avoiding repetition).
        
        Returns:
            Random biblical quote
        """
        available = [v for v in self._all_verses if v != self._last_verse]
        verse = random.choice(available)
        self._last_verse = verse
        return verse
    
    def get_by_category(self, category: str) -> str:
        """
        Get a random verse from specific category.
        
        Args:
            category: Category name ('building', 'purpose', etc.)
            
        Returns:
            Random quote from category
        """
        if category not in self.VERSES:
            return self.get_random()
        
        verses = self.VERSES[category]
        available = [v for v in verses if v != self._last_verse]
        if not available:
            available = verses
        
        verse = random.choice(available)
        self._last_verse = verse
        return verse
    
    def get_for_context(self, operation: str) -> str:
        """
        Get contextually appropriate verse based on operation.
        
        Args:
            operation: Operation type ('indexing', 'searching', 'analyzing', etc.)
            
        Returns:
            Contextually appropriate quote
        """
        # Map operations to categories
        context_map = {
            'index': 'building',
            'build': 'building',
            'compile': 'building',
            'search': 'wisdom',
            'analyze': 'wisdom',
            'think': 'truth',
            'plan': 'purpose',
            'execute': 'persistence',
            'optimize': 'excellence',
            'refactor': 'excellence',
            'test': 'truth',
            'debug': 'truth',
        }
        
        # Find matching category
        operation_lower = operation.lower()
        for key, category in context_map.items():
            if key in operation_lower:
                return self.get_by_category(category)
        
        # Default: random verse
        return self.get_random()
    
    @property
    def categories(self) -> List[str]:
        """Get all available categories."""
        return list(self.VERSES.keys())
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about verse collection."""
        return {
            'total_verses': len(self._all_verses),
            'categories': len(self.VERSES),
            'verses_per_category': {
                cat: len(verses) for cat, verses in self.VERSES.items()
            }
        }


# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def format_verse_for_terminal(verse: str, width: int = 70) -> str:
    """
    Format verse with proper line wrapping and centering.
    
    Args:
        verse: Biblical quote
        width: Terminal width
        
    Returns:
        Formatted verse ready for display
    """
    # Split into text and reference
    if '—' in verse:
        text, ref = verse.rsplit('—', 1)
        text = text.strip()
        ref = ref.strip()
    else:
        text = verse
        ref = ""
    
    # Word wrap text
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + (1 if current_line else 0)
        if current_length + word_length <= width - 4:  # Leave margin
            current_line.append(word)
            current_length += word_length
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Add reference
    if ref:
        lines.append('')
        lines.append(f'  — {ref}')
    
    # Center all lines
    centered = []
    for line in lines:
        padding = (width - len(line)) // 2
        centered.append(' ' * padding + line)
    
    return '\n'.join(centered)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

# Global instance for easy access
_wisdom_instance = None

def get_wisdom() -> BiblicalWisdom:
    """Get global wisdom instance (singleton)."""
    global _wisdom_instance
    if _wisdom_instance is None:
        _wisdom_instance = BiblicalWisdom()
    return _wisdom_instance


if __name__ == "__main__":
    # Test the wisdom system
    wisdom = BiblicalWisdom()
    
    print("📖 BIBLICAL WISDOM SYSTEM TEST")
    print("=" * 70)
    
    print("\n1. Random verses:")
    for _ in range(3):
        print(f"  • {wisdom.get_random()[:60]}...")
    
    print("\n2. Category: Building")
    print(f"  • {wisdom.get_by_category('building')[:60]}...")
    
    print("\n3. Context-aware (indexing):")
    print(f"  • {wisdom.get_for_context('indexing')[:60]}...")
    
    print("\n4. Formatted:")
    verse = wisdom.get_random()
    print(format_verse_for_terminal(verse, 60))
    
    print("\n5. Statistics:")
    stats = wisdom.get_stats()
    print(f"  Total verses: {stats['total_verses']}")
    print(f"  Categories: {stats['categories']}")
    print("  Per category:", ', '.join(f"{k}: {v}" for k, v in stats['verses_per_category'].items()))
    
    print("\n✅ Biblical Wisdom System Ready!")
