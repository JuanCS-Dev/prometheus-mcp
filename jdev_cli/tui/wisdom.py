"""
Biblical Wisdom System - Inspirational verses during loading states.

Philosophy:
- Every waiting moment is an opportunity for inspiration
- Biblical wisdom grounds our work in purpose
- Excellence as worship to the Creator
- Loading states become moments of reflection

"Whatever you do, work at it with all your heart, 
 as working for the Lord." - Colossians 3:23

Created: 2025-11-18 21:37 UTC
"""

import random
from typing import Optional
from dataclasses import dataclass


@dataclass
class Verse:
    """A biblical verse with reference."""
    text: str
    reference: str
    category: str

    def format(self, max_width: Optional[int] = None) -> str:
        """Format verse for display."""
        full_text = f'"{self.text}" - {self.reference}'
        if max_width and len(full_text) > max_width:
            # Truncate gracefully
            available = max_width - len(self.reference) - 6  # "..." + " - "
            return f'"{self.text[:available]}..." - {self.reference}'
        return full_text


# =============================================================================
# BIBLICAL VERSES COLLECTION
# =============================================================================

VERSES_BUILDING = [
    Verse(
        "Unless the LORD builds the house, the builders labor in vain.",
        "Psalm 127:1",
        "building"
    ),
    Verse(
        "Commit to the LORD whatever you do, and he will establish your plans.",
        "Proverbs 16:3",
        "building"
    ),
    Verse(
        "By wisdom a house is built, and through understanding it is established.",
        "Proverbs 24:3",
        "building"
    ),
    Verse(
        "The wise woman builds her house, but with her own hands the foolish one tears hers down.",
        "Proverbs 14:1",
        "building"
    ),
]

VERSES_PURPOSE = [
    Verse(
        "For I know the plans I have for you, declares the LORD, plans to prosper you.",
        "Jeremiah 29:11",
        "purpose"
    ),
    Verse(
        "Many are the plans in a person's heart, but it is the LORD's purpose that prevails.",
        "Proverbs 19:21",
        "purpose"
    ),
    Verse(
        "In their hearts humans plan their course, but the LORD establishes their steps.",
        "Proverbs 16:9",
        "purpose"
    ),
    Verse(
        "And we know that in all things God works for the good of those who love him.",
        "Romans 8:28",
        "purpose"
    ),
]

VERSES_PERSISTENCE = [
    Verse(
        "I can do all things through Christ who strengthens me.",
        "Philippians 4:13",
        "persistence"
    ),
    Verse(
        "Let us not become weary in doing good, for at the proper time we will reap.",
        "Galatians 6:9",
        "persistence"
    ),
    Verse(
        "Be strong and courageous. Do not be afraid; do not be discouraged.",
        "Joshua 1:9",
        "persistence"
    ),
    Verse(
        "Perseverance must finish its work so that you may be mature and complete.",
        "James 1:4",
        "persistence"
    ),
    Verse(
        "Consider it pure joy whenever you face trials of many kinds.",
        "James 1:2",
        "persistence"
    ),
]

VERSES_TRUTH = [
    Verse(
        "I am the way and the truth and the life.",
        "John 14:6",
        "truth"
    ),
    Verse(
        "Your word is a lamp to my feet and a light to my path.",
        "Psalm 119:105",
        "truth"
    ),
    Verse(
        "Then you will know the truth, and the truth will set you free.",
        "John 8:32",
        "truth"
    ),
    Verse(
        "The sum of your word is truth, and every one of your righteous rules endures forever.",
        "Psalm 119:160",
        "truth"
    ),
]

VERSES_WISDOM = [
    Verse(
        "If any of you lacks wisdom, let him ask God, who gives generously to all.",
        "James 1:5",
        "wisdom"
    ),
    Verse(
        "The fear of the LORD is the beginning of wisdom.",
        "Proverbs 9:10",
        "wisdom"
    ),
    Verse(
        "Trust in the LORD with all your heart and lean not on your own understanding.",
        "Proverbs 3:5",
        "wisdom"
    ),
    Verse(
        "In all your ways acknowledge him, and he will make straight your paths.",
        "Proverbs 3:6",
        "wisdom"
    ),
    Verse(
        "For the LORD gives wisdom; from his mouth come knowledge and understanding.",
        "Proverbs 2:6",
        "wisdom"
    ),
]

VERSES_EXCELLENCE = [
    Verse(
        "Whatever you do, work at it with all your heart, as working for the Lord.",
        "Colossians 3:23",
        "excellence"
    ),
    Verse(
        "Do you see someone skilled in their work? They will serve before kings.",
        "Proverbs 22:29",
        "excellence"
    ),
    Verse(
        "The hand of the diligent will rule, while the slothful will be put to forced labor.",
        "Proverbs 12:24",
        "excellence"
    ),
    Verse(
        "Finally, brothers, whatever is true, whatever is honorable, whatever is just, think about these things.",
        "Philippians 4:8",
        "excellence"
    ),
    Verse(
        "Let your light shine before others, that they may see your good deeds.",
        "Matthew 5:16",
        "excellence"
    ),
]

# Combined collection
ALL_VERSES = (
    VERSES_BUILDING +
    VERSES_PURPOSE +
    VERSES_PERSISTENCE +
    VERSES_TRUTH +
    VERSES_WISDOM +
    VERSES_EXCELLENCE
)


