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
Validate AQL Tool

Validates AQL query syntax using QRadar's validation endpoint.
"""

from typing import Dict, Any

from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema


class ValidateAQLTool(MCPTool):
    """Tool for validating AQL query syntax."""

    @property
    def name(self) -> str:
        return "validate_aql"

    @property
    def description(self) -> str:
        return """Validate AQL (Ariel Query Language) query syntax before execution.

REQUIRED WORKFLOW: Always use this tool to validate AQL queries BEFORE using create_ariel_search.

Use cases:
  - Verify AQL syntax is correct before creating a search
  - Check for common AQL errors and get helpful error messages
  - Validate queries generated from natural language
  - Ensure queries will execute successfully

This tool uses QRadar's built-in AQL validator to check query syntax without executing the query.
Validation prevents wasted searches and provides helpful error messages with suggestions."""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("query_expression")
                .description("The AQL query to validate (e.g., 'SELECT sourceip FROM events LAST 1 HOURS')")
                .required()
            .build())

    @property
    def http_verb(self) -> str:
        return "POST"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an AQL query.

        Args:
            arguments: Dict containing:
                - query_expression: The AQL query to validate

        Returns:
            Dict with validation results
        """
        query_expression = arguments.get('query_expression')

        if not query_expression:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: query_expression is required"
                    }
                ],
                "isError": True
            }


        # Call QRadar AQL validation endpoint with query parameters
        response = await self.client.post(
            'ariel/validators/aql',
            params={'query_expression': query_expression}
        )

        if response.status_code == 200:
            # Query is valid
            result = response.json()

            # Check if there are any warnings
            warnings = result.get('warnings', [])
            warning_text = ""
            if warnings:
                warning_text = "\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"✓ AQL query is valid{warning_text}\n\nQuery: {query_expression}"
                    }
                ]
            }

        if response.status_code == 422:
            # Query has validation errors
            error_data = response.json()
            error_message = error_data.get('message', 'Unknown validation error')

            # Extract detailed error information if available
            details = error_data.get('details', {})
            error_text = f"✗ AQL validation failed:\n\n{error_message}"

            if details:
                error_text += f"\n\nDetails: {details}"

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"{error_text}\n\nQuery: {query_expression}"
                    }
                ],
                "isError": True
            }

        # Unexpected error
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error validating AQL query: {response.status_code} - {response.text}"
                }
                ],
                "isError": True
            }
