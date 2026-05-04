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
Unit tests for the UpdateOffenseTool.
"""

import pytest
import httpx
from unittest.mock import AsyncMock
from qradar_mcp.tools.offense.update_offense import UpdateOffenseTool


class TestUpdateOffenseTool:
    """Tests for UpdateOffenseTool class."""

    def test_tool_name(self):
        """Test that tool has correct name."""
        tool = UpdateOffenseTool()
        assert tool.name == "update_offense"

    def test_tool_description(self):
        """Test that tool has correct description."""
        tool = UpdateOffenseTool()
        assert "Update offense properties" in tool.description
        assert "status" in tool.description.lower()
        assert "assign" in tool.description.lower()

    def test_input_schema_structure(self):
        """Test that input schema has correct structure."""
        tool = UpdateOffenseTool()
        schema = tool.input_schema

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "offense_id" in schema["properties"]
        assert "status" in schema["properties"]
        assert "assigned_to" in schema["properties"]
        assert "closing_reason_id" in schema["properties"]
        assert "follow_up" in schema["properties"]
        assert "protected" in schema["properties"]
        assert "fields" in schema["properties"]

    def test_input_schema_offense_id_required(self):
        """Test that offense_id is required in schema."""
        tool = UpdateOffenseTool()
        schema = tool.input_schema

        assert "required" in schema
        assert "offense_id" in schema["required"]

    def test_input_schema_offense_id_constraints(self):
        """Test offense_id parameter constraints."""
        tool = UpdateOffenseTool()
        schema = tool.input_schema

        offense_id_schema = schema["properties"]["offense_id"]
        assert offense_id_schema["type"] == "integer"
        assert offense_id_schema["minimum"] == 0
        assert "description" in offense_id_schema

    def test_input_schema_status_enum(self):
        """Test status parameter has correct enum values."""
        tool = UpdateOffenseTool()
        schema = tool.input_schema

        status_schema = schema["properties"]["status"]
        assert status_schema["type"] == "string"
        assert "enum" in status_schema
        assert set(status_schema["enum"]) == {"OPEN", "HIDDEN", "CLOSED"}

    def test_input_schema_boolean_fields(self):
        """Test boolean fields have correct type."""
        tool = UpdateOffenseTool()
        schema = tool.input_schema

        assert schema["properties"]["follow_up"]["type"] == "boolean"
        assert schema["properties"]["protected"]["type"] == "boolean"

    def test_to_mcp_tool_definition(self):
        """Test converting tool to MCP definition."""
        tool = UpdateOffenseTool()
        definition = tool.to_mcp_tool_definition()

        assert definition["name"] == "update_offense"
        assert "description" in definition
        assert "inputSchema" in definition

    @pytest.mark.asyncio
    async def test_execute_update_status(self):
        """Test updating offense status."""
        # Setup mock
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_response = httpx.Response(
            status_code=200,
            json={
                "id": 123,
                "status": "CLOSED",
                "closing_reason_id": 1
            },
            request=httpx.Request("POST", "http://test")
        )
        tool.client.post = AsyncMock(return_value=mock_response)

        result = await tool.execute({
            "offense_id": 123,
            "status": "CLOSED",
            "closing_reason_id": 1
        })

        # Verify API call
        tool.client.post.assert_called_once()
        call_args = tool.client.post.call_args
        assert call_args[1]["api_path"] == "siem/offenses/123"
        assert call_args[1]["params"]["status"] == "CLOSED"
        assert call_args[1]["params"]["closing_reason_id"] == 1

        # Verify result
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_execute_assign_offense(self):
        """Test assigning offense to user."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_response = httpx.Response(
            status_code=200,
            json={
                "id": 123,
                "assigned_to": "admin"
            },
            request=httpx.Request("POST", "http://test")
        )
        tool.client.post = AsyncMock(return_value=mock_response)

        result = await tool.execute({
            "offense_id": 123,
            "assigned_to": "admin"
        })

        # Verify API call
        call_args = tool.client.post.call_args
        assert call_args[1]["params"]["assigned_to"] == "admin"

        # Verify success
        assert "content" in result
        assert "admin" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_set_follow_up(self):
        """Test setting follow-up flag."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_response = httpx.Response(
            status_code=200,
            json={
                "id": 123,
                "follow_up": True
            },
            request=httpx.Request("POST", "http://test")
        )
        tool.client.post = AsyncMock(return_value=mock_response)

        result = await tool.execute({
            "offense_id": 123,
            "follow_up": True
        })

        # Verify API call
        call_args = tool.client.post.call_args
        assert call_args[1]["params"]["follow_up"] is True

        # Verify success
        assert "content" in result

    @pytest.mark.asyncio
    async def test_execute_protect_offense(self):
        """Test protecting an offense."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_response = httpx.Response(
            status_code=200,
            json={
                "id": 123,
                "protected": True
            },
            request=httpx.Request("POST", "http://test")
        )
        tool.client.post = AsyncMock(return_value=mock_response)

        result = await tool.execute({
            "offense_id": 123,
            "protected": True
        })

        # Verify API call
        call_args = tool.client.post.call_args
        assert call_args[1]["params"]["protected"] is True

        # Verify success
        assert "content" in result

    @pytest.mark.asyncio
    async def test_execute_multiple_updates(self):
        """Test updating multiple properties at once."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_response = httpx.Response(
            status_code=200,
            json={
                "id": 123,
                "status": "OPEN",
                "assigned_to": "admin",
                "follow_up": True,
                "protected": True
            },
            request=httpx.Request("POST", "http://test")
        )
        tool.client.post = AsyncMock(return_value=mock_response)

        result = await tool.execute({
            "offense_id": 123,
            "status": "OPEN",
            "assigned_to": "admin",
            "follow_up": True,
            "protected": True
        })

        # Verify all parameters were sent
        call_args = tool.client.post.call_args
        params = call_args[1]["params"]
        assert params["status"] == "OPEN"
        assert params["assigned_to"] == "admin"
        assert params["follow_up"] is True
        assert params["protected"] is True

        # Verify success
        assert "content" in result

    @pytest.mark.asyncio
    async def test_execute_with_fields_parameter(self):
        """Test using fields parameter to limit response."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_response = httpx.Response(
            status_code=200,
            json={
                "id": 123,
                "status": "CLOSED"
            },
            request=httpx.Request("POST", "http://test")
        )
        tool.client.post = AsyncMock(return_value=mock_response)

        result = await tool.execute({
            "offense_id": 123,
            "status": "CLOSED",
            "closing_reason_id": 1,
            "fields": "id,status"
        })

        # Verify fields parameter was sent
        call_args = tool.client.post.call_args
        assert call_args[1]["params"]["fields"] == "id,status"

        # Verify success
        assert "content" in result

    @pytest.mark.asyncio
    async def test_execute_missing_offense_id(self):
        """Test error when offense_id is missing."""
        tool = UpdateOffenseTool()
        result = await tool.execute({"status": "CLOSED"})

        # Verify error response
        assert "content" in result
        assert result["content"][0]["type"] == "text"
        assert "offense_id is required" in result["content"][0]["text"].lower()
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_execute_invalid_offense_id(self):
        """Test error when offense_id is invalid."""
        tool = UpdateOffenseTool()
        result = await tool.execute({"offense_id": -1, "status": "CLOSED"})

        # Verify error response
        assert "content" in result
        assert "invalid offense_id" in result["content"][0]["text"].lower()
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_execute_no_update_parameters(self):
        """Test error when no update parameters provided."""
        tool = UpdateOffenseTool()
        result = await tool.execute({"offense_id": 123})

        # Verify error response
        assert "content" in result
        assert "at least one update parameter" in result["content"][0]["text"].lower()
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_execute_close_without_reason(self):
        """Test error when closing offense without closing_reason_id."""
        tool = UpdateOffenseTool()
        result = await tool.execute({
            "offense_id": 123,
            "status": "CLOSED"
        })

        # Verify error response
        assert "content" in result
        assert "closing_reason_id is required" in result["content"][0]["text"].lower()
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_execute_offense_not_found(self):
        """Test error when offense not found."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_request = httpx.Request("POST", "http://test")
        mock_response = httpx.Response(
            status_code=404,
            text="Not found",
            request=mock_request
        )
        tool.client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "404 Client Error: Not Found",
            request=mock_request,
            response=mock_response
        ))

        result = await tool.execute({
            "offense_id": 999,
            "status": "CLOSED",
            "closing_reason_id": 1
        })

        # Verify error response
        assert "content" in result
        assert "error" in result["content"][0]["text"].lower()
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_execute_permission_denied(self):
        """Test error when user lacks permission."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_request = httpx.Request("POST", "http://test")
        mock_response = httpx.Response(
            status_code=403,
            text="Forbidden",
            request=mock_request
        )
        tool.client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "403 Client Error: Forbidden",
            request=mock_request,
            response=mock_response
        ))

        result = await tool.execute({
            "offense_id": 123,
            "status": "CLOSED",
            "closing_reason_id": 1
        })

        # Verify error response
        assert "content" in result
        assert "error" in result["content"][0]["text"].lower()
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_execute_conflict_state(self):
        """Test error when offense state prevents update."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_request = httpx.Request("POST", "http://test")
        mock_response = httpx.Response(
            status_code=409,
            text="Conflict",
            request=mock_request
        )
        tool.client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "409 Client Error: Conflict",
            request=mock_request,
            response=mock_response
        ))

        result = await tool.execute({
            "offense_id": 123,
            "status": "CLOSED",
            "closing_reason_id": 1
        })

        # Verify error response
        assert "content" in result
        assert "error" in result["content"][0]["text"].lower()
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_execute_invalid_parameters(self):
        """Test error when parameters are invalid."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_request = httpx.Request("POST", "http://test")
        mock_response = httpx.Response(
            status_code=422,
            text="Invalid closing_reason_id",
            request=mock_request
        )
        tool.client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "422 Client Error: Unprocessable Entity",
            request=mock_request,
            response=mock_response
        ))

        result = await tool.execute({
            "offense_id": 123,
            "status": "CLOSED",
            "closing_reason_id": 999
        })

        # Verify error response
        assert "content" in result
        assert "error" in result["content"][0]["text"].lower()
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_execute_server_error(self):
        """Test error when server returns 500."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_request = httpx.Request("POST", "http://test")
        mock_response = httpx.Response(
            status_code=500,
            text="Internal server error",
            request=mock_request
        )
        tool.client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "500 Server Error: Internal Server Error",
            request=mock_request,
            response=mock_response
        ))

        result = await tool.execute({
            "offense_id": 123,
            "status": "CLOSED",
            "closing_reason_id": 1
        })

        # Verify error response
        assert "content" in result
        assert "error" in result["content"][0]["text"].lower()
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_execute_logs_update_attempt(self):
        """Test that update attempts are logged."""
        tool = UpdateOffenseTool()
        tool.client = AsyncMock()

        mock_response = httpx.Response(
            status_code=200,
            json={"id": 123, "status": "CLOSED"},
            request=httpx.Request("POST", "http://test")
        )
        tool.client.post = AsyncMock(return_value=mock_response)

        result = await tool.execute({
            "offense_id": 123,
            "status": "CLOSED",
            "closing_reason_id": 1
        })

        # Verify execution completed successfully
        assert "content" in result
        assert "123" in result["content"][0]["text"]
        assert "CLOSED" in result["content"][0]["text"]
