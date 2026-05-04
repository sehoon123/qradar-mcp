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
Update Offense Tool

Updates offense properties in QRadar SIEM (status, assignment, follow-up, protected).
"""

from typing import Dict, Any, Optional
import json
from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.validators import validate_offense_id


class UpdateOffenseTool(MCPTool):
    """Tool for updating QRadar offense properties."""

    @property
    def name(self) -> str:
        return "update_offense"

    @property
    def description(self) -> str:
        return """Update offense properties in QRadar SIEM.

Use cases:
  - Close an offense: status="CLOSED", closing_reason_id=1
  - Assign to analyst: assigned_to="admin"
  - Mark for follow-up: follow_up=true
  - Protect offense: protected=true
  - Hide offense: status="HIDDEN"

Note: When closing an offense (status="CLOSED"), you must provide a valid closing_reason_id."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .integer("offense_id")
                .description("The ID of the offense to update")
                .minimum(0)
                .required()
            .string("status")
                .description("New status: OPEN, HIDDEN, or CLOSED. When CLOSED, closing_reason_id is required")
                .enum(["OPEN", "HIDDEN", "CLOSED"])
            .string("assigned_to")
                .description("Username to assign the offense to")
            .integer("closing_reason_id")
                .description("Closing reason ID (required when status=CLOSED)")
                .minimum(1)
            .boolean("follow_up")
                .description("Set to true to mark offense for follow-up")
            .boolean("protected")
                .description("Set to true to protect the offense from being closed")
            .string("fields")
                .description("Comma-separated list of fields to return in response")
            .build())

    @property
    def http_verb(self) -> str:
        return "POST"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the update_offense tool.

        Args:
            arguments: Dictionary containing offense_id and optional update parameters

        Returns:
            MCP response with updated offense data or error
        """
        # Validate and extract parameters
        validation_result = self._validate_arguments(arguments)
        if validation_result:
            return validation_result

        offense_id = arguments["offense_id"]
        params = self._build_request_params(arguments)

        # Make API request
        updated_offense = await self._update_offense(offense_id, params)

        # Return formatted response
        return self.create_success_response(json.dumps(updated_offense, indent=2))

    def _validate_arguments(self, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate input arguments. Returns error response if invalid, None if valid."""
        offense_id = arguments.get("offense_id")

        if offense_id is None:
            return self.create_error_response("offense_id is required")

        if not validate_offense_id(offense_id):
            return self.create_error_response(f"Invalid offense_id: {offense_id}")

        # Validate that at least one update parameter is provided
        update_params = ["status", "assigned_to", "closing_reason_id", "follow_up", "protected"]
        if not any(arguments.get(param) is not None for param in update_params):
            return self.create_error_response(
                "At least one update parameter must be provided: status, assigned_to, "
                "closing_reason_id, follow_up, or protected"
            )

        # Validate that closing_reason_id is provided when status is CLOSED
        status = arguments.get("status")
        closing_reason_id = arguments.get("closing_reason_id")

        if status == "CLOSED" and closing_reason_id is None:
            return self.create_error_response(
                "closing_reason_id is required when status is CLOSED"
            )

        return None

    def _build_request_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for the API request."""
        params = {}

        # Add optional parameters if provided
        if arguments.get("status") is not None:
            params["status"] = arguments["status"]

        if arguments.get("assigned_to") is not None:
            params["assigned_to"] = arguments["assigned_to"]

        if arguments.get("closing_reason_id") is not None:
            params["closing_reason_id"] = arguments["closing_reason_id"]

        if arguments.get("follow_up") is not None:
            params["follow_up"] = arguments["follow_up"]

        if arguments.get("protected") is not None:
            params["protected"] = arguments["protected"]

        if arguments.get("fields") is not None:
            params["fields"] = arguments["fields"]

        return params

    async def _update_offense(self, offense_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the offense via QRadar API.

        Args:
            offense_id: The offense ID to update
            params: Query parameters for the update

        Returns:
            Updated offense data as dictionary

        Raises:
            RuntimeError: If the API request fails
        """
        api_path = f"siem/offenses/{offense_id}"


        response = await self.client.post(api_path=api_path, params=params)
        response.raise_for_status()
        return response.json()
