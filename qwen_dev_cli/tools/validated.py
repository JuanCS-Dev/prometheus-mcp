"""
Validated tool base class.

Boris Cherny: "Validate early, fail fast with clear feedback."

This module provides a base class that automatically validates
tool inputs using our validation system before execution.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from .base import Tool, ToolResult
from ..core.validation import (
    Validator,
    ValidationResultImpl,
    Required,
    TypeCheck,
    validate_file_path
)
from ..core.errors import ValidationError as ErrorValidationError


class ValidatedTool(Tool, ABC):
    """
    Base class for tools with automatic input validation.
    
    Subclasses should:
    1. Define validators in get_validators()
    2. Implement _execute_validated() instead of execute()
    
    The base class will automatically validate inputs before
    calling _execute_validated().
    """
    
    def get_validators(self) -> Dict[str, Validator]:
        """
        Return validators for each parameter.
        
        Returns:
            Dict mapping parameter name to Validator instance
        
        Example:
            return {
                'path': Required('path'),
                'content': TypeCheck(str, 'content')
            }
        """
        return {}
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute tool with validation.
        
        This wraps the actual execution with validation.
        Subclasses should implement _execute_validated() instead.
        """
        # Validate inputs
        validation_result = self._validate_inputs(kwargs)
        
        if not validation_result.valid:
            # Return validation errors
            error_msg = "\n".join(validation_result.errors)
            return ToolResult(
                success=False,
                error=f"Validation failed:\n{error_msg}",
                metadata={
                    'validation_errors': validation_result.errors,
                    'validation_warnings': validation_result.warnings
                }
            )
        
        # Show warnings if any
        if validation_result.warnings:
            # Could log or display warnings here
            pass
        
        # Execute the actual tool logic
        try:
            return await self._execute_validated(**kwargs)
        except ErrorValidationError as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={'error_type': 'validation', 'recoverable': e.recoverable}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Execution failed: {e}",
                metadata={'error_type': 'execution', 'exception': type(e).__name__}
            )
    
    @abstractmethod
    async def _execute_validated(self, **kwargs) -> ToolResult:
        """
        Execute tool logic after validation.
        
        Subclasses must implement this method.
        All inputs are guaranteed to be valid when this is called.
        """
        raise NotImplementedError(f"{self.__class__.__name__}._execute_validated() not implemented")
    
    def _validate_inputs(self, inputs: Dict[str, Any]) -> ValidationResultImpl:
        """
        Validate inputs against defined validators.
        
        Args:
            inputs: Input parameters to validate
        
        Returns:
            ValidationResult with errors/warnings
        """
        result = ValidationResultImpl.success()
        validators = self.get_validators()
        
        for param_name, validator in validators.items():
            value = inputs.get(param_name)
            
            # Validate this parameter
            param_result = validator.validate(value)
            
            if not param_result.valid:
                for error in param_result.errors:
                    result.add_error(f"{param_name}: {error}")
            
            for warning in param_result.warnings:
                result.add_warning(f"{param_name}: {warning}")
        
        return result


# Helper function for quick validation
def validate_tool_inputs(
    inputs: Dict[str, Any],
    validators: Dict[str, Validator]
) -> ValidationResultImpl:
    """
    Validate tool inputs standalone (without ValidatedTool class).
    
    Args:
        inputs: Input parameters
        validators: Validators for each parameter
    
    Returns:
        ValidationResult
    
    Example:
        validators = {
            'path': Required('path'),
            'mode': OneOf(['r', 'w', 'a'], 'mode')
        }
        result = validate_tool_inputs(inputs, validators)
        if not result.valid:
            raise ValidationError(result.errors[0])
    """
    result = ValidationResultImpl.success()
    
    for param_name, validator in validators.items():
        value = inputs.get(param_name)
        param_result = validator.validate(value)
        
        if not param_result.valid:
            for error in param_result.errors:
                result.add_error(f"{param_name}: {error}")
        
        for warning in param_result.warnings:
            result.add_warning(f"{param_name}: {warning}")
    
    return result


__all__ = [
    'ValidatedTool',
    'validate_tool_inputs',
]
