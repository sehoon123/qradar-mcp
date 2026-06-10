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
List Regex Custom Properties Tool

Retrieves regex-based custom event properties. These define extra fields that
QRadar extracts from event payloads and that can be referenced in AQL queries.
"""

from typing import Dict, Any
import json
from qradar_mcp.tools.base import MCPTool
from qradar_mcp.tools.schema import schema
from qradar_mcp.utils.parameters import (
    build_query_params,
    parse_range_from_limit_offset,
    build_headers
)


class ListRegexPropertiesTool(MCPTool):
    """Tool for listing QRadar regex-based custom event properties."""

    @property
    def name(self) -> str:
        return "list_regex_properties"

    @property
    def description(self) -> str:
        return """List regex-based custom event properties from QRadar with optional filtering, sorting, and pagination.

Regex custom properties are user-defined fields that QRadar extracts from event
payloads using regular expressions. Their names can be referenced directly in AQL
queries (e.g. SELECT "Username" FROM events ...). Use this to discover which custom
fields are available before building an Ariel search.

Examples:
  - List all regex properties: (no parameters)
  - Find by name: filter="name LIKE '%Username%'"
  - Get first 100: limit=100, offset=0"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return (schema()
            .string("filter")
                .description('Optional AQL-style filter expression. Examples: "name LIKE \'%Username%\'", "property_type=\'STRING\'"')
            .string("fields")
                .description('Comma-separated list of fields to include. Examples: "id,name,property_type,description"')
            .string("sort")
                .description('Optional sort expression. Use +field for ascending, -field for descending. Examples: "+name"')
            .integer("limit")
                .description("Maximum number of properties to return (default: 100, max: 10000)")
                .minimum(1)
                .maximum(10000)
                .default(100)
            .integer("offset")
                .description("Number of properties to skip for pagination (default: 0)")
                .minimum(0)
                .default(0)
            .boolean("format_output")
                .description("Format output as human-readable text (default: false)")
                .default(False)
            .build())

    @property
    def http_verb(self) -> str:
        return "GET"

    async def _execute_impl(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        filter_expr = arguments.get("filter")
        fields_str = arguments.get("fields")
        sort_expr = arguments.get("sort")
        limit = arguments.get("limit", 100)
        offset = arguments.get("offset", 0)

        fields_list = [f.strip() for f in fields_str.split(",")] if fields_str else None
        params = build_query_params(
            filter_expr=filter_expr,
            sort_fields=[sort_expr] if sort_expr else None,
            fields=fields_list
        )

        start, end = parse_range_from_limit_offset(limit, offset)
        headers = build_headers(start=start, end=end)

        response = await self.client.get(
            '/config/event_sources/custom_properties/regex_properties',
            params=params if params else None,
            headers=headers
        )
        response.raise_for_status()
        properties = response.json()

        if arguments.get("format_output", False):
            return self.create_success_response(self._format_properties(properties))

        return self.create_success_response(json.dumps(properties, indent=2))

    def _format_properties(self, properties: Any) -> str:
        if not properties:
            return "No regex custom properties found"

        lines = [f"Found {len(properties)} regex custom property(ies)\n", "=" * 80]
        for prop in properties:
            lines.append(
                f"[{prop.get('id', 'N/A')}] {prop.get('name', 'N/A')} "
                f"(type: {prop.get('property_type', 'N/A')})"
            )
            description = prop.get('description')
            if description:
                lines.append(f"  Description: {description}")
        return "\n".join(lines)
