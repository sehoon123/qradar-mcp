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
Tests for FastMCP Adapter

Tests the adapter pattern that bridges MCPTool implementations with FastMCP.
"""

from unittest.mock import Mock, patch, AsyncMock

import pytest
import httpx
from qradar_mcp.tools.capability_registry import CAPABILITY_SPECS
from qradar_mcp.tools.fastmcp_adapter import (
    _json_schema_type_to_python,
    _create_pydantic_fields,
    register_mcp_tool_with_fastmcp
)
from qradar_mcp.tools.offense.get_offense import GetOffenseTool
from qradar_mcp.tools.ariel.validate_aql import ValidateAQLTool
from qradar_mcp.tools.system.get_system_info import GetSystemInfoTool


class TestJsonSchemaConversion:
    """Test JSON Schema to Python type conversion."""

    def test_string_type(self):
        """Test string type conversion."""
        assert _json_schema_type_to_python("string") == str

    def test_integer_type(self):
        """Test integer type conversion."""
        assert _json_schema_type_to_python("integer") == int

    def test_number_type(self):
        """Test number type conversion."""
        assert _json_schema_type_to_python("number") == float

    def test_boolean_type(self):
        """Test boolean type conversion."""
        assert _json_schema_type_to_python("boolean") == bool

    def test_array_type(self):
        """Test array type conversion."""
        assert _json_schema_type_to_python("array") == list

    def test_object_type(self):
        """Test object type conversion."""
        assert _json_schema_type_to_python("object") == dict

    def test_unknown_type_defaults_to_string(self):
        """Test unknown type defaults to string."""
        assert _json_schema_type_to_python("unknown") == str


class TestPydanticFieldCreation:
    """Test Pydantic field creation from JSON Schema."""

    def test_required_field(self):
        """Test required field creation."""
        schema = {
            "properties": {
                "offense_id": {
                    "type": "integer",
                    "description": "The offense ID"
                }
            },
            "required": ["offense_id"]
        }

        fields = _create_pydantic_fields(schema)
        assert "offense_id" in fields
        field_type, field_def = fields["offense_id"]
        assert field_type == int
        assert field_def.description == "The offense ID"

    def test_optional_field(self):
        """Test optional field creation."""
        schema = {
            "properties": {
                "fields": {
                    "type": "string",
                    "description": "Optional fields"
                }
            },
            "required": []
        }

        fields = _create_pydantic_fields(schema)
        assert "fields" in fields
        # Optional fields should have Optional type annotation
        assert "fields" in fields

    def test_field_with_constraints(self):
        """Test field with numeric constraints."""
        schema = {
            "properties": {
                "offense_id": {
                    "type": "integer",
                    "description": "The offense ID",
                    "minimum": 0,
                    "maximum": 999999
                }
            },
            "required": ["offense_id"]
        }

        fields = _create_pydantic_fields(schema)
        field_type, field_def = fields["offense_id"]
        # Pydantic FieldInfo stores constraints in metadata
        assert field_def.metadata is not None or field_def.ge == 0

    def test_field_with_string_constraints(self):
        """Test field with string length constraints."""
        schema = {
            "properties": {
                "query": {
                    "type": "string",
                    "description": "AQL query",
                    "minLength": 1,
                    "maxLength": 10000
                }
            },
            "required": ["query"]
        }

        fields = _create_pydantic_fields(schema)
        field_type, field_def = fields["query"]
        # Pydantic FieldInfo stores constraints in metadata
        assert field_def.metadata is not None or field_def.min_length == 1


class TestToolSchemaExtraction:
    """Test schema extraction from MCPTool instances."""

    def test_get_offense_tool_schema(self):
        """Test GetOffenseTool schema extraction."""
        tool = GetOffenseTool()

        assert tool.name == "get_offense"
        assert "offense" in tool.description.lower()

        schema = tool.input_schema
        assert "properties" in schema
        assert "offense_id" in schema["properties"]
        assert schema["properties"]["offense_id"]["type"] == "integer"
        assert "offense_id" in schema["required"]

    def test_validate_aql_tool_schema(self):
        """Test ValidateAQLTool schema extraction."""
        tool = ValidateAQLTool()

        assert tool.name == "validate_aql"
        assert "aql" in tool.description.lower()

        schema = tool.input_schema
        assert "properties" in schema
        assert "query_expression" in schema["properties"]
        assert schema["properties"]["query_expression"]["type"] == "string"
        assert "query_expression" in schema["required"]

    def test_get_system_info_tool_schema(self):
        """Test GetSystemInfoTool schema extraction."""
        tool = GetSystemInfoTool()

        assert tool.name == "get_system_info"
        assert "system" in tool.description.lower()

        schema = tool.input_schema
        assert "properties" in schema
        # This tool has optional parameters
        assert "fields" in schema["properties"]


class TestAdapterRegistration:
    """Test adapter registration with FastMCP."""

    @patch('qradar_mcp.tools.fastmcp_adapter.FastMCP')
    def test_register_tool_with_fastmcp(self, mock_fastmcp):
        """Test registering a tool with FastMCP."""
        # Create mock FastMCP instance
        mcp = Mock()
        mock_tool_decorator = Mock()
        mcp.tool.return_value = mock_tool_decorator

        # Create a tool instance
        tool = GetOffenseTool()

        # Register the tool
        register_mcp_tool_with_fastmcp(mcp, tool)

        # Verify tool decorator was called
        mcp.tool.assert_called_once()
        mock_tool_decorator.assert_called_once()

    def test_tool_wrapper_preserves_name(self):
        """Test that tool wrapper preserves the tool name."""
        tool = GetOffenseTool()

        # The wrapper function should have the same name as the tool
        assert tool.name == "get_offense"

    def test_tool_wrapper_preserves_description(self):
        """Test that tool wrapper preserves the tool description."""
        tool = GetOffenseTool()

        # The wrapper function should have the same description
        assert "offense" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_json_content_returns_structured_data(self):
        """Test JSON MCP content is returned as structured data through the wrapper."""

        class JsonTool(GetOffenseTool):
            @property
            def name(self):
                return "json_tool"

            @property
            def input_schema(self):
                return {"type": "object", "properties": {}}

            async def _execute_impl(self, arguments):
                return self.create_json_response({"ok": True, "items": [1, 2]})

        registered = []
        mcp = Mock()
        mcp.tool.return_value = lambda func: registered.append(func) or func

        register_mcp_tool_with_fastmcp(mcp, JsonTool())

        assert await registered[0]() == {"ok": True, "items": [1, 2]}

    @pytest.mark.asyncio
    async def test_wrapper_enforces_original_json_schema_constraints(self):
        """Test enum, pattern, and array item constraints are enforced at runtime."""

        class StrictSchemaTool(GetOffenseTool):
            @property
            def name(self):
                return "strict_schema_tool"

            @property
            def input_schema(self):
                return {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string", "enum": ["events", "flows"]},
                        "ip": {"type": "string", "pattern": r"^\d+\.\d+\.\d+\.\d+$"},
                        "fields": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["mode", "ip"],
                }

            async def _execute_impl(self, arguments):
                return self.create_json_response({"arguments": arguments})

        registered = []
        mcp = Mock()
        mcp.tool.return_value = lambda func: registered.append(func) or func

        register_mcp_tool_with_fastmcp(mcp, StrictSchemaTool())

        valid = await registered[0](mode="events", ip="10.0.0.1", fields=["qid"])
        assert valid["arguments"]["mode"] == "events"

        with pytest.raises(ValueError, match="Invalid tool arguments"):
            await registered[0](mode="offenses", ip="10.0.0.1")

        with pytest.raises(ValueError, match="Invalid tool arguments"):
            await registered[0](mode="events", ip="not-an-ip")

        with pytest.raises(ValueError, match="Invalid tool arguments"):
            await registered[0](mode="events", ip="10.0.0.1", fields=["qid", 3])


class TestToolExecution:
    """Test tool execution through the adapter."""

    @pytest.mark.asyncio
    async def test_get_offense_execution(self):
        """Test GetOffenseTool execution."""
        # Mock the REST client
        mock_client = AsyncMock()
        mock_response = httpx.Response(200, json={"id": 123, "description": "Test offense"}, request=httpx.Request("GET", "http://test"))
        mock_client.get = AsyncMock(return_value=mock_response)

        # Create and execute tool with mocked client
        tool = GetOffenseTool()
        tool.client = mock_client
        result = await tool.execute({"offense_id": 123})

        # Verify result
        assert "content" in result
        assert len(result["content"]) > 0
        assert "text" in result["content"][0]
        assert "123" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_validate_aql_execution(self):
        """Test ValidateAQLTool execution."""
        # Mock the REST client
        mock_client = AsyncMock()
        mock_response = httpx.Response(200, json={"warnings": []}, request=httpx.Request("POST", "http://test"))
        mock_client.post = AsyncMock(return_value=mock_response)

        # Create and execute tool with mocked client
        tool = ValidateAQLTool()
        tool.client = mock_client
        result = await tool.execute({"query_expression": "SELECT * FROM events"})

        # Verify result
        assert "content" in result
        assert len(result["content"]) > 0
        assert "text" in result["content"][0]
        assert "valid" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool error handling."""
        tool = GetOffenseTool()

        # Execute with missing required parameter
        result = await tool.execute({})

        # Verify error response
        assert "content" in result
        assert result.get("isError") is True
        assert "offense_id" in result["content"][0]["text"].lower()


