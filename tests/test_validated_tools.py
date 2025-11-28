"""
Tests for ValidatedTool base class.

Boris Cherny: "Tests or it didn't happen."
"""

import pytest
from typing import Dict, Any

from jdev_cli.tools.validated import ValidatedTool, validate_tool_inputs
from jdev_cli.tools.base import ToolResult
from jdev_cli.core.validation import Required, TypeCheck


class MockValidatedTool(ValidatedTool):
    """Mock tool for testing validation."""

    def get_name(self) -> str:
        return "mock_tool"

    def get_description(self) -> str:
        return "Mock tool for testing"

    def get_validators(self) -> Dict[str, Any]:
        return {
            'path': Required('path'),
            'content': TypeCheck(str, 'content')
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute after validation."""
        return ToolResult(
            success=True,
            data={'executed_with': kwargs},
            metadata={'validated': True}
        )


class TestValidatedTool:
    """Test suite for ValidatedTool."""

    @pytest.mark.asyncio
    async def test_valid_inputs_pass(self):
        """Valid inputs should pass validation and execute."""
        tool = MockValidatedTool()

        result = await tool.execute(
            path="/tmp/test.txt",
            content="test content",
            mode="rw"
        )

        assert result.success is True
        assert result.metadata.get('validated') is True
        assert 'executed_with' in result.data

    @pytest.mark.asyncio
    async def test_missing_required_fails(self):
        """Missing required parameter should fail validation."""
        tool = MockValidatedTool()

        result = await tool.execute(
            content="test content",
            mode="rw"
            # Missing 'path'
        )

        assert result.success is False
        assert "Validation failed" in result.error
        assert "path" in result.error.lower()

    @pytest.mark.asyncio
    async def test_wrong_type_fails(self):
        """Wrong type should fail validation."""
        tool = MockValidatedTool()

        result = await tool.execute(
            path="/tmp/test.txt",
            content=123,  # Should be str
            mode="rw"
        )

        assert result.success is False
        assert "content" in result.error.lower()

    @pytest.mark.asyncio
    async def test_multiple_validation_errors(self):
        """Multiple validation errors should all be reported."""
        tool = MockValidatedTool()

        result = await tool.execute(
            content="test"  # Missing path
        )

        assert result.success is False
        assert "path" in result.error.lower()

    @pytest.mark.asyncio
    async def test_validation_errors_in_metadata(self):
        """Validation errors should be in metadata."""
        tool = MockValidatedTool()

        result = await tool.execute(
            content="test"
            # Missing path
        )

        assert result.success is False
        assert 'validation_errors' in result.metadata
        assert len(result.metadata['validation_errors']) >= 1  # path

    @pytest.mark.asyncio
    async def test_extra_params_allowed(self):
        """Extra parameters should be allowed (not validated)."""
        tool = MockValidatedTool()

        result = await tool.execute(
            path="/tmp/test.txt",
            content="test",
            extra_param="allowed"  # Not validated, should be ok
        )

        assert result.success is True


class TestValidateToolInputs:
    """Test standalone validation function."""

    def test_valid_inputs(self):
        """Valid inputs should pass."""
        validators = {
            'name': Required('name'),
            'age': TypeCheck(int, 'age')
        }

        result = validate_tool_inputs(
            {'name': 'John', 'age': 30},
            validators
        )

        assert result.valid is True
        assert len(result.errors) == 0

    def test_invalid_inputs(self):
        """Invalid inputs should fail."""
        validators = {
            'name': Required('name'),
            'age': TypeCheck(int, 'age')
        }

        result = validate_tool_inputs(
            {'age': 'thirty'},  # Missing name, wrong type for age
            validators
        )

        assert result.valid is False
        assert len(result.errors) >= 2

    def test_empty_validators(self):
        """Empty validators should pass anything."""
        result = validate_tool_inputs(
            {'anything': 'goes'},
            {}
        )

        assert result.valid is True
        assert len(result.errors) == 0


class TestValidatedToolIntegration:
    """Integration tests for ValidatedTool in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_file_write_tool_validation(self):
        """Test file write tool with validation."""
        class FileWriteTool(ValidatedTool):
            def get_name(self) -> str:
                return "write_file"

            def get_description(self) -> str:
                return "Write content to file"

            def get_validators(self) -> Dict[str, Any]:
                return {
                    'path': Required('path'),
                    'content': TypeCheck(str, 'content')
                }

            async def _execute_validated(self, path: str, content: str, **kwargs) -> ToolResult:
                # In real tool, would write to file
                return ToolResult(
                    success=True,
                    data={'bytes_written': len(content), 'path': path}
                )

        tool = FileWriteTool()

        # Valid case
        result = await tool.execute(path="/tmp/test.txt", content="Hello World")
        assert result.success is True
        assert result.data['bytes_written'] == 11
        assert result.data['path'] == "/tmp/test.txt"

        # Invalid case - missing content
        result = await tool.execute(path="/tmp/test.txt")
        assert result.success is False
        assert "content" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execution_error_handling(self):
        """Test that execution errors are caught and returned properly."""
        class FailingTool(ValidatedTool):
            def get_name(self) -> str:
                return "failing_tool"

            def get_description(self) -> str:
                return "Tool that fails"

            def get_validators(self) -> Dict[str, Any]:
                return {'input': Required('input')}

            async def _execute_validated(self, **kwargs) -> ToolResult:
                raise RuntimeError("Intentional failure")

        tool = FailingTool()
        result = await tool.execute(input="test")

        assert result.success is False
        assert "Execution failed" in result.error
        assert result.metadata['error_type'] == 'execution'
        assert result.metadata['exception'] == 'RuntimeError'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
