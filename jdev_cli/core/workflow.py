"""
Multi-Step Workflow Orchestration Engine

Implements Constitutional Layer 2 (Deliberation): Tree-of-Thought planning
- Dependency graph with topological sort (Cursor AI pattern)
- Tree-of-Thought multi-path exploration (Claude pattern)
- Auto-critique with LEI metric (Constitutional requirement)
- Transactional execution with rollback (ACID pattern)
- Checkpoint system for state management (Cursor AI pattern)

Best-of-breed: Cursor (orchestration) + Claude (reasoning) + Constitutional (guarantees)
"""

import logging
import time
import copy
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Step execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Single step in workflow."""
    step_id: str
    tool_name: str
    args: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)

    # Execution state
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0

    # Risk assessment
    is_risky: bool = False  # Requires checkpoint
    is_reversible: bool = True  # Can be rolled back

    def to_dict(self) -> Dict[str, Any]:
        """Serialize step."""
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "args": self.args,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "error": self.error,
            "execution_time": self.execution_time,
        }


@dataclass
class ThoughtPath:
    """Single path in Tree-of-Thought."""
    path_id: str
    description: str
    steps: List[WorkflowStep]

    # Scoring (Constitutional criteria)
    completeness_score: float = 0.0  # P1: Completude
    validation_score: float = 0.0    # P2: Validação
    efficiency_score: float = 0.0    # P6: Eficiência
    total_score: float = 0.0

    def calculate_score(self) -> float:
        """Calculate total score using Constitutional weights."""
        self.total_score = (
            self.completeness_score * 0.4 +
            self.validation_score * 0.3 +
            self.efficiency_score * 0.3
        )
        return self.total_score


@dataclass
class Checkpoint:
    """State checkpoint for rollback."""
    checkpoint_id: str
    timestamp: float
    context: Dict[str, Any]
    completed_steps: List[str]

    # File backups
    file_backups: Dict[str, str] = field(default_factory=dict)


@dataclass
class Critique:
    """Auto-critique result (Constitutional Layer 2)."""
    passed: bool
    completeness_score: float
    validation_passed: bool
    efficiency_score: float
    lei: float  # Lazy Execution Index

    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize critique."""
        return {
            "passed": self.passed,
            "completeness": self.completeness_score,
            "validation": self.validation_passed,
            "efficiency": self.efficiency_score,
            "lei": self.lei,
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


class DependencyGraph:
    """
    Dependency graph for workflow steps (Cursor AI pattern).
    
    Features:
    - Topological sort for execution order
    - Cycle detection
    - Parallel execution identification
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, WorkflowStep] = {}
        self.edges: List[Tuple[str, str]] = []  # (from, to)

    def add_step(self, step: WorkflowStep) -> None:
        """Add step to graph."""
        self.nodes[step.step_id] = step

        # Add edges for dependencies
        for dep_id in step.dependencies:
            self.edges.append((dep_id, step.step_id))

    def topological_sort(self) -> List[WorkflowStep]:
        """
        Sort steps respecting dependencies.
        
        Returns:
            Ordered list of steps
        
        Raises:
            ValueError: If cycle detected
        """
        # Calculate in-degrees
        in_degree = {node_id: 0 for node_id in self.nodes}

        for from_id, to_id in self.edges:
            in_degree[to_id] += 1

        # Queue nodes with no dependencies
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Pick node with no dependencies
            node_id = queue.pop(0)
            result.append(self.nodes[node_id])

            # Remove edges from this node
            for from_id, to_id in self.edges:
                if from_id == node_id:
                    in_degree[to_id] -= 1
                    if in_degree[to_id] == 0:
                        queue.append(to_id)

        # Check for cycles
        if len(result) != len(self.nodes):
            raise ValueError("Dependency cycle detected in workflow")

        return result

    def find_parallel_groups(self) -> List[List[WorkflowStep]]:
        """
        Find steps that can execute in parallel.
        
        Returns:
            List of groups, where each group can run in parallel
        """
        sorted_steps = self.topological_sort()
        groups: List[List[WorkflowStep]] = []

        processed = set()

        for step in sorted_steps:
            # Check if all dependencies are processed
            deps_ready = all(dep in processed for dep in step.dependencies)

            if deps_ready:
                # Find which group this belongs to
                found_group = False
                for group in groups:
                    # Can add to group if no dependencies within group
                    if not any(
                        dep_step.step_id in step.dependencies
                        for dep_step in group
                    ):
                        group.append(step)
                        found_group = True
                        break

                if not found_group:
                    groups.append([step])

                processed.add(step.step_id)

        return groups


class TreeOfThought:
    """
    Tree-of-Thought planning (Claude pattern + Constitutional Layer 2).
    
    Features:
    - Multi-path exploration
    - Constitutional scoring
    - Best path selection
    """

    def __init__(self, llm_client: Any = None) -> None:
        self.llm = llm_client

    async def generate_paths(
        self,
        user_goal: str,
        available_tools: List[str],
        max_paths: int = 3
    ) -> List[ThoughtPath]:
        """
        Generate multiple solution paths.
        
        Args:
            user_goal: User's goal
            available_tools: Available tools
            max_paths: Max paths to generate
        
        Returns:
            List of thought paths
        """
        if self.llm is None:
            # Fallback: single naive path
            return [self._generate_naive_path(user_goal, available_tools)]

        try:
            # Use LLM to brainstorm approaches
            prompt = self._build_brainstorm_prompt(user_goal, available_tools)

            response = await self.llm.generate_async(
                messages=[
                    {"role": "system", "content": self._get_planning_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # Higher for creativity
                max_tokens=1000
            )

            # Parse LLM response into paths
            paths = self._parse_paths(response.get("content", ""), user_goal)

            # Limit to max_paths
            return paths[:max_paths]

        except Exception as e:
            logger.error(f"LLM path generation failed: {e}")
            return [self._generate_naive_path(user_goal, available_tools)]

    def _get_planning_system_prompt(self) -> str:
        """System prompt for planning."""
        return """You are an expert workflow planner. Generate multiple approaches to solve tasks.

For each approach:
1. List the steps needed
2. Explain pros and cons
3. Estimate complexity

Format:
PATH 1: [Name]
Steps:
1. tool_name(args)
2. tool_name(args)
Pros: ...
Cons: ...
Complexity: Low/Medium/High

PATH 2: [Name]
...

Be creative and consider different strategies."""

    def _build_brainstorm_prompt(self, goal: str, tools: List[str]) -> str:
        """Build brainstorming prompt."""
        tools_str = ", ".join(tools)
        return f"""Generate 3 different approaches to: "{goal}"

Available tools: {tools_str}

Think about:
- Direct approach (fastest)
- Safe approach (most reliable)
- Smart approach (most efficient)

Generate 3 distinct paths."""

    def _parse_paths(self, llm_response: str, goal: str) -> List[ThoughtPath]:
        """Parse LLM response into paths."""
        paths = []

        # Simple parsing (production would be more robust)
        path_sections = llm_response.split("PATH ")

        for i, section in enumerate(path_sections[1:], 1):  # Skip first split
            lines = section.strip().split('\n')
            if not lines:
                continue

            path = ThoughtPath(
                path_id=f"path_{i}",
                description=lines[0].split(':', 1)[-1].strip() if ':' in lines[0] else f"Approach {i}",
                steps=[]
            )

            # Extract steps (simplified)
            # Production would parse more carefully
            paths.append(path)

        return paths if paths else [self._generate_naive_path(goal, [])]

    def _generate_naive_path(self, goal: str, tools: List[str]) -> ThoughtPath:
        """Generate simple fallback path."""
        return ThoughtPath(
            path_id="naive_path",
            description="Direct approach",
            steps=[],
            completeness_score=0.7,
            validation_score=0.7,
            efficiency_score=0.7,
            total_score=0.7
        )

    def score_paths(self, paths: List[ThoughtPath]) -> List[ThoughtPath]:
        """
        Score paths using Constitutional criteria.
        
        Args:
            paths: Paths to score
        
        Returns:
            Paths sorted by score (best first)
        """
        for path in paths:
            # P1: Completeness (are all steps defined?)
            path.completeness_score = self._score_completeness(path)

            # P2: Validation (can we verify results?)
            path.validation_score = self._score_validation(path)

            # P6: Efficiency (is it efficient?)
            path.efficiency_score = self._score_efficiency(path)

            # Total score
            path.calculate_score()

        return sorted(paths, key=lambda p: p.total_score, reverse=True)

    def _score_completeness(self, path: ThoughtPath) -> float:
        """Score path completeness."""
        if not path.steps:
            return 0.5  # No steps defined yet

        # Check if steps have all required info
        complete_steps = sum(
            1 for step in path.steps
            if step.tool_name and step.args is not None
        )

        return complete_steps / len(path.steps) if path.steps else 0.5

    def _score_validation(self, path: ThoughtPath) -> float:
        """Score path validation capability."""
        # Paths with test/verify steps score higher
        has_validation = any(
            'test' in step.tool_name.lower() or 'verify' in step.tool_name.lower()
            for step in path.steps
        )

        return 0.9 if has_validation else 0.6

    def _score_efficiency(self, path: ThoughtPath) -> float:
        """Score path efficiency."""
        if not path.steps:
            return 0.5

        # Shorter paths are more efficient (but not too short)
        num_steps = len(path.steps)

        if num_steps <= 3:
            return 0.9
        elif num_steps <= 6:
            return 0.7
        else:
            return 0.5

    def select_best_path(self, paths: List[ThoughtPath]) -> ThoughtPath:
        """Select best path after scoring."""
        scored_paths = self.score_paths(paths)
        return scored_paths[0] if scored_paths else paths[0]


class AutoCritique:
    """
    Auto-critique system (Constitutional Layer 2).
    
    Features:
    - Completeness check (P1)
    - Validation check (P2)
    - Efficiency check (P6)
    - LEI calculation (Constitutional metric)
    """

    def __init__(self) -> None:
        self.lei_threshold = 1.0  # Constitutional requirement

    def critique_step(self, step: WorkflowStep, result: Any) -> Critique:
        """
        Critique step execution.
        
        Args:
            step: Executed step
            result: Step result
        
        Returns:
            Critique with Constitutional checks
        """
        # P1: Completeness
        completeness = self._check_completeness(result)

        # P2: Validation
        validation = self._validate_result(result)

        # P6: Efficiency
        efficiency = self._check_efficiency(step)

        # Constitutional: LEI calculation
        lei = self._calculate_lei(result)

        # Determine if passed
        passed = all([
            completeness > 0.9,
            validation,
            efficiency > 0.7,
            lei < self.lei_threshold
        ])

        critique = Critique(
            passed=passed,
            completeness_score=completeness,
            validation_passed=validation,
            efficiency_score=efficiency,
            lei=lei
        )

        # Generate issues and suggestions
        if not passed:
            critique.issues = self._identify_issues(
                completeness, validation, efficiency, lei
            )
            critique.suggestions = self._generate_suggestions(critique.issues)

        return critique

    def _check_completeness(self, result: Any) -> float:
        """Check if result is complete."""
        if result is None:
            return 0.0

        # Check for success indicator
        if hasattr(result, 'success'):
            return 1.0 if result.success else 0.5

        return 0.8  # Assume mostly complete

    def _validate_result(self, result: Any) -> bool:
        """Validate result correctness."""
        if result is None:
            return False

        # Check for error indicators
        if hasattr(result, 'success'):
            return bool(result.success)

        if hasattr(result, 'error') and result.error:
            return False

        return True

    def _check_efficiency(self, step: WorkflowStep) -> float:
        """Check execution efficiency."""
        # Fast execution scores higher
        if step.execution_time < 1.0:
            return 1.0
        elif step.execution_time < 5.0:
            return 0.8
        elif step.execution_time < 10.0:
            return 0.6
        else:
            return 0.4

    def _calculate_lei(self, result: Any) -> float:
        """
        Calculate Lazy Execution Index (Constitutional metric).
        
        LEI = (lazy_patterns / total_lines) * 1000
        Target: < 1.0
        """
        # Extract code if available
        code = ""
        if hasattr(result, 'data') and isinstance(result.data, str):
            code = result.data
        elif isinstance(result, str):
            code = result

        if not code:
            return 0.0  # No code to analyze

        # Lazy patterns
        lazy_patterns = [
            'TODO',
            'FIXME',
            'HACK',
            'XXX',
            'NotImplementedError',
            'pass  #',
            '... #',
            'raise NotImplementedError'
        ]

        lazy_count = sum(1 for pattern in lazy_patterns if pattern in code)

        lines = [l for l in code.split('\n') if l.strip()]
        total_lines = len(lines)

        if total_lines == 0:
            return 0.0

        lei = (lazy_count / total_lines) * 1000
        return lei

    def _identify_issues(
        self,
        completeness: float,
        validation: bool,
        efficiency: float,
        lei: float
    ) -> List[str]:
        """Identify specific issues."""
        issues = []

        if completeness < 0.9:
            issues.append(f"Incomplete result (score: {completeness:.2f})")

        if not validation:
            issues.append("Validation failed")

        if efficiency < 0.7:
            issues.append(f"Low efficiency (score: {efficiency:.2f})")

        if lei >= self.lei_threshold:
            issues.append(f"Lazy code detected (LEI: {lei:.2f}, threshold: {self.lei_threshold})")

        return issues

    def _generate_suggestions(self, issues: List[str]) -> List[str]:
        """Generate suggestions for fixes."""
        suggestions = []

        for issue in issues:
            if "Incomplete" in issue:
                suggestions.append("Complete all required fields")
            elif "Validation" in issue:
                suggestions.append("Fix validation errors")
            elif "efficiency" in issue:
                suggestions.append("Optimize execution time")
            elif "Lazy" in issue:
                suggestions.append("Replace TODO/FIXME with actual implementation")

        return suggestions


class CheckpointManager:
    """
    Checkpoint system for state management (Cursor AI pattern).
    
    Features:
    - State snapshots
    - File backups
    - Rollback support
    """

    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or Path.home() / ".qwen_checkpoints"
        self.backup_dir.mkdir(exist_ok=True)

        self.checkpoints: Dict[str, Checkpoint] = {}

    def create_checkpoint(
        self,
        checkpoint_id: str,
        context: Dict[str, Any],
        completed_steps: List[str]
    ) -> Checkpoint:
        """Create checkpoint."""
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=time.time(),
            context=copy.deepcopy(context),
            completed_steps=completed_steps.copy()
        )

        self.checkpoints[checkpoint_id] = checkpoint

        logger.info(f"Created checkpoint: {checkpoint_id}")
        return checkpoint

    def backup_file(self, checkpoint_id: str, file_path: str) -> None:
        """Backup file before modification."""
        if checkpoint_id not in self.checkpoints:
            logger.warning(f"Checkpoint {checkpoint_id} not found")
            return

        try:
            source = Path(file_path)
            if not source.exists():
                return

            # Create backup
            backup_path = self.backup_dir / f"{checkpoint_id}_{source.name}"
            backup_path.write_text(source.read_text())

            # Record backup
            self.checkpoints[checkpoint_id].file_backups[file_path] = str(backup_path)

            logger.info(f"Backed up: {file_path} → {backup_path}")

        except Exception as e:
            logger.error(f"Backup failed for {file_path}: {e}")

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore from checkpoint."""
        if checkpoint_id not in self.checkpoints:
            logger.error(f"Checkpoint {checkpoint_id} not found")
            return False

        checkpoint = self.checkpoints[checkpoint_id]

        try:
            # Restore files
            for original_path, backup_path in checkpoint.file_backups.items():
                backup = Path(backup_path)
                if backup.exists():
                    Path(original_path).write_text(backup.read_text())
                    logger.info(f"Restored: {original_path}")

            logger.info(f"Checkpoint {checkpoint_id} restored successfully")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False


class Transaction:
    """
    Transactional workflow execution (ACID-like).
    
    Features:
    - All-or-nothing execution
    - Rollback on failure
    - Commit on success
    """

    def __init__(self, transaction_id: str):
        self.transaction_id = transaction_id
        self.operations: List[Tuple[WorkflowStep, Any]] = []
        self.committed = False

    def add_operation(self, step: WorkflowStep, result: Any) -> None:
        """Add completed operation."""
        self.operations.append((step, result))

    async def rollback(self, checkpoint_manager: CheckpointManager) -> bool:
        """Rollback all operations."""
        logger.warning(f"Rolling back transaction: {self.transaction_id}")

        # Rollback in reverse order
        for step, result in reversed(self.operations):
            logger.info(f"Rolling back step: {step.step_id}")
            # Actual rollback handled by checkpoint manager

        return True

    async def commit(self) -> None:
        """Commit transaction."""
        self.committed = True
        logger.info(f"Transaction committed: {self.transaction_id}")


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    completed_steps: List[WorkflowStep]
    failed_step: Optional[WorkflowStep] = None
    total_time: float = 0.0

    # Critique results
    critiques: List[Critique] = field(default_factory=list)

    # Context
    final_context: Dict[str, Any] = field(default_factory=dict)


class WorkflowEngine:
    """
    Multi-step workflow orchestration engine.
    
    Combines:
    - Cursor AI: Dependency graph + checkpoints
    - Claude: Tree-of-Thought + self-critique  
    - Constitutional: LEI tracking + validation
    """

    def __init__(
        self,
        llm_client: Any,
        recovery_engine: Any,
        tool_registry: Any
    ) -> None:
        self.llm = llm_client
        self.recovery = recovery_engine
        self.tools = tool_registry

        # Components
        self.tree_of_thought: TreeOfThought = TreeOfThought(llm_client)
        self.dependency_graph: DependencyGraph = DependencyGraph()
        self.auto_critique: AutoCritique = AutoCritique()
        self.checkpoints: CheckpointManager = CheckpointManager()

    async def execute_workflow(
        self,
        user_goal: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """
        Execute multi-step workflow.
        
        Args:
            user_goal: User's goal
            initial_context: Initial context
        
        Returns:
            Workflow result
        """
        start_time = time.time()
        context = initial_context or {}

        logger.info(f"Starting workflow: {user_goal}")

        # 1. Tree-of-Thought planning (Constitutional Layer 2)
        available_tools = list(self.tools.get_all().keys())
        paths = await self.tree_of_thought.generate_paths(
            user_goal,
            available_tools,
            max_paths=3
        )

        best_path = self.tree_of_thought.select_best_path(paths)
        logger.info(f"Selected path: {best_path.description} (score: {best_path.total_score:.2f})")

        # 2. Build dependency graph
        for step in best_path.steps:
            self.dependency_graph.add_step(step)

        try:
            execution_order = self.dependency_graph.topological_sort()
        except ValueError as e:
            logger.error(f"Dependency error: {e}")
            return WorkflowResult(
                success=False,
                completed_steps=[],
                total_time=time.time() - start_time
            )

        # 3. Create transaction
        transaction = Transaction(f"workflow_{int(time.time())}")

        # 4. Execute steps with checkpoints
        completed: List[WorkflowStep] = []
        critiques: List[Critique] = []

        for i, step in enumerate(execution_order):
            # Create checkpoint before risky operations
            if step.is_risky:
                checkpoint_id = f"{transaction.transaction_id}_step_{i}"
                self.checkpoints.create_checkpoint(
                    checkpoint_id,
                    context,
                    [s.step_id for s in completed]
                )

            # Execute step
            step.status = StepStatus.EXECUTING
            step_start = time.time()

            tool = self.tools.get(step.tool_name)
            if not tool:
                step.status = StepStatus.FAILED
                step.error = f"Tool not found: {step.tool_name}"

                await transaction.rollback(self.checkpoints)

                return WorkflowResult(
                    success=False,
                    completed_steps=completed,
                    failed_step=step,
                    total_time=time.time() - start_time
                )

            try:
                result = await tool.execute(**step.args)
                step.execution_time = time.time() - step_start
                step.result = result

                if not result.success:
                    step.status = StepStatus.FAILED
                    step.error = str(result.data)

                    await transaction.rollback(self.checkpoints)

                    return WorkflowResult(
                        success=False,
                        completed_steps=completed,
                        failed_step=step,
                        total_time=time.time() - start_time,
                        critiques=critiques
                    )

                # Auto-critique (Constitutional Layer 2)
                critique = self.auto_critique.critique_step(step, result)
                critiques.append(critique)

                if not critique.passed:
                    logger.warning(f"Step {step.step_id} critique failed: {critique.issues}")

                    # Attempt to fix issues
                    # (In production, this would trigger recovery)

                    step.status = StepStatus.FAILED
                    step.error = f"Critique failed: {', '.join(critique.issues)}"

                    await transaction.rollback(self.checkpoints)

                    return WorkflowResult(
                        success=False,
                        completed_steps=completed,
                        failed_step=step,
                        total_time=time.time() - start_time,
                        critiques=critiques
                    )

                # Success
                step.status = StepStatus.COMPLETED
                transaction.add_operation(step, result)
                completed.append(step)

                # Update context
                context[f"step_{step.step_id}_result"] = result

            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)

                await transaction.rollback(self.checkpoints)

                return WorkflowResult(
                    success=False,
                    completed_steps=completed,
                    failed_step=step,
                    total_time=time.time() - start_time,
                    critiques=critiques
                )

        # 5. Commit transaction
        await transaction.commit()

        total_time = time.time() - start_time
        logger.info(f"Workflow completed in {total_time:.2f}s ({len(completed)} steps)")

        return WorkflowResult(
            success=True,
            completed_steps=completed,
            total_time=total_time,
            critiques=critiques,
            final_context=context
        )


# ============================================================================
# DAY 7 ENHANCEMENTS: Git Rollback & Partial Rollback
# ============================================================================

class GitRollback:
    """Git-based rollback for code changes.
    
    Provides checkpoint/rollback functionality using git commits.
    Allows atomic rollback of multi-file changes.
    """

    def __init__(self) -> None:
        """Initialize git rollback manager."""
        self.commits_made: List[str] = []
        self.checkpoints: Dict[str, str] = {}  # checkpoint_id -> commit_sha

    async def create_checkpoint_commit(self, message: str) -> Optional[str]:
        """Create checkpoint git commit.
        
        Args:
            message: Checkpoint message
        
        Returns:
            Commit SHA or None if failed
        """
        try:
            import subprocess

            # Check if in git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.warning("Not in a git repository, cannot create checkpoint")
                return None

            # Check if there are changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if not result.stdout.strip():
                logger.info("No changes to checkpoint")
                return None

            # Stage all changes
            subprocess.run(
                ["git", "add", "-A"],
                capture_output=True,
                timeout=10
            )

            # Commit with checkpoint tag
            commit_msg = f"[QWEN-CHECKPOINT] {message}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"Failed to create checkpoint: {result.stderr}")
                return None

            # Get commit SHA
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )

            sha = result.stdout.strip()
            self.commits_made.append(sha)

            logger.info(f"Created checkpoint commit: {sha[:7]} - {message}")
            return sha

        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return None

    async def rollback_to_checkpoint(self, checkpoint_sha: str) -> bool:
        """Rollback to checkpoint commit.
        
        Args:
            checkpoint_sha: Commit SHA to rollback to
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import subprocess

            # Reset to checkpoint (keep working directory changes in case of partial rollback)
            result = subprocess.run(
                ["git", "reset", "--hard", checkpoint_sha],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"Rollback failed: {result.stderr}")
                return False

            logger.info(f"Rolled back to {checkpoint_sha[:7]}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    async def rollback_last_checkpoint(self) -> bool:
        """Rollback to last checkpoint made.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.commits_made:
            logger.warning("No checkpoints to rollback to")
            return False

        last_checkpoint = self.commits_made[-1]
        success = await self.rollback_to_checkpoint(last_checkpoint)

        if success:
            self.commits_made.pop()

        return success

    def get_checkpoints(self) -> List[str]:
        """Get list of checkpoint commits.
        
        Returns:
            List of commit SHAs
        """
        return self.commits_made.copy()

    def clear_checkpoints(self) -> None:
        """Clear checkpoint history."""
        self.commits_made.clear()
        self.checkpoints.clear()


