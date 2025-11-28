"""Workflow library for DevSquad."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class WorkflowType(Enum):
    SCAFFOLD = "scaffold"
    FEATURE = "feature"
    MIGRATION = "migration"
    REFACTOR = "refactor"
    CUSTOM = "custom"

@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    description: str
    agent: str  # "architect", "explorer", "planner", "refactorer", "reviewer"
    params: Dict[str, Any] = field(default_factory=dict)
    required: bool = True

@dataclass
class Workflow:
    """A predefined workflow definition."""
    id: str
    name: str
    description: str
    type: WorkflowType
    steps: List[WorkflowStep]
    parameters: Dict[str, str] = field(default_factory=dict)  # name -> description
    created_at: datetime = field(default_factory=datetime.now)

class WorkflowLibrary:
    """Library of predefined workflows."""

    def __init__(self) -> None:
        """Initialize workflow library with default workflows."""
        self.workflows: Dict[str, Workflow] = {}
        self._register_defaults()

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self.workflows.get(name)

    def list_workflows(self) -> List[Workflow]:
        """List all available workflows."""
        return list(self.workflows.values())

    def _register_defaults(self) -> None:
        """Register default workflows."""

        # 1. Setup FastAPI Project
        self.register(Workflow(
            id="setup-fastapi",
            name="setup-fastapi",
            description="Scaffold a new production-ready FastAPI project",
            type=WorkflowType.SCAFFOLD,
            parameters={
                "project_name": "Name of the project directory",
                "python_version": "Python version (default: 3.11)"
            },
            steps=[
                WorkflowStep(
                    name="Analyze Requirements",
                    description="Analyze project requirements and structure",
                    agent="architect",
                    params={"task": "Design a production-ready FastAPI project structure for {project_name}"}
                ),
                WorkflowStep(
                    name="Create Plan",
                    description="Generate execution plan for scaffolding",
                    agent="planner",
                    params={"task": "Create detailed plan to scaffold FastAPI project '{project_name}'"}
                ),
                WorkflowStep(
                    name="Scaffold Project",
                    description="Execute scaffolding plan",
                    agent="refactorer",
                    params={"task": "Execute plan to create FastAPI project '{project_name}'"}
                ),
                WorkflowStep(
                    name="Review Code",
                    description="Validate project structure and configuration",
                    agent="reviewer",
                    params={"task": "Review created FastAPI project structure and configuration"}
                )
            ]
        ))

        # 2. Add Authentication
        self.register(Workflow(
            id="add-auth",
            name="add-auth",
            description="Add JWT authentication with refresh tokens",
            type=WorkflowType.FEATURE,
            parameters={
                "user_model": "Name of user model (default: User)",
                "auth_route": "Authentication route prefix (default: /auth)"
            },
            steps=[
                WorkflowStep(
                    name="Analyze Existing Code",
                    description="Understand current project structure",
                    agent="explorer",
                    params={"task": "Find user models, database config, and API structure"}
                ),
                WorkflowStep(
                    name="Design Auth System",
                    description="Design JWT authentication architecture",
                    agent="architect",
                    params={"task": "Design JWT auth system with access/refresh tokens for {user_model}"}
                ),
                WorkflowStep(
                    name="Plan Implementation",
                    description="Create implementation steps",
                    agent="planner",
                    params={"task": "Create plan to implement JWT auth system"}
                ),
                WorkflowStep(
                    name="Implement Auth",
                    description="Write authentication code",
                    agent="refactorer",
                    params={"task": "Implement JWT auth system according to plan"}
                ),
                WorkflowStep(
                    name="Security Review",
                    description="Validate security implementation",
                    agent="reviewer",
                    params={"task": "Review authentication implementation for security vulnerabilities"}
                )
            ]
        ))

        # 3. Migrate to FastAPI
        self.register(Workflow(
            id="migrate-fastapi",
            name="migrate-fastapi",
            description="Plan migration from Flask/Django to FastAPI",
            type=WorkflowType.MIGRATION,
            parameters={
                "source_framework": "Current framework (flask/django)",
                "scope": "Scope of migration (full/partial)"
            },
            steps=[
                WorkflowStep(
                    name="Analyze Source",
                    description="Analyze existing codebase",
                    agent="explorer",
                    params={"task": "Analyze {source_framework} project structure and dependencies"}
                ),
                WorkflowStep(
                    name="Feasibility Study",
                    description="Assess migration feasibility and risks",
                    agent="architect",
                    params={"task": "Analyze feasibility of migrating from {source_framework} to FastAPI"}
                ),
                WorkflowStep(
                    name="Migration Plan",
                    description="Create detailed migration strategy",
                    agent="planner",
                    params={"task": "Create step-by-step migration plan from {source_framework} to FastAPI"}
                )
                # Note: Execution is usually too large for a single run, so we stop at planning
            ]
        ))

    def register(self, workflow: Workflow) -> None:
        """Register a new workflow."""
        self.workflows[workflow.name] = workflow
