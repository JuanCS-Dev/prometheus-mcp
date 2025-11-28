"""
planner/dependency.py: Dependency Graph Analysis.

Analyzes step dependencies to find:
- Parallel execution opportunities
- Critical path (longest chain)
- Circular dependencies
- Optimal execution order
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class DependencyAnalyzer:
    """
    Analyzes step dependencies to find parallel execution opportunities,
    critical paths, and detect circular dependencies.

    Example:
        steps = [step1, step2, step3]  # SOPStep objects
        parallel_groups = DependencyAnalyzer.find_parallel_groups(steps)
        critical_path = DependencyAnalyzer.find_critical_path(steps)
        cycles = DependencyAnalyzer.detect_cycles(steps)
    """

    @staticmethod
    def build_graph(steps: List[Any]) -> Dict[str, List[str]]:
        """Build adjacency list from dependencies."""
        graph = {}
        for step in steps:
            # Handle both .id and .step_number patterns
            step_id = getattr(step, 'id', None) or str(getattr(step, 'step_number', id(step)))
            deps = getattr(step, 'dependencies', [])
            # Convert int dependencies to strings if needed
            graph[step_id] = [str(d) for d in deps] if deps else []
        return graph

    @staticmethod
    def find_parallel_groups(steps: List[Any]) -> List[List[str]]:
        """
        Find groups of steps that can execute in parallel.
        Steps with no dependencies on each other can run together.

        Uses topological sort to find execution levels.
        """
        if not steps:
            return []

        graph = DependencyAnalyzer.build_graph(steps)
        step_ids = list(graph.keys())

        # Calculate in-degree for each node
        in_degree = {sid: 0 for sid in step_ids}
        for sid, deps in graph.items():
            for dep in deps:
                if dep in step_ids:  # Only count valid dependencies
                    pass  # dep points TO sid, so sid depends on dep
            # Count how many steps this step depends on
            in_degree[sid] = len([d for d in deps if d in step_ids])

        levels = []
        processed = set()

        while len(processed) < len(step_ids):
            # Current level: nodes with no remaining dependencies
            current_level = [
                sid for sid in step_ids
                if sid not in processed and in_degree[sid] == 0
            ]

            if not current_level:
                # Cycle detected or invalid graph
                remaining = [sid for sid in step_ids if sid not in processed]
                levels.append(remaining)
                break

            levels.append(current_level)

            # Mark as processed and update in-degrees
            for sid in current_level:
                processed.add(sid)
                # Decrease in-degree of steps that depend on this one
                for other_sid, deps in graph.items():
                    if sid in deps and other_sid not in processed:
                        in_degree[other_sid] -= 1

        return levels

    @staticmethod
    def find_critical_path(steps: List[Any]) -> List[str]:
        """
        Find critical path: longest dependency chain.
        This determines minimum execution time.

        Uses dynamic programming with memoization.
        """
        if not steps:
            return []

        graph = DependencyAnalyzer.build_graph(steps)

        # Build step map with costs
        step_map = {}
        for step in steps:
            step_id = getattr(step, 'id', None) or str(getattr(step, 'step_number', id(step)))
            cost = getattr(step, 'cost', 1.0)
            deps = graph.get(step_id, [])
            step_map[step_id] = {'cost': cost, 'deps': deps}

        # Calculate longest path using dynamic programming
        memo: Dict[str, Tuple[float, List[str]]] = {}

        def longest_path(step_id: str) -> Tuple[float, List[str]]:
            if step_id in memo:
                return memo[step_id]

            if step_id not in step_map:
                return (0.0, [])

            step_info = step_map[step_id]
            deps = step_info['deps']
            cost = step_info['cost']

            if not deps:
                result = (cost, [step_id])
            else:
                # Find longest path through dependencies
                max_cost = 0.0
                max_path: List[str] = []

                for dep_id in deps:
                    if dep_id in step_map:
                        dep_cost, dep_path = longest_path(dep_id)
                        if dep_cost > max_cost:
                            max_cost = dep_cost
                            max_path = dep_path

                result = (max_cost + cost, max_path + [step_id])

            memo[step_id] = result
            return result

        # Find overall longest path
        max_cost = 0.0
        critical_path: List[str] = []

        for step_id in step_map:
            cost, path = longest_path(step_id)
            if cost > max_cost:
                max_cost = cost
                critical_path = path

        return critical_path

    @staticmethod
    def detect_cycles(steps: List[Any]) -> List[List[str]]:
        """
        Detect circular dependencies using DFS.

        Returns list of cycles found (each cycle is a list of step IDs).
        """
        if not steps:
            return []

        graph = DependencyAnalyzer.build_graph(steps)
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path = path + [node]

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor) if neighbor in path else -1
                    if cycle_start >= 0:
                        cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)

        for step in steps:
            step_id = getattr(step, 'id', None) or str(getattr(step, 'step_number', id(step)))
            if step_id not in visited:
                dfs(step_id, [])

        return cycles

    @staticmethod
    def get_execution_order(steps: List[Any]) -> List[str]:
        """
        Get a valid execution order respecting dependencies.
        Returns flattened list of step IDs.
        """
        parallel_groups = DependencyAnalyzer.find_parallel_groups(steps)
        return [step_id for group in parallel_groups for step_id in group]

    @staticmethod
    def validate_dependencies(steps: List[Any]) -> Dict[str, Any]:
        """
        Validate dependency graph and return analysis.

        Returns:
            Dict with 'valid', 'cycles', 'parallel_groups', 'critical_path'
        """
        cycles = DependencyAnalyzer.detect_cycles(steps)
        parallel_groups = DependencyAnalyzer.find_parallel_groups(steps)
        critical_path = DependencyAnalyzer.find_critical_path(steps)

        return {
            'valid': len(cycles) == 0,
            'cycles': cycles,
            'parallel_groups': parallel_groups,
            'critical_path': critical_path,
            'total_levels': len(parallel_groups),
            'max_parallelism': max(len(g) for g in parallel_groups) if parallel_groups else 0,
        }