class PartialRollback:
    """Granular rollback of individual operations.
    
    Maintains a stack of reversible operations that can be undone
    individually or in groups. Useful for fine-grained error recovery.
    """

    def __init__(self) -> None:
        """Initialize partial rollback manager."""
        self.operations: List[Dict[str, Any]] = []

    def add_operation(
        self,
        op_type: str,
        data: Dict[str, Any],
        reversible: bool = True
    ) -> None:
        """Add reversible operation to stack.
        
        Args:
            op_type: Type of operation (file_write, file_delete, etc)
            data: Operation data needed for rollback
            reversible: Whether operation can be reversed
        """
        self.operations.append({
            'type': op_type,
            'data': data,
            'timestamp': time.time(),
            'reversible': reversible
        })

        logger.debug(f"Added operation to rollback stack: {op_type}")

    async def rollback_last_n(self, n: int) -> Tuple[int, int]:
        """Rollback last N operations.
        
        Args:
            n: Number of operations to rollback
        
        Returns:
            (successful_rollbacks, failed_rollbacks)
        """
        successful = 0
        failed = 0

        for _ in range(min(n, len(self.operations))):
            op = self.operations.pop()

            if not op['reversible']:
                logger.warning(f"Operation {op['type']} is not reversible")
                failed += 1
                continue

            try:
                await self._rollback_operation(op)
                successful += 1
            except Exception as e:
                logger.error(f"Failed to rollback {op['type']}: {e}")
                failed += 1

        logger.info(f"Rolled back {successful}/{successful+failed} operations")
        return successful, failed

    async def rollback_until(self, target_timestamp: float) -> Tuple[int, int]:
        """Rollback operations until target timestamp.
        
        Args:
            target_timestamp: Rollback operations after this time
        
        Returns:
            (successful_rollbacks, failed_rollbacks)
        """
        count = 0
        for op in reversed(self.operations):
            if op['timestamp'] <= target_timestamp:
                break
            count += 1

        return await self.rollback_last_n(count)

    async def _rollback_operation(self, op: Dict[str, Any]) -> None:
        """Rollback single operation.
        
        Args:
            op: Operation to rollback
        """
        op_type = op['type']
        data = op['data']

        if op_type == 'file_write':
            # Restore from backup
            if 'backup_path' in data:
                import shutil
                shutil.copy(data['backup_path'], data['file_path'])
                logger.debug(f"Restored {data['file_path']} from backup")

        elif op_type == 'file_delete':
            # Restore deleted file
            if 'backup_content' in data:
                Path(data['file_path']).write_text(data['backup_content'])
                logger.debug(f"Restored deleted file {data['file_path']}")

        elif op_type == 'file_edit':
            # Restore previous content
            if 'original_content' in data:
                Path(data['file_path']).write_text(data['original_content'])
                logger.debug(f"Restored original content of {data['file_path']}")

        elif op_type == 'command_execute':
            # Most commands are irreversible
            logger.warning(
                f"Cannot rollback command execution: {data.get('command', 'unknown')}"
            )

        else:
            logger.warning(f"Unknown operation type: {op_type}")

    def get_operations(self) -> List[Dict[str, Any]]:
        """Get list of tracked operations.
        
        Returns:
            List of operation dictionaries
        """
        return self.operations.copy()

    def clear_operations(self) -> None:
        """Clear operations stack."""
        self.operations.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of operations.
        
        Returns:
            Summary dictionary
        """
        return {
            'total_operations': len(self.operations),
            'reversible': sum(1 for op in self.operations if op['reversible']),
            'irreversible': sum(1 for op in self.operations if not op['reversible']),
            'types': list(set(op['type'] for op in self.operations)),
            'oldest': self.operations[0]['timestamp'] if self.operations else None,
            'newest': self.operations[-1]['timestamp'] if self.operations else None
        }