# =============================================================================
# WISDOM SYSTEM
# =============================================================================

class WisdomSystem:
    """
    System for displaying biblical wisdom during operations.
    
    Examples:
        wisdom = WisdomSystem()
        verse = wisdom.get_random()
        print(verse.format())
        
        # Category-specific
        verse = wisdom.get_by_category("excellence")
    """

    def __init__(self):
        """Initialize wisdom system."""
        self.verses = ALL_VERSES
        self.categories = {
            "building": VERSES_BUILDING,
            "purpose": VERSES_PURPOSE,
            "persistence": VERSES_PERSISTENCE,
            "truth": VERSES_TRUTH,
            "wisdom": VERSES_WISDOM,
            "excellence": VERSES_EXCELLENCE,
        }
        self._last_verse: Optional[Verse] = None

    def get_random(self, avoid_repeat: bool = True) -> Verse:
        """
        Get random verse from all categories.
        
        Args:
            avoid_repeat: Don't show same verse twice in a row
            
        Returns:
            Random Verse object
        """
        available = [v for v in self.verses if v != self._last_verse] if avoid_repeat else self.verses
        verse = random.choice(available)
        self._last_verse = verse
        return verse

    def get_by_category(self, category: str, avoid_repeat: bool = True) -> Verse:
        """
        Get random verse from specific category.
        
        Args:
            category: Category name (building, purpose, persistence, etc.)
            avoid_repeat: Don't show same verse twice in a row
            
        Returns:
            Random Verse from category
        """
        if category not in self.categories:
            return self.get_random(avoid_repeat)

        verses = self.categories[category]
        available = [v for v in verses if v != self._last_verse] if avoid_repeat else verses
        verse = random.choice(available)
        self._last_verse = verse
        return verse

    def get_for_operation(self, operation_type: str) -> Verse:
        """
        Get contextually appropriate verse for operation.
        
        Args:
            operation_type: Type of operation (build, read, analyze, etc.)
            
        Returns:
            Contextually appropriate Verse
        """
        # Map operations to categories
        operation_map = {
            "build": "building",
            "create": "building",
            "compile": "building",
            "install": "building",
            "analyze": "wisdom",
            "search": "wisdom",
            "review": "wisdom",
            "test": "excellence",
            "validate": "excellence",
            "deploy": "excellence",
            "fix": "persistence",
            "retry": "persistence",
            "recover": "persistence",
            "plan": "purpose",
            "design": "purpose",
            "architect": "purpose",
        }

        category = operation_map.get(operation_type.lower(), "excellence")
        return self.get_by_category(category)

    def get_formatted(self, max_width: Optional[int] = 80) -> str:
        """
        Get random verse formatted for display.
        
        Args:
            max_width: Maximum width for formatting
            
        Returns:
            Formatted verse string
        """
        return self.get_random().format(max_width)


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

wisdom_system = WisdomSystem()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_random_verse(max_width: Optional[int] = 80) -> str:
    """
    Quick helper to get formatted random verse.
    
    Args:
        max_width: Maximum width for formatting
        
    Returns:
        Formatted verse string
        
    Example:
        verse = get_random_verse(60)
        print(verse)
    """
    return wisdom_system.get_formatted(max_width)


def get_verse_for_operation(operation: str, max_width: Optional[int] = 80) -> str:
    """
    Get verse appropriate for operation type.
    
    Args:
        operation: Operation type (build, analyze, test, etc.)
        max_width: Maximum width for formatting
        
    Returns:
        Formatted verse string
    """
    verse = wisdom_system.get_for_operation(operation)
    return verse.format(max_width)


def get_loading_message(operation: str = "processing") -> str:
    """
    Get complete loading message with verse.
    
    Args:
        operation: Operation description
        
    Returns:
        Loading message with verse
        
    Example:
        msg = get_loading_message("Building project")
        # Returns: "Building project... 'Unless the LORD builds...' - Psalm 127:1"
    """
    verse = wisdom_system.get_for_operation(operation)
    return f"{operation}... {verse.format(60)}"


# =============================================================================
# VALIDATION
# =============================================================================

def validate_wisdom_system():
    """Validate wisdom system."""
    print("✅ Wisdom System:")
    print(f"  - Total verses: {len(ALL_VERSES)}")
    print(f"  - Categories: {len(wisdom_system.categories)}")
    print(f"  - Building: {len(VERSES_BUILDING)}")
    print(f"  - Purpose: {len(VERSES_PURPOSE)}")
    print(f"  - Persistence: {len(VERSES_PERSISTENCE)}")
    print(f"  - Truth: {len(VERSES_TRUTH)}")
    print(f"  - Wisdom: {len(VERSES_WISDOM)}")
    print(f"  - Excellence: {len(VERSES_EXCELLENCE)}")
    print()
    print("📖 Sample verses:")
    for category in wisdom_system.categories:
        verse = wisdom_system.get_by_category(category)
        print(f"  {category}: {verse.format(70)}")


if __name__ == "__main__":
    validate_wisdom_system()

    def get_all_categories(self) -> list[str]:
        """Get all available wisdom categories."""
        return list(self.verses.keys())

    def get_all_categories(self) -> list[str]:
        """Get all wisdom categories."""
        return list(self.verses.keys())
