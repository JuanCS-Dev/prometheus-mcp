"""Tests for WorkflowLibrary."""

from jdev_cli.orchestration.workflows import WorkflowLibrary, WorkflowType

def test_workflow_library_initialization():
    """Test that library initializes with default workflows."""
    lib = WorkflowLibrary()
    workflows = lib.list_workflows()
    assert len(workflows) >= 3

    names = [w.name for w in workflows]
    assert "setup-fastapi" in names
    assert "add-auth" in names
    assert "migrate-fastapi" in names

def test_get_workflow():
    """Test retrieving a specific workflow."""
    lib = WorkflowLibrary()
    workflow = lib.get_workflow("setup-fastapi")

    assert workflow is not None
    assert workflow.name == "setup-fastapi"
    assert workflow.type == WorkflowType.SCAFFOLD
    assert len(workflow.steps) == 4
    assert "project_name" in workflow.parameters

def test_workflow_steps_structure():
    """Test that workflow steps have correct structure."""
    lib = WorkflowLibrary()
    workflow = lib.get_workflow("add-auth")

    assert workflow is not None
    steps = workflow.steps

    # Check sequence
    assert steps[0].agent == "explorer"
    assert steps[1].agent == "architect"
    assert steps[2].agent == "planner"
    assert steps[3].agent == "refactorer"
    assert steps[4].agent == "reviewer"

    # Check params
    assert "{user_model}" in steps[1].params["task"]

def test_get_nonexistent_workflow():
    """Test retrieving a non-existent workflow."""
    lib = WorkflowLibrary()
    workflow = lib.get_workflow("non-existent")
    assert workflow is None
