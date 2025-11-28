"""
MIRIX-inspired 6-Type Memory System.

Reference: arXiv:2507.07957 - MIRIX: Multi-Agent Memory System for LLM-Based Agents
Additional: arXiv:2502.06975 - +47% adaptation with episodic memory

Memory Types:
1. Core Memory: Identity, values, persistent objectives
2. Episodic Memory: Past experiences ("what happened")
3. Semantic Memory: Factual knowledge ("what I know")
4. Procedural Memory: Learned skills ("how I do things")
5. Resource Memory: External resource cache
6. Knowledge Vault: Long-term consolidated knowledge
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import hashlib
import math


class MemoryType(Enum):
    """Types of memory in the MIRIX system."""
    CORE = "core"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    RESOURCE = "resource"
    KNOWLEDGE_VAULT = "knowledge_vault"


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    type: MemoryType
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 0.5  # 0-1, used for decay and consolidation
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "importance": self.importance,
            "tags": self.tags,
        }

    def update_access(self):
        """Update access time and count."""
        self.accessed_at = datetime.now()
        self.access_count += 1

    def compute_relevance(self, recency_weight: float = 0.3) -> float:
        """
        Compute relevance score based on importance and recency.

        Uses exponential decay for recency.
        """
        days_since_access = (datetime.now() - self.accessed_at).days
        recency_score = math.exp(-0.1 * days_since_access)
        return (1 - recency_weight) * self.importance + recency_weight * recency_score


class EpisodicMemory:
    """
    Episodic Memory - "What happened"

    Stores past experiences with temporal context.
    Enables learning from previous successes and failures.

    Reference: +47% adaptation to new situations (arXiv:2502.06975)
    """

    def __init__(self, max_entries: int = 1000):
        self.entries: List[MemoryEntry] = []
        self.max_entries = max_entries
        self._index: Dict[str, int] = {}  # id -> index

    def store(
        self,
        experience: str,
        outcome: str,
        context: dict,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> MemoryEntry:
        """
        Store an experience.

        Args:
            experience: What happened
            outcome: Result of the experience
            context: Additional context
            importance: How important (0-1)
            tags: Optional tags for retrieval

        Returns:
            Created memory entry
        """
        entry_id = self._generate_id(experience)

        entry = MemoryEntry(
            id=entry_id,
            type=MemoryType.EPISODIC,
            content=f"Experience: {experience}\nOutcome: {outcome}",
            metadata={
                "context": context,
                "outcome_type": self._classify_outcome(outcome),
                "experience_raw": experience,
                "outcome_raw": outcome,
            },
            importance=importance,
            tags=tags or [],
        )

        self.entries.append(entry)
        self._index[entry_id] = len(self.entries) - 1
        self._prune_if_needed()

        return entry

    def recall_similar(
        self,
        query: str,
        top_k: int = 5,
        min_relevance: float = 0.0,
    ) -> List[MemoryEntry]:
        """
        Retrieve similar experiences.

        Uses keyword matching (can be upgraded to embeddings).
        """
        query_words = set(self._tokenize(query))
        scored_entries = []

        for entry in self.entries:
            entry_words = set(self._tokenize(entry.content))
            overlap = len(query_words & entry_words)

            if overlap > 0:
                # Jaccard similarity + relevance
                similarity = overlap / len(query_words | entry_words)
                relevance = entry.compute_relevance()
                combined_score = 0.6 * similarity + 0.4 * relevance

                if combined_score >= min_relevance:
                    scored_entries.append((combined_score, entry))
                    entry.update_access()

        scored_entries.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored_entries[:top_k]]

    def recall_by_outcome(self, outcome_type: str) -> List[MemoryEntry]:
        """Retrieve experiences by outcome type (success/failure)."""
        return [
            e for e in self.entries
            if e.metadata.get("outcome_type") == outcome_type
        ]

    def recall_recent(self, n: int = 10) -> List[MemoryEntry]:
        """Retrieve most recent experiences."""
        sorted_entries = sorted(
            self.entries,
            key=lambda e: e.created_at,
            reverse=True
        )
        return sorted_entries[:n]

    def get_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get entry by ID."""
        idx = self._index.get(entry_id)
        if idx is not None and idx < len(self.entries):
            return self.entries[idx]
        return None

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for entry."""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{content}{timestamp}".encode()).hexdigest()[:12]

    def _classify_outcome(self, outcome: str) -> str:
        """Classify outcome as success, failure, or neutral."""
        outcome_lower = outcome.lower()
        success_keywords = ["success", "completed", "achieved", "solved", "correct", "passed"]
        failure_keywords = ["fail", "error", "wrong", "incorrect", "crashed", "timeout"]

        if any(kw in outcome_lower for kw in success_keywords):
            return "success"
        elif any(kw in outcome_lower for kw in failure_keywords):
            return "failure"
        return "neutral"

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        import re
        return re.findall(r'\b\w+\b', text.lower())

    def _prune_if_needed(self):
        """Remove low-relevance entries if exceeding limit."""
        if len(self.entries) > self.max_entries:
            # Sort by relevance, keep top entries
            self.entries.sort(key=lambda e: e.compute_relevance(), reverse=True)
            self.entries = self.entries[:self.max_entries]
            # Rebuild index
            self._index = {e.id: i for i, e in enumerate(self.entries)}

    def export(self) -> List[dict]:
        """Export all entries."""
        return [e.to_dict() for e in self.entries]

    def import_entries(self, data: List[dict]):
        """Import entries from export."""
        for item in data:
            entry = MemoryEntry(
                id=item["id"],
                type=MemoryType(item["type"]),
                content=item["content"],
                metadata=item.get("metadata", {}),
                created_at=datetime.fromisoformat(item["created_at"]),
                importance=item.get("importance", 0.5),
                tags=item.get("tags", []),
            )
            self.entries.append(entry)
            self._index[entry.id] = len(self.entries) - 1


class SemanticMemory:
    """
    Semantic Memory - "What I know"

    Stores factual knowledge and concepts.
    Organized by topics and relations.
    """

    def __init__(self):
        self.facts: Dict[str, MemoryEntry] = {}  # topic -> entry
        self.relations: Dict[str, List[str]] = {}  # concept -> related concepts
        self._topic_index: Dict[str, List[str]] = {}  # keyword -> topics

    def store_fact(
        self,
        topic: str,
        fact: str,
        source: Optional[str] = None,
        confidence: float = 0.8,
        tags: Optional[List[str]] = None,
    ) -> MemoryEntry:
        """
        Store a factual knowledge entry.

        Args:
            topic: Topic/subject of the fact
            fact: The factual content
            source: Where this fact came from
            confidence: Confidence level (0-1)
            tags: Optional tags

        Returns:
            Created memory entry
        """
        entry = MemoryEntry(
            id=hashlib.md5(topic.encode()).hexdigest()[:12],
            type=MemoryType.SEMANTIC,
            content=fact,
            metadata={
                "topic": topic,
                "source": source,
                "confidence": confidence,
            },
            importance=confidence,
            tags=tags or [],
        )

        self.facts[topic] = entry
        self._update_topic_index(topic, fact)

        return entry

    def query(self, topic: str) -> Optional[MemoryEntry]:
        """Query knowledge by exact topic."""
        entry = self.facts.get(topic)
        if entry:
            entry.update_access()
        return entry

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, MemoryEntry]]:
        """
        Search knowledge by keywords.

        Returns list of (topic, entry) tuples.
        """
        query_words = set(query.lower().split())
        results = []

        for keyword in query_words:
            if keyword in self._topic_index:
                for topic in self._topic_index[keyword]:
                    if topic in self.facts:
                        entry = self.facts[topic]
                        results.append((topic, entry))
                        entry.update_access()

        # Deduplicate and limit
        seen = set()
        unique_results = []
        for topic, entry in results:
            if topic not in seen:
                seen.add(topic)
                unique_results.append((topic, entry))

        return unique_results[:top_k]

    def add_relation(self, concept_a: str, concept_b: str, relation_type: str = "related"):
        """Add a relation between concepts."""
        if concept_a not in self.relations:
            self.relations[concept_a] = []

        relation_entry = f"{relation_type}:{concept_b}"
        if relation_entry not in self.relations[concept_a]:
            self.relations[concept_a].append(relation_entry)

        # Bidirectional for "related"
        if relation_type == "related":
            if concept_b not in self.relations:
                self.relations[concept_b] = []
            reverse_entry = f"{relation_type}:{concept_a}"
            if reverse_entry not in self.relations[concept_b]:
                self.relations[concept_b].append(reverse_entry)

    def get_related(self, concept: str) -> List[str]:
        """Get concepts related to a given concept."""
        if concept not in self.relations:
            return []
        return [r.split(":", 1)[1] for r in self.relations[concept]]

    def update_confidence(self, topic: str, delta: float):
        """Update confidence for a fact."""
        if topic in self.facts:
            entry = self.facts[topic]
            new_confidence = max(0, min(1, entry.metadata["confidence"] + delta))
            entry.metadata["confidence"] = new_confidence
            entry.importance = new_confidence

    def _update_topic_index(self, topic: str, content: str):
        """Update keyword index."""
        words = set(topic.lower().split() + content.lower().split())
        for word in words:
            if len(word) > 2:  # Skip very short words
                if word not in self._topic_index:
                    self._topic_index[word] = []
                if topic not in self._topic_index[word]:
                    self._topic_index[word].append(topic)

    def export(self) -> dict:
        """Export semantic memory."""
        return {
            "facts": {t: e.to_dict() for t, e in self.facts.items()},
            "relations": self.relations,
        }


class ProceduralMemory:
    """
    Procedural Memory - "How I do things"

    Stores learned skills and procedures.
    Enables reuse of successful solutions.
    """

    def __init__(self):
        self.procedures: Dict[str, MemoryEntry] = {}  # skill_name -> procedure
        self._skill_index: Dict[str, List[str]] = {}  # keyword -> skill_names

    def store_procedure(
        self,
        skill_name: str,
        steps: List[str],
        success_rate: float = 0.0,
        preconditions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> MemoryEntry:
        """
        Store a learned procedure.

        Args:
            skill_name: Name of the skill/procedure
            steps: List of steps to execute
            success_rate: Historical success rate (0-1)
            preconditions: Required conditions
            tags: Optional tags

        Returns:
            Created memory entry
        """
        entry = MemoryEntry(
            id=hashlib.md5(skill_name.encode()).hexdigest()[:12],
            type=MemoryType.PROCEDURAL,
            content="\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)]),
            metadata={
                "skill_name": skill_name,
                "steps": steps,
                "steps_count": len(steps),
                "success_rate": success_rate,
                "execution_count": 0,
                "preconditions": preconditions or [],
            },
            importance=success_rate,
            tags=tags or [],
        )

        self.procedures[skill_name] = entry
        self._update_skill_index(skill_name, steps)

        return entry

    def get_procedure(self, skill_name: str) -> Optional[MemoryEntry]:
        """Get procedure by skill name."""
        entry = self.procedures.get(skill_name)
        if entry:
            entry.update_access()
        return entry

    def get_steps(self, skill_name: str) -> Optional[List[str]]:
        """Get steps for a procedure."""
        entry = self.get_procedure(skill_name)
        if entry:
            return entry.metadata.get("steps", [])
        return None

    def search_procedures(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """Search procedures by keywords."""
        query_words = set(query.lower().split())
        results = []

        for keyword in query_words:
            if keyword in self._skill_index:
                for skill_name in self._skill_index[keyword]:
                    if skill_name in self.procedures:
                        entry = self.procedures[skill_name]
                        results.append(entry)

        # Deduplicate and sort by success rate
        seen = set()
        unique_results = []
        for entry in results:
            if entry.id not in seen:
                seen.add(entry.id)
                unique_results.append(entry)

        unique_results.sort(
            key=lambda e: e.metadata.get("success_rate", 0),
            reverse=True
        )
        return unique_results[:top_k]

    def update_success_rate(self, skill_name: str, success: bool):
        """Update success rate after execution."""
        if skill_name in self.procedures:
            entry = self.procedures[skill_name]
            current_rate = entry.metadata.get("success_rate", 0.5)
            exec_count = entry.metadata.get("execution_count", 0)

            # Exponential moving average with more weight on recent
            alpha = 0.2 if exec_count > 5 else 0.5
            new_rate = (1 - alpha) * current_rate + alpha * (1.0 if success else 0.0)

            entry.metadata["success_rate"] = new_rate
            entry.metadata["execution_count"] = exec_count + 1
            entry.importance = new_rate

    def add_step(self, skill_name: str, step: str, position: Optional[int] = None):
        """Add a step to an existing procedure."""
        if skill_name in self.procedures:
            entry = self.procedures[skill_name]
            steps = entry.metadata.get("steps", [])

            if position is not None and 0 <= position <= len(steps):
                steps.insert(position, step)
            else:
                steps.append(step)

            entry.metadata["steps"] = steps
            entry.metadata["steps_count"] = len(steps)
            entry.content = "\n".join([f"{i+1}. {s}" for i, s in enumerate(steps)])

    def _update_skill_index(self, skill_name: str, steps: List[str]):
        """Update keyword index."""
        words = set(skill_name.lower().split())
        for step in steps:
            words.update(step.lower().split())

        for word in words:
            if len(word) > 2:
                if word not in self._skill_index:
                    self._skill_index[word] = []
                if skill_name not in self._skill_index[word]:
                    self._skill_index[word].append(skill_name)

    def list_skills(self) -> List[str]:
        """List all skill names."""
        return list(self.procedures.keys())

    def export(self) -> dict:
        """Export procedural memory."""
        return {
            skill: entry.to_dict()
            for skill, entry in self.procedures.items()
        }


class MemorySystem:
    """
    Unified Memory System (MIRIX-inspired).

    Combines all 6 memory types into a unified interface.
    """

    def __init__(
        self,
        agent_name: str = "Prometheus",
        max_episodic: int = 1000,
    ):
        # Initialize all memory subsystems
        self.episodic = EpisodicMemory(max_entries=max_episodic)
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()

        # Core memory - persistent identity
        self.core: Dict[str, Any] = {
            "name": agent_name,
            "purpose": "Self-evolving agent that improves through experience",
            "values": ["accuracy", "efficiency", "learning", "helpfulness"],
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
        }

        # Resource cache - external resources
        self.resource_cache: Dict[str, Any] = {}

        # Knowledge vault - consolidated long-term knowledge
        self.knowledge_vault: List[MemoryEntry] = []

        # Stats
        self._stats = {
            "total_experiences": 0,
            "total_facts": 0,
            "total_procedures": 0,
            "consolidations": 0,
        }

    # === Core Memory ===

    def get_identity(self) -> Dict[str, Any]:
        """Get agent identity from core memory."""
        return self.core.copy()

    def update_core(self, key: str, value: Any):
        """Update core memory value."""
        self.core[key] = value

    # === Episodic Memory Interface ===

    def remember_experience(
        self,
        experience: str,
        outcome: str,
        context: Optional[dict] = None,
        importance: float = 0.5,
    ) -> str:
        """
        Store an experience.

        Returns entry ID.
        """
        entry = self.episodic.store(
            experience=experience,
            outcome=outcome,
            context=context or {},
            importance=importance,
        )
        self._stats["total_experiences"] += 1
        return entry.id

    def recall_experiences(
        self,
        situation: str,
        top_k: int = 5,
    ) -> List[dict]:
        """Recall relevant past experiences."""
        entries = self.episodic.recall_similar(situation, top_k)
        return [e.to_dict() for e in entries]

    def recall_successes(self, top_k: int = 5) -> List[dict]:
        """Recall successful experiences."""
        entries = self.episodic.recall_by_outcome("success")
        entries.sort(key=lambda e: e.importance, reverse=True)
        return [e.to_dict() for e in entries[:top_k]]

    def recall_failures(self, top_k: int = 5) -> List[dict]:
        """Recall failure experiences (for learning)."""
        entries = self.episodic.recall_by_outcome("failure")
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return [e.to_dict() for e in entries[:top_k]]

    # === Semantic Memory Interface ===

    def learn_fact(
        self,
        topic: str,
        fact: str,
        source: Optional[str] = None,
        confidence: float = 0.8,
    ):
        """Learn a new fact."""
        self.semantic.store_fact(topic, fact, source, confidence)
        self._stats["total_facts"] += 1

    def query_knowledge(self, topic: str) -> Optional[str]:
        """Query knowledge about a topic."""
        entry = self.semantic.query(topic)
        return entry.content if entry else None

    def search_knowledge(self, query: str, top_k: int = 5) -> List[dict]:
        """Search knowledge base."""
        results = self.semantic.search(query, top_k)
        return [{"topic": t, "content": e.content} for t, e in results]

    # === Procedural Memory Interface ===

    def learn_procedure(
        self,
        skill_name: str,
        steps: List[str],
        preconditions: Optional[List[str]] = None,
    ):
        """Learn a new procedure."""
        self.procedural.store_procedure(
            skill_name=skill_name,
            steps=steps,
            preconditions=preconditions,
        )
        self._stats["total_procedures"] += 1

    def get_procedure(self, skill_name: str) -> Optional[List[str]]:
        """Get steps for a procedure."""
        return self.procedural.get_steps(skill_name)

    def find_procedures(self, query: str, top_k: int = 5) -> List[dict]:
        """Find relevant procedures."""
        entries = self.procedural.search_procedures(query, top_k)
        return [
            {
                "skill": e.metadata["skill_name"],
                "steps": e.metadata["steps"],
                "success_rate": e.metadata.get("success_rate", 0),
            }
            for e in entries
        ]

    def record_procedure_outcome(self, skill_name: str, success: bool):
        """Record outcome of procedure execution."""
        self.procedural.update_success_rate(skill_name, success)

    # === Resource Cache ===

    def cache_resource(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Cache an external resource."""
        self.resource_cache[key] = {
            "value": value,
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now().timestamp() + ttl_seconds),
        }

    def get_cached_resource(self, key: str) -> Optional[Any]:
        """Get cached resource if not expired."""
        if key in self.resource_cache:
            entry = self.resource_cache[key]
            if datetime.now().timestamp() < entry["expires_at"]:
                return entry["value"]
            else:
                del self.resource_cache[key]
        return None

    # === Knowledge Vault ===

    def consolidate_to_vault(self):
        """
        Consolidate important knowledge to vault.

        Moves high-value procedural knowledge and
        frequent patterns to long-term storage.
        """
        consolidated = 0

        # Consolidate high-success procedures
        for name, entry in self.procedural.procedures.items():
            if entry.metadata.get("success_rate", 0) > 0.8:
                vault_entry = MemoryEntry(
                    id=f"vault_{entry.id}",
                    type=MemoryType.KNOWLEDGE_VAULT,
                    content=f"SKILL: {name}\n{entry.content}",
                    metadata={
                        **entry.metadata,
                        "consolidated_at": datetime.now().isoformat(),
                    },
                    importance=1.0,
                )

                # Avoid duplicates
                if not any(v.id == vault_entry.id for v in self.knowledge_vault):
                    self.knowledge_vault.append(vault_entry)
                    consolidated += 1

        # Consolidate high-confidence facts
        for topic, entry in self.semantic.facts.items():
            if entry.metadata.get("confidence", 0) > 0.9:
                vault_entry = MemoryEntry(
                    id=f"vault_fact_{entry.id}",
                    type=MemoryType.KNOWLEDGE_VAULT,
                    content=f"FACT [{topic}]: {entry.content}",
                    metadata={
                        **entry.metadata,
                        "consolidated_at": datetime.now().isoformat(),
                    },
                    importance=1.0,
                )

                if not any(v.id == vault_entry.id for v in self.knowledge_vault):
                    self.knowledge_vault.append(vault_entry)
                    consolidated += 1

        self._stats["consolidations"] += 1
        return consolidated

    def query_vault(self, query: str, top_k: int = 5) -> List[dict]:
        """Query the knowledge vault."""
        query_words = set(query.lower().split())
        results = []

        for entry in self.knowledge_vault:
            entry_words = set(entry.content.lower().split())
            overlap = len(query_words & entry_words)
            if overlap > 0:
                results.append((overlap, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        return [e.to_dict() for _, e in results[:top_k]]

    # === Context Generation ===

    def get_context_for_task(self, task_description: str) -> dict:
        """
        Generate comprehensive context for a task.

        Combines relevant memories from all types.
        """
        return {
            "identity": self.get_identity(),
            "relevant_experiences": self.recall_experiences(task_description, top_k=3),
            "relevant_knowledge": self.search_knowledge(task_description, top_k=3),
            "relevant_procedures": self.find_procedures(task_description, top_k=3),
            "vault_knowledge": self.query_vault(task_description, top_k=2),
        }

    def get_learning_context(self) -> dict:
        """Get context focused on learning from past mistakes."""
        return {
            "recent_failures": self.recall_failures(top_k=5),
            "recent_successes": self.recall_successes(top_k=3),
            "mastered_skills": [
                skill for skill, entry in self.procedural.procedures.items()
                if entry.metadata.get("success_rate", 0) > 0.8
            ],
            "skills_to_improve": [
                skill for skill, entry in self.procedural.procedures.items()
                if 0.3 < entry.metadata.get("success_rate", 0) < 0.7
            ],
        }

    # === Persistence ===

    def export_state(self) -> dict:
        """Export complete memory state for persistence."""
        return {
            "core": self.core,
            "episodic": self.episodic.export(),
            "semantic": self.semantic.export(),
            "procedural": self.procedural.export(),
            "knowledge_vault": [e.to_dict() for e in self.knowledge_vault],
            "stats": self._stats,
        }

    def import_state(self, state: dict):
        """Import memory state from export."""
        if "core" in state:
            self.core.update(state["core"])

        if "episodic" in state:
            self.episodic.import_entries(state["episodic"])

        if "semantic" in state:
            for topic, entry_data in state["semantic"].get("facts", {}).items():
                self.semantic.store_fact(
                    topic=topic,
                    fact=entry_data["content"],
                    confidence=entry_data.get("metadata", {}).get("confidence", 0.8),
                )
            self.semantic.relations = state["semantic"].get("relations", {})

        if "procedural" in state:
            for skill, entry_data in state["procedural"].items():
                self.procedural.store_procedure(
                    skill_name=skill,
                    steps=entry_data.get("metadata", {}).get("steps", []),
                    success_rate=entry_data.get("metadata", {}).get("success_rate", 0),
                )

        if "stats" in state:
            self._stats.update(state["stats"])

    def get_stats(self) -> dict:
        """Get memory system statistics."""
        return {
            **self._stats,
            "episodic_entries": len(self.episodic.entries),
            "semantic_facts": len(self.semantic.facts),
            "procedural_skills": len(self.procedural.procedures),
            "vault_entries": len(self.knowledge_vault),
            "cache_entries": len(self.resource_cache),
        }

    def clear_all(self):
        """Clear all memories (use with caution)."""
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.resource_cache = {}
        self.knowledge_vault = []
        self._stats = {
            "total_experiences": 0,
            "total_facts": 0,
            "total_procedures": 0,
            "consolidations": 0,
        }