class TestSchemaValidation:
    """Test schema validation for different parameter types."""

    def test_integer_parameter_validation(self):
        """Test integer parameter schema."""
        tool = GetOffenseTool()
        schema = tool.input_schema

        offense_id_schema = schema["properties"]["offense_id"]
        assert offense_id_schema["type"] == "integer"
        assert "minimum" in offense_id_schema
        assert offense_id_schema["minimum"] == 1

    def test_string_parameter_validation(self):
        """Test string parameter schema."""
        tool = ValidateAQLTool()
        schema = tool.input_schema

        query_schema = schema["properties"]["query_expression"]
        assert query_schema["type"] == "string"
        assert "description" in query_schema

    def test_optional_parameter_validation(self):
        """Test optional parameter schema."""
        tool = GetSystemInfoTool()
        schema = tool.input_schema

        # fields parameter is optional
        assert "fields" in schema["properties"]
        assert "fields" not in schema.get("required", [])


class TestRegisterAllTools:
    """Test register_all_tools function."""

    @pytest.fixture
    def all_enabled_config(self, tmp_path):
        """Create a config file with all toggles enabled."""
        from qradar_mcp.utils.feature_toggle_manager import FeatureToggleManager
        config_file = tmp_path / "feature_toggles.json"
        config_file.write_text("""{
            "verb_toggles": {
                "GET": true,
                "POST": true,
                "DELETE": true
            },
            "group_toggles": {
                "offense": true,
                "ariel": true,
                "reference_data": true,
                "asset": true,
                "log_source": true,
                "analytics": true,
                "system": true,
                "config": true,
                "data_classification": true,
                "health_data": true,
                "help": true,
                "services": true,
                "composite": true,
                "forensics": true,
                "qvm": true
            },
            "per_tool_toggles": {}
        }""")
        return FeatureToggleManager(str(config_file))

    @pytest.fixture
    def some_disabled_config(self, tmp_path):
        """Create a config file with some tools disabled."""
        from qradar_mcp.utils.feature_toggle_manager import FeatureToggleManager
        config_file = tmp_path / "feature_toggles.json"
        config_file.write_text("""{
            "verb_toggles": {
                "GET": true,
                "POST": true,
                "DELETE": false
            },
            "group_toggles": {
                "offense": true,
                "ariel": true,
                "reference_data": true,
                "asset": true,
                "log_source": true,
                "analytics": true,
                "system": true,
                "config": true,
                "data_classification": true,
                "health_data": true,
                "help": true,
                "services": true,
                "composite": true,
                "forensics": true,
                "qvm": false
            },
            "per_tool_toggles": {
                "QradarDoctorTool": false
            }
        }""")
        return FeatureToggleManager(str(config_file))

    def test_all_tools_registered_when_all_enabled(self, all_enabled_config):
        """Test that all public capabilities are registered when enabled."""
        from qradar_mcp.tools.fastmcp_adapter import register_all_tools

        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda func: func)
        mock_qradar_client = AsyncMock()

        registered_tools, skipped_tools = register_all_tools(mock_mcp, all_enabled_config, mock_qradar_client)

        assert len(registered_tools) == len(CAPABILITY_SPECS)
        assert len(skipped_tools) == 0

    def test_returns_tuple(self, all_enabled_config):
        """Test that register_all_tools returns a tuple of (registered, skipped)."""
        from qradar_mcp.tools.fastmcp_adapter import register_all_tools

        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda func: func)
        mock_qradar_client = AsyncMock()

        result = register_all_tools(mock_mcp, all_enabled_config, mock_qradar_client)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)

    def test_some_tools_skipped_when_disabled(self, some_disabled_config):
        """Test that disabled tools are skipped during registration."""
        from qradar_mcp.tools.fastmcp_adapter import register_all_tools

        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda func: func)
        mock_qradar_client = AsyncMock()

        registered_tools, skipped_tools = register_all_tools(mock_mcp, some_disabled_config, mock_qradar_client)

        # Should have some registered and some skipped
        assert len(registered_tools) > 0
        assert len(skipped_tools) > 0
        assert len(registered_tools) + len(skipped_tools) == len(CAPABILITY_SPECS)

    def test_public_capabilities_do_not_include_delete_tools(self, all_enabled_config):
        """Test that public capability registration excludes DELETE endpoint wrappers."""
        from qradar_mcp.tools.fastmcp_adapter import register_all_tools

        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda func: func)
        mock_qradar_client = AsyncMock()

        registered_tools, skipped_tools = register_all_tools(mock_mcp, all_enabled_config, mock_qradar_client)

        assert skipped_tools == []
        assert all(tool.http_verb != "DELETE" for tool in registered_tools)

    def test_disabled_group_skips_public_capabilities(self, tmp_path):
        """Test that group toggles apply to public capabilities."""
        from qradar_mcp.utils.feature_toggle_manager import FeatureToggleManager
        from qradar_mcp.tools.fastmcp_adapter import register_all_tools

        config_file = tmp_path / "feature_toggles.json"
        config_file.write_text("""{
            "verb_toggles": {
                "GET": true,
                "POST": true,
                "DELETE": true
            },
            "group_toggles": {
                "offense": true,
                "ariel": true,
                "reference_data": true,
                "asset": true,
                "log_source": true,
                "analytics": true,
                "system": true,
                "config": true,
                "data_classification": true,
                "health_data": true,
                "help": false,
                "services": true,
                "composite": true,
                "forensics": true,
                "qvm": true
            },
            "per_tool_toggles": {}
        }""")
        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda func: func)
        mock_qradar_client = AsyncMock()

        registered_tools, skipped_tools = register_all_tools(
            mock_mcp,
            FeatureToggleManager(str(config_file)),
            mock_qradar_client,
        )

        assert all(tool.tool_group != "help" for tool in registered_tools)
        assert {type(tool).__name__ for tool in skipped_tools if tool.tool_group == "help"} == {
            "DiscoverQradarEndpointsTool",
            "QradarDoctorTool",
        }

    def test_per_tool_override_skips_specific_tool(self, some_disabled_config):
        """Test that per-tool override disables specific tool."""
        from qradar_mcp.tools.fastmcp_adapter import register_all_tools

        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda func: func)
        mock_qradar_client = AsyncMock()

        registered_tools, skipped_tools = register_all_tools(mock_mcp, some_disabled_config, mock_qradar_client)

        # Check that qradar_doctor is not registered
        registered_names = [t.name for t in registered_tools]
        assert "qradar_doctor" not in registered_names

        # Check that qradar_doctor is in skipped list
        skipped_names = [t.name for t in skipped_tools]
        assert "qradar_doctor" in skipped_names

    def test_no_duplicate_tools(self, some_disabled_config):
        """Test that no tool appears in both registered and skipped lists."""
        from qradar_mcp.tools.fastmcp_adapter import register_all_tools

        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda func: func)
        mock_qradar_client = AsyncMock()

        registered_tools, skipped_tools = register_all_tools(mock_mcp, some_disabled_config, mock_qradar_client)

        registered_names = set(t.name for t in registered_tools)
        skipped_names = set(t.name for t in skipped_tools)

        # No overlap between registered and skipped
        assert len(registered_names & skipped_names) == 0

        # All public capabilities accounted for
        assert len(registered_names | skipped_names) == len(CAPABILITY_SPECS)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
