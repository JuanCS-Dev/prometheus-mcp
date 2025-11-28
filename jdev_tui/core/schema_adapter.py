"""
Schema Adapter
==============

Transforms internal tool schemas into Google Gemini SDK compatible FunctionDeclarations.
Handles strict Protobuf requirements and schema mismatches.

Author: JuanCS Dev
Date: 2025-11-28
"""

from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class SchemaAdapter:
    """Adapts internal tool schemas to Gemini SDK requirements."""

    @staticmethod
    def to_gemini_schema(internal_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms an internal tool schema into a Gemini-compatible schema dict.
        
        Args:
            internal_schema: The raw schema from ToolBridge
            
        Returns:
            A dictionary ready to be passed to FunctionDeclaration
        """
        # 1. Basic fields
        name = internal_schema.get("name", "")
        description = internal_schema.get("description", "")

        # 2. Process parameters
        raw_params = internal_schema.get("parameters", {})
        clean_params = SchemaAdapter._clean_object_schema(raw_params)

        return {
            "name": name,
            "description": description,
            "parameters": clean_params
        }

    @staticmethod
    def _clean_object_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively cleans a JSON schema object for Gemini compatibility.
        
        Transformations:
        - Converts property-level 'required=True' to top-level 'required' list
        - Removes 'default' fields (not supported in protobuf)
        - Ensures arrays have valid 'items' with 'type'
        - Removes 'title', 'additionalProperties' if present (cleanup)
        """
        if not isinstance(schema, dict):
            return schema

        clean_schema = {}

        # Copy allowed fields
        for key in ["type", "description", "enum", "format"]:
            if key in schema:
                clean_schema[key] = schema[key]

        # Handle 'properties' and 'required'
        if "properties" in schema:
            clean_props = {}
            required_fields = schema.get("required", [])
            # Ensure required is a list (internal schema might have it, but we rebuild it)
            if not isinstance(required_fields, list):
                required_fields = []

            for prop_name, prop_def in schema["properties"].items():
                if not isinstance(prop_def, dict):
                    continue

                # Check for property-level required=True (Internal format)
                if prop_def.get("required") is True:
                    if prop_name not in required_fields:
                        required_fields.append(prop_name)

                # Recursively clean the property definition
                clean_props[prop_name] = SchemaAdapter._clean_schema_node(prop_def)

            clean_schema["properties"] = clean_props
            if required_fields:
                clean_schema["required"] = required_fields

        return clean_schema

    @staticmethod
    def _clean_schema_node(node: Dict[str, Any]) -> Dict[str, Any]:
        """Cleaning for a single schema node (property or item)."""
        if not isinstance(node, dict):
            return node

        clean_node = {}

        # Copy allowed fields
        # Note: 'required' is NOT allowed here for boolean usage in Gemini
        # 'default' is NOT allowed
        for key in ["type", "description", "enum", "format"]:
            if key in node:
                clean_node[key] = node[key]

        # Handle Array Type
        if node.get("type") == "array":
            items = node.get("items", {})
            if not items:
                # Fallback for missing items
                items = {"type": "string"}
            elif "type" not in items:
                # Infer type if missing
                if "properties" in items:
                    items["type"] = "object"
                else:
                    items["type"] = "string"

            clean_node["items"] = SchemaAdapter._clean_schema_node(items)

        # Handle Object Type (Nested)
        elif node.get("type") == "object":
            # Recurse into object structure
            # We reuse _clean_object_schema logic but need to adapt it since
            # _clean_object_schema assumes it's processing the 'parameters' root or a full object definition
            nested_object = SchemaAdapter._clean_object_schema(node)
            clean_node.update(nested_object)

        return clean_node
