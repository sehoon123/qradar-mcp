# Copyright 2026 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
FastMCP Adapter for MCPTool
Bridges existing MCPTool implementations with FastMCP's decorator system.

This adapter preserves all existing tool logic including:
- Structured logging
- Input sanitization
- Audit logging
- Error handling
"""

from importlib import import_module
from inspect import Parameter, Signature
from typing import Any, Dict, Iterable, Optional

from fastmcp import FastMCP
from jsonschema import Draft7Validator
from pydantic import Field

from .base import MCPTool
from .capability_registry import CAPABILITY_SPECS, CapabilitySpec


def _json_schema_type_to_python(json_type: str) -> type:
    """Convert JSON Schema types to Python types"""
    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return type_mapping.get(json_type, str)


def _create_pydantic_fields(input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert JSON Schema to Pydantic field definitions"""
    pydantic_fields = {}
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    for param_name, param_def in properties.items():
        param_type = _json_schema_type_to_python(param_def.get("type", "string"))
        param_description = param_def.get("description", "")

        # Create Field with constraints
        field_kwargs = {"description": param_description}

        # Add numeric constraints
        if "minimum" in param_def:
            field_kwargs["ge"] = param_def["minimum"]
        if "maximum" in param_def:
            field_kwargs["le"] = param_def["maximum"]
        if "minLength" in param_def:
            field_kwargs["min_length"] = param_def["minLength"]
        if "maxLength" in param_def:
            field_kwargs["max_length"] = param_def["maxLength"]

        # Mark as required or optional
        if param_name in required:
            pydantic_fields[param_name] = (param_type, Field(**field_kwargs))
        else:
            default_value = param_def.get("default", None)
            pydantic_fields[param_name] = (
                Optional[param_type],
                Field(default_value, **field_kwargs)
            )

    return pydantic_fields


def _validate_json_schema(input_schema: Dict[str, Any], arguments: Dict[str, Any]) -> None:
    """Validate arguments against the original tool JSON Schema."""
    validator = Draft7Validator(input_schema)
    errors = sorted(validator.iter_errors(arguments), key=lambda error: list(error.path))
    if not errors:
        return

    error = errors[0]
    location = ".".join(str(part) for part in error.path)
    prefix = f"{location}: " if location else ""
    raise ValueError(f"Invalid tool arguments: {prefix}{error.message}")


def register_mcp_tool_with_fastmcp(mcp: FastMCP, tool: MCPTool) -> None:
    """
    Register an MCPTool instance with FastMCP using adapter pattern.

    This preserves all existing tool logic including:
    - Structured logging
    - Input sanitization
    - Audit logging
    - Error handling

    Args:
        mcp: FastMCP server instance
        tool: MCPTool instance to register
    """

    # Extract tool metadata
    tool_name = tool.name
    tool_description = tool.description
    input_schema = tool.input_schema

    # Create Pydantic fields for dynamic signature
    pydantic_fields = _create_pydantic_fields(input_schema)

    # Build parameter list for function signature
    param_names = list(pydantic_fields.keys())

    # Create the core execution logic as a closure (async)
    async def _execute_tool(kwargs_dict):
        """Execute the tool with provided arguments"""
        # Filter out None values
        filtered_kwargs = {k: v for k, v in kwargs_dict.items() if v is not None}
        _validate_json_schema(input_schema, filtered_kwargs)

        # Call original tool's execute method (now async)
        result = await tool.execute(filtered_kwargs)

        # Handle error responses
        if isinstance(result, dict) and result.get("isError"):
            error_text = result["content"][0].get("text", "Unknown error")
            raise ValueError(error_text)

        # Extract structured content from MCP response format.
        if isinstance(result, dict) and "content" in result:
            if len(result["content"]) > 0:
                first_content = result["content"][0]
                if first_content.get("type") == "json" and "json" in first_content:
                    return first_content["json"]
                return first_content.get("text", "")

        return str(result)

    # Create wrapper function with explicit parameters using inspect.Signature
    # This is the cleanest way to create explicit parameters without exec()
    def create_wrapper_with_signature():
        # Build parameters for the signature
        parameters = []
        for param_name in param_names:
            field_type, field_def = pydantic_fields[param_name]
            default_value = field_def.default

            # Create Parameter with proper default
            param = Parameter(
                param_name,
                Parameter.POSITIONAL_OR_KEYWORD,
                default=default_value,
                annotation=field_type
            )
            parameters.append(param)

        # Create the base wrapper function (async)
        async def tool_wrapper(**kwargs):
            """Wrapper function that will have its signature replaced"""
            return await _execute_tool(kwargs)

        # Replace the signature
        tool_wrapper.__signature__ = Signature(parameters)

        return tool_wrapper

    tool_wrapper = create_wrapper_with_signature()

    # Set function metadata for FastMCP
    tool_wrapper.__name__ = tool_name
    tool_wrapper.__doc__ = tool_description

    # Update function annotations for type checking
    annotations = {
        name: field_type for name, (field_type, _) in pydantic_fields.items()
    }
    annotations["return"] = Any
    tool_wrapper.__annotations__ = annotations

    # Register with FastMCP
    mcp.tool()(tool_wrapper)


def _iter_registration_specs(toggle_manager) -> Iterable[CapabilitySpec]:
    """
    Yield public capability specs that should be considered for registration.

    In read-only mode, specs marked ``read_only=False`` are removed before class
    loading so mutating tool modules are not imported at all.
    """
    read_only_mode = getattr(toggle_manager, "read_only_mode", False)
    for spec in CAPABILITY_SPECS.values():
        if read_only_mode and not spec.read_only:
            continue
        yield spec


def _load_tool_class(spec: CapabilitySpec) -> type[MCPTool]:
    """Load a tool class from its capability metadata."""
    module = import_module(spec.module_path)
    tool_class = getattr(module, spec.class_name)
    if not issubclass(tool_class, MCPTool):
        raise TypeError(f"{spec.class_path} is not an MCPTool subclass")
    return tool_class


def _build_tool_candidates(toggle_manager) -> list[MCPTool]:
    """Instantiate all registration candidates from the capability registry."""
    return [_load_tool_class(spec)() for spec in _iter_registration_specs(toggle_manager)]


def register_all_tools(mcp: FastMCP, toggle_manager, qradar_client) -> tuple:
    """
    Register enabled MCPTool instances with FastMCP.

    CapabilitySpec is the source of truth for public MCP tool exposure.
    EndpointSpec remains the internal QRadar REST API catalog used by
    compatibility checks and low-level implementation metadata. In read-only
    mode, mutating capability specs are filtered before import, so mutating
    modules are not loaded as registration candidates.

    Args:
        mcp: FastMCP server instance
        toggle_manager: FeatureToggleManager for filtering tools
        qradar_client: QRadarRestClient instance to use for all tools

    Returns:
        tuple: (list of registered tools, list of skipped tools)
    """
    MCPTool.set_qradar_client(qradar_client)
    tools = _build_tool_candidates(toggle_manager)

    # Filter tools based on feature toggles
    registered_tools = []
    skipped_tools = []

    for tool in tools:
        if toggle_manager.is_tool_enabled(tool):
            register_mcp_tool_with_fastmcp(mcp, tool)
            registered_tools.append(tool)
        else:
            skipped_tools.append(tool)

    return (registered_tools, skipped_tools)
